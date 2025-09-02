import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, and_, Text
from sqlalchemy.orm import Session, mapped_column, Mapped
from sqlalchemy import text

from app.db.db import Base
from app.models.user_model import User


class CatalogORM(Base):
    __tablename__ = "catalogs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    file_id: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text())

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


def create(session: Session, current_user: User, catalog: CatalogORM) -> Optional[CatalogORM]:
    catalog.id = str(uuid.uuid4())
    catalog.user_id = current_user.id
    catalog.group_id = current_user.group_id
    catalog.created_at = int(time.time())
    catalog.updated_at = int(time.time())
    session.add(catalog)
    session.commit()
    session.refresh(catalog)
    return catalog


def list(session: Session, current_user: User = None, project_id: str = None, file_id: str = None) -> List[CatalogORM]:
    query = session.query(CatalogORM).filter(CatalogORM.is_deleted == 0,
                                             CatalogORM.group_id == current_user.group_id,
                                             CatalogORM.project_id == project_id)

    if file_id:
        query = query.filter(CatalogORM.file_id == file_id)
    return query.all()


def get(session: Session, current_user: User, project_id: str) -> Optional[CatalogORM]:
    return session.query(CatalogORM).filter(
        CatalogORM.id == project_id,
        CatalogORM.group_id == current_user.group_id,
        CatalogORM.is_deleted == 0
    ).first()


def update(session: Session, current_user: User, project_id: str, update_data: dict) -> Optional[CatalogORM]:
    catalog = get(session, current_user, project_id)
    if catalog:
        for key, value in update_data.items():
            setattr(catalog, key, value)
        catalog.updated_at = int(time.time())
        session.commit()
        session.refresh(catalog)
    return catalog


def delete(session: Session, current_user: User, id: str) -> Optional[CatalogORM]:
    catalog = get(session, current_user, id)
    if catalog:
        catalog.is_deleted = int(time.time())
        session.commit()
        session.refresh(catalog)
    return None


def bulk_delete_catalog(
        db: Session,
        current_user: User,

        project_ids: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
) -> int:
    # 构建查询条件
    conditions = []

    if project_ids:
        conditions.append(CatalogORM.project_id.in_(project_ids))
    if file_ids:
        conditions.append(CatalogORM.file_id.in_(file_ids))

    # 添加用户/组权限条件
    conditions.append(CatalogORM.group_id == current_user.group_id)
    conditions.append(CatalogORM.is_deleted == 0)

    # 确保至少有一个删除条件
    if not conditions:
        return 0

    # 组合所有条件
    filter_condition = and_(*conditions)

    # 软删除 - 更新 is_deleted 标志
    result = db.query(CatalogORM).filter(filter_condition).update(
        {"is_deleted": int(time.time()), "updated_at": int(time.time())},
        synchronize_session=False
    )
    db.commit()
    return result
