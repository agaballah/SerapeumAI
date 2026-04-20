# -*- coding: utf-8 -*-
import os
import logging
from typing import List, Set, Dict, Optional
import ezdxf

logger = logging.getLogger(__name__)

class XREFInfo:
    def __init__(self, parent_abs_path: str, ref_rel_path: str, ref_abs_path: str):
        self.parent_abs_path = parent_abs_path
        self.ref_rel_path = ref_rel_path
        self.ref_abs_path = ref_abs_path
        self.extension = os.path.splitext(ref_rel_path)[1].lower()

class XREFDetector:
    """
    Detects external references (XREFs) in CAD files (DXF).
    Handles path resolution and recursive dependency trees.
    """

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)

    def scan(self, abs_path: str, visited: Optional[Set[str]] = None) -> List[XREFInfo]:
        """
        Scan a DXF file for XREFs.
        Returns a list of resolved XREFInfo objects.
        """
        if visited is None:
            visited = set()
        
        abs_path = os.path.abspath(abs_path)
        if abs_path in visited:
            logger.warning(f"[XREFDetector] Circular reference detected: {abs_path}")
            return []
        
        visited.add(abs_path)
        
        if not abs_path.lower().endswith(".dxf"):
            # If it's DGN, we expect to be called on the converted DXF
            logger.debug(f"[XREFDetector] Skipping non-DXF file for direct ezdxf scan: {abs_path}")
            return []

        xrefs: List[XREFInfo] = []
        try:
            doc = ezdxf.readfile(abs_path)
            # In DXF, XREFs are blocks with a path attribute
            for block in doc.blocks:
                if block.is_xref:
                    ref_path = block.xref_path
                    if ref_path:
                        resolved_abs = self._resolve_path(os.path.dirname(abs_path), ref_path)
                        if resolved_abs:
                            xrefs.append(XREFInfo(abs_path, ref_path, resolved_abs))
                            # Recursive scan
                            # xrefs.extend(self.scan(resolved_abs, visited)) 
                            # (Recursive call should be handled by the orchestrator/service)
        except Exception as e:
            logger.error(f"[XREFDetector] Failed to scan {abs_path}: {e}")

        return xrefs

    def _resolve_path(self, parent_dir: str, ref_path: str) -> Optional[str]:
        """
        Resolve a CAD reference path (can be absolute, relative, or just a filename).
        """
        # 1. Try relative to parent
        candidate = os.path.normpath(os.path.join(parent_dir, ref_path))
        if os.path.exists(candidate):
            return candidate

        # 2. Try absolute path directly
        if os.path.isabs(ref_path) and os.path.exists(ref_path):
            return ref_path

        # 3. Try relative to project root
        candidate = os.path.normpath(os.path.join(self.project_root, ref_path))
        if os.path.exists(candidate):
            return candidate

        # 4. Search in same directory by filename only
        filename = os.path.basename(ref_path)
        candidate = os.path.join(parent_dir, filename)
        if os.path.exists(candidate):
            return candidate

        logger.debug(f"[XREFDetector] Could not resolve reference: {ref_path}")
        return None
