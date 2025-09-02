import hashlib
import os
from typing import List

import chardet
from fastapi import UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.api.middleware.context import get_current_locale
from app.db.dataset_db_model import project_db, file_db, job_db, file_pair_db, question_db, dataset_db, ga_pair_db
from app.db.dataset_db_model.file_db import FileORM
from app.db.dataset_db_model.job_db import JobORM
from app.lib.i18n.config import i18n
from app.models.dataset_models.file_model import FileList, FileItem, GetFileItem, FileSplitConfig, FilePairGeneratorContent, \
    FileDeleteConfig, FileDeleteGeneratorContent
from app.models.dataset_models.job_model import JobType, JobStatus
from app.models.user_model import User
from app.services.dataset_services.jobs.manager import job_manager

ALLOWED_FILE_TYPES = {
    "markdown": [".md", ".markdown"],
    "pdf": [".pdf"],
    "text": [".txt"],
    "word": [".doc", ".docx"]
}

ALLOWED_EXTENSIONS = [ext for exts in ALLOWED_FILE_TYPES.values() for ext in exts]


def get_file_type(extension: str) -> str:
    """根据文件后缀获取文件类型名称"""
    for file_type, exts in ALLOWED_FILE_TYPES.items():
        if extension.lower() in exts:
            return file_type
    return "unknown"


def is_valid_extension(filename: str) -> bool:
    """检查文件后缀是否有效"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file(session: Session, current_user: User, id: str) -> GetFileItem:
    file = file_db.get(session, current_user, id)
    if not file:
        raise HTTPException(status_code=500, detail=i18n.gettext("File not found. id: {id}").format(id=id))

    return GetFileItem(**file.to_dict())


def delete_file(session: Session, current_user: User, id: str, config: FileDeleteConfig) -> FileItem:
    file_pair_db.bulk_delete_file_pairs(session, current_user, file_ids=[id])
    question_db.bulk_delete_questions(session, current_user, file_ids=[id])
    dataset_db.bulk_delete_datasets(session, current_user, file_ids=[id])
    ga_pair_db.bulk_delete_ga_pairs(session, current_user, file_ids=[id])

    file = file_db.delete(session, current_user, id)
    if file:
        content = FileDeleteGeneratorContent(
            file=GetFileItem(**file.to_dict()),
            config=config,
        )

        job = job_db.create(session, current_user, JobORM(
            type=JobType.FileDeleteGenerator,
            status=JobStatus.Running,
            content=content.json(),
            locale=get_current_locale(),
            project_id=file.project_id,
        ))
        job_manager.add_job(job)

        return FileItem(**file.to_dict())
    else:
        raise HTTPException(status_code=500, detail=i18n.gettext("File not found. id: {id}").format(id=id))


def decode_content(content: bytes) -> str:
    # 检测编码
    encoding_info = chardet.detect(content)
    encoding = encoding_info["encoding"]
    confidence = encoding_info["confidence"]  # 检测置信度

    if encoding is None or confidence < 0.8:  # 如果置信度太低，默认用 UTF-8
        encoding = "utf-8"

    try:
        return content.decode(encoding)
    except UnicodeDecodeError:
        # 如果检测的编码失败，尝试常见编码（如 GBK、ISO-8859-1）
        for fallback_encoding in ["utf-8", "gbk", "iso-8859-1", "latin1"]:
            try:
                return content.decode(fallback_encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Failed to decode file content with any encoding")


def compute_file_hash(content: bytes, algorithm: str = "md5") -> str:
    """计算文件的哈希值"""
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content)
    return hash_obj.hexdigest()  # 返回 16 进制字符串


def upload_files(session: Session, current_user: User, project_id: str, files: List[UploadFile] = File(...)) -> \
        List[FileItem]:
    project = project_db.get(session, current_user, project_id)
    if not project:
        raise HTTPException(status_code=500, detail=i18n.gettext("Project not found. id: {id}").format(id=project_id))

    file_list: List[FileORM] = []
    for file in files:
        # 检查文件后缀
        if not is_valid_extension(file.filename):
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("Unsupported file type. Allowed types: {types}").format(
                                    types=', '.join(ALLOWED_FILE_TYPES.keys())))

        _, total = file_db.list(session, current_user, 1, 1, file_name_match=file.filename, project_id=project_id)
        if total > 0:
            raise HTTPException(status_code=500, detail=i18n.gettext("Upload file failed, identical file exists: {file_name}").format(file_name=file.filename))

        # 获取文件后缀
        original_ext = os.path.splitext(file.filename)[1]
        content = file.file.read()
        after_content = decode_content(content)

        file_list.append(FileORM(
            file_name=file.filename,
            file_ext=original_ext,
            file_type=get_file_type(original_ext),
            content=after_content,
            md5=compute_file_hash(content),
            size=len(content),
            project_id=project_id
        ))

    results: List[FileItem] = []
    for file in file_list:
        create_result = file_db.create(session, current_user, file)
        results.append(FileItem(**create_result.to_dict()))

    return results


def list_files(session: Session, current_user: User, page_no: int = 1, page_size: int = 100, projectId: str = "",
               fileName: str = "") -> FileList:
    file_orm_list, total = file_db.list(session, current_user, page_no, page_size, projectId, fileName)
    return FileList(
        data=[FileItem(**file.to_dict()) for file in file_orm_list],
        count=total
    )


def file_split(session: Session, current_user: User, id: str, config: FileSplitConfig) -> str:
    file = get_file(session, current_user, id)

    content = FilePairGeneratorContent(
        file_ids=[file.id],
        config=config,
    )

    job = job_db.create(session, current_user, JobORM(
        type=JobType.FilePairGenerator,
        status=JobStatus.Running,
        content=content.json(),
        locale=get_current_locale(),
        project_id=file.project_id,
    ))
    job_manager.add_job(job)
    return job.id
