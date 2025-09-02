import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, JSON
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from app.db.db import Base
from app.lib.machine_connect import machine_connect
from app.lib.machine_connect.machine_connect import RemoteMachine
from app.models.user_model import User


class Machine(BaseModel):
    id: str  # UUID as string
    user_id: str
    group_id: str

    hostname: str
    device_type: Optional[str] = None  # Nullable in DB
    cuda_available: bool = True
    gpu_count: int = 1
    is_active: bool = True

    client_config: Optional[dict] = None  # Nullable JSON field

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


class MachineORM(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # Explicit length for VARCHAR in MySQL
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[str] = mapped_column(String(64), nullable=False)

    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    device_type: Mapped[str] = mapped_column(String(64), nullable=True)  # e.g., A100
    cuda_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gpu_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    client_config: Mapped[dict] = mapped_column(JSON, nullable=True)

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

    def to_remote_machine(self):
        return RemoteMachine(
            machine_connect.Machine(
                ip=self.client_config.get("ip"),
                ssh_port=self.client_config.get("ssh_port"),
                ssh_user=self.client_config.get("ssh_user"),
                ssh_password=self.client_config.get("ssh_password"),
                ssh_private_key=self.client_config.get("ssh_private_key")
            )
        )


def create_machine(session: Session, machine: MachineORM, current_user: User) -> MachineORM:
    machine.id = str(uuid.uuid4())
    machine.user_id = current_user.id
    machine.group_id = current_user.group_id
    machine.created_at = int(time.time())
    machine.updated_at = int(time.time())
    session.add(machine)
    session.commit()
    session.refresh(machine)
    return machine


def get_machine_by_id(session: Session, current_user: User, machine_id: str) -> Optional[MachineORM]:
    return session.query(MachineORM).filter_by(
        id=machine_id,
        group_id=current_user.group_id
    ).first()


def update_machine(session: Session, current_user: User, machine_id: str, update_data: dict) -> Optional[MachineORM]:
    machine = get_machine_by_id(session, current_user, machine_id)
    if not machine:
        return None
    for key, value in update_data.items():
        setattr(machine, key, value)
    machine.updated_at = int(time.time())
    session.commit()
    session.refresh(machine)
    return machine


def delete_machine(session: Session, current_user: User, machine_id: str) -> bool:
    machine = get_machine_by_id(session, current_user, machine_id)
    if not machine:
        return False
    machine.is_deleted = int(time.time())
    session.commit()
    return True


def list_machines(
        session: Session,
        current_user: User,
        page_no: int = 1,
        page_size: int = 100,
        is_active: Optional[bool] = None,
        ids: list[str] = None
) -> (List[MachineORM], int):
    query = session.query(MachineORM).filter_by(group_id=current_user.group_id, is_deleted=0)

    if is_active:
        query = query.filter(MachineORM.is_active == True)
    if ids is not None:
        query = query.filter(MachineORM.id.in_(ids))

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total
