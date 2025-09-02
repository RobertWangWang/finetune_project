import logging
import time
import uuid
from typing import Optional, List

from sqlalchemy import String, Column, Integer, and_, Text
from sqlalchemy.orm import Session, mapped_column, Mapped

from app.db.db import Base
from sqlalchemy import text

from app.models.user_model import User


class FileORM(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    file_name: Mapped[str] = mapped_column(String(255))
    file_ext: Mapped[str] = mapped_column(String(10))
    file_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text())
    md5: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer())

    project_id: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0)

    def to_dict(self):
        return {c.key: getattr(self, c.key)
                for c in self.__table__.columns}


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100,
         project_id: str = None, file_name: str = None, file_name_match: str = None, file_ext: str = None, file_ids: list[str] = None) -> (List[FileORM], int):
    query = session.query(FileORM).filter(FileORM.is_deleted == 0, FileORM.group_id == current_user.group_id,
                                          FileORM.project_id == project_id)

    if file_name:  # Add fuzzy search if name parameter is provided
        query = query.filter(FileORM.file_name.ilike(f'%{file_name}%'))

    if file_name_match:
        query = query.filter(FileORM.file_name == file_name_match)

    if file_ext:
        query = query.filter(FileORM.file_ext.ilike(f'%{file_ext}%'))
    if file_ids and len(file_ids) > 0:
        query = query.filter(FileORM.id.in_(file_ids))

    total = query.count()

    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[FileORM]:
    return session.query(FileORM).filter(
        FileORM.id == id,
        FileORM.group_id == current_user.group_id,
        FileORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, file: FileORM) -> Optional[FileORM]:
    file.id = str(uuid.uuid4())

    file.user_id = current_user.id
    file.group_id = current_user.group_id
    file.created_at = int(time.time())
    file.updated_at = int(time.time())

    session.add(file)
    session.commit()
    session.refresh(file)
    return file


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[FileORM]:
    file = get(session, current_user, id)
    if file:
        for key, value in update_data.items():
            setattr(file, key, value)
        file.updated_at = int(time.time())
        session.commit()
        session.refresh(file)
    return file


def delete(session: Session, current_user: User, id: str) -> Optional[FileORM]:
    file = get(session, current_user, id)
    if file:
        file.is_deleted = int(time.time())
        session.commit()
        session.refresh(file)
    return file


def bulk_delete_files(
        db: Session,
        current_user: User,

        project_ids: Optional[List[str]] = None
) -> int:
    # 构建查询条件
    conditions = [
        FileORM.group_id == current_user.group_id,
        FileORM.is_deleted == 0
    ]

    if project_ids:
        conditions.append(FileORM.project_id.in_(project_ids))

    if len(conditions) == 1:
        filter_condition = conditions[0]
    else:
        filter_condition = and_(*conditions)

    # 软删除 - 更新 is_deleted 标志
    result = db.query(FileORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result
