from fastapi import APIRouter, HTTPException
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.ga_pair_model import GAPairList, GAPairSave, GAPairItem, GaPairGeneratorConfig
from app.services.dataset_services import ga_pair_service

router = APIRouter(prefix="/ga_pairs", tags=["ga_pairs"])

@router.get(
    "/", response_model=GAPairList, summary="查询 GA Pair 列表", description="返回 GA Pair 列表"
)
def list_ga_pair(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100, file_id: str = None) -> Any:
    if file_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("file_id cannot be empty"))

    ga_pairs = ga_pair_service.list_ga_pair(session, current_user, page, page_size, file_id)
    return ga_pairs


@router.post(
    "/", response_model=GAPairItem, summary="创建 GA Pair", description="创建 GA Pair"
)
def create_ga_pair(session: SessionDep, current_user: CurrentUserDep, ga_pair_save: GAPairSave) -> Any:
    ga_pairs = ga_pair_service.save_ga_pair(session, current_user, None, save_ga_pair=ga_pair_save)
    return ga_pairs


@router.put(
    "/{id}", response_model=GAPairItem, summary="更新 GA Pair", description="更新 GA Pair"
)
def update_ga_pair(session: SessionDep, current_user: CurrentUserDep, id: str, ga_pair_save: GAPairSave) -> Any:
    ga_pairs = ga_pair_service.save_ga_pair(session, current_user, id, save_ga_pair=ga_pair_save)
    return ga_pairs


@router.delete(
    "/{id}", response_model=GAPairItem, summary="删除 GA Pair", description="删除 GA Pair"
)
def delete_ga_pair(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    ga_pairs = ga_pair_service.delete_ga_pair(session, current_user, id)
    return ga_pairs


@router.post(
    "/generator", response_model=str, summary="生成 GA Pair", description="生成 GA Pair"
)
def generator_ga_pair(session: SessionDep, current_user: CurrentUserDep, config: GaPairGeneratorConfig) -> Any:
    job_id = ga_pair_service.generate_ga_pair(session, current_user, config)
    return job_id
