import time
from typing import List,Tuple
from sqlalchemy.orm import Session
import uuid
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer

from app.db.db import Base
from app.models.user_model import User



class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    # 主键 UUID
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="数据集唯一 ID"
    )

    # 基础信息
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据集名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="数据集描述")
    partition_keyword: Mapped[str] = mapped_column(String(100), nullable=False, comment="分区关键字（train/test等）")
    eval_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="评测类型（qa-eval/text-gen/classification等）")
    dataset_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="数据集文件路径")
    evaluation_extraction_keyword: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="数据提取关键字（如 messages/conversation）"
    )
    current_role: Mapped[str] = mapped_column(String(100), nullable=False, comment="角色（system/user）")

    # 归属信息
    user_id: Mapped[str] = mapped_column(String(255), comment="用户ID")
    group_id: Mapped[str] = mapped_column(String(255), comment="用户所属的群组ID")

    # 错误信息
    error_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="评估任务的错误信息")

    # 元信息
    created_at: Mapped[int] = mapped_column(Integer(), comment="创建时间戳")
    updated_at: Mapped[int] = mapped_column(Integer(), comment="更新时间戳")
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0, comment="0表示未删除，1表示已删除")

    def to_dict(self) -> dict:
        """方便序列化"""
        return {k: getattr(self, k) for k in self.__mapper__.c.keys()}


def _now() -> int:
    return int(time.time())


# ---------- CRUD ----------
def list_datasets(
    session: Session,
    current_user: User,
    page_no: int = 1,
    page_size: int = 100,
    eval_type: Optional[str] = None,
    current_role: Optional[str] = None,
) -> Tuple[List[EvaluationDataset], int]:
    """分页列出 EvaluationDataset 记录"""
    q = session.query(EvaluationDataset).filter(
        EvaluationDataset.is_deleted == 0,
        EvaluationDataset.group_id == current_user.group_id,
    )
    if eval_type:
        q = q.filter(EvaluationDataset.eval_type == eval_type)
    if current_role:
        q = q.filter(EvaluationDataset.current_role == current_role)

    total = q.count()
    rows = (
        q.order_by(EvaluationDataset.created_at.desc())
        .offset((page_no - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_dataset(
    session: Session,
    current_user: User,
    dataset_id: str
) -> Optional[EvaluationDataset]:
    """根据 id 获取 EvaluationDataset"""
    return (
        session.query(EvaluationDataset)
        .filter(
            EvaluationDataset.id == dataset_id,
            EvaluationDataset.group_id == current_user.group_id,
            EvaluationDataset.is_deleted == 0,
        )
        .first()
    )


def create_dataset(
    session: Session,
    current_user: User,
    dataset: EvaluationDataset
) -> EvaluationDataset:
    """创建新的 EvaluationDataset"""
    dataset.id = str(uuid.uuid4())
    dataset.user_id = current_user.id
    dataset.group_id = current_user.group_id
    dataset.created_at = _now()
    dataset.updated_at = _now()
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def update_dataset(
    session: Session,
    current_user: User,
    dataset_id: str,
    update_data: dict
) -> Optional[EvaluationDataset]:
    """更新 EvaluationDataset"""
    obj = get_dataset(session, current_user, dataset_id)
    if not obj:
        return None
    for k, v in update_data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    obj.updated_at = _now()
    session.commit()
    session.refresh(obj)
    return obj


def delete_dataset(
    session: Session,
    current_user: User,
    dataset_id: str
) -> Optional[EvaluationDataset]:
    """软删除 EvaluationDataset"""
    obj = get_dataset(session, current_user, dataset_id)
    if not obj:
        return None
    obj.is_deleted = 1
    obj.updated_at = _now()
    session.commit()
    session.refresh(obj)
    return obj