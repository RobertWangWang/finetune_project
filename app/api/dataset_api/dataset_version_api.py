import os

from fastapi import APIRouter, HTTPException
from typing import Any

from starlette.responses import FileResponse

from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.dataset_version_model import DatasetVersionList, DatasetVersionItem, \
    DatasetVersionCreate, DatasetVersionUpdate
from app.services.dataset_services import dataset_version_service

router = APIRouter(prefix="/dataset_versions", tags=["dataset_versions"])

@router.get(
    "/", response_model=DatasetVersionList, summary="查询数据集版本列表", description="返回数据集版本列表"
)
def list_dataset_version(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100, project_id: str = None, name: str = None) -> Any:
    dataset_versions = dataset_version_service.list_dataset_version(session, current_user, page, page_size, project_id, name)
    return dataset_versions

@router.get(
    "/{id}/download", summary="下载数据集", description="下载数据集"
)
def list_dataset_version(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    path = dataset_version_service.get_dataset_version_path(session, current_user, id)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        filename="dataset_version_file.jsonl",
        media_type="application/octet-stream"
    )

@router.post(
    "/", response_model=DatasetVersionItem, summary="创建数据集版本", description="创建数据集版本"
)
def create_dataset_version(session: SessionDep, current_user: CurrentUserDep, dataset_version_create: DatasetVersionCreate) -> Any:

    """
    class DatasetVersionCreate(BaseModel):
        name: str = Field(..., description="版本名称")
        description: str = Field(..., description="版本描述")

        project_id: str = Field(..., description="项目id")
        dataset_id_list: list[str] = Field(..., description="数据集列表")
        dataset_type: DatasetType = Field(..., description="数据集类型")

        options: dict = Field({}, description="版本配置")
    """

    if dataset_version_create.dataset_id_list is None or len(dataset_version_create.dataset_id_list) == 0:
        raise HTTPException(status_code=500, detail=i18n.gettext("Parameter verification failed. {param}").format(param="dataset_id_list"))
    dataset_version_item = dataset_version_service.create_dataset_version(session, current_user, dataset_version_create)
    return dataset_version_item


@router.put(
    "/{id}", response_model=DatasetVersionItem, summary="更新数据集版本", description="更新数据集版本"
)
def update_dataset_version(session: SessionDep, current_user: CurrentUserDep, id: str, dataset_version_update: DatasetVersionUpdate) -> Any:
    dataset_version_item = dataset_version_service.update_dataset_version(session, current_user, id, dataset_version_update)
    return dataset_version_item


@router.delete(
    "/{id}", response_model=DatasetVersionItem, summary="删除数据集版本", description="删除数据集版本"
)
def delete_dataset_version(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    dataset_version_item = dataset_version_service.delete_dataset_version(session, current_user, id)
    return dataset_version_item