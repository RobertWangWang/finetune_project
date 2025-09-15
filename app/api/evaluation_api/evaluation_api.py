# app/api/v1/evaluations.py
from __future__ import annotations
from fastapi import status, Query, Path
from fastapi import APIRouter, HTTPException
from loguru import logger
from starlette.responses import JSONResponse

# 根据你的项目结构调整导入路径：
# - SessionDep / CurrentUserDep: 你项目里的 FastAPI 依赖（示例：app.api.deps）
# - User: 当前登录用户模型（仅作类型提示）
from app.api.middleware.deps import SessionDep, CurrentUserDep # 常见写法
from app.models.evaluation_models.evaluation_model import (
    EvaluationCreate,
    EvaluationUpdate,
    EvaluationOut,
    EvaluationListQuery,
    EvaluationListOut,
    DatasetEvaluationRequest
)
from app.services.evaluation_services.evaluation_service import (
    list_evaluations,
    get_evaluation,
    create_evaluation,
    update_evaluation,
    delete_evaluation,
    evaluate_model_on_dataset
)

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get("/", response_model=EvaluationListOut, summary="分页获取评测列表")
def list_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    page_no: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(100, ge=1, le=1000, description="每页数量"),
    dataset_version_id: str | None = Query(None, description="按项目过滤"),
    tag_name: str | None = Query(None, description="按标签过滤"),
    model: str | None = Query(None, description="按模型过滤"),
):
    """
    与 service 层参数保持一致。
    如若你的 ORM 过滤字段未来更换为 dataset_version_id/eval_type/eval_model_id，
    只需在这里把查询参数改名并传给 `EvaluationListQuery` 即可。
    """
    query = EvaluationListQuery(
        page_no=page_no,
        page_size=page_size,
        dataset_version_id=dataset_version_id,
        tag_name=tag_name,
        model=model,
    )
    return list_evaluations(session=session, current_user=current_user, query=query)


@router.get("/{evaluation_id}", response_model=EvaluationOut, summary="获取评测详情")
def get_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    evaluation_id: str = Path(..., description="评测ID"),

):
    row = get_evaluation(session=session, current_user=current_user, evaluation_id=evaluation_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return row


@router.post("/", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED, summary="创建评测")
def create_api(
    payload: EvaluationCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    logger.info(payload)
    return create_evaluation(session=session, current_user=current_user, data=payload)


@router.patch("/{evaluation_id}", response_model=EvaluationOut, summary="更新评测（部分字段）")
def patch_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    evaluation_id: str = Path(..., description="评测ID"),
    patch: EvaluationUpdate = ...,
):
    updated = update_evaluation(session=session, current_user=current_user, evaluation_id=evaluation_id, patch=patch)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return updated


@router.delete("/{evaluation_id}", response_model=EvaluationOut, summary="删除评测（软删除）")
def delete_api(
    session: SessionDep,
    current_user: CurrentUserDep,
    evaluation_id: str = Path(..., description="评测ID"),
):
    deleted = delete_evaluation(session=session, current_user=current_user, evaluation_id=evaluation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return deleted


@router.post("/evaluate_dataset", summary="在指定机器上运行数据集评测")
async def evaluate_dataset(
    payload: DatasetEvaluationRequest,
    session: SessionDep,
    current_user: CurrentUserDep
):
    """
    接收 DatasetEvaluationRequest 请求体，调用 service 执行数据集评测
    """
    try:
        result = await evaluate_model_on_dataset(
            db=session,
            current_user=current_user,
            request=payload
        )
        return JSONResponse(content={
            "status": "success",
            "message": "数据集评测完成 ✅",
            "data": result
        }, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))