from fastapi import APIRouter
from typing import Any
from app.api.middleware.deps import CurrentUserDep, ModelSessionDep
from app.models.common_models.llm_model import LLMModelList, LLMItem, \
    LLMSaveRequest
from app.services.common_services import model_service

router = APIRouter(prefix="/llms", tags=["llms"])

@router.get(
    "/", response_model=LLMModelList, summary="查询模型列表", description="返回模型列表"
)
def list_llm(session: ModelSessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100) -> Any:
    return model_service.list_model(session, current_user, page, page_size)


@router.post(
    "/", response_model=LLMItem, summary="创建模型", description="创建模型"
)
def create_llm(session: ModelSessionDep, current_user: CurrentUserDep, create: LLMSaveRequest) -> Any:
    item = model_service.create_model(session, current_user, create)
    return item


@router.put(
    "/{id}", response_model=LLMItem, summary="更新模型", description="更新模型"
)
def update_llm(session: ModelSessionDep, current_user: CurrentUserDep, id: str, update: LLMSaveRequest) -> Any:
    return model_service.update_model(session, current_user, id, update)

@router.delete(
    "/{id}", response_model=LLMItem, summary="删除模型", description="删除模型"
)
def delete_llm(session: ModelSessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return model_service.delete_model(session, current_user, id)


@router.post(
    "/{id}/set_default", response_model=str, summary="设置默认模型", description="设置默认模型"
)
def set_default_llm(session: ModelSessionDep, current_user: CurrentUserDep, id: str) -> Any:
    model_service.set_default_llm(session, current_user, id)
    return "success"