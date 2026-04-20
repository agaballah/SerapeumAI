import os
import logging
from typing import Dict, Any, List
from src.application.jobs.job_base import Job
from src.domain.facts.models import Link, LinkStatus
from src.domain.facts.repository import FactRepository
from src.domain.models.relationship_types import RelationshipType

logger = logging.getLogger(__name__)

class FileLinkerJob(Job):
    """
    Job: FILE_LINKER
    Scans the registry for "Sibling Files" (same basename, different extension)
    and creates REPRESENTATION_OF links (e.g. Layout.pdf is representation of Layout.dwg).
    """
    
    TYPE_NAME = "FILE_LINKER"
    
    def __init__(self, job_id: str, project_id: str, target_file_id: str):
        super().__init__(job_id, project_id, priority=20)
        self.target_file_id = target_file_id

    @property
    def type_name(self) -> str:
        return self.TYPE_NAME

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "target_file_id": self.target_file_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        return cls(
            job_id=data["job_id"],
            project_id=data["project_id"],
            target_file_id=data["target_file_id"]
        )

    def run(self, context) -> Any:
        db = context["db"]
        
        # 1. Get Target File Info
        target = db.execute(
            "SELECT file_id, first_seen_path, file_id as fid FROM file_registry WHERE file_id = ?", 
            (self.target_file_id,)
        ).fetchone()
        
        if not target:
            return {"status": "skipped", "reason": "target_not_found"}

        path = target["first_seen_path"]
        if not path:
             return {"status": "skipped", "reason": "no_path"}
             
        directory = os.path.dirname(path)
        basename = os.path.splitext(os.path.basename(path))[0]
        
        # 2. Find Candidates in Registry with same Directory and Basename
        # We search by partial path match effectively (or by project_id and python filter if DB lacks path splitting)
        # For SQLite, we can use a LIKE if paths are normalized.
        
        # Heuristic: Scan all files in project, match dirname/basename.
        # Efficient approach: We assume files are in `file_registry` with `first_seen_path`.
        
        candidates = db.execute(
            """
            SELECT file_id, first_seen_path 
            FROM file_registry 
            WHERE project_id = ? AND file_id != ?
            """, 
            (self.project_id, self.target_file_id)
        ).fetchall()
        
        linked_count = 0
        
        for cand in candidates:
            c_path = cand["first_seen_path"]
            if not c_path: continue
            
            c_dir = os.path.dirname(c_path)
            c_base = os.path.splitext(os.path.basename(c_path))[0]
            
            if c_dir == directory and c_base == basename:
                # MATCH FOUND!
                # Determine direction. 
                # Rule: Richer Data (XER, DWG, RVT) -> Representation (PDF, PNG)
                
                t_ext = os.path.splitext(path)[1].lower()
                c_ext = os.path.splitext(c_path)[1].lower()
                
                parent_id, child_id = self._determine_hierarchy(
                    (self.target_file_id, t_ext), 
                    (cand["file_id"], c_ext)
                )
                
                if parent_id and child_id:
                    v_parent = self._get_latest_version(db, parent_id)
                    v_child = self._get_latest_version(db, child_id)
                    
                    if v_parent and v_child:
                        repo = FactRepository(db)
                        link_id = f"link_file_auto_{v_parent[:8]}_{v_child[:8]}"
                        
                        # Truth Engine V2: Set to AUTO_VALIDATED for highly deterministic basename matches
                        new_link = Link(
                            link_id=link_id,
                            project_id=self.project_id,
                            link_type="REPRESENTATION_OF",
                            from_kind="file_version",
                            from_id=v_parent,
                            to_kind="file_version",
                            to_id=v_child,
                            status=LinkStatus.AUTO_VALIDATED,
                            confidence=1.0,
                            confidence_tier="AUTO_VALIDATED",
                            method_id="heuristic_exact_basename_v2",
                            created_at=db._ts(),
                            validated_at=db._ts()
                        )
                        
                        repo.save_links([new_link])
                        linked_count += 1
                        logger.info(f"Auto-validated link: {v_parent} -> {v_child}")

        return {"status": "success", "linked": linked_count}

    def _determine_hierarchy(self, f1, f2):
        id1, ext1 = f1
        id2, ext2 = f2
        
        rich = {".xer", ".xml", ".mpp", ".dwg", ".dgn", ".rvt", ".ifc", ".xls", ".xlsx"}
        reps = {".pdf", ".png", ".jpg", ".tif"}
        
        # If one is rich and other is rep
        if ext1 in rich and ext2 in reps:
            return id1, id2
        elif ext2 in rich and ext1 in reps:
            return id2, id1
            
        return None, None

    def _get_latest_version(self, db, file_id):
        row = db.execute(
            "SELECT file_version_id FROM file_versions WHERE file_id=? ORDER BY imported_at DESC LIMIT 1",
            (file_id,)
        ).fetchone()
        return row[0] if row else None
