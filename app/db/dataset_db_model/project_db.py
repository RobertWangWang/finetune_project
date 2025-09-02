import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import Session, Mapped, mapped_column
from sqlalchemy import text

from app.db.db import Base
from app.models.user_model import User


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    name: Mapped[str] = mapped_column(String(255))

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


def list(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100, name: str = None) -> (List[ProjectORM], int):
    query = session.query(ProjectORM).filter(ProjectORM.is_deleted == 0, ProjectORM.group_id == current_user.group_id)

    if name:  # Add fuzzy search if name parameter is provided
        query = query.filter(ProjectORM.name.ilike(f'%{name}%'))

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, project_id: str) -> Optional[ProjectORM]:
    return session.query(ProjectORM).filter(
        ProjectORM.id == project_id,
        ProjectORM.group_id == current_user.group_id,
        ProjectORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, project: ProjectORM) -> Optional[ProjectORM]:
    project.id = str(uuid.uuid4())
    project.user_id = current_user.id
    project.group_id = current_user.group_id
    project.created_at = int(time.time())
    project.updated_at = int(time.time())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def update(session: Session, current_user: User, project_id: str, update_data: dict) -> Optional[ProjectORM]:
    project = get(session, current_user, project_id)
    if project:
        for key, value in update_data.items():
            setattr(project, key, value)
        project.updated_at = int(time.time())
        session.commit()
        session.refresh(project)
    return project


def delete(session: Session, current_user: User, project_id: str) -> Optional[ProjectORM]:
    project = get(session, current_user, project_id)
    if project:
        project.is_deleted = int(time.time())
        session.commit()
        session.refresh(project)
    return project