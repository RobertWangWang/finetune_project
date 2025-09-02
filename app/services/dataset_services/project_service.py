from typing import Optional

from fastapi import HTTPException

from app.db.dataset_db_model import project_db, file_db, file_pair_db, question_db, dataset_db, ga_pair_db
from app.db.dataset_db_model.project_db import ProjectORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.project_model import ProjectList, ProjectItem, ProjectCreate, ProjectUpdate
from sqlalchemy.orm import Session

from app.models.user_model import User


def list_project(session: Session, current_user: User, page_no: int, page_size: int) -> ProjectList:
    project_orm_list, total = project_db.list(session, current_user, page_no, page_size, None)
    return ProjectList(
        data=[ProjectItem(**project.to_dict()) for project in project_orm_list],
        count=total
    )


def create_project(session: Session, current_user: User, project_create: ProjectCreate) -> Optional[ProjectItem]:
    project_orm = project_db.create(session, current_user, ProjectORM(
        name=project_create.name,
    ))
    return ProjectItem(**project_orm.to_dict())


def update_project(session: Session, current_user: User, project_update: ProjectUpdate) -> Optional[ProjectItem]:
    project_orm = project_db.update(session, current_user, project_update.id, project_update.model_dump(exclude_unset=True))
    if not project_orm:
        raise HTTPException(status_code=500, detail=i18n.gettext("Project not found. id: {id}").format(id=project_update.id))
    return ProjectItem(**project_orm.to_dict())


def delete_project(session: Session, current_user: User, project_id: str) -> Optional[ProjectItem]:
    file_db.bulk_delete_files(session, current_user, [project_id])
    file_pair_db.bulk_delete_file_pairs(session, current_user, [project_id])
    question_db.bulk_delete_questions(session, current_user, [project_id])
    dataset_db.bulk_delete_datasets(session, current_user, [project_id])
    ga_pair_db.bulk_delete_ga_pairs(session, current_user, [project_id])

    project_orm = project_db.delete(session, current_user, project_id)
    if project_orm:
        return ProjectItem(**project_orm.to_dict())
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("Project not found. id: {id}").format(id=project_id))


def get_project(session: Session, current_user: User, project_id: str) -> Optional[ProjectItem]:
    project_orm = project_db.get(session, current_user, project_id)
    if project_orm:
        return ProjectItem(**project_orm.to_dict())
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("Project not found. id: {id}").format(id=project_id))
