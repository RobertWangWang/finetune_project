from app.db.dataset_db_model.job_db import JobORM
from app.services.dataset_services.jobs.connon import JobHandlerInterface


class TagGeneratorHandler(JobHandlerInterface):
    def execute(self, job: JobORM) -> JobORM:
        pass

