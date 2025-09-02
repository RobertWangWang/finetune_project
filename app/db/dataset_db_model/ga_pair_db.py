import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy import String, Column, Integer, BOOLEAN, and_, Boolean
from sqlalchemy.orm import Session, mapped_column, Mapped

from app.db.db import Base
from sqlalchemy import text

from app.models.user_model import User


class GAPairORM(Base):
    __tablename__ = "ga_pairs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    text_style: Mapped[str] = mapped_column(String(100))
    text_desc: Mapped[str] = mapped_column(String(500))
    audience: Mapped[str] = mapped_column(String(100))
    audience_desc: Mapped[str] = mapped_column(String(500))
    enable: Mapped[bool] = mapped_column(Boolean(), default=True)

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


def list_ga_pair_to_map(session: Session, current_user: User = None, ga_pair_id_list: list = None) -> dict[str, GAPairORM]:
    query = session.query(GAPairORM).filter(GAPairORM.is_deleted == 0, GAPairORM.group_id == current_user.group_id)
    query = query.filter(GAPairORM.id.in_(ga_pair_id_list))
    result = query.all()
    result_map = {}
    for ga_pair in result:
        result_map[ga_pair.id] = ga_pair
    return result_map


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100, file_id=None, enable: str = None) -> (List[GAPairORM], int):
    query = session.query(GAPairORM).filter(GAPairORM.is_deleted == 0,
                                            GAPairORM.group_id == current_user.group_id,
                                            GAPairORM.file_id == file_id)

    if enable == "true":
        query = query.filter(GAPairORM.enable == True)
    elif enable == "false":
        query = query.filter(GAPairORM.enable == False)

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[GAPairORM]:
    return session.query(GAPairORM).filter(
        GAPairORM.id == id,
        GAPairORM.group_id == current_user.group_id,
        GAPairORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, ga_pair: GAPairORM) -> Optional[GAPairORM]:
    ga_pair.id = str(uuid.uuid4())
    ga_pair.user_id = current_user.id
    ga_pair.group_id = current_user.group_id
    ga_pair.created_at = int(time.time())
    ga_pair.updated_at = int(time.time())
    session.add(ga_pair)
    session.commit()
    session.refresh(ga_pair)
    return ga_pair


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[GAPairORM]:
    ga_pair = get(session, current_user, id)
    if ga_pair:
        for key, value in update_data.items():
            setattr(ga_pair, key, value)
        ga_pair.updated_at = int(time.time())
        session.commit()
        session.refresh(ga_pair)
    return ga_pair


def delete(session: Session, current_user: User, id: str) -> Optional[GAPairORM]:
    ga_pair = get(session, current_user, id)
    if ga_pair:
        ga_pair.is_deleted = int(time.time())
        session.commit()
        session.refresh(ga_pair)
    return ga_pair


def bulk_create(session: Session, current_user: User, ga_pair_data: List[Dict]):
    if not ga_pair_data:
        return None

    current_time = int(time.time())
    mappings = []
    for data in ga_pair_data:
        mappings.append({
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "group_id": current_user.group_id,
            "created_at": current_time,
            "updated_at": current_time,
            **data  # 其他字段从参数传入
        })

    session.bulk_insert_mappings(GAPairORM, mappings)
    session.commit()


def bulk_delete_ga_pairs(
        db: Session,
        current_user: User,

        project_ids: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
) -> int:
    # 构建查询条件
    conditions = [
        GAPairORM.group_id == current_user.group_id,
        GAPairORM.is_deleted == 0
    ]

    if project_ids:
        conditions.append(GAPairORM.project_id.in_(project_ids))

    if file_ids:
        conditions.append(GAPairORM.file_id.in_(file_ids))

    if len(conditions) == 1:
        filter_condition = conditions[0]
    else:
        filter_condition = and_(*conditions)


    # 软删除 - 更新 is_deleted 标志
    result = db.query(GAPairORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result
