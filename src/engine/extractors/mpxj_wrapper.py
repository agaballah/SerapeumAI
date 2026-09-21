"""
MPXJWrapper — Python wrapper for MPXJ Java library to extract .mpp (Microsoft Project) files.

Uses JPype to bridge Python → JVM → MPXJ.
"""
from __future__ import annotations

import glob
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from src.engine.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy JVM startup
# ---------------------------------------------------------------------------

_JVM_STARTED = False
_UNIVERSAL_READER = None


def _ensure_jvm() -> None:
    """Start JVM and load MPXJ classes if not already done."""
    global _JVM_STARTED, _UNIVERSAL_READER
    if _JVM_STARTED:
        return

    try:
        import jpype
        import mpxj
    except ImportError as exc:
        raise ImportError(
            "MPXJ extraction unavailable: missing dependencies. "
            "Install with: pip install mpxj jpype1"
        ) from exc

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        # Try common Windows paths
        candidates = [
            r"C:\Program Files\Java\jre1.8.0_501",
            r"C:\Program Files\Java\jdk-17",
            r"C:\Program Files\Java\jre8",
        ]
        for c in candidates:
            if os.path.isdir(c):
                java_home = c
                break

    if not java_home:
        raise ImportError("MPXJ extraction unavailable: Java runtime not found. Set JAVA_HOME or install JDK 8+.")

    jvm_path = os.path.join(java_home, "bin", "server", "jvm.dll")
    if not os.path.isfile(jvm_path):
        jvm_path = os.path.join(java_home, "bin", "client", "jvm.dll")
    if not os.path.isfile(jvm_path):
        jvm_path = os.path.join(java_home, "bin", "java.exe")  # fallback

    mpxj_lib = os.path.join(os.path.dirname(mpxj.__file__), "lib")
    jar_files = glob.glob(os.path.join(mpxj_lib, "*.jar"))
    classpath = os.pathsep.join(jar_files)

    try:
        jpype.startJVM(jvmpath=jvm_path, classpath=classpath, convertStrings=False)
        from jpype import JClass
        _UNIVERSAL_READER = JClass("net.sf.mpxj.reader.UniversalProjectReader")
        _JVM_STARTED = True
        logger.info("[MPXJWrapper] JVM started successfully")
    except Exception as exc:
        raise ImportError(f"MPXJ JVM initialization failed: {exc}") from exc


