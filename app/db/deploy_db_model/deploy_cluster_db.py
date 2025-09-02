import time
import uuid

from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy import String, Integer, Text, JSON
from typing import List, Optional, Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.db import Base
from app.db.llamafactory_db_model.finetune_job_db import PydanticType

from app.models.deploy_models.deploy_cluster_model import DeployStatus, FinetuneMethod, LoraDeployInfo, \
    RayRunningStatus
from app.models.user_model import User


class DeployClusterORM(Base):
    __tablename__ = "deploy_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[str] = mapped_column(String(64), nullable=False)

    name: Mapped[str] = mapped_column(String(255))
    machine_id_list: Mapped[list[str]] = mapped_column(JSON)
    ray_running_status: Mapped[list[RayRunningStatus]] = mapped_column(PydanticType(RayRunningStatus))
    status: Mapped[DeployStatus] = mapped_column(String(255))
    error_info: Mapped[str] = mapped_column(Text(), nullable=True)

    base_model: Mapped[str] = mapped_column(String(255))
    finetune_method: Mapped[FinetuneMethod] = mapped_column(String(255))
    lora_deploy_infos: Mapped[list[LoraDeployInfo]] = mapped_column(PydanticType(LoraDeployInfo), nullable=True)

    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0)

    def to_dict(self) -> dict[str, Any]:
        # 去除 SQLAlchemy 内部字段（如 _sa_instance_state）
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        }


def create_deploy_cluster(session: Session, current_user: User, cluster: DeployClusterORM) -> DeployClusterORM:
    cluster.id = str(uuid.uuid4())
    cluster.user_id = current_user.id
    cluster.group_id = current_user.group_id
    cluster.created_at = int(time.time())
    cluster.updated_at = int(time.time())
    session.add(cluster)
    session.commit()
    session.refresh(cluster)
    return cluster


def get_deploy_cluster_by_id(session: Session, current_user: User, cluster_id: str) -> Optional[DeployClusterORM]:
    return session.query(DeployClusterORM).filter_by(
        id=cluster_id,
        group_id=current_user.group_id
    ).first()


def update_deploy_cluster(session: Session, current_user: User, cluster_id: str, update_data: dict) -> Optional[
    DeployClusterORM]:
    cluster = get_deploy_cluster_by_id(session, current_user, cluster_id)
    if not cluster:
        return None
    for key, value in update_data.items():
        if key in ["ray_running_status", "lora_deploy_infos"]:
            # 对于 Pydantic 字段，需要先标记为已修改
            flag_modified(cluster, key)
            setattr(cluster, key, value)
        else:
            setattr(cluster, key, value)
    cluster.updated_at = int(time.time())
    session.commit()
    session.refresh(cluster)
    return cluster


def delete_deploy_cluster(session: Session, current_user: User, cluster_id: str) -> bool:
    cluster = get_deploy_cluster_by_id(session, current_user, cluster_id)
    if not cluster:
        return False
    cluster.is_deleted = int(time.time())
    session.commit()
    return True


def list_deploy_clusters(
        session: Session,
        current_user: User,
        page_no: int = 1,
        page_size: int = 100,
        name: str = None,
        status: DeployStatus = None
) -> (List[DeployClusterORM], int):
    query = session.query(DeployClusterORM).filter_by(group_id=current_user.group_id, is_deleted=0)

    if name:
        query = query.filter(DeployClusterORM.name.ilike(f'%{name}%'))
    if status:
        query = query.filter(DeployClusterORM.status == status)

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total
