from fastapi import APIRouter
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.models.llamafactory_models.finetune_config_model import FinetuneConfigList, FinetuneConfigItem, FinetuneConfigSave
from app.services.llamafactory_services import finetune_config_service

router = APIRouter(prefix="/finetune_configs", tags=["finetune_configs"])

@router.get(
    "/", response_model=FinetuneConfigList, summary="查询微调配置列表", description="返回微调配置列表"
)
def list_finetune_config(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100, module: str = None,
                         config_type: str = None, name: str = None) -> Any:
    finetune_configs = finetune_config_service.list_finetune_config(session, current_user, page, page_size, module, config_type, name)
    return finetune_configs


@router.post(
    "/", response_model=FinetuneConfigItem, summary="创建微调配置", description="创建微调配置"
)
def create_finetune_config(session: SessionDep, current_user: CurrentUserDep, save: FinetuneConfigSave) -> Any:
    finetune_config_item = finetune_config_service.create_finetune_config(session, current_user, save)
    return finetune_config_item


@router.put(
    "/{id}", response_model=FinetuneConfigItem, summary="更新微调配置", description="更新微调配置"
)
def update_finetune_config(session: SessionDep, current_user: CurrentUserDep, id: str, save: FinetuneConfigSave) -> Any:
    finetune_config_item = finetune_config_service.update_finetune_config(session, current_user, id, save)
    return finetune_config_item


@router.delete(
    "/{id}", response_model=FinetuneConfigItem, summary="删除微调配置", description="删除微调配置"
)
def delete_finetune_config(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    finetune_config_item = finetune_config_service.delete_finetune_config(session, current_user, id)
    return finetune_config_item