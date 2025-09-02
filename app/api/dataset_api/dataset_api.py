from fastapi import APIRouter, HTTPException
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.dataset_model import DatasetList, DatasetItem, DatasetUpdate
from app.services.dataset_services import dataset_service

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get(
    "/", response_model=DatasetList, summary="查询所有数据集列表", description="查询所有数据集列表"
)
def list_dataset(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100,
                        project_id: str = None, content: str = None, confirmed: str = None) -> Any:
    if project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("Project_id param is required"))
    dataset_list = dataset_service.list_datasets(session, current_user, page, page_size, project_id, content, confirmed)
    return dataset_list


@router.put(
    "/{id}", response_model=DatasetItem, summary="更新数据库", description="更新数据库"
)
def update_dataset(session: SessionDep, current_user: CurrentUserDep, id: str,
                     update: DatasetUpdate) -> Any:
    dataset = dataset_service.update_dataset(session, current_user, id, update)
    return dataset


@router.delete(
    "/{id}", response_model=DatasetItem, summary="删除数据集", description="删除数据集"
)
def delete_dataset(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    dataset = dataset_service.delete_dataset(session, current_user, id)
    return dataset
