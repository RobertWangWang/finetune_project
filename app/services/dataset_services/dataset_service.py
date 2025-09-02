import json
import threading

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.middleware.deps import manual_get_db
from app.db.dataset_db_model import dataset_db, file_pair_db, ga_pair_db
from app.lib.i18n.config import i18n
from app.models.dataset_models.dataset_model import DatasetList, DatasetItem, DatasetUpdate, BatchDeleteDatasetRequest
from app.models.dataset_models.ga_pair_model import GAPairOrigin
from app.models.user_model import User
from app.services.dataset_services.common_service import check_and_update_question_has_dataset
from app.services.dataset_services.file_pair_service import db_file_pair_to_item


def list_datasets(session: Session, current_user: User, page_no: int, page_size: int, project_id: str,
                  content: str = None, confirmed: str = None, ids: list[str] = None) -> DatasetList:
    dataset_list, total = dataset_db.list(session, current_user, page_no, page_size, project_id, content, confirmed, ids=ids)

    file_pair_id_list = []
    for dataset_orm in dataset_list:
        file_pair_id_list.append(dataset_orm.file_pair_id)

    file_pair_map = file_pair_db.list_file_pair_to_map(session, current_user, file_pair_id_list)

    items: list[DatasetItem] = []
    for dataset_orm in dataset_list:
        dataset = DatasetItem(
            id=dataset_orm.id,
            question=dataset_orm.question,
            answer=dataset_orm.answer,
            cot=dataset_orm.cot,
            question_id=dataset_orm.question_id,
            tag_name=dataset_orm.tag_name,

            model=dataset_orm.model,
            confirmed=dataset_orm.confirmed,

            file_id=dataset_orm.file_id,

            created_at=dataset_orm.created_at,
            updated_at=dataset_orm.updated_at,
        )

        file_pair = file_pair_map.get(dataset_orm.file_pair_id)
        if file_pair:
            dataset.file_pair_item = db_file_pair_to_item(file_pair)

        if dataset_orm.ga_pair and dataset_orm.ga_pair != "":
            dataset.ga_pair_item = GAPairOrigin(**json.loads(dataset_orm.ga_pair))

        items.append(dataset)

    return DatasetList(count=total, data=items)


def delete_dataset(session: Session, current_user: User, id: str) -> DatasetItem:
    dataset_orm = dataset_db.delete(session, current_user, id)
    if dataset_orm:
        check_and_update_question_has_dataset(session, current_user, dataset_orm.question_id)
        return DatasetItem(**dataset_orm.to_dict())
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("Dataset not found. id: {id}").format(id=id))


def batch_delete_dataset(session: Session, current_user: User, req: BatchDeleteDatasetRequest):
    dataset_list_orm = dataset_db.list(session, current_user, 1, len(req.dataset_ids), project_id=req.project_id,
                                       ids=req.dataset_ids)
    if dataset_list_orm and len(dataset_list_orm) > 0:
        dataset_db.bulk_delete_datasets(session, current_user, req.dataset_ids)

        def async_delete_task():
            try:
                with manual_get_db() as session:
                    for dataset_orm in dataset_list_orm:
                        check_and_update_question_has_dataset(session, User(
                            id=dataset_orm.user_id,
                            group_id=dataset_orm.group_id
                        ), dataset_orm.question_id)
            except Exception as e:
                print(f"异步删除数据集出错: {e}")

        threading.Thread(target=async_delete_task, daemon=True).start()


def update_dataset(session: Session, current_user: User, id: str, dataset_update: DatasetUpdate) -> DatasetItem:
    dataset_orm = dataset_db.update(session, current_user, id, dataset_update.model_dump(exclude_unset=True))
    if not dataset_orm:
        raise HTTPException(status_code=500, detail=i18n.gettext("Dataset not found. id: {id}").format(id=id))
    return DatasetItem(**dataset_orm.to_dict())
