from datetime import datetime

from fastapi import APIRouter, HTTPException
from typing import Any, List

from starlette.responses import StreamingResponse

from app.api.dataset_api.file_api import string_to_bytesio
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.file_pair_model import FilePairList, FilePairItem, FilePairUpdate, FilePairExportRequest, FilePairQuestionGeneratorContent
from app.services.dataset_services import file_pair_service

router = APIRouter(prefix="/file_pairs", tags=["file_pairs"])


@router.get(
    "/", response_model=FilePairList, summary="查询文件分片列表", description="查询文件分片列表"
)
def list_file_pair(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100,
                       project_id: str = None, file_ids: List[str] = None, has_question: str = None) -> Any:
    if project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("Project_id param is required"))
    file_pairs = file_pair_service.list_file_pairs(session, current_user, page, page_size, project_id, file_ids, has_question)
    return file_pairs



@router.put(
    "/{id}", response_model=FilePairItem, summary="更新文件分片", description="更新文件分片"
)
def update_file_pair(session: SessionDep, current_user: CurrentUserDep, id: str, update_file_pair: FilePairUpdate) -> Any:
    file_pair_item = file_pair_service.update_file_pair(session, current_user, id, update_file_pair)
    return file_pair_item


@router.delete(
    "/{id}", response_model=FilePairItem, summary="删除文件分片", description="删除文件分片"
)
def update_file_pair(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    file_pair_item = file_pair_service.delete_file_pair(session, current_user, id)
    return file_pair_item


@router.post(
    "/question_generator", response_model=str, summary="分片的问题生成", description="分片的问题生成"
)
def question_generator(session: SessionDep, current_user: CurrentUserDep, req: FilePairQuestionGeneratorContent) -> Any:
    if len(req.file_pair_ids) == 0:
        return i18n.gettext("Param {param} is required").format(param="file_pair_ids")
    if len(req.project_id) == 0:
        return i18n.gettext("Param {param} is required").format(param="project_id")

    return file_pair_service.question_generator(session, current_user, req)


@router.post(
    "/export", summary="分片导出", description="分片导出"
)
def file_pair_export(session: SessionDep, current_user: CurrentUserDep, export_req: FilePairExportRequest) -> Any:
    if len(export_req.file_pair_ids) == 0:
        return i18n.gettext("Param {param} is required").format(param="file_pair_ids")
    if len(export_req.project_id) == 0:
        return i18n.gettext("Param {param} is required").format(param="project_id")

    content = file_pair_service.file_pair_export(session, current_user, export_req)

    content_stream = string_to_bytesio(content)

    formatted_date = datetime.now().date().strftime("%Y-%m-%d")
    file_name = f"text-chunks-export-{formatted_date}.json"

    response = StreamingResponse(
        content=content_stream,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={file_name}"
        }
    )
    return response