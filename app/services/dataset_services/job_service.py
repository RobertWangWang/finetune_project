import json

from fastapi import HTTPException

from app.db.dataset_db_model import job_db
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.job_model import JobList, JobItem, JobResult, JobStatus
from sqlalchemy.orm import Session

from app.models.user_model import User
from app.services.dataset_services.jobs.manager import job_manager


def job_orm_to_model(item: JobORM) -> JobItem:
    job_item = JobItem(
        id=item.id,

        type=item.type,
        status=item.status,
        locale=item.locale,
        content=item.content,

        project_id=item.project_id,
    )
    if item.result != "":
        job_item.result = JobResult(**json.loads(item.result))
    return job_item


def list_job(session: Session, current_user: User, page_no: int, page_size: int, project_id: str) -> JobList:
    job_orm_list, total = job_db.list(session, current_user, page_no, page_size, project_id)

    result = JobList(
        count=total,
        data=[job_orm_to_model(item) for item in job_orm_list]
    )
    return result

#### 长时间jobmanager的创建

def delete_job(session: Session, current_user: User, id: str) -> JobItem:
    job = job_db.get(session, current_user, id)
    if job is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Job not found. id: {id}").format(id=id))
    if job.status == JobStatus.Running:
        raise HTTPException(status_code=500, detail=i18n.gettext("Running tasks cannot be deleted, please stop first"))
    orm = job_db.delete(session, current_user, id)
    return job_orm_to_model(orm)


def cancel_job(session: Session, current_user: User, id: str) -> JobItem:
    job = job_db.get(session, current_user, id)
    if job is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Job not found. id: {id}").format(id=id))
    if job.status != JobStatus.Running:
        raise HTTPException(status_code=500, detail=i18n.gettext("Only running tasks can be stopped"))

    job = job_db.update(session, current_user, id, {
        "status": JobStatus.Cancel.name
    })
    job_manager.cancel_job(id)
    return job_orm_to_model(job)
