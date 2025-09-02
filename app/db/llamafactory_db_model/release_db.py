import time
import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from app.db.db import Base
from app.models.dataset_models.dataset_version_model import DatasetType
from app.models.user_model import User


class ReleaseORM(Base):
    __tablename__ = "releases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Explicit length for VARCHAR in MySQL
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[str] = mapped_column(String(64), nullable=False)

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2000))
    base_model: Mapped[str] = mapped_column(String(255))
    stage: Mapped[DatasetType] = mapped_column(String(255))
    finetune_method: Mapped[str] = mapped_column(String(255))

    job_id: Mapped[str] = mapped_column(String(255))
    finetune_model_path: Mapped[str] = mapped_column(String(500))

    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())

    def to_dict(self) -> dict[str, Any]:
        # 去除 SQLAlchemy 内部字段（如 _sa_instance_state）
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        }


def get_release_by_id(session: Session, current_user: User, release_id: str) -> Optional[ReleaseORM]:
    return session.query(ReleaseORM).filter_by(
        id=release_id,
        group_id=current_user.group_id
    ).first()


def create_release(session: Session, current_user: User, release: ReleaseORM) -> ReleaseORM:
    release.id = str(uuid.uuid4())
    release.user_id = current_user.id
    release.group_id = current_user.group_id
    release.created_at = int(time.time())
    release.updated_at = int(time.time())
    session.add(release)
    session.commit()
    session.refresh(release)
    return release


def update_release(session: Session, current_user: User, release_id: str, update_data: dict) -> Optional[ReleaseORM]:
    release = get_release_by_id(session, current_user, release_id)
    if not release:
        return None
    for key, value in update_data.items():
        setattr(release, key, value)
    release.updated_at = int(time.time())
    session.commit()
    session.refresh(release)
    return release


def delete_release(session: Session, current_user: User, release_id: str) -> bool:
    release = get_release_by_id(session, current_user, release_id)
    if not release:
        return False
    release.is_deleted = int(time.time())
    session.commit()
    return True


def list_releases(
        session: Session,
        current_user: User,
        page_no: int = 1,
        page_size: int = 100,
        name: str = None,
        finetune_type: str = None
) -> (List[ReleaseORM], int):
    query = session.query(ReleaseORM).filter_by(group_id=current_user.group_id, is_deleted=0)

    if name:
        query = query.filter(ReleaseORM.name.ilike(f'%{name}%'))
    if finetune_type:
        query = query.filter(ReleaseORM.finetune_type == finetune_type)

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total
