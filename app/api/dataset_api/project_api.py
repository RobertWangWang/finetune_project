from fastapi import APIRouter
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.models.dataset_models.project_model import ProjectList, ProjectItem, ProjectCreate, ProjectUpdate
from app.services.dataset_services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get(
    "/", response_model=ProjectList, summary="查询项目列表", description="返回项目列表"
)
def list_project(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100) -> Any:
    projects = project_service.list_project(session, current_user, page, page_size)
    return projects


@router.get(
    "/{id}", response_model=ProjectItem, summary="获取单个项目", description="获取单个项目"
            )
def get_project(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    project_item = project_service.get_project(session, current_user, id)
    return project_item


@router.post(
    "/", response_model=ProjectItem, summary="创建项目", description="创建项目"
)
def create_project(session: SessionDep, current_user: CurrentUserDep, project_create: ProjectCreate) -> Any:
    project_item = project_service.create_project(session, current_user, project_create)
    return project_item


@router.put(
    "/{id}", response_model=ProjectItem, summary="更新项目", description="更新项目"
)
def update_project(session: SessionDep, current_user: CurrentUserDep, id: str, project_update: ProjectUpdate) -> Any:
    project_update.id = id
    project_item = project_service.update_project(session, current_user, project_update)
    return project_item


@router.delete(
    "/{id}", response_model=ProjectItem, summary="删除项目", description="删除项目"
)
def delete_project(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    project_item = project_service.delete_project(session, current_user, id)
    return project_item