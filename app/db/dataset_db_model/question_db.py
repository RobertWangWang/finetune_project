import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import String, Column, Integer, and_, BOOLEAN, Text, Boolean
from sqlalchemy.orm import Session, mapped_column, Mapped

from app.db.db import Base
from sqlalchemy import text

from app.models.user_model import User


class QuestionORM(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    question: Mapped[str] = mapped_column(Text())

    tag_name: Mapped[str] = mapped_column(String(255))
    ga_pair: Mapped[str] = mapped_column(Text())

    has_dataset: Mapped[bool] = mapped_column(Boolean(), default=False)
    file_pair_id: Mapped[str] = mapped_column(String(255))
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
         question: str = None,
         tag_name: str = None,
         match_tag_name: str = None,
         id_list: list[str] = None) -> (List[QuestionORM], int):
    query = session.query(QuestionORM).filter(QuestionORM.is_deleted == 0,
                                              QuestionORM.group_id == current_user.group_id,
                                              QuestionORM.project_id == project_id)
    if id_list is not None and len(id_list) > 0:
        query = query.filter(QuestionORM.id.in_(id_list))

    if question is not None:
        query = query.filter(QuestionORM.question.ilike(f'%{question}%'))

    if tag_name is not None:
        query = query.filter(QuestionORM.tag_name.ilike(f'%{tag_name}%'))

    if match_tag_name is not None:
        query = query.filter(QuestionORM.tag_name == match_tag_name)

    total = query.count()

    query = query.order_by(QuestionORM.created_at.desc())
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[QuestionORM]:
    return session.query(QuestionORM).filter(
        QuestionORM.id == id,
        QuestionORM.group_id == current_user.group_id,
        QuestionORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, question: QuestionORM) -> Optional[QuestionORM]:
    question.id = str(uuid.uuid4())
    question.user_id = current_user.id
    question.group_id = current_user.group_id
    question.created_at = int(time.time())
    question.updated_at = int(time.time())
    session.add(question)
    session.commit()
    session.refresh(question)
    return question


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[QuestionORM]:
    question = get(session, current_user, id)
    if question:
        for key, value in update_data.items():
            setattr(question, key, value)
        question.updated_at = int(time.time())
        session.commit()
        session.refresh(question)
    return question


def delete(session: Session, current_user: User, id: str) -> Optional[QuestionORM]:
    question = get(session, current_user, id)
    if question:
        question.is_deleted = int(time.time())
        session.commit()
        session.refresh(question)
    return question


def bulk_create(session: Session, current_user: User, question_data: List[Dict]):
    if not question_data:
        return None

    current_time = int(time.time())
    mappings = []
    for data in question_data:
        mappings.append({
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "group_id": current_user.group_id,
            "created_at": current_time,
            "updated_at": current_time,
            **data  # 其他字段从参数传入
        })

    session.bulk_insert_mappings(QuestionORM, mappings)
    session.commit()


def bulk_delete_questions(
        db: Session,
        current_user: User,

        project_ids: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
        file_pair_ids: Optional[List[str]] = None,
        id_list: Optional[List[str]] = None
) -> int:
    # 构建查询条件
    conditions = [
        QuestionORM.group_id == current_user.group_id,
        QuestionORM.is_deleted == 0
    ]

    if project_ids:
        conditions.append(QuestionORM.project_id.in_(project_ids))
    if file_ids:
        conditions.append(QuestionORM.file_id.in_(file_ids))
    if file_pair_ids:
        conditions.append(QuestionORM.file_pair_id.in_(file_pair_ids))
    if id_list:
        conditions.append(QuestionORM.id.in_(file_pair_ids))
    # Combine all conditions with and_
    # Need to handle cases where we have only one condition (the fixed ones)
    if len(conditions) == 1:
        filter_condition = conditions[0]
    else:
        filter_condition = and_(*conditions)

    # 软删除 - 更新 is_deleted 标志
    result = db.query(QuestionORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result