class MPXJWrapper(BaseExtractor):
    """Extracts project schedule data from .mpp files using MPXJ."""

    maturity = "EXPERIMENTAL"

    @property
    def id(self) -> str:
        return "mpp-extractor-v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_extensions(self) -> List[str]:
        return [".mpp"]

    def extract(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        context = context or {}
        abs_path = os.path.abspath(file_path or "")
        file_name = os.path.basename(abs_path)
        doc_id = context.get("doc_id", "unknown")

        records: List[Dict[str, Any]] = []
        diagnostics: List[str] = []

        try:
            _ensure_jvm()
        except ImportError as exc:
            diagnostic = f"MPXJ unavailable: {exc}"
            logger.error("[MPXJWrapper] %s", diagnostic)
            return ExtractionResult(
                records=[],
                success=False,
                diagnostics=[diagnostic],
                metadata={"source_file": abs_path, "file_name": file_name, "doc_id": doc_id},
            )

        try:
            reader = _UNIVERSAL_READER()
            project = reader.read(abs_path)

            # Project properties
            props = project.getProjectProperties()
            records.append({
                "type": "mpp_project",
                "data": {
                    "title": props.getProjectTitle() or "",
                    "start_date": str(props.getStartDate()) if props.getStartDate() else "",
                    "finish_date": str(props.getFinishDate()) if props.getFinishDate() else "",
                    "author": props.getAuthor() or "",
                    "company": props.getCompany() or "",
                    "file_version": props.getMpxFileVersion() or "",
                    "application_version": props.getApplicationVersion() or "",
                    "source_file": abs_path,
                },
                "provenance": {"source": "mpxj_wrapper"},
            })

            # Tasks
            tasks = list(project.getTasks())
            for task in tasks:
                record = {
                    "type": "mpp_task",
                    "data": {
                        "id": task.getID(),
                        "guid": task.getGUID() if hasattr(task, 'getGUID') else "",
                        "name": task.getName() or "",
                        "start": str(task.getStart()) if task.getStart() else "",
                        "finish": str(task.getFinish()) if task.getFinish() else "",
                        "duration": str(task.getDuration()) if task.getDuration() else "",
                        "percent_complete": task.getPercentComplete() if hasattr(task, 'getPercentComplete') else 0,
                        "wbs": task.getWBS() or "",
                        "summary": task.getSummary() if hasattr(task, 'getSummary') else False,
                        "outline_level": task.getOutlineLevel() if hasattr(task, 'getOutlineLevel') else 0,
                        "predecessors": self._format_predecessors(task),
                        "source_file": abs_path,
                    },
                    "provenance": {"source": "mpxj_wrapper", "entity": "task"},
                }
                records.append(record)

            # Resources
            resources = list(project.getResources())
            for res in resources:
                record = {
                    "type": "mpp_resource",
                    "data": {
                        "id": res.getID(),
                        "guid": res.getGUID() if hasattr(res, 'getGUID') else "",
                        "name": res.getName() or "",
                        "type": str(res.getType()) if hasattr(res, 'getType') else "",
                        "max_units": res.getMaxUnits() if hasattr(res, 'getMaxUnits') else 0,
                        "standard_rate": str(res.getStandardRate()) if hasattr(res, 'getStandardRate') else "",
                        "overtime_rate": str(res.getOvertimeRate()) if hasattr(res, 'getOvertimeRate') else "",
                        "source_file": abs_path,
                    },
                    "provenance": {"source": "mpxj_wrapper", "entity": "resource"},
                }
                records.append(record)

            # Assignments (MPXJ uses getRelationships or iteration)
            assignments = []
            try:
                # Try different methods to get assignments
                if hasattr(project, 'getRelations'):
                    assignments = list(project.getRelations())
                elif hasattr(project, 'getRelationships'):
                    assignments = list(project.getRelationships())
                else:
                    # Fallback: empty list
                    assignments = []
            except Exception:
                assignments = []
            
            for assign in assignments[:50]:  # Limit to 50 assignments
                record = {
                    "type": "mpp_assignment",
                    "data": {
                        "task_id": assign.getTaskUID() if hasattr(assign, 'getTaskUID') else "",
                        "resource_id": assign.getResourceUID() if hasattr(assign, 'getResourceUID') else "",
                        "units": assign.getUnits() if hasattr(assign, 'getUnits') else 0,
                        "work": str(assign.getWork()) if hasattr(assign, 'getWork') else "",
                        "actual_work": str(assign.getActualWork()) if hasattr(assign, 'getActualWork') else "",
                        "source_file": abs_path,
                    },
                    "provenance": {"source": "mpxj_wrapper", "entity": "assignment"},
                }
                records.append(record)

            diagnostics.append(f"Successfully extracted {len(tasks)} tasks, {len(resources)} resources, {len(assignments)} assignments")

        except Exception as exc:
            logger.exception("[MPXJWrapper] Failed on %s", abs_path)
            diagnostics.append(f"Extraction error: {exc}")
            return ExtractionResult(
                records=records,
                success=False,
                diagnostics=diagnostics,
                metadata={"source_file": abs_path, "file_name": file_name, "doc_id": doc_id},
            )

        return ExtractionResult(
            records=records,
            diagnostics=diagnostics,
            metadata={
                "source_file": abs_path,
                "file_name": file_name,
                "doc_id": doc_id,
                "task_count": len([r for r in records if r["type"] == "mpp_task"]),
                "resource_count": len([r for r in records if r["type"] == "mpp_resource"]),
                "assignment_count": len([r for r in records if r["type"] == "mpp_assignment"]),
            },
            success=True,
        )

    def _format_predecessors(self, task) -> List[str]:
        """Format predecessor relationships."""
        try:
            preds = task.getPredecessors()
            if not preds:
                return []
            result = []
            for p in preds:
                pred_type = getattr(p, 'getRelationType', lambda: '')()
                lag = getattr(p, 'getLag', lambda: 0)()
                pred_task = p.getTask()
                result.append(f"{pred_type}: {pred_task.getName() if pred_task else 'unknown'}")
            return result
        except Exception:
            return []
