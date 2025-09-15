from typing import Optional
from sqlalchemy.orm import Session

from app.db.evaluation_db_model.evaluation_dataset_db import EvaluationDataset
from app.models.user_model import User
from app.db.evaluation_db_model.evaluation_dataset_db import (
    list_datasets as orm_list,
    get_dataset as orm_get,
    create_dataset as orm_create,
    update_dataset as orm_update,
    delete_dataset as orm_delete,
)
from app.models.evaluation_models.evaluation_dataset_model import (
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    EvaluationDatasetOut,
    EvaluationDatasetListQuery,
    EvaluationDatasetListOut,
)


# ------------------- CRUD for routes to call ------------------- #
def list_evaluation_datasets(
    session: Session,
    current_user: User,
    query: EvaluationDatasetListQuery
) -> EvaluationDatasetListOut:
    """
    分页查询 EvaluationDataset
    """
    rows, total = orm_list(
        session=session,
        current_user=current_user,
        page_no=query.page_no,
        page_size=query.page_size,
        eval_type=query.eval_type,
        current_role=query.current_role,
    )

    items = [EvaluationDatasetOut.model_validate(r) for r in rows]
    return EvaluationDatasetListOut(items=items, total=total)


def get_evaluation_dataset(
    session: Session,
    current_user: User,
    dataset_id: str
) -> Optional[EvaluationDatasetOut]:
    """
    根据 ID 获取单条 EvaluationDataset
    """
    row = orm_get(session=session, current_user=current_user, dataset_id=dataset_id)
    return EvaluationDatasetOut.model_validate(row) if row else None


def create_evaluation_dataset(
    session: Session,
    current_user: User,
    data: EvaluationDatasetCreate
) -> EvaluationDatasetOut:
    """
    创建 EvaluationDataset
    """
    dataset = EvaluationDataset()
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(dataset, k, v)

    created = orm_create(session=session, current_user=current_user, dataset=dataset)
    return EvaluationDatasetOut.model_validate(created)


def update_evaluation_dataset(
    session: Session,
    current_user: User,
    dataset_id: str,
    patch: EvaluationDatasetUpdate
) -> Optional[EvaluationDatasetOut]:
    """
    更新 EvaluationDataset
    """
    payload = patch.model_dump(exclude_none=True)
    updated = orm_update(
        session=session,
        current_user=current_user,
        dataset_id=dataset_id,
        update_data=payload
    )
    return EvaluationDatasetOut.model_validate(updated) if updated else None


def delete_evaluation_dataset(
    session: Session,
    current_user: User,
    dataset_id: str
) -> Optional[EvaluationDatasetOut]:
    """
    删除 EvaluationDataset（软删除）
    """
    deleted = orm_delete(session=session, current_user=current_user, dataset_id=dataset_id)
    return EvaluationDatasetOut.model_validate(deleted) if deleted else None
