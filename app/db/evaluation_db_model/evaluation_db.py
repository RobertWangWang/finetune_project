# app/db/evaluation_db_model/evaluation_db.py
import time, uuid
from datetime import datetime
from typing import Optional, List, Tuple
from enum import Enum
from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Session, Mapped, mapped_column

from app.db.db import Base
from app.models.user_model import User


class EvaluationStatus(str, Enum):

    DEPLOYED_LORA = "deployed_lora"
    DEPLOYED_LLM_MODEL = "deployed_llm_model"


class EvaluationORM(Base):
    __tablename__ = "evaluations"

    # 基本归属
    id: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=lambda: str(uuid.uuid4()),
        comment = "主键"
    )
    user_id: Mapped[str] = mapped_column(String(255), comment="用户ID")
    group_id: Mapped[str] = mapped_column(String(255), comment = "用户所属的群组ID")

    # 数据版本
    evaluation_dataset_id: Mapped[str] = mapped_column(String(255), comment="评估用的数据集ID")

    # 评测结果（JSON，可为空）
    eval_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment = "评测结果，包含bleu和rogue")

    # 评测类型
    eval_type: Mapped[str] = mapped_column(String(255), comment = "评测类型")

    # 产出来源
    deploy_cluster_id: Mapped[str] = mapped_column(String(255), comment = "部署集群ID")

    # 使用模型
    eval_model_id: Mapped[str] = mapped_column(String(255), comment = "使用模型的名字，对应name或者namespace")

    # 状态字段
    status: Mapped[str] = mapped_column(
        String(50), default="", comment = "评估任务的状态"
    )

    # 错误信息
    error_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment = "评估任务的错误信息")

    # 元信息
    created_at: Mapped[int] = mapped_column(Integer(), comment = "创建时间")
    updated_at: Mapped[int] = mapped_column(Integer(), comment = "更新时间")
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0, comment="0表示未删除，1表示已删除")


    def to_dict(self):
        d = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
                elif isinstance(v, Enum):
                    d[k] = v.value
                else:
                    d[k] = v
        return d

# ---------- CRUD helpers ----------
def _now() -> int:
    return int(time.time())


# ---------- CRUD ----------
def list_evaluations(
    session: Session,
    current_user: User,
    page_no: int = 1,
    page_size: int = 100,
    evaluation_dataset_id: Optional[str] = None,
    eval_type: Optional[str] = None,
    eval_model_id: Optional[str] = None,
) -> Tuple[List[EvaluationORM], int]:
    """分页列出 Evaluation 记录"""
    q = session.query(EvaluationORM).filter(
        EvaluationORM.is_deleted == 0,
        EvaluationORM.group_id == current_user.group_id,
    )
    if evaluation_dataset_id:
        q = q.filter(EvaluationORM.evaluation_dataset_id == evaluation_dataset_id)
    if eval_type:
        q = q.filter(EvaluationORM.eval_type == eval_type)
    if eval_model_id:
        q = q.filter(EvaluationORM.eval_model_id == eval_model_id)

    total = q.count()
    rows = (
        q.order_by(EvaluationORM.created_at.desc())
        .offset((page_no - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_evaluation(session: Session, current_user: User, evaluation_id: str) -> Optional[EvaluationORM]:
    """根据 id 获取 Evaluation"""
    return (
        session.query(EvaluationORM)
        .filter(
            EvaluationORM.id == evaluation_id,
            EvaluationORM.group_id == current_user.group_id,
            EvaluationORM.is_deleted == 0,
        )
        .first()
    )


def create_evaluation(session: Session, current_user: User, evaluation: EvaluationORM) -> EvaluationORM:
    """创建新的 Evaluation"""
    evaluation.id = str(uuid.uuid4())
    evaluation.user_id = current_user.id
    evaluation.group_id = current_user.group_id
    evaluation.created_at = _now()
    evaluation.updated_at = _now()
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return evaluation


def update(session: Session, current_user: User, evaluation_id: str, update_data: dict) -> Optional[EvaluationORM]:
    """更新 Evaluation"""
    obj = get_evaluation(session, current_user, evaluation_id)
    if not obj:
        return None
    for k, v in update_data.items():
        setattr(obj, k, v)
    obj.updated_at = _now()
    session.commit()
    session.refresh(obj)
    return obj


def delete(session: Session, current_user: User, evaluation_id: str) -> Optional[EvaluationORM]:
    """软删除 Evaluation"""
    obj = get_evaluation(session, current_user, evaluation_id)
    if not obj:
        return None
    obj.is_deleted = 1
    obj.updated_at = _now()
    session.commit()
    session.refresh(obj)
    return obj
