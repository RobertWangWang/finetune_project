from fastapi import APIRouter
from typing import Any, Generator, List


from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.models.llamafactory_models.release_model import ReleaseList, ReleaseItem, ReleaseUpdate
from app.services.llamafactory_services import release_service

router = APIRouter(prefix="/release", tags=["release"])

@router.get(
    "/", response_model=ReleaseList, summary="查询微调制品列表", description="查询微调制品列表"
)
def list_release(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100, name: str = None, finetune_type: str = None) -> Any:
    return release_service.list_release(session, current_user, page, page_size, name, finetune_type)


@router.put(
    "/{id}", response_model=ReleaseItem, summary="更新微调制品版本", description="更新微调制品版本"
)
def update_release(session: SessionDep, current_user: CurrentUserDep, id: str, update: ReleaseUpdate) -> Any:
    return release_service.update_release(session, current_user, id, update)
