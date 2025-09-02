import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import String, Column, Integer, and_, Text
from sqlalchemy.orm import Session, mapped_column, Mapped

from app.db.db import Base
from sqlalchemy import text

from app.models.user_model import User


class FilePairORM(Base):
    __tablename__ = "file_pairs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    size: Mapped[int] = mapped_column(Integer())
    content: Mapped[str] = mapped_column(Text())
    summary: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    chunk_index: Mapped[int] = mapped_column(Integer())
    question_id_list: Mapped[str] = mapped_column(Text(), nullable=True)

    file_id: Mapped[str] = mapped_column(String(255))
    project_id: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0)

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


def list_file_pair_to_map(session: Session, current_user: User = None, list_pair_id_list: list = None) -> dict[
    str, FilePairORM]:
    query = session.query(FilePairORM).filter(FilePairORM.is_deleted == 0,
                                              FilePairORM.group_id == current_user.group_id)
    query = query.filter(FilePairORM.id.in_(list_pair_id_list))
    result = query.all()
    result_map = {}
    for file_pair in result:
        result_map[file_pair.id] = file_pair
    return result_map


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100,
         project_id: str = None, file_ids: List[str] = None, has_question: str = None, id_list: List[str] = None) -> (List[FilePairORM], int):
    query = session.query(FilePairORM).filter(FilePairORM.is_deleted == 0,
                                              FilePairORM.group_id == current_user.group_id,
                                              FilePairORM.project_id == project_id)

    if file_ids is not None and len(file_ids) > 0:
        query = query.filter(FilePairORM.file_id.in_(file_ids))
    if has_question == "true":
        query = query.filter(FilePairORM.question_id_list != "")
    elif has_question == "false":
        query = query.filter(FilePairORM.question_id_list == "")
    if id_list is not None:
        query = query.filter(FilePairORM.id.in_(id_list))

    total = query.count()

    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[FilePairORM]:
    return session.query(FilePairORM).filter(
        FilePairORM.id == id,
        FilePairORM.group_id == current_user.group_id,
        FilePairORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, file_pair: FilePairORM) -> Optional[FilePairORM]:
    file_pair.id = str(uuid.uuid4())

    file_pair.user_id = current_user.id
    file_pair.group_id = current_user.group_id
    file_pair.created_at = int(time.time())
    file_pair.updated_at = int(time.time())

    session.add(file_pair)
    session.commit()
    session.refresh(file_pair)
    return file_pair


def bulk_create(session: Session, current_user: User, file_pair_data: List[Dict]):
    if not file_pair_data:
        return None

    current_time = int(time.time())
    mappings = []
    for data in file_pair_data:
        mappings.append({
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "group_id": current_user.group_id,
            "created_at": current_time,
            "updated_at": current_time,
            **data  # 其他字段从参数传入
        })

    session.bulk_insert_mappings(FilePairORM, mappings)
    session.commit()


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[FilePairORM]:
    file_pair = get(session, current_user, id)
    if file_pair:
        for key, value in update_data.items():
            setattr(file_pair, key, value)
        file_pair.updated_at = int(time.time())
        session.commit()
        session.refresh(file_pair)
    return file_pair


def delete(session: Session, current_user: User, id: str) -> Optional[FilePairORM]:
    file_pair = get(session, current_user, id)
    if file_pair:
        file_pair.is_deleted = int(time.time())
        session.commit()
        session.refresh(file_pair)
    return file_pair


def bulk_delete_file_pairs(
        db: Session,
        current_user: User,

        project_ids: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
) -> int:
    # 构建查询条件
    conditions = [
        FilePairORM.group_id == current_user.group_id,
        FilePairORM.is_deleted == 0
    ]

    if project_ids:
        conditions.append(FilePairORM.project_id.in_(project_ids))
    if file_ids:
        conditions.append(FilePairORM.file_id.in_(file_ids))

    if len(conditions) == 1:
        filter_condition = conditions[0]
    else:
        filter_condition = and_(*conditions)


    # 软删除 - 更新 is_deleted 标志
    result = db.query(FilePairORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result