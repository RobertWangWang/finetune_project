import time
import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Session, Mapped, mapped_column

from app.db.db import Base
from app.models.dataset_models.dataset_version_model import DatasetType
from app.models.user_model import User


class DatasetVersion(BaseModel):
    id: str
    user_id: str
    group_id: str

    name: str
    description: str
    dataset_type: DatasetType
    options: dict

    project_id: str

    created_at: int
    updated_at: int
    is_deleted: int = 0

    def __json__(self):
        return self.model_dump()

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


class DatasetVersionORM(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(500))
    dataset_type: Mapped[DatasetType] = mapped_column(String(255))
    options: Mapped[dict] = mapped_column(JSON)

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


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100, project_id: str = None,
         name: str = None) -> (List[DatasetVersionORM], int):
    query = session.query(DatasetVersionORM).filter(DatasetVersionORM.is_deleted == 0,
                                                    DatasetVersionORM.project_id == project_id,
                                                    DatasetVersionORM.group_id == current_user.group_id)

    if name:  # Add fuzzy search if name parameter is provided
        query = query.filter(DatasetVersionORM.name.ilike(f'%{name}%'))

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[DatasetVersionORM]:
    return session.query(DatasetVersionORM).filter(
        DatasetVersionORM.id == id,
        DatasetVersionORM.group_id == current_user.group_id,
        DatasetVersionORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, dataset_version: DatasetVersionORM) -> Optional[DatasetVersionORM]:
    dataset_version.id = str(uuid.uuid4())
    dataset_version.user_id = current_user.id
    dataset_version.group_id = current_user.group_id
    dataset_version.created_at = int(time.time())
    dataset_version.updated_at = int(time.time())
    session.add(dataset_version)
    session.commit()
    session.refresh(dataset_version)
    return dataset_version


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[DatasetVersionORM]:
    dataset_version = get(session, current_user, id)
    if dataset_version:
        for key, value in update_data.items():
            setattr(dataset_version, key, value)
        dataset_version.updated_at = int(time.time())
        session.commit()
        session.refresh(dataset_version)
    return dataset_version


def delete(session: Session, current_user: User, id: str) -> Optional[DatasetVersionORM]:
    dataset_version = get(session, current_user, id)
    if dataset_version:
        dataset_version.is_deleted = int(time.time())
        session.commit()
        session.refresh(dataset_version)
    return dataset_version
