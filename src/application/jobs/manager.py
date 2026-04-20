import threading
import time
import logging
import traceback
from contextlib import contextmanager
from typing import Optional, TYPE_CHECKING

from src.application.jobs.job_queue import SQLiteJobQueue
from src.application.jobs.job_base import Job
from src.infra.adapters.cancellation import CancellationError

logger = logging.getLogger(__name__)

# Jobs that require heavy GPU resources
_HEAVY_JOB_TYPES = {"ANALYZE_DOC", "VISION_INDEX"}
_MEDIUM_JOB_TYPES = {"EXTRACT"}


class SmartScheduler:
    """
    Decides when and in what order to run jobs based on resource availability.
    Uses hardware_utils to detect VRAM/thermal state and degrades gracefully.
    """

    def __init__(self):
        self._consecutive_waits = 0
        self._interactive_wait_logged = False

    def _sleep_with_stop(self, seconds: float, stop_event=None) -> bool:
        end = time.time() + max(0.0, seconds)
        while time.time() < end:
            if stop_event is not None and hasattr(stop_event, 'is_set') and stop_event.is_set():
                return False
            time.sleep(min(0.1, max(0.0, end - time.time())))
        return True

    def check_and_wait(self, job_type: str, *, interactive_active: bool = False, stop_event=None) -> bool:
        """
        Check if system has resources to run this job type.
        Returns True when safe to proceed, implicitly applies wait on stress.

        Strategy:
          HEAVY (ANALYZE_DOC, VISION_INDEX) → needs 'vision' tier (4GB+)
          MEDIUM (EXTRACT)                  → needs 'analysis' tier (2GB+)
          LIGHT  (everything else)          → always OK
        """
        if interactive_active and job_type in (_HEAVY_JOB_TYPES | _MEDIUM_JOB_TYPES):
            if not self._interactive_wait_logged:
                logger.info(
                    f"[SmartScheduler] Interactive chat is active. Yielding background job '{job_type}' to protect chat responsiveness."
                )
                self._interactive_wait_logged = True
            end = time.time() + 0.75
            while time.time() < end:
                if stop_event is not None and hasattr(stop_event, 'is_set') and stop_event.is_set():
                    return False
                time.sleep(0.05)
            return False
        self._interactive_wait_logged = False
        try:
            from src.utils.hardware_utils import check_resource_availability, get_gpu_info

            if job_type in _HEAVY_JOB_TYPES:
                if not check_resource_availability("vision"):
                    gpu = get_gpu_info()
                    free = gpu.get("vram_free_mb", 0)
                    logger.warning(
                        f"[SmartScheduler] VRAM too low ({free}MB) for HEAVY job '{job_type}'. "
                        f"Pausing 15s to let resources free..."
                    )
                    self._consecutive_waits += 1
                    wait = min(15.0 * self._consecutive_waits, 60.0)  # progressive back-off
                    self._sleep_with_stop(wait, stop_event)
                    return False
                else:
                    self._consecutive_waits = 0
                    return True

            elif job_type in _MEDIUM_JOB_TYPES:
                if not check_resource_availability("analysis"):
                    gpu = get_gpu_info()
                    free = gpu.get("vram_free_mb", 0)
                    logger.warning(
                        f"[SmartScheduler] Low VRAM ({free}MB) for MEDIUM job '{job_type}'. "
                        f"Pausing 8s..."
                    )
                    self._sleep_with_stop(8.0, stop_event)
                    return False
                else:
                    self._consecutive_waits = 0
                    return True

        except Exception as e:
            logger.debug(f"[SmartScheduler] Resource check error (safe pass): {e}")

        return True  # Always safe to run light jobs


