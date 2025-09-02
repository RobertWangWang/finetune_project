import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, BOOLEAN, or_, and_, Text, Boolean
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy import text

from app.db.db import Base
from app.models.user_model import User


class DatasetORM(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    question: Mapped[str] = mapped_column(Text())
    answer: Mapped[str] = mapped_column(Text())
    cot: Mapped[str] = mapped_column(Text(), nullable=True)

    question_id: Mapped[str] = mapped_column(String(255))
    tag_name: Mapped[str] = mapped_column(String(255))
    ga_pair: Mapped[str] = mapped_column(Text())
    file_pair_id: Mapped[str] = mapped_column(String(255))

    model: Mapped[str] = mapped_column(String(255))
    confirmed: Mapped[bool] = mapped_column(Boolean(), default=False)

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


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100,
               project_id: str = None,
               content: str = None,
               confirmed: str = None,
               question_id: str = None,
               ids: list[str] = None) -> (List[DatasetORM], int):
    query = session.query(DatasetORM).filter(DatasetORM.is_deleted == 0,
                                             DatasetORM.group_id == current_user.group_id,
                                             DatasetORM.project_id == project_id)

    if content is not None:
        query = query.filter(
            or_(
                DatasetORM.question.ilike(f'%{content}%'),
                DatasetORM.answer.ilike(f'%{content}%')
            )
        )
    if confirmed == "true":
        query = query.filter(DatasetORM.confirmed == True)
    elif confirmed == "false":
        query = query.filter(DatasetORM.confirmed == False)

    if question_id:
        query = query.filter(DatasetORM.question_id == question_id)

    if ids and len(ids) > 0:
        query = query.filter(DatasetORM.id.in_(ids))

    total = query.count()

    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[DatasetORM]:
    return session.query(DatasetORM).filter(
        DatasetORM.id == id,
        DatasetORM.group_id == current_user.group_id,
        DatasetORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, dataset: DatasetORM) -> Optional[DatasetORM]:
    dataset.id = str(uuid.uuid4())
    dataset.user_id = current_user.id
    dataset.group_id = current_user.group_id
    dataset.created_at = int(time.time())
    dataset.updated_at = int(time.time())
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[DatasetORM]:
    dataset = get(session, current_user, id)
    if dataset:
        for key, value in update_data.items():
            setattr(dataset, key, value)
        dataset.updated_at = int(time.time())
        session.commit()
        session.refresh(dataset)
    return dataset


def delete(session: Session, current_user: User, id: str) -> Optional[DatasetORM]:
    dataset = get(session, current_user, id)
    if dataset:
        dataset.is_deleted = int(time.time())
        session.commit()
        session.refresh(dataset)
    return None


def bulk_delete_datasets(
        db: Session,
        current_user: User,

        ids: Optional[List[str]] = None,
        project_ids: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
        file_pair_ids: Optional[List[str]] = None,
        question_ids: Optional[List[str]] = None
) -> int:
    # 构建查询条件
    conditions = [
        DatasetORM.group_id == current_user.group_id,
        DatasetORM.is_deleted == 0
    ]

    if project_ids:
        conditions.append(DatasetORM.project_id.in_(project_ids))
    if file_ids:
        conditions.append(DatasetORM.file_id.in_(file_ids))
    if file_pair_ids:
        conditions.append(DatasetORM.file_pair_id.in_(file_pair_ids))
    if question_ids:
        conditions.append(DatasetORM.question_id.in_(question_ids))
    if ids:
        conditions.append(DatasetORM.id.in_(ids))

    if len(conditions) == 1:
        filter_condition = conditions[0]
    else:
        filter_condition = and_(*conditions)

    # 软删除 - 更新 is_deleted 标志
    result = db.query(DatasetORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result