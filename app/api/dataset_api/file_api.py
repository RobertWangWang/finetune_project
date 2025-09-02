import urllib
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile
from typing import Any, List

from fastapi.params import File, Form
from starlette.responses import StreamingResponse

from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.file_model import FileList, FileItem, FileSplitConfig, FileDeleteConfig
from app.services.dataset_services import file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.get(
    "/", response_model=FileList, summary="查询文件列表", description="返回文件列表"
)
def list_files(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100,
                     project_id: str = "", file_name: str = "") -> Any:
    if project_id == "":
        raise HTTPException(500, detail=i18n.gettext("Project_id param is required"))
    files = file_service.list_files(session, current_user, page, page_size, project_id, file_name)
    return files


@router.post(
    "/upload", response_model=List[FileItem], summary="上传文件", description="上传文件"
)
def upload_files(session: SessionDep,
                       current_user: CurrentUserDep,
                       project_id: str = Form(...),
                       files: List[UploadFile] = File(...)
                       ) -> Any:
    if project_id == "":
        raise HTTPException(500, detail=i18n.gettext("Project_id param is required"))
    # if len(files) == 0:
    #     raise HTTPException(500, detail="files is required")
    files = file_service.upload_files(session, current_user, project_id, files)
    return files


def string_to_bytesio(unknown_str, encoding='utf-8'):
    """
    将未知编码的字符串转换为BytesIO对象

    参数:
        unknown_str: 需要转换的字符串
        encoding: 字符串的编码格式，默认为utf-8

    返回:
        BytesIO对象
    """
    try:
        # 如果输入已经是bytes，直接使用
        if isinstance(unknown_str, bytes):
            byte_data = unknown_str
        else:
            # 尝试将字符串编码为bytes
            byte_data = unknown_str.encode(encoding)

        # 创建BytesIO对象
        return BytesIO(byte_data)
    except UnicodeEncodeError:
        # 如果编码失败，尝试其他常见编码
        common_encodings = ['utf-8', 'latin-1', 'ascii', 'utf-16', 'gbk', 'gb2312']
        for enc in common_encodings:
            try:
                return BytesIO(unknown_str.encode(enc))
            except UnicodeEncodeError:
                continue
        raise ValueError("无法确定字符串编码，尝试常见编码均失败")


@router.get(
    "/{id}/download", summary="下载文件", description="下载文件"
)
def download_file(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    file = file_service.get_file(session, current_user, id)

    content_stream = string_to_bytesio(file.content)

    response = StreamingResponse(
        content=content_stream,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={urllib.parse.quote(file.file_name)}"
        }
    )

    return response


@router.get(
    "/{id}", summary="获取文件详情", description="获取文件详情"
)
def get_file(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    file = file_service.get_file(session, current_user, id)
    return file


@router.delete(
    "/{id}", response_model=FileItem, summary="删除文件", description="删除文件"
)
def delete_file(session: SessionDep, current_user: CurrentUserDep, id: str, config: FileDeleteConfig) -> Any:
    file = file_service.delete_file(session, current_user, id, config)
    return file


@router.post(
    "/{id}/split", response_model=str, summary="文件分片", description="文件分片"
)
def file_split(session: SessionDep, current_user: CurrentUserDep, id: str, config: FileSplitConfig) -> Any:
    job_id = file_service.file_split(session, current_user, id, config)
    return job_id