class JobManager:
    """
    Orchestrator for the V02 Job System.
    Manages the background worker thread and provides API for job submission.
    Now includes smart resource-aware scheduling via SmartScheduler.
    """

    def __init__(self, db_manager, project_id: str):
        self.db_manager = db_manager
        self.project_id = project_id
        self.queue = SQLiteJobQueue(db_manager)
        self.scheduler = SmartScheduler()

        self._stop_event = threading.Event()
        self._interactive_event = threading.Event()
        self._interactive_lock = threading.Lock()
        self._interactive_count = 0
        self._thread: Optional[threading.Thread] = None
        self.poll_interval = 1.0  # Seconds

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"JobWorker-{self.project_id}"
        )
        self._thread.start()
        logger.info(f"[JobManager] Started smart worker for project {self.project_id}")

    def begin_interactive_session(self):
        with self._interactive_lock:
            self._interactive_count += 1
            self._interactive_event.set()

    def end_interactive_session(self):
        with self._interactive_lock:
            if self._interactive_count > 0:
                self._interactive_count -= 1
            if self._interactive_count <= 0:
                self._interactive_count = 0
                self._interactive_event.clear()

    def is_interactive_active(self) -> bool:
        return self._interactive_event.is_set()

    @contextmanager
    def interactive_session(self):
        self.begin_interactive_session()
        try:
            yield
        finally:
            self.end_interactive_session()

    def stop(self, *, reason: str = "Session shutdown requested", cancel_incomplete: bool = True):
        if not self._thread and not cancel_incomplete:
            return
        logger.info("[JobManager] Stopping worker...")
        self._stop_event.set()
        self._interactive_event.clear()
        self.poll_interval = 0.1
        if cancel_incomplete:
            try:
                self.queue.cancel_incomplete_for_project(self.project_id, reason=reason)
            except Exception:
                logger.debug("[JobManager] Could not cancel incomplete jobs during shutdown.", exc_info=True)
        if self._thread:
            deadline = time.time() + 30.0
            while self._thread.is_alive() and time.time() < deadline:
                self._thread.join(timeout=0.25)
            if self._thread.is_alive():
                logger.debug("[JobManager] Worker still alive after bounded shutdown wait.")
            else:
                logger.info("[JobManager] Worker stopped cleanly.")
                self._thread = None

    def register_handler(self, job_cls):
        self.queue.register_job_type(job_cls)

    def submit(self, job: Job):
        if job.project_id != self.project_id:
            logger.warning(
                f"Submitting job for project {job.project_id} to manager of {self.project_id}"
            )
        self.queue.enqueue(job)
        logger.debug(f"[JobManager] Enqueued job {job.job_id} ({job.type_name})")

    def _worker_loop(self):
        import sqlite3
        from src.infra.persistence.global_db_initializer import global_db_path, ensure_global_db
        
        # Initialize Global DB Connection for high-priority routing
        g_path = global_db_path()
        ensure_global_db(g_path)
        g_conn = sqlite3.connect(g_path)
        g_conn.row_factory = sqlite3.Row

        while not self._stop_event.is_set():
            try:
                # 1. Pick next job
                job = self.queue.pick_next(self.project_id)
                if not job:
                    if self._stop_event.wait(self.poll_interval):
                        break
                    continue

                # 2. Smart resource check BEFORE running the job
                job_type = (job.type_name or "").upper()
                if not self.scheduler.check_and_wait(job_type, interactive_active=self.is_interactive_active(), stop_event=self._stop_event):
                    try:
                        self.queue.mark_pending(job.job_id)
                    except Exception:
                        pass
                    continue

                # 3. Execute with enhanced context
                logger.info(f"[JobManager] Executing {job.type_name} ({job.job_id})...")
                job.mark_started()

                context = {
                    "db": self.db_manager,
                    "global_db": g_conn,
                    "manager": self,
                    "stop_event": self._stop_event,
                    "interactive_event": self._interactive_event,
                }

                try:
                    if self._stop_event.is_set():
                        raise CancellationError("Session shutdown requested before job execution.")
                    result = job.run(context)
                    if self._stop_event.is_set():
                        raise CancellationError("Session shutdown requested during job execution.")
                    job.mark_completed(result)
                    self.queue.mark_completed(job.job_id, result or {})
                except CancellationError as e:
                    logger.info(f"[JobManager] Job {job.job_id} cancelled: {e}")
                    self.queue.mark_cancelled(job.job_id, str(e))
                except Exception as e:
                    logger.error(f"[JobManager] Job {job.job_id} failed: {e}")
                    traceback.print_exc()
                    job.mark_failed(e)
                    self.queue.mark_failed(job.job_id, e)

            except Exception as outer_e:
                logger.error(f"[JobManager] Worker loop error: {outer_e}")
                time.sleep(5.0)
        
        g_conn.close()
