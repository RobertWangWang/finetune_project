# app/api/evaluation_api/evaluation_api.py
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.evaluation_models.evaluation_model import (
    EvaluationList, EvaluationItem, EvaluationCreate, EvaluationUpdate, EvaluationRun
)
from app.services.evaluation_services import evaluation_service

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/", response_model=EvaluationList, summary="查询评估任务列表")
def list_evaluations(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = 1,
    page_size: int = 100,
    project_id: Optional[str] = None,
    tag_name: Optional[str] = None,
    model: Optional[str] = None,
) -> Any:
    if not project_id:
        raise HTTPException(status_code=400, detail=i18n.gettext("project_id is required"))
    return evaluation_service.list_evaluations(session, current_user, page, page_size, project_id, tag_name, model)


@router.get("/{id}", response_model=EvaluationItem, summary="查询评估任务详情")
def get_evaluation(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return evaluation_service.get_evaluation(session, current_user, id)


@router.post("/", response_model=EvaluationItem, summary="创建评估任务（不自动执行）")
def create_evaluation(session: SessionDep, current_user: CurrentUserDep, create: EvaluationCreate) -> Any:
    return evaluation_service.create_evaluation(session, current_user, create)


@router.patch("/{id}", response_model=EvaluationItem, summary="更新评估任务")
def update_evaluation(session: SessionDep, current_user: CurrentUserDep, id: str, update: EvaluationUpdate) -> Any:
    return evaluation_service.update_evaluation(session, current_user, id, update)


@router.delete("/{id}", response_model=EvaluationItem, summary="删除评估任务")
def delete_evaluation(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return evaluation_service.delete_evaluation(session, current_user, id)


@router.post("/{id}/run", response_model=EvaluationItem,
             summary="运行评测（命令行动态加载 LoRA + 批量推理 + 计算指标）")
def run_evaluation(session: SessionDep, current_user: CurrentUserDep, id: str, body: EvaluationRun) -> Any:
    return evaluation_service.run_evaluation(session, current_user, id, body)
