from __future__ import annotations
from fastapi import status, Query, Path
from fastapi import APIRouter, HTTPException
from loguru import logger

# 根据项目结构调整导入路径
from app.api.middleware.deps import SessionDep, CurrentUserDep

from app.models.evaluation_models.evaluation_dataset_model import (
    EvaluationDatasetCreate,
    EvaluationDatasetUpdate,
    EvaluationDatasetOut,
    EvaluationDatasetListQuery,
    EvaluationDatasetListOut,
)

from app.services.evaluation_services.evaluation_dataset_service import (
    list_evaluation_datasets,
    get_evaluation_dataset,
    create_evaluation_dataset,
    update_evaluation_dataset,
    delete_evaluation_dataset,
)


router = APIRouter(prefix="/evaluation_datasets", tags=["EvaluationDatasets"])


@router.get("/", response_model=EvaluationDatasetListOut, summary="分页获取数据集列表")
def list_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    page_no: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(100, ge=1, le=1000, description="每页数量"),
    eval_type: str | None = Query(None, description="按评测类型过滤"),
    current_role: str | None = Query(None, description="按角色过滤（system/user）"),
):
    """
    分页获取 EvaluationDataset 列表。
    过滤字段与 ORM 保持一致。
    """
    query = EvaluationDatasetListQuery(
        page_no=page_no,
        page_size=page_size,
        eval_type=eval_type,
        current_role=current_role,
    )
    return list_evaluation_datasets(session=session, current_user=current_user, query=query)


@router.get("/{dataset_id}", response_model=EvaluationDatasetOut, summary="获取数据集详情")
def get_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    dataset_id: str = Path(..., description="数据集ID"),
):
    row = get_evaluation_dataset(session=session, current_user=current_user, dataset_id=dataset_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationDataset not found")
    return row


@router.post("/", response_model=EvaluationDatasetOut, status_code=status.HTTP_201_CREATED, summary="创建数据集")
def create_api(
    payload: EvaluationDatasetCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    logger.info(f"创建 EvaluationDataset 请求: {payload}")
    return create_evaluation_dataset(session=session, current_user=current_user, data=payload)


@router.patch("/{dataset_id}", response_model=EvaluationDatasetOut, summary="更新数据集（部分字段）")
def patch_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    dataset_id: str = Path(..., description="数据集ID"),
    patch: EvaluationDatasetUpdate = ...,
):
    updated = update_evaluation_dataset(
        session=session,
        current_user=current_user,
        dataset_id=dataset_id,
        patch=patch,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationDataset not found")
    return updated


@router.delete("/{dataset_id}", response_model=EvaluationDatasetOut, summary="删除数据集（软删除）")
def delete_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    dataset_id: str = Path(..., description="数据集ID"),
):
    deleted = delete_evaluation_dataset(session=session, current_user=current_user, dataset_id=dataset_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EvaluationDataset not found")
    return deleted
