import json
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.middleware.context import get_current_locale
from app.db.dataset_db_model import file_pair_db, question_db, dataset_db, file_db, project_db, job_db
from app.db.dataset_db_model.file_pair_db import FilePairORM
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.file_pair_model import FilePairList, FilePairItem, FilePairExportRequest, \
    FilePairExportItem, FilePairQuestionGeneratorContent, FilePairUpdate
from app.models.dataset_models.job_model import JobType, JobStatus
from app.models.user_model import User
from app.services.dataset_services.jobs.manager import job_manager


def db_file_pair_to_item(item: FilePairORM) -> FilePairItem:
    file_pair = FilePairItem(
        id=item.id,
        size=item.size,
        content=item.content,
        summary=item.summary,
        name=item.name,
        chunk_index=item.chunk_index,

        file_id=item.file_id,

        created_at=item.created_at,
        updated_at=item.updated_at,
    )
    if item.question_id_list != "" and item.question_id_list:
        file_pair.question_id_list = item.question_id_list.split(",")
    return file_pair


def list_file_pairs(session: Session, current_user: User, page_no: int, page_size: int, project_id: str,
                          file_ids: List[str], has_question: str) -> FilePairList:
    file_pair_orm_list, total = file_pair_db.list(session, current_user, page_no, page_size, project_id, file_ids,
                                                  has_question)

    file_pair_list = FilePairList(
        count=total,
        data=[],
    )
    for item in file_pair_orm_list:
        file_pair = db_file_pair_to_item(item)
        file_pair_list.data.append(file_pair)

    return file_pair_list


def delete_file_pair(session: Session, current_user: User, id: str) -> FilePairItem:
    question_db.bulk_delete_questions(session, current_user, file_pair_ids=[id])
    dataset_db.bulk_delete_datasets(session, current_user, file_pair_ids=[id])

    file_pair = file_pair_db.delete(session, current_user, id)
    if file_pair:
        return db_file_pair_to_item(file_pair)
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("File pair not found. id: {id}").format(id=id))


def update_file_pair(session: Session, current_user: User, id: str, file_pair: FilePairUpdate) -> FilePairItem:
    file_pair_orm = file_pair_db.update(session, current_user, id, file_pair.model_dump(exclude_unset=True))

    if not file_pair_orm:
        raise HTTPException(status_code=500, detail=i18n.gettext("File pair not found. id: {id}").format(id=id))

    return db_file_pair_to_item(file_pair_orm)


def file_pair_export(session: Session, current_user: User, export_req: FilePairExportRequest) -> str:
    project = project_db.get(session, current_user, export_req.project_id)

    pairs_orm, total = file_pair_db.list(session, current_user, 1, len(export_req.file_pair_ids), project_id=export_req.project_id, id_list=export_req.file_pair_ids)

    file_ids: [str] = []
    for pair in pairs_orm:
        file_ids.append(pair.file_id)
    files_orm, _ = file_db.list(session, current_user, 1, len(file_ids), file_ids=file_ids)
    file_map = {file.id: file for file in files_orm}

    items: [dict] = []
    for pair in pairs_orm:
        item = FilePairExportItem(
            **pair.to_dict()
        )
        item.project_name = project.name
        file = file_map.get(pair.file_id)
        if file:
            item.file_name = file.file_name
        items.append(item.dict())

    return json.dumps(items, indent=2, ensure_ascii=False)


def question_generator(session: Session, current_user: User, req: FilePairQuestionGeneratorContent) -> str:
    job = job_db.create(session, current_user, JobORM(
        type=JobType.QuestionGenerator,
        status=JobStatus.Running,
        content=req.json(),
        locale=get_current_locale(),
        project_id=req.project_id,
    ))
    job_manager.add_job(job)
    return job.id
