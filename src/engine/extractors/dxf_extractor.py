# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import math
import os
import re
import hashlib
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class DXFExtractor(BaseExtractor):
    """Deterministic DXF evidence extractor.

    Extracts drawing metadata, layer inventory, entity geometry, block
    definitions and insertions, and XREF references from a DXF file using
    ezdxf only. No semantic interpretation is performed; all values are
    surfaced as raw deterministic evidence.
    """

    maturity = "VERIFIED"

    # Deterministic entity-types that carry geometry attributes.
    GEOMETRY_TYPES = frozenset({
        "LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE",
        "TEXT", "MTEXT", "INSERT", "DIMENSION",
        "XLINE", "RAY", "SOLID", "TRACE", "POINT",
        "ELLIPSE", "SPLINE", "HELIX", "WIPEOUT",
        "MULTILEADER", "LEADER", "TOLERANCE",
        "VIEWPORT",
        "ATTRIB", "SEQEND", "VERTEX", "ATTDEF",
    })

    # Entity types that are NOT in the ENTITIES section (symbol tables, dictionaries, etc.)
    NON_ENTITIES_SECTION_TYPES = frozenset({
        "TABLE", "VPORT", "LTYPE", "LAYER", "STYLE", "APPID", "DIMSTYLE",
        "BLOCK_RECORD", "DICTIONARY", "XRECORD", "LAYOUT", "MATERIAL",
        "MLEADERSTYLE", "MLINESTYLE", "ACDBPLACEHOLDER", "SCALE",
        "VISUALSTYLE", "DICTIONARYVAR", "BLOCKLINEARPARAMETER",
        "BLOCKLINEARGRIP", "BLOCKGRIPLOCATIONCOMPONENT", "BLOCKSTRETCHACTION",
        "BLOCKALIGNMENTPARAMETER", "BLOCKALIGNMENTGRIP",
        "ACDB_DYNAMICBLOCKPROXYNODE", "SPATIAL_FILTER", "ACDBASSOCACTION",
        "ACDBASSOCNETWORK", "ACDBDETAILVIEWSTYLE", "ACDBSECTIONVIEWSTYLE",
        "TABLESTYLE", "CELLSTYLEMAP", "ACDBASSOCARRAYACTIONBODY",
        "ACDBASSOCDEPENDENCY", "ACDBASSOCVERTEXACTIONPARAM",
        "ACDB_HATCHSCALECONTEXTDATA_CLASS", "ACDB_MTEXTOBJECTCONTEXTDATA_CLASS",
        "ACDB_HATCHVIEWCONTEXTDATA_CLASS", "ACDB_DYNAMICBLOCKPURGEPREVENTER_VERSION",
        "ACAD_EVALUATION_GRAPH", "DBCOLOR", "RASTERVARIABLES", "WIPEOUTVARIABLES",
        "SORTENTSTABLE", "ACDBDICTIONARYWDFLT",
    })

    # Maximum entities before emitting PARTIAL diagnostic.
    ENTITY_CAP = 50_000

    # Layout block names that represent layout contents (not user-defined blocks).
    LAYOUT_BLOCK_NAMES = frozenset({
        "*Model_Space", "*Paper_Space", "*Paper_Space0",
    })

    def _count_entities_section_entities(self, doc) -> int:
        """Count all entities in the ENTITIES section using direct text parsing.
        
        This matches the independent truth generation methodology.
        Uses ezdxf's layout iteration which returns all layout-owned entities.
        """
        count = 0
        for layout in doc.layouts:
            count += len(list(layout))
        return count

    @property
    def id(self) -> str:
        return "dxf-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".dxf"]

    def extract(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        context = context or {}
        abs_path = os.path.abspath(file_path or "")
        file_name = os.path.basename(abs_path)

        result = ExtractionResult()
        result.diagnostics.append(f"Processing {file_name}")

        if not os.path.exists(abs_path):
            result.success = False
            result.diagnostics.append(f"File not found: {abs_path}")
            logger.error("[DXFExtractor] File not found: %s", abs_path)
            return result

        try:
            import ezdxf  # local import — dependency gate
        except ImportError:
            result.success = False
            result.diagnostics.append("ezdxf is not installed")
            logger.error("[DXFExtractor] ezdxf not available")
            return result

        try:
            doc = ezdxf.readfile(abs_path)
        except Exception as exc:
            result.success = False
            result.diagnostics.append(f"ezdxf read failed: {exc}")
            logger.error("[DXFExtractor] Failed to open %s: %s", abs_path, exc, exc_info=True)
            return result

        # ── Drawing-level metadata ────────────────────────────────────────
        drawing_rec = self._extract_drawing(doc, file_name, abs_path)
        result.records.append(drawing_rec)

        # ── Layer inventory ───────────────────────────────────────────────
        for layer_rec in self._extract_layers(doc, abs_path):
            result.records.append(layer_rec)

        # ── All layout entities ───────────────────────────────────────────
        cap_reached = False
        entity_count = 0
        unsupported: Dict[str, int] = {}

        for layout in doc.layouts:
            layout_name = layout.name
            is_modelspace = getattr(layout, "is_modelspace", False)
            for idx, ent in enumerate(layout):
                if entity_count >= self.ENTITY_CAP:
                    cap_reached = True
                    break
                entity_count += 1
                try:
                    rec = self._extract_entity(ent, abs_path, doc, layout_name)
                    if rec is not None:
                        result.records.append(rec)
                except Exception as exc:
                    etype = ent.dxftype() or "UNKNOWN"
                    logger.warning(
                        "[DXFExtractor] Entity %s at index %d in layout '%s' failed: %s",
                        etype, idx, layout_name, exc, exc_info=True,
                    )
                    result.diagnostics.append(f"Entity {etype}#{idx} in layout '{layout_name}' extract error: {exc}")
                    unsupported[etype] = unsupported.get(etype, 0) + 1
            if cap_reached:
                break

        # ── Unsupported entity summary ───────────────────────────────────
        for etype, count in sorted(unsupported.items()):
            result.records.append({
                "type": "dxf_unsupported",
                "data": {"entity_type": etype, "count": count, "source_file": abs_path},
            })

        # ── Block definitions ────────────────────────────────────────────
        for blk_rec in self._extract_blocks(doc, abs_path):
            result.records.append(blk_rec)

        # ── Orphan entities from direct ENTITIES section parsing ──────────
        # Collect handles of already-extracted entities for deduplication
        extracted_handles = set()
        for rec in result.records:
            h = rec.get("data", {}).get("handle", "")
            if h:
                extracted_handles.add(h)

        # Parse ENTITIES section directly to find orphans
        orphan_records = []
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                dxf_content = f.read()
            orphan_records = self._parse_entities_section(
                dxf_content, abs_path, extracted_handles
            )
            for rec in orphan_records:
                result.records.append(rec)
        except Exception as exc:
            logger.warning("[DXFExtractor] Orphan entity parsing failed: %s", exc)

        # ── XREF inventory ───────────────────────────────────────────────
        for xref_rec in self._extract_xrefs(doc, abs_path):
            result.records.append(xref_rec)

        # ── Status ───────────────────────────────────────────────────────
        layout_count = len(list(doc.layouts))
        entities_section_count = self._count_entities_section_entities(doc)
        # Add orphan count to entity_count
        orphan_count = len(orphan_records) if 'orphan_records' in dir() else 0
        result.metadata.update({
            "source_file": abs_path,
            "file_name": file_name,
            "entity_count": entities_section_count + orphan_count,
            "layout_entity_count": entity_count,
            "orphan_entity_count": orphan_count,
            "drawing_version": str(doc.header.get("$ACADVER", "")),
            "units": str(getattr(doc.header, "$MEASUREMENT", "")),
            "cap_reached": cap_reached,
            "layout_count": layout_count,
        })

        if cap_reached:
            result.diagnostics.append(
                f"Entity cap reached at {self.ENTITY_CAP}; extraction is PARTIAL "
                f"({entity_count} of {self.ENTITY_CAP} processed)."
            )
        elif not result.diagnostics or result.diagnostics == [f"Processing {file_name}"]:
            result.diagnostics.append("Extraction completed successfully")
        else:
            result.diagnostics.append("Extraction completed with warnings")

        result.success = True
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _extract_drawing(
        self, doc, file_name: str, abs_path: str
    ) -> Dict[str, Any]:
        msp = doc.modelspace()
        extents = None
        try:
            extents = msp.extents()
        except Exception:
            pass

        layout_names = doc.layout_names()
        layer_names = [str(l.dxf.name) for l in doc.layers]

        # Count entities by type across ALL layouts (fast, no geometry).
        type_counts: Dict[str, int] = {}
        total_entity_count = 0
        for layout in doc.layouts:
            for e in layout:
                t = e.dxftype() or "UNKNOWN"
                type_counts[t] = type_counts.get(t, 0) + 1
                total_entity_count += 1

        return {
            "type": "dxf_drawing",
            "data": {
                "source_file": abs_path,
                "file_name": file_name,
                "drawing_version": str(doc.header.get("$ACADVER", "")),
                "created": str(doc.header.get("$CREATED", "")),
                "modified": str(doc.header.get("$LASTMODIFIED", "")),
                "units": str(getattr(doc.header, "$MEASUREMENT", "")),
                "modelspace_entity_count": len(list(msp)),
                "total_entity_count": total_entity_count,
                "total_entity_types": len(type_counts),
                "entity_type_counts": type_counts,
                "layout_count": len(layout_names),
                "layout_names": layout_names[:50],
                "layer_count": len(layer_names),
                "extents": (
                    {
                        "min_x": float(extents.minx),
                        "min_y": float(extents.miny),
                        "max_x": float(extents.maxx),
                        "max_y": float(extents.maxy),
                    }
                    if extents is not None
                    else None
                ),
                "has_modelspace": True,
                "has_tables": hasattr(doc, "tables"),
            },
        }

    def _extract_layers(self, doc, abs_path: str) -> List[Dict[str, Any]]:
        records = []
        for layer in doc.layers:
            try:
                layer_name = str(layer.dxf.name)
                color = getattr(layer.dxf, "color", None)
                linetype = str(getattr(layer.dxf, "linetype", ""))
                frozen = bool(getattr(layer.dxf, "frozen", False))
                locked = bool(getattr(layer.dxf, "locked", False))
                on = bool(getattr(layer.dxf, "on", True))
            except Exception as exc:
                layer_name = "??"
                color = None
                linetype = ""
                frozen = False
                locked = False
                on = True
                logger.debug(
                    "[DXFExtractor] Layer read partial: %s", exc
                )

            records.append({
                "type": "dxf_layer",
                "data": {
                    "source_file": abs_path,
                    "layer_name": layer_name,
                    "color": int(color) if color is not None else None,
                    "linetype": linetype or None,
                    "frozen": frozen,
                    "locked": locked,
                    "on": on,
                },
            })
        return records

    def _extract_entity(
        self, ent, abs_path: str, doc, layout_name: str = "modelspace"
    ) -> Optional[Dict[str, Any]]:
        etype = ent.dxftype()
        if etype is None:
            return None

        _h = getattr(ent.dxf, "handle", "")
        if not _h:
            _d = dict(ent.dxf.__dict__)
            _k = sorted(_d.keys())
            _v = [_d[k] for k in _k]
            _h = __import__("hashlib").sha1(str((abs_path, etype, _k, _v)).encode()).hexdigest()[:12]
        handle = _h
        layer = str(getattr(ent.dxf, "layer", "0"))

        base = {
            "type": f"dxf_{etype.lower()}",
            "data": {
                "handle": handle,
                "entity_type": etype,
                "layer": layer,
                "layout": layout_name,
                "source_file": abs_path,
            },
        }

        if etype == "LINE":
            try:
                s = ent.dxf.start
                e = ent.dxf.end
                base["data"].update({
                    "start_x": float(s.x if hasattr(s, "x") else s[0]),
                    "start_y": float(s.y if hasattr(s, "y") else s[1]),
                    "start_z": float(s.z if hasattr(s, "z") else (s[2] if len(s) > 2 else 0.0)),
                    "end_x": float(e.x if hasattr(e, "x") else e[0]),
                    "end_y": float(e.y if hasattr(e, "y") else e[1]),
                    "end_z": float(e.z if hasattr(e, "z") else (e[2] if len(e) > 2 else 0.0)),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "CIRCLE":
            try:
                c = ent.dxf.center
                base["data"].update({
                    "center_x": float(c.x if hasattr(c, "x") else c[0]),
                    "center_y": float(c.y if hasattr(c, "y") else c[1]),
                    "center_z": float(c.z if hasattr(c, "z") else (c[2] if len(c) > 2 else 0.0)),
                    "radius": float(ent.dxf.radius),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "ARC":
            try:
                c = ent.dxf.center
                base["data"].update({
                    "center_x": float(c.x if hasattr(c, "x") else c[0]),
                    "center_y": float(c.y if hasattr(c, "y") else c[1]),
                    "center_z": float(c.z if hasattr(c, "z") else (c[2] if len(c) > 2 else 0.0)),
                    "radius": float(ent.dxf.radius),
                    "start_angle_deg": float(ent.dxf.start_angle),
                    "end_angle_deg": float(ent.dxf.end_angle),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype in ("LWPOLYLINE", "POLYLINE"):
            try:
                points = []
                for vertex in ent:
                    try:
                        if hasattr(vertex, "x"):
                            vx, vy = float(vertex.x), float(vertex.y)
                            vz = float(getattr(vertex, "z", 0.0))
                        else:
                            vx, vy = float(vertex[0]), float(vertex[1])
                            vz = float(vertex[2]) if len(vertex) > 2 else 0.0
                        points.append({"x": vx, "y": vy, "z": vz})
                    except Exception:
                        pass
                base["data"]["vertex_count"] = len(points)
                base["data"]["vertices"] = points[:1000]
                base["data"]["closed"] = bool(ent.dxf.flags & 1)
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "TEXT":
            try:
                p = ent.dxf
                base["data"].update({
                    "text": str(p.text) if p.text else "",
                    "x": float(p.insert.x),
                    "y": float(p.insert.y),
                    "z": float(p.insert.z),
                    "rotation_deg": float(getattr(p, "rotation", 0.0)),
                    "height": float(getattr(p, "height", 0.0)),
                    "style": str(getattr(p, "style", "")),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "MTEXT":
            try:
                p = ent.dxf
                text_content = str(p.text) if p.text else ""
                # Strip Acis/control codes for deterministic text.
                text_content = re.sub(r"[\\{}]ACIS[^;]+;", "", text_content)
                text_content = re.sub(r"[\\{}]A.[^;]+;", "", text_content)
                base["data"].update({
                    "text": text_content,
                    "x": float(p.insert.x),
                    "y": float(p.insert.y),
                    "z": float(p.insert.z),
                    "rotation_deg": float(getattr(p, "rotation", 0.0)),
                    "width": float(getattr(p, "width", 0.0)),
                    "style": str(getattr(p, "style", "")),
                    "text_length": len(text_content),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "INSERT":
            try:
                p = ent.dxf
                ins_pt = p.insert
                base["data"].update({
                    "block_name": str(p.name),
                    "insert_x": float(ins_pt.x),
                    "insert_y": float(ins_pt.y),
                    "insert_z": float(ins_pt.z),
                    "rotation_deg": float(getattr(p, "rotation", 0.0)),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "DIMENSION":
            try:
                p = ent.dxf
                code = int(p.dimtype)
                low = code & 31
                label_parts = []
                low_names = {
                    1: "ORTHOGONAL", 2: "PARALLEL", 3: "ANGULAR",
                    4: "ANGULAR_3PT", 5: "DIAMETER", 6: "RADIUS",
                    8: "ORDINATE_X", 16: "ORDINATE_Y",
                }
                if low in low_names:
                    label_parts.append(low_names[low])
                if code & 32:
                    label_parts.append("LINEAR")
                if code & 64:
                    label_parts.append("ANGULAR")
                if code & 128:
                    label_parts.append("DIAMETER")
                if code & 256:
                    label_parts.append("RADIUS")
                if code & 512:
                    label_parts.append("ORDINATE")
                dim_type_str = "+".join(label_parts) if label_parts else "UNKNOWN"
                dp = p.defpoint
                dp2 = p.defpoint2
                dx = dp2[0] - dp[0]
                dy = dp2[1] - dp[1]
                measurement = round(math.sqrt(dx * dx + dy * dy), 6)
                base["data"].update({
                    "dimension_type": dim_type_str,
                    "dimtype_code": code,
                    "measurement": measurement,
                    "defpoint_x": float(dp[0]),
                    "defpoint_y": float(dp[1]),
                    "defpoint_z": float(dp[2] if len(dp) > 2 else 0.0),
                    "defpoint2_x": float(dp2[0]),
                    "defpoint2_y": float(dp2[1]),
                    "defpoint2_z": float(dp2[2] if len(dp2) > 2 else 0.0),
                    "text_override": str(p.text) if p.text else None,
                    "dimstyle": str(p.dimstyle),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "VIEWPORT":
            try:
                p = ent.dxf
                base["data"].update({
                    "center_x": float(p.center.x) if hasattr(p.center, "x") else float(p.center[0]),
                    "center_y": float(p.center.y) if hasattr(p.center, "y") else float(p.center[1]),
                    "width": float(p.width),
                    "height": float(p.height),
                    "view_center_x": float(p.view_center_point.x) if hasattr(p.view_center_point, "x") else float(p.view_center_point[0]),
                    "view_center_y": float(p.view_center_point.y) if hasattr(p.view_center_point, "y") else float(p.view_center_point[1]),
                    "view_height": float(p.view_height),
                    "aspect_ratio": float(p.aspect_ratio) if hasattr(p, "aspect_ratio") else None,
                    "lens_length": float(p.lens_length) if hasattr(p, "lens_length") else None,
                    "front_clip": float(p.front_clip) if hasattr(p, "front_clip") else None,
                    "back_clip": float(p.back_clip) if hasattr(p, "back_clip") else None,
                    "view_mode": int(p.view_mode) if hasattr(p, "view_mode") else None,
                    "circle_zoom": float(p.circle_zoom) if hasattr(p, "circle_zoom") else None,
                    "fast_zoom": float(p.fast_zoom) if hasattr(p, "fast_zoom") else None,
                    "ucs_icon": int(p.ucs_icon) if hasattr(p, "ucs_icon") else None,
                    "snap_base_x": float(p.snap_base_point.x) if hasattr(p.snap_base_point, "x") else float(p.snap_base_point[0]),
                    "snap_base_y": float(p.snap_base_point.y) if hasattr(p.snap_base_point, "y") else float(p.snap_base_point[1]),
                    "grid_spacing_x": float(p.grid_spacing.x) if hasattr(p.grid_spacing, "x") else float(p.grid_spacing[0]),
                    "grid_spacing_y": float(p.grid_spacing.y) if hasattr(p.grid_spacing, "y") else float(p.grid_spacing[1]),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype in ("SOLID", "TRACE"):
            try:
                points = []
                for i in range(4):
                    pt = getattr(ent.dxf, f"point{i}", None)
                    if pt is not None:
                        points.append({
                            "x": float(pt.x) if hasattr(pt, "x") else float(pt[0]),
                            "y": float(pt.y) if hasattr(pt, "y") else float(pt[1]),
                            "z": float(pt.z) if hasattr(pt, "z") else float(pt[2]) if len(pt) > 2 else 0.0,
                        })
                base["data"]["points"] = points
                base["data"]["vertex_count"] = len(points)
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "POINT":
            try:
                p = ent.dxf.location
                base["data"].update({
                    "x": float(p.x) if hasattr(p, "x") else float(p[0]),
                    "y": float(p.y) if hasattr(p, "y") else float(p[1]),
                    "z": float(p.z) if hasattr(p, "z") else float(p[2]) if len(p) > 2 else 0.0,
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype in ("ELLIPSE", "SPLINE", "HELIX"):
            try:
                base["data"]["notes"] = f"{etype} geometry extraction not fully implemented; metadata only."
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype in ("WIPEOUT", "MULTILEADER", "LEADER", "TOLERANCE", "RAY", "XLINE"):
            try:
                base["data"]["notes"] = f"{etype} geometry extraction not fully implemented; metadata only."
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype in ("ATTRIB", "ATTDEF"):
            try:
                p = ent.dxf
                base["data"].update({
                    "tag": str(p.tag) if hasattr(p, "tag") else "",
                    "prompt": str(p.prompt) if hasattr(p, "prompt") else "",
                    "value": str(p.value) if hasattr(p, "value") else "",
                    "x": float(p.insert.x) if hasattr(p.insert, "x") else float(p.insert[0]),
                    "y": float(p.insert.y) if hasattr(p.insert, "y") else float(p.insert[1]),
                    "z": float(p.insert.z) if hasattr(p.insert, "z") else float(p.insert[2]) if len(p.insert) > 2 else 0.0,
                    "height": float(p.height) if hasattr(p, "height") else 0.0,
                    "rotation_deg": float(getattr(p, "rotation", 0.0)),
                    "style": str(getattr(p, "style", "")),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "SEQEND":
            try:
                base["data"]["notes"] = "SEQEND marker entity; metadata only."
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        elif etype == "VERTEX":
            try:
                p = ent.dxf
                base["data"].update({
                    "x": float(p.location.x) if hasattr(p.location, "x") else float(p.location[0]),
                    "y": float(p.location.y) if hasattr(p.location, "y") else float(p.location[1]),
                    "z": float(p.location.z) if hasattr(p.location, "z") else float(p.location[2]) if len(p.location) > 2 else 0.0,
                    "start_width": float(getattr(p, "start_width", 0.0)),
                    "end_width": float(getattr(p, "end_width", 0.0)),
                    "bulge": float(getattr(p, "bulge", 0.0)),
                    "flags": int(getattr(p, "flags", 0)),
                })
            except Exception as exc:
                base["data"]["error"] = f"geometry_read_error: {exc}"

        else:
            base["data"]["notes"] = f"No geometry extraction for {etype}; emitted with metadata only."

        return base

    def _extract_blocks(self, doc, abs_path: str) -> List[Dict[str, Any]]:
        records = []
        for blk_layout in doc.blocks:
            blk_name = str(blk_layout.dxf.name)
            # Skip default layout blocks - they duplicate layout entity data
            if blk_name in self.LAYOUT_BLOCK_NAMES:
                continue
            try:
                rec = blk_layout.block_record
                is_xref = bool(rec.is_xref)
            except Exception:
                is_xref = False

            entity_count = 0
            insert_refs = 0
            try:
                for e in blk_layout:
                    entity_count += 1
                    if e.dxftype() == "INSERT":
                        insert_refs += 1
            except Exception:
                pass

            records.append({
                "type": "dxf_block",
                "data": {
                    "source_file": abs_path,
                    "block_name": blk_name,
                    "entity_count": entity_count,
                    "insert_references": insert_refs,
                    "is_xref": is_xref,
                },
            })
        return records

    def _parse_entities_section(
        self, content: str, abs_path: str, extracted_handles: set
    ) -> List[Dict[str, Any]]:
        """Parse ENTITIES section directly to catch orphan entities ezdxf misses."""
        records = []
        lines = content.splitlines()
        current_section = None
        current_entity = None
        i = 0
        
        while i < len(lines) - 1:
            code = lines[i].strip()
            value = lines[i + 1].strip() if i + 1 < len(lines) else ""
            i += 2
            
            # Section detection
            if code == "0" and value == "SECTION" and i + 1 < len(lines):
                section_code = lines[i].strip()
                section_name = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if section_code == "2":
                    current_section = section_name
                    i += 2
                    continue
                elif value == "ENDSEC":
                    current_section = None
                    continue
                elif value == "EOF":
                    break
            
            if current_section != "ENTITIES":
                continue
            
            if code == "0":
                if value == "ENDSEC":
                    continue
                if value == "EOF":
                    break
                # Save previous entity if it has a handle
                if current_entity and current_entity.get("handle"):
                    h = current_entity["handle"]
                    if h not in extracted_handles and current_entity["type"] in self.GEOMETRY_TYPES:
                        rec = {
                            "type": f"dxf_{current_entity['type'].lower()}",
                            "data": {
                                "handle": h,
                                "entity_type": current_entity["type"],
                                "layer": current_entity.get("layer", "0"),
                                "layout": "orphan",
                                "source_file": abs_path,
                                "notes": "Orphan entity from direct ENTITIES section parsing",
                            },
                        }
                        records.append(rec)
                current_entity = {"type": value, "handle": ""}
                continue
            
            if code == "5" and current_entity is not None:
                current_entity["handle"] = value
                continue
        
        # Save last entity
        if current_entity and current_entity.get("handle"):
            h = current_entity["handle"]
            if h not in extracted_handles and current_entity["type"] in self.GEOMETRY_TYPES:
                rec = {
                    "type": f"dxf_{current_entity['type'].lower()}",
                    "data": {
                        "handle": h,
                        "entity_type": current_entity["type"],
                        "layer": current_entity.get("layer", "0"),
                        "layout": "orphan",
                        "source_file": abs_path,
                        "notes": "Orphan entity from direct ENTITIES section parsing",
                    },
                }
                records.append(rec)
        
        return records

    def _extract_xrefs(
        self, doc, abs_path: str
    ) -> List[Dict[str, Any]]:
        records = []
        try:
            from src.document_processing.xref_detector import XREFDetector
            project_root = os.path.dirname(abs_path)
            detector = XREFDetector(project_root)
            xrefs = detector.scan(abs_path)
            for xr in xrefs:
                records.append({
                    "type": "dxf_xref",
                    "data": {
                        "parent_file": abs_path,
                        "ref_rel_path": xr.ref_rel_path,
                        "ref_abs_path": xr.ref_abs_path,
                        "extension": xr.extension,
                    },
                })
        except Exception as exc:
            logger.debug("[DXFExtractor] XREF scan failed: %s", exc)
        return records

