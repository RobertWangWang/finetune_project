import asyncio
import logging
import threading
import traceback
from typing import Dict

from app.api.middleware.context import set_current_locale
from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import job_db
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.job_model import JobStatus, JobResult, JobType
from app.services.dataset_services.jobs.connon import JobHandlerInterface, update_job_status, build_user
from app.services.dataset_services.jobs.generator.dataset import DatasetGeneratorHandler
from app.services.dataset_services.jobs.generator.file_delete import FileDeleteGeneratorHandler
from app.services.dataset_services.jobs.generator.file_pair import FilePairGeneratorHandler
from app.services.dataset_services.jobs.generator.ga_pair import GaPairGeneratorHandler
from app.services.dataset_services.jobs.generator.question import QuestionGeneratorHandler
from app.services.dataset_services.jobs.generator.tag import TagGeneratorHandler


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, JobORM] = {}
        self.handlers = {str: JobHandlerInterface}
        self._lock = threading.Lock()
        self._running_tasks = set()
        self._stop_event = asyncio.Event()

    def register_handler(self, name: str, handler: JobHandlerInterface):
        with self._lock:
            self.handlers[name] = handler

    def add_job(self, job: JobORM):
        with self._lock:
            self.jobs[job.id] = job

    def cancel_job(self, id: str):
        with self._lock:
            for task in self._running_tasks:
                if getattr(task, '_job_id', None) == id:
                    task.cancel()
                    break

    def get_job(self, id: str) -> JobORM:
        with self._lock:
            return self.jobs[id]

    async def stop(self):
        """Stop the job manager gracefully"""
        self._stop_event.set()
        await asyncio.gather(*self._running_tasks, return_exceptions=True)

    async def _execute_job(self, job: JobORM):
        """Execute a single job with its handler and call done() when complete"""
        try:
            logging.info(f"Start process job: {job.id}")
            handler = self.handlers.get(job.type)  # Using .get() to avoid KeyError
            if not handler:
                update_job_status(None, job.id, build_user(job), JobStatus.Failed, JobResult(
                    logs="",
                    error=i18n.gettext("No handler found for job type: {type}", locale=job.locale).format(type=job.type)
                ))
                return

            set_current_locale(job.locale)
            result = handler.execute(job)  # Assuming execute is async
            handler.done(result)
        except asyncio.CancelledError:
            logging.info(f"User cancelled job. id: {job.id}")
            update_job_status(None, job.id, build_user(job), JobStatus.Cancel, JobResult(
                logs="",
                error=i18n.gettext("Job cancel", locale=job.locale)
            ))
        except Exception as e:
            traceback.print_exc()
            update_job_status(None, job.id, build_user(job), JobStatus.Failed, JobResult(
                logs="",
                error=i18n.gettext("Error executing job, error: {error}", locale=job.locale).format(error=str(e))
            ))
        finally:
            # Remove the task from running tasks when done
            with self._lock:
                self._running_tasks = {
                    task for task in self._running_tasks
                    if not task.done() or task.get_name() != f"job_{job.id}"
                }
                logging.info(f"End process job: {job.id}")
                if job.id in self.jobs:
                    del self.jobs[job.id]

    async def run(self):
        """Continuously process jobs with max concurrency of 5"""
        while not self._stop_event.is_set():
            # Clean up completed tasks first
            with self._lock:
                self._running_tasks = {
                    task for task in self._running_tasks
                    if not task.done()
                }

            # Get next batch of jobs if we have capacity
            available_slots = 5 - len(self._running_tasks)
            if available_slots > 0:
                with self._lock:
                    # Get jobs not currently running
                    running_ids = {
                        getattr(task, '_job_id', None)
                        for task in self._running_tasks
                    }
                    jobs_to_run = [
                                      job for job in self.jobs.values()
                                      if job.id not in running_ids
                                  ][:available_slots]

                # Start tasks for the new jobs
                for job in jobs_to_run:
                    task = asyncio.create_task(
                        self._execute_job(job),
                        name=f"job_{job.id}"  # Name tasks for better tracking
                    )
                    task._job_id = job.id  # Store job ID for tracking
                    with self._lock:
                        self._running_tasks.add(task)

            # Use wait instead of sleep when at max capacity
            if len(self._running_tasks) >= 5:
                await asyncio.wait(
                    self._running_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=1.0
                )
            else:
                await asyncio.sleep(0.1)  # Reduced sleep time


job_manager = JobManager()
job_manager.register_handler(JobType.FilePairGenerator, FilePairGeneratorHandler())
job_manager.register_handler(JobType.FileDeleteGenerator, FileDeleteGeneratorHandler())
job_manager.register_handler(JobType.GaPairGenerator, GaPairGeneratorHandler())
job_manager.register_handler(JobType.TagGenerator, TagGeneratorHandler())
job_manager.register_handler(JobType.QuestionGenerator, QuestionGeneratorHandler())
job_manager.register_handler(JobType.DatasetGenerator, DatasetGeneratorHandler())


async def start_job_manager():
    with manual_get_db() as session:
        jobs, total = job_db.list(session, None, 1, 9999, status=JobStatus.Running)
        for job in jobs:
            job_manager.add_job(job)
    # Start the manager
    await asyncio.create_task(job_manager.run())
