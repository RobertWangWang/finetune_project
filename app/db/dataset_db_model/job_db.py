import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Column, Integer, Text
from sqlalchemy.orm import Session, mapped_column, Mapped

from app.db.db import Base
from sqlalchemy import text

from app.models.user_model import User


class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text().with_variant(Text(length=16777215), 'mysql'))  # MEDIUMTEXT equivalent
    result: Mapped[str] = mapped_column(Text().with_variant(Text(length=4294967295), 'mysql'), nullable=True)  # LONGTEXT equivalent

    locale: Mapped[str] = mapped_column(String(100))
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


def list(session: Session, current_user: User, page_no: int, page_size: int, project_id: str = None, status: str = None, typer=None) -> (
List[JobORM], int):
    query = session.query(JobORM).filter(JobORM.is_deleted == 0)

    if project_id is not None:
        query = query.filter(JobORM.project_id == project_id)
    if status is not None:
        query = query.filter(JobORM.status == status)
    if typer is not None:
        query = query.filter(JobORM.type == typer)
    if current_user is not None:
        query = query.filter(JobORM.group_id == current_user.group_id)

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, id: str) -> Optional[JobORM]:
    return session.query(JobORM).filter(
        JobORM.id == id,
        JobORM.group_id == current_user.group_id,
        JobORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, job: JobORM) -> Optional[JobORM]:
    job.id = str(uuid.uuid4())
    job.user_id = current_user.id
    job.group_id = current_user.group_id
    job.created_at = int(time.time())
    job.updated_at = int(time.time())
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[JobORM]:
    job = get(session, current_user, id)
    if job:
        for key, value in update_data.items():
            setattr(job, key, value)
        job.updated_at = int(time.time())
        session.commit()
        session.refresh(job)
    return job


def delete(session: Session, current_user: User, id: str) -> Optional[JobORM]:
    job = get(session, current_user, id)
    if job:
        job.is_deleted = int(time.time())
        session.commit()
        session.refresh(job)
    return job
