from fastapi import APIRouter, HTTPException
from typing import Any, List
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.tag_model import TagItem, TagCreate, TagUpdate
from app.services.dataset_services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "/all", response_model=List[TagItem], summary="查询所有标签", description="查询所有标签"
)
def list_all_tag(session: SessionDep, current_user: CurrentUserDep, project_id: str) -> Any:
    if project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("Project_id param is required"))
    tags = tag_service.get_all_tags(session, current_user, project_id)
    return tags


@router.post(
    "/", response_model=TagItem, summary="创建标签", description="创建标签"
)
def create_tag(session: SessionDep, current_user: CurrentUserDep, tag_create: TagCreate) -> Any:
    tag = tag_service.create_tag(session, current_user, tag_create)
    return tag


@router.put(
    "/{id}", response_model=TagItem, summary="更新标签", description="更新标签"
)
def update_tag(session: SessionDep, current_user: CurrentUserDep, id: str, tag_update: TagUpdate) -> Any:
    tag = tag_service.update_tag(session, current_user, id, tag_update)
    return tag


@router.delete(
    "/{id}", response_model=TagItem, summary="删除标签", description="删除标签"
)
def delete_tag(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    tag = tag_service.delete_tag(session, current_user, id)
    return tag
