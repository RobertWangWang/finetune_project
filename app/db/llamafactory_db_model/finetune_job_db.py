import os
import time
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.db.db import Base
from app.db.dataset_db_model.dataset_version_db import DatasetVersion
from app.db.llamafactory_db_model.finetune_config_db import FinetuneConfig, ConfigType
from app.db.common_db_model.machine_db import Machine
from app.models.dataset_models.dataset_version_model import DatasetType
from app.models.llamafactory_models.finetune_job_model import FinetuneJobStatus
from app.models.user_model import User
from sqlalchemy import TypeDecorator, JSON
from typing import List, Optional


class PydanticType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pydantic_type = pydantic_type

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return [v.dict() for v in value]
        return value.dict()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return [self.pydantic_type(**v) for v in value]
        return self.pydantic_type(**value)


class FinetuneJobORM(Base):
    __tablename__ = "finetune_jobs"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(500))
    status: Mapped[FinetuneJobStatus] = mapped_column(String(255))

    stage: Mapped[DatasetType] = mapped_column(String(255))
    finetune_method: Mapped[str] = mapped_column(String(255))

    dataset_version: Mapped[DatasetVersion] = mapped_column(PydanticType(DatasetVersion))
    finetune_config_list: Mapped[List[FinetuneConfig]] = mapped_column(PydanticType(FinetuneConfig))
    node_finetune_machine_list: Mapped[List[Machine]] = mapped_column(PydanticType(Machine))

    error_info: Mapped[str] = mapped_column(Text())
    done_node_num: Mapped[int] = mapped_column(Integer())

    local: Mapped[str] = mapped_column(String(200))
    release_id: Mapped[str] = mapped_column(String(200))

    start_at: Mapped[int] = mapped_column(Integer())
    end_at: Mapped[int] = mapped_column(Integer())
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

    def get_node_by_id(self, machine_id: str) -> Optional[Machine]:
        for node in self.node_finetune_machine_list:
            if node.id == machine_id:
                return node
        return None

    def _get_config(self, config_type, config_name):
        config_dict = {finetune_config.config_type: finetune_config.config for finetune_config in
                       self.finetune_config_list}
        config = config_dict.get(config_type)
        if config is None:
            return ""
        config_value = config.get(config_name)
        if config_value is None:
            return ""
        return config_value

    def get_base_model(self) -> str:
        model_path = self._get_config(ConfigType.ModelArguments, "model_name_or_path")
        if model_path == "":
            return ""
        return os.path.basename(model_path)


def list_jobs(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 100, name: str = None,
              status: Optional[FinetuneJobStatus] = None, stage: Optional[DatasetType] = None,
              finetune_method: Optional[DatasetType] = None) -> (
        List[FinetuneJobORM], int):
    query = session.query(FinetuneJobORM).filter(FinetuneJobORM.is_deleted == 0)

    if current_user:
        query = query.filter(FinetuneJobORM.group_id == current_user.group_id)

    if name:  # Add fuzzy search if name parameter is provided
        query = query.filter(FinetuneJobORM.name.ilike(f'%{name}%'))
    if status:
        query = query.filter(FinetuneJobORM.status == status)
    if stage:
        query = query.filter(FinetuneJobORM.stage == stage)
    if finetune_method:
        query = query.filter(FinetuneJobORM.finetune_method == finetune_method)

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get(session: Session, current_user: User, finetune_job_id: str) -> Optional[FinetuneJobORM]:
    return session.query(FinetuneJobORM).filter(
        FinetuneJobORM.id == finetune_job_id,
        FinetuneJobORM.group_id == current_user.group_id,
        FinetuneJobORM.is_deleted == 0
    ).first()


def create(session: Session, current_user: User, finetune_job: FinetuneJobORM) -> Optional[FinetuneJobORM]:
    finetune_job.id = str(uuid.uuid4())
    finetune_job.user_id = current_user.id
    finetune_job.group_id = current_user.group_id
    finetune_job.created_at = int(time.time())
    finetune_job.updated_at = int(time.time())
    session.add(finetune_job)
    session.commit()
    session.refresh(finetune_job)
    return finetune_job


def update(session: Session, current_user: User, finetune_job_id: str, update_data: dict) -> Optional[FinetuneJobORM]:
    finetune_job = get(session, current_user, finetune_job_id)
    if finetune_job:
        for key, value in update_data.items():
            setattr(finetune_job, key, value)
        finetune_job.updated_at = int(time.time())
        session.commit()
        session.refresh(finetune_job)
    return finetune_job


def delete(session: Session, current_user: User, finetune_job_id: str) -> Optional[FinetuneJobORM]:
    finetune_job = get(session, current_user, finetune_job_id)
    if finetune_job:
        finetune_job.is_deleted = int(time.time())
        session.commit()
        session.refresh(finetune_job)
    return finetune_job
