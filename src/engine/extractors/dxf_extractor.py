# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import math
import os
import re
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
    })

    # Maximum entities before emitting PARTIAL diagnostic.
    ENTITY_CAP = 50_000

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
        for layer_rec in self._extract_layers(doc):
            result.records.append(layer_rec)

        # ── Modelspace entities ───────────────────────────────────────────
        msp = doc.modelspace()
        cap_reached = False
        entity_count = 0
        unsupported: Dict[str, int] = {}

        for idx, ent in enumerate(msp):
            if idx >= self.ENTITY_CAP:
                cap_reached = True
                break
            entity_count += 1
            try:
                rec = self._extract_entity(ent, abs_path, doc)
                if rec is not None:
                    result.records.append(rec)
            except Exception as exc:
                etype = ent.dxftype() or "UNKNOWN"
                logger.warning(
                    "[DXFExtractor] Entity %s at index %d failed: %s",
                    etype, idx, exc, exc_info=True,
                )
                result.diagnostics.append(f"Entity {etype}#{idx} extract error: {exc}")
                unsupported[etype] = unsupported.get(etype, 0) + 1

        # ── Unsupported entity summary ───────────────────────────────────
        for etype, count in sorted(unsupported.items()):
            result.records.append({
                "type": "dxf_unsupported",
                "data": {"entity_type": etype, "count": count, "source_file": abs_path},
            })

        # ── Block definitions ────────────────────────────────────────────
        for blk_rec in self._extract_blocks(doc):
            result.records.append(blk_rec)

        # ── XREF inventory ───────────────────────────────────────────────
        for xref_rec in self._extract_xrefs(doc, abs_path):
            result.records.append(xref_rec)

        # ── Status ───────────────────────────────────────────────────────
        layout_count = len(list(doc.layouts))
        result.metadata.update({
            "source_file": abs_path,
            "file_name": file_name,
            "entity_count": entity_count,
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

        # Count entities by type (fast, no geometry).
        type_counts: Dict[str, int] = {}
        for e in msp:
            t = e.dxftype() or "UNKNOWN"
            type_counts[t] = type_counts.get(t, 0) + 1

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

    def _extract_layers(self, doc) -> List[Dict[str, Any]]:
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
        self, ent, abs_path: str, doc
    ) -> Optional[Dict[str, Any]]:
        etype = ent.dxftype()
        if etype is None:
            return None

        handle = getattr(ent, "handle", "")
        layer = str(getattr(ent.dxf, "layer", "0"))

        base = {
            "type": f"dxf_{etype.lower()}",
            "data": {
                "handle": handle,
                "entity_type": etype,
                "layer": layer,
                "layout": "modelspace",
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

        else:
            base["data"]["notes"] = f"No geometry extraction for {etype}; emitted with metadata only."

        return base

    def _extract_blocks(self, doc) -> List[Dict[str, Any]]:
        records = []
        for blk_layout in doc.blocks:
            blk_name = str(blk_layout.dxf.name)
            # Skip default layouts.
            if blk_name in ("*Model_Space", "*Paper_Space", "*Paper_Space0"):
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
                    "block_name": blk_name,
                    "entity_count": entity_count,
                    "insert_references": insert_refs,
                    "is_xref": is_xref,
                },
            })
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
