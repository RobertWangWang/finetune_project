import logging
import time
import uuid
from datetime import datetime
from operator import and_
from typing import Optional, List

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy import text

from app.db.db import Base
from app.models.user_model import User


class TagORM(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    label: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str] = mapped_column(String(255))
    root_ids: Mapped[str] = mapped_column(String(2000), nullable=True)  # For storing multiple root IDs

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


def list_tags_to_map(session: Session, current_user: User = None, tag_id_list: list = None) -> dict[str, TagORM]:
    query = session.query(TagORM).filter(TagORM.is_deleted == 0, TagORM.group_id == current_user.group_id)
    query = query.filter(TagORM.id.in_(tag_id_list))
    result = query.all()
    result_map = {}
    for tag in result:
        result_map[tag.id] = tag
    return result_map


def list(session: Session, current_user: User = None, project_id: str = None) -> List[TagORM]:
    query = session.query(TagORM).filter(TagORM.is_deleted == 0, TagORM.group_id == current_user.group_id,
                                         TagORM.project_id == project_id)

    return query.all()


def get(session: Session, current_user: User, id: str) -> Optional[TagORM]:
    return session.query(TagORM).filter(
        TagORM.id == id,
        TagORM.group_id == current_user.group_id,
        TagORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, tag: TagORM) -> Optional[TagORM]:
    tag.id = str(uuid.uuid4())
    tag.user_id = current_user.id
    tag.group_id = current_user.group_id
    tag.created_at = int(time.time())
    tag.updated_at = int(time.time())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[TagORM]:
    tag = get(session, current_user, id)
    if tag:
        for key, value in update_data.items():
            setattr(tag, key, value)
        tag.updated_at = int(time.time())
        session.commit()
        session.refresh(tag)
    return tag


def delete(session: Session, current_user: User, id: str) -> Optional[TagORM]:
    tag = get(session, current_user, id)
    if tag:
        tag.is_deleted = int(time.time())
        session.commit()
        session.refresh(tag)
    return tag


def bulk_delete_tags(
        db: Session,
        current_user: User,
        project_ids: Optional[List[str]] = None,
        parent_id: str = None
) -> int:
    # Start with the fixed conditions
    conditions = [
        TagORM.group_id == current_user.group_id,
        TagORM.is_deleted == 0
    ]

    # Add optional conditions
    if project_ids:
        conditions.append(TagORM.project_id.in_(project_ids))
    if parent_id:
        conditions.append(TagORM.root_ids.ilike(f'%{parent_id}%'))

    # Combine all conditions with and_
    # Need to handle cases where we have only one condition (the fixed ones)
    if len(conditions) == 1:
        filter_condition = conditions[0]
    else:
        filter_condition = conditions[0]
        for condition in conditions[1:]:
            filter_condition = and_(filter_condition, condition)

    # 软删除 - 更新 is_deleted 标志
    result = db.query(TagORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result
