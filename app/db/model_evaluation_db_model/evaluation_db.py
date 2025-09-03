# app/db/evaluation_db_model/evaluation_db.py
import time, uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Session, Mapped, mapped_column

from app.db.db import Base
from app.models.user_model import User


class EvaluationORM(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))

    # 评测使用的数据过滤（与 DatasetORM 对齐）
    project_id: Mapped[str] = mapped_column(String(255))
    tag_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 评测指标（执行后写入）
    bleu: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    rouge: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)   # 存 rougeLsum 单值
    accuracy: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    latency: Mapped[Optional[float]] = mapped_column(Float(), nullable=True) # 平均延迟（秒）
    throughput: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)  # requests/sec

    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0)

    def to_dict(self):
        d = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
                else:
                    d[k] = v
        return d


# ---------- CRUD helpers ----------
def _now() -> int:
    return int(time.time())


def list(
    session: Session,
    current_user: User,
    page_no: int = 1,
    page_size: int = 100,
    project_id: Optional[str] = None,
    tag_name: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[List[EvaluationORM], int]:
    q = session.query(EvaluationORM).filter(
        EvaluationORM.is_deleted == 0,
        EvaluationORM.group_id == current_user.group_id,
    )
    if project_id:
        q = q.filter(EvaluationORM.project_id == project_id)
    if tag_name:
        q = q.filter(EvaluationORM.tag_name == tag_name)
    if model:
        q = q.filter(EvaluationORM.model == model)
    total = q.count()
    rows = q.order_by(EvaluationORM.created_at.desc()).offset((page_no - 1) * page_size).limit(page_size).all()
    return rows, total


def get(session: Session, current_user: User, id: str) -> Optional[EvaluationORM]:
    return session.query(EvaluationORM).filter(
        EvaluationORM.id == id,
        EvaluationORM.group_id == current_user.group_id,
        EvaluationORM.is_deleted == 0,
    ).first()


def create(session: Session, current_user: User, evaluation: EvaluationORM) -> EvaluationORM:
    evaluation.id = str(uuid.uuid4())
    evaluation.user_id = current_user.id
    evaluation.group_id = current_user.group_id
    evaluation.created_at = _now()
    evaluation.updated_at = _now()
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return evaluation


def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[EvaluationORM]:
    obj = get(session, current_user, id)
    if not obj:
        return None
    for k, v in update_data.items():
        setattr(obj, k, v)
    obj.updated_at = _now()
    session.commit()
    session.refresh(obj)
    return obj


def delete(session: Session, current_user: User, id: str) -> Optional[EvaluationORM]:
    obj = get(session, current_user, id)
    if not obj:
        return None
    obj.is_deleted = _now()  # 软删记录时间戳
    obj.updated_at = _now()
    session.commit()
    session.refresh(obj)
    return obj
