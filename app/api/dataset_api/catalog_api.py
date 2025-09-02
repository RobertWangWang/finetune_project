from fastapi import APIRouter, HTTPException
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.services.dataset_services import catalog_service

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

@router.get(
    "/", response_model=str, summary="获取目录树", description="获取目录树"
)
def get_catalog(session: SessionDep, current_user: CurrentUserDep, project_id: str) -> Any:
    if project_id == "":
        raise HTTPException(500, detail=i18n.gettext("Project_id param is required"))

    return catalog_service.get_catalog(session, current_user, project_id)