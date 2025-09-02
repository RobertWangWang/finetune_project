import json

from fastapi import HTTPException

from app.api.middleware.context import get_current_locale
from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import question_db, file_pair_db, dataset_db, tag_db, job_db
from sqlalchemy.orm import Session

from app.db.dataset_db_model.job_db import JobORM
from app.db.dataset_db_model.question_db import QuestionORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.ga_pair_model import GAPairOrigin
from app.models.dataset_models.question_model import QuestionList, QuestionItem, QuestionSave, \
    BatchDeleteRequest, DatasetGeneratorRequest
from app.models.dataset_models.job_model import JobStatus, JobType
from app.models.user_model import User
from app.services.dataset_services.file_pair_service import db_file_pair_to_item
from app.services.dataset_services.jobs.manager import job_manager


def question_or_to_item(question_orm: QuestionORM, file_pair_map: dict) -> QuestionItem:
    question = QuestionItem(
        id=question_orm.id,

        question=question_orm.question,
        file_id=question_orm.file_id,

        tag_name=question_orm.tag_name,

        created_at=question_orm.created_at,
        updated_at=question_orm.updated_at,
    )

    if question_orm.ga_pair and question_orm.ga_pair != "":
        question.ga_pair_item = GAPairOrigin(**json.loads(question_orm.ga_pair))

    file_pair = file_pair_map.get(question_orm.file_pair_id)
    if file_pair:
        question.file_pair_item = db_file_pair_to_item(file_pair)

    if question_orm.has_dataset:
        with manual_get_db() as session:
            dataset_list_orm, _ = dataset_db.list(session, User(
                id=question_orm.user_id,
                group_id=question_orm.group_id,
            ), 1, 9999, project_id=question_orm.project_id,
                                                  question_id=question_orm.id)
            if dataset_list_orm and len(dataset_list_orm) > 0:
                question.dataset_id_list = [dataset.id for dataset in dataset_list_orm]
    else:
        question.dataset_id_list = []
    return question


def list_question(session: Session, current_user: User, page_no: int, page_size: int, project_id: str, question: str,
                  label: str) -> QuestionList:
    question_orm_list, total = question_db.list(session, current_user, page_no, page_size, project_id, question, label)

    file_pair_id_list = []
    for question_orm in question_orm_list:
        file_pair_id_list.append(question_orm.file_pair_id)

    file_pair_map = file_pair_db.list_file_pair_to_map(session, current_user, file_pair_id_list)

    items: list[QuestionItem] = []
    for question_orm in question_orm_list:
        question = question_or_to_item(question_orm, file_pair_map)
        items.append(question)

    return QuestionList(count=total, data=items)


def delete_question(session: Session, current_user: User, id: str) -> QuestionItem:
    dataset_db.bulk_delete_datasets(session, current_user, question_ids=[id])

    question_orm = question_db.delete(session, current_user, id)
    if question_orm:
        return QuestionItem(**question_orm.to_dict())
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("Question not found. id: {id}").format(id=id))


def batch_delete_questions(session: Session, current_user: User, req: BatchDeleteRequest):
    question_orm_list, total = question_db.list(session, current_user, 1, len(req.question_ids), req.project_id,
                                                id_list=req.question_ids)
    dataset_db.bulk_delete_datasets(session, current_user,
                                    question_ids=[question_orm.id for question_orm in question_orm_list])
    question_db.bulk_delete_questions(session, current_user, id_list=req.question_ids)


def update_question(session: Session, current_user: User, id: str, question_update: QuestionSave) -> QuestionItem:
    return save_question(session, current_user, id, question_update)


def create_question(session: Session, current_user: User, question_update: QuestionSave) -> QuestionItem:
    return save_question(session, current_user, "", question_update)


def save_question(session: Session, current_user: User, id: str, question_update: QuestionSave) -> QuestionItem:
    file_pair_map = file_pair_db.list_file_pair_to_map(session, current_user, [question_update.file_pair_id])
    tag_orm = tag_db.get(session, current_user, question_update.tag_id)
    if id is None or id == "":
        file_pair = file_pair_map.get(question_update.file_pair_id)
        question_orm = question_db.create(session, current_user, QuestionORM(
            question=question_update.question,
            tag_name=tag_orm.label,
            file_pair_id=file_pair.id,
            file_id=file_pair.file_id,
            project_id=file_pair.project_id,
            ga_pair=""
        ))
    else:
        question_orm = question_db.update(session, current_user, id, {
            "question": question_update.question,
            "tag_name": tag_orm.label,
            "file_pair_id": question_update.file_pair_id
        })
    return question_or_to_item(question_orm, file_pair_map)


def dataset_generator(session: Session, current_user: User, req: DatasetGeneratorRequest) -> str:
    job = job_db.create(session, current_user, JobORM(
        type=JobType.DatasetGenerator,
        status=JobStatus.Running,
        content=req.json(),
        locale=get_current_locale(),
        project_id=req.project_id,
    ))
    job_manager.add_job(job)
    return job.id