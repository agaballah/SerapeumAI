# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

from .processor_utils import stable_doc_id


logger = logging.getLogger(__name__)


class CADProcessor:
    """DXF ingestion via ezdxf (DWG not supported here)."""

    def process(self, abs_path: str, rel_path: str, export_root: str, *, doc_id_override: str | None = None, project_root: str | None = None) -> Dict[str, Any]:
        doc_id = doc_id_override or stable_doc_id(abs_path, prefix="cad")
        ext = os.path.splitext(abs_path)[1].lower()
        
        entities: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        found_xrefs = []
        
        target_path = abs_path
        is_dgn = ext == ".dgn"
        converted_path = None

        try:
            # 1. Handle DGN conversion
            if is_dgn:
                from .oda_converter import ODAConverter
                converter = ODAConverter()
                if converter.is_available():
                    logger.info(f"   [CADProcessor] Converting DGN to DXF: {rel_path}")
                    converted_path = converter.convert_to_dxf(abs_path)
                    if converted_path:
                        target_path = converted_path
                    else:
                        text_parts.append(f"[cad] DGN conversion failed for {rel_path}")
                else:
                    text_parts.append(f"[cad] ODA File Converter not found. Cannot process DGN: {rel_path}")
                    target_path = None

            # 2. Parse DXF
            if target_path and os.path.exists(target_path):
                import ezdxf
                doc = ezdxf.readfile(target_path)
                msp = doc.modelspace()

                # Cap entities to avoid huge payloads during ingestion
                cap = None
                for i, e in enumerate(msp):
                    if cap and i >= cap: break
                    try:
                        etype = e.dxftype()
                        layer = e.dxf.layer if hasattr(e, "dxf") and hasattr(e.dxf, "layer") else "0"
                        entities.append({"type": etype, "layer": layer})
                    except Exception: continue

                text_parts.append(f"CAD entities: {len(entities)} (Type: {ext.upper()})")

                # 3. Scan XREFs
                if project_root:
                    from .xref_detector import XREFDetector
                    detector = XREFDetector(project_root)
                    found_xrefs = detector.scan(target_path)
                    if found_xrefs:
                        text_parts.append(f"Detected {len(found_xrefs)} XREFs")
        
        except Exception as e:
            text_parts.append(f"[cad] error processing {rel_path}: {e}")
            logger.error(f"[CADProcessor] Failed to process {rel_path}: {e}", exc_info=True)
        finally:
            # Cleanup converted temp file
            if converted_path and os.path.exists(converted_path):
                try: os.remove(converted_path)
                except: pass

        return {
            "doc_id": doc_id,
            "text": "\n".join(text_parts).strip(),
            "pages": [
                {
                    "page_index": 0,
                    "py_text": "\n".join(text_parts).strip(),
                    "text_hint": rel_path,
                    "has_vector": 1,
                    "quality": "queued",
                }
            ],
            "structured_data": entities,
            "xrefs": [{"rel_path": x.ref_rel_path, "abs_path": x.ref_abs_path} for x in found_xrefs],
            "meta": {"source": "cad-processor", "rel_path": rel_path, "original_ext": ext},
        }
