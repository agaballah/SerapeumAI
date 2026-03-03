import threading
import time
import logging
import traceback
from typing import Optional, TYPE_CHECKING

from src.application.jobs.job_queue import SQLiteJobQueue
from src.application.jobs.job_base import Job

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

    def check_and_wait(self, job_type: str) -> bool:
        """
        Check if system has resources to run this job type.
        Returns True when safe to proceed, implicitly applies wait on stress.

        Strategy:
          HEAVY (ANALYZE_DOC, VISION_INDEX) → needs 'vision' tier (4GB+)
          MEDIUM (EXTRACT)                  → needs 'analysis' tier (2GB+)
          LIGHT  (everything else)          → always OK
        """
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
                    time.sleep(wait)
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
                    time.sleep(8.0)
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

    def stop(self):
        if not self._thread:
            return
        logger.info("[JobManager] Stopping worker...")
        self._stop_event.set()
        self._thread.join(timeout=2.0)
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
        while not self._stop_event.is_set():
            try:
                # 1. Pick next job
                job = self.queue.pick_next(self.project_id)
                if not job:
                    time.sleep(self.poll_interval)
                    continue

                # 2. Smart resource check BEFORE running the job
                job_type = (job.type_name or "").upper()
                if not self.scheduler.check_and_wait(job_type):
                    # Put job back as pending and continue loop
                    try:
                        self.queue.mark_pending(job.job_id)
                    except Exception:
                        pass  # queue may not have mark_pending
                    continue

                # 3. Execute
                logger.info(f"[JobManager] Executing {job.type_name} ({job.job_id})...")
                job.mark_started()

                context = {
                    "db": self.db_manager,
                    "manager": self
                }

                try:
                    result = job.run(context)
                    job.mark_completed(result)
                    self.queue.mark_completed(job.job_id, result or {})
                except Exception as e:
                    logger.error(f"[JobManager] Job {job.job_id} failed: {e}")
                    traceback.print_exc()
                    job.mark_failed(e)
                    self.queue.mark_failed(job.job_id, e)

            except Exception as outer_e:
                logger.error(f"[JobManager] Worker loop error: {outer_e}")
                time.sleep(5.0)  # Backoff on system error
