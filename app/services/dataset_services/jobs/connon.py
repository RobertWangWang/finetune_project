import json
import logging
import traceback
from abc import ABC, abstractmethod

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import job_db
from app.db.dataset_db_model.job_db import JobORM
from app.models.dataset_models.job_model import JobResult, JobStatus
from app.models.user_model import User


def build_user(job: JobORM) -> User:
    return User(id=job.user_id, group_id=job.group_id)


def do_update_job_status(session, id: str, user: User, status: JobStatus, result: JobResult):
    job = job_db.get(session, user, id)

    try:
        # 执行日志拼接
        if job.result != "" and job.result:
            pre_result = JobResult(**json.loads(job.result))
            if result.logs == "" or result.logs is None:
                result.logs = pre_result.logs
            else:
                result.logs = pre_result.logs + "\n" + result.logs

            # 没有设置 progress 就设置为之前的 progress
            if result.progress is None:
                result.progress = pre_result.progress
    except Exception as e:
        traceback.print_exc()
        result.error += f"\n{str(e)}"
        logging.error(f"update_job_status failed. error: {str(e)}")

    job_db.update(session, user, id, {
        "status": status.name,
        "result": result.json(),
    })


def update_job_status(session, id: str, user: User, status: JobStatus, result: JobResult):
    if session:
        do_update_job_status(session, id, user, status, result)
    else:
        with manual_get_db() as session:
            do_update_job_status(session, id, user, status, result)
    result.clean_logs()


class JobHandlerInterface(ABC):

    @abstractmethod
    def execute(self, job: JobORM) -> JobORM:
        pass

    def done(self, job: JobORM):
        try:
            result = JobResult(**json.loads(job.result))
            update_job_status(None, job.id, build_user(job), JobStatus.Success, result)
        except Exception as e:
            traceback.print_exc()
            update_job_status(None, job.id, build_user(job), JobStatus.Failed, JobResult(
                logs="",
                error=f"\n{str(e)}"
            ))
