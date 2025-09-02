from typing import Optional

from fastapi import HTTPException

from app.api.middleware.context import get_current_locale
from app.db.dataset_db_model import project_db, ga_pair_db, file_db, job_db
from app.db.dataset_db_model.ga_pair_db import GAPairORM
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.ga_pair_model import GAPairList, GAPairItem, GAPairSave, GaPairGeneratorConfig
from sqlalchemy.orm import Session

from app.models.dataset_models.job_model import JobType, JobStatus
from app.models.user_model import User
from app.services.dataset_services.jobs.manager import job_manager


def list_ga_pair(session: Session, current_user: User, page_no: int, page_size: int, file_id: str) -> GAPairList:
    ga_pair_orm_list, total = ga_pair_db.list(session, current_user, page_no, page_size, file_id)
    return GAPairList(
        data=[GAPairItem(**ga_pair.to_dict()) for ga_pair in ga_pair_orm_list],
        count=total
    )


def save_ga_pair(session: Session, current_user: User, id: str = None, save_ga_pair: GAPairSave = None) -> Optional[
    GAPairItem]:
    project = project_db.get(session, current_user, save_ga_pair.project_id)
    if not project:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Project not found. id: {id}").format(id=save_ga_pair.project_id))
    file = file_db.get(session, current_user, save_ga_pair.file_id)
    if not file:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("File not found. id: {id}").format(id=save_ga_pair.file_id))

    if id == "" or id is None:
        item = ga_pair_db.create(session, current_user, GAPairORM(
            text_style=save_ga_pair.text_style,
            text_desc=save_ga_pair.text_desc,
            audience=save_ga_pair.audience,
            audience_desc=save_ga_pair.audience_desc,
            enable=save_ga_pair.enable,
            file_id=save_ga_pair.file_id,
            project_id=save_ga_pair.project_id,
        ))
    else:
        item = ga_pair_db.update(session, current_user, id, save_ga_pair.model_dump(exclude_unset=True))
    return GAPairItem(**item.to_dict())


def delete_ga_pair(session: Session, current_user: User, id: str) -> Optional[GAPairItem]:
    ga_pair_orm = ga_pair_db.delete(session, current_user, id)
    if ga_pair_orm:
        return GAPairItem(**ga_pair_orm.to_dict())
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("GA Pair not found. id: {id}").format(id=id))


def generate_ga_pair(session: Session, current_user: User, config: GaPairGeneratorConfig) -> str:
    if not config.file_ids or len(config.file_ids) <= 0:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Parameter verification failed. {param}").format(param="file_ids"))

    if config.project_id is None or config.project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("project_id param is required"))

    file_orm_list, _ = file_db.list(session, current_user, page_no=1, page_size=len(config.file_ids),
                                    project_id=config.project_id, file_ids=config.file_ids)
    for file_id in config.file_ids:
        if not any(file_id == file_orm.id for file_orm in file_orm_list):
            raise HTTPException(status_code=500, detail=i18n.gettext("File not found. id: {id}").format(id=id))

    job = job_db.create(session, current_user, JobORM(
        type=JobType.GaPairGenerator,
        status=JobStatus.Running,
        content=config.json(),
        locale=get_current_locale(),
        project_id=config.project_id,
    ))
    job_manager.add_job(job)
    return job.id
