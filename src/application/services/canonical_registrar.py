# -*- coding: utf-8 -*-
import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal

from src.application.services.scope_router import ScopeRouter

@dataclass
class RegistrationResult:
    status: Literal["registered", "ambiguous", "duplicate_version", "rejected"]
    scope: Literal["project", "global", "ambiguous"]
    db_kind: Literal["project", "global", "none"]
    doc_id: Optional[str] = None
    file_version_id: Optional[str] = None
    project_id: Optional[str] = None
    doc_key: Optional[str] = None
    queue_payload: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

class CanonicalRegistrar:
    """Sole owner of doc/file-version persistence."""
    def __init__(self, project_db=None, global_db=None, scope_router: Optional[ScopeRouter] = None):
        self.scope_router = scope_router or ScopeRouter()
        self.project_db = project_db
        self.global_db = global_db

    def register_incoming_file(
        self,
        abs_path: str,
        source_channel: str,
        project_id: Optional[str] = None,
        origin_context: str = "",
        explicit_scope: Optional[Literal["project", "global"]] = None,
        rel_path: Optional[str] = None
    ) -> RegistrationResult:
        decision = self.scope_router.route_file(
            abs_path=abs_path,
            source_channel=source_channel,
            origin_context=origin_context,
            explicit_scope=explicit_scope
        )

        if decision.status == "rejected":
            return RegistrationResult(
                status="rejected",
                scope="ambiguous",
                db_kind="none",
                message=f"File rejected by scope router: {', '.join(decision.reason_codes)}"
            )

        if decision.status == "ambiguous" or decision.scope == "ambiguous":
            return RegistrationResult(
                status="ambiguous",
                scope="ambiguous",
                db_kind="none",
                message=f"File scope is ambiguous: {', '.join(decision.reason_codes)}"
            )

        db_kind = decision.scope

        # Compute file properties
        file_hash = self._calculate_file_hash(abs_path)
        stat = os.stat(abs_path)
        file_size = int(stat.st_size)
        file_mtime = float(stat.st_mtime)
        filename = os.path.basename(abs_path)
        ext = os.path.splitext(filename)[1].lower()

        canonical_rel_path = rel_path or filename
        doc_key = decision.suggested_doc_key_basis or canonical_rel_path
        
        # Build logical doc id depending on scope
        if db_kind == "project":
            if not self.project_db:
                return RegistrationResult("rejected", db_kind, "none", message="Project DB missing")
            if not project_id:
                return RegistrationResult("rejected", db_kind, "none", message="project_id required for project scope")
                
            doc_id = self._compute_deterministic_doc_id("proj", project_id, doc_key)
            db = self.project_db
        else:
            if not self.global_db:
                return RegistrationResult("rejected", db_kind, "none", message="Global DB missing")
            doc_id = self._compute_deterministic_doc_id("glob", "global", doc_key)
            db = self.global_db

        file_version_id = f"fv_{file_hash[:16]}"

        if self._file_version_exists(db, db_kind, project_id, doc_id, file_hash):
             return RegistrationResult(
                 status="duplicate_version",
                 scope=db_kind,
                 db_kind=db_kind,
                 doc_id=doc_id,
                 file_version_id=file_version_id,
                 project_id=project_id,
                 doc_key=doc_key,
                 message="File version already exists"
             )

        # Write the documents and versions
        self._write_document_stub(
            db=db,
            db_kind=db_kind,
            project_id=project_id,
            doc_id=doc_id,
            doc_key=doc_key,
            title=decision.normalized_title,
            doc_type=decision.doc_type,
            discipline=decision.discipline,
            current_file_version_id=file_version_id
        )

        self._write_file_version(
            db=db,
            db_kind=db_kind,
            file_version_id=file_version_id,
            project_id=project_id,
            doc_id=doc_id,
            content_hash=file_hash,
            filename=filename,
            ext=ext,
            rel_path=canonical_rel_path,
            abs_path=abs_path,
            file_size=file_size,
            file_mtime=file_mtime,
            source_channel=source_channel
        )

        self._update_document_latest_version(db, db_kind, project_id, doc_id, file_version_id)

        queue_payload = {
            "target": db_kind,
            "project_id": project_id,
            "doc_id": doc_id,
            "file_version_id": file_version_id,
            "abs_path": abs_path,
            "force": False
        }

        return RegistrationResult(
            status="registered",
            scope=db_kind,
            db_kind=db_kind,
            doc_id=doc_id,
            file_version_id=file_version_id,
            project_id=project_id,
            doc_key=doc_key,
            queue_payload=queue_payload,
            message="Registered successfully"
        )


    def _calculate_file_hash(self, filepath: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(1024 * 1024), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


    def _compute_deterministic_doc_id(self, prefix: str, domain: str, doc_key: str) -> str:
        h = hashlib.sha1(f"{domain}::{doc_key}".encode("utf-8")).hexdigest()
        return f"{prefix}_{h[:16]}"
        

    def _file_version_exists(self, db, db_kind, project_id, doc_id, file_hash) -> bool:
        try:
            if db_kind == "project":
                # Check directly on db connections assuming they have basic _query or execute
                res = db._query("SELECT 1 FROM file_versions WHERE project_id = ? AND doc_id = ? AND content_hash = ?", (project_id, doc_id, file_hash))
                return len(res) > 0
            else:
                # Assuming global_db uses sqlite3 direct execute
                res = db.execute("SELECT 1 FROM global_file_versions WHERE doc_id = ? AND content_hash = ?", (doc_id, file_hash)).fetchall()
                return len(res) > 0
        except Exception:
            return False


    def _write_document_stub(self, db, db_kind, project_id, doc_id, doc_key, title, doc_type, discipline, current_file_version_id):
        now = int(time.time())
        try:
            if db_kind == "project":
                db.execute(
                    """
                    INSERT INTO documents (doc_id, project_id, scope, doc_key, title, doc_type, discipline, status, current_file_version_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(doc_id) DO UPDATE SET 
                        title=excluded.title,
                        doc_type=excluded.doc_type,
                        discipline=excluded.discipline,
                        current_file_version_id=excluded.current_file_version_id,
                        updated_at=excluded.updated_at
                    """,
                    (doc_id, project_id, "project", doc_key, title, doc_type, discipline, "queued", current_file_version_id, now, now)
                )
            else:
                db.execute(
                    """
                    INSERT INTO global_documents (doc_id, scope, doc_key, title, source_type, status, current_file_version_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(doc_id) DO UPDATE SET 
                        title=excluded.title,
                        source_type=excluded.source_type,
                        current_file_version_id=excluded.current_file_version_id,
                        updated_at=excluded.updated_at
                    """,
                    (doc_id, "global", doc_key, title, "standards", "queued", current_file_version_id, now, now)
                )
                db.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to write document stub in {db_kind} DB: {e}")


    def _write_file_version(self, db, db_kind, file_version_id, project_id, doc_id, content_hash, filename, ext, rel_path, abs_path, file_size, file_mtime, source_channel):
        now = int(time.time())
        try:
            if db_kind == "project":
                db.execute(
                    """
                    INSERT INTO file_versions (file_version_id, project_id, doc_id, content_hash, file_name, file_ext, rel_path, abs_path_snapshot, file_size, file_mtime, source_channel, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_version_id) DO NOTHING
                    """,
                    (file_version_id, project_id, doc_id, content_hash, filename, ext, rel_path, abs_path, file_size, file_mtime, source_channel, now)
                )
            else:
                db.execute(
                    """
                    INSERT INTO global_file_versions (file_version_id, doc_id, content_hash, file_name, file_ext, abs_path_snapshot, file_size, file_mtime, source_channel, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_version_id) DO NOTHING
                    """,
                    (file_version_id, doc_id, content_hash, filename, ext, abs_path, file_size, file_mtime, source_channel, now)
                )
                db.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to write file version in {db_kind} DB: {e}")


    def _update_document_latest_version(self, db, db_kind, project_id, doc_id, file_version_id):
        try:
            if db_kind == "project":
                 db.execute("UPDATE documents SET current_file_version_id = ? WHERE doc_id = ?", (file_version_id, doc_id))
            else:
                 db.execute("UPDATE global_documents SET current_file_version_id = ? WHERE doc_id = ?", (file_version_id, doc_id))
                 db.commit()
        except Exception as e:
             raise RuntimeError(f"Failed to update document latest version: {e}")
