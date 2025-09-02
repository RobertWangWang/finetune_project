from fastapi import APIRouter, HTTPException
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.job_model import JobList, JobItem
from app.services.dataset_services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get(
    "/", response_model=JobList, summary="查询任务列表", description="查询任务列表"
)
def list_job(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100, project_id: str = None) -> Any:
    if project_id == "":
        raise HTTPException(500, detail=i18n.gettext("Project_id param is required"))
    return job_service.list_job(session, current_user, page, page_size, project_id)


@router.delete(
    "/{id}", response_model=JobItem, summary="删除任务", description="删除任务"
)
def delete_job(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return job_service.delete_job(session, current_user, id)


@router.post(
    "/{id}/cancel", response_model=JobItem, summary="取消任务", description="取消任务"
)
def cancel_job(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return job_service.cancel_job(session, current_user, id)
