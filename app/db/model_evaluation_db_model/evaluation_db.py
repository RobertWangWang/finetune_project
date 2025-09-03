# app/db/evaluation_db_model/evaluation_db.py
import time, uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Session, Mapped, mapped_column
from app.db.db import Base
from app.models.user_model import User

class EvaluationORM(Base):
    __tablename__ = "evaluations"
    # Primary and foreign key fields
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    group_id: Mapped[str] = mapped_column(String(255))
    # Evaluation task metadata fields
    project_id: Mapped[str] = mapped_column(String(255))
    tag_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)   # optional dataset tag filter
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)      # optional dataset model filter
    # Evaluation metric fields (nullable until set)
    bleu: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    rouge: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    latency: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    throughput: Mapped[Optional[float]] = mapped_column(Float(), nullable=True)
    # Timestamps and deletion flag
    created_at: Mapped[int] = mapped_column(Integer())
    updated_at: Mapped[int] = mapped_column(Integer())
    is_deleted: Mapped[int] = mapped_column(Integer(), default=0)

    def to_dict(self):
        """Convert ORM object to dict (for debugging or serialization)."""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result

# CRUD operations for EvaluationORM
def list(session: Session, current_user: User, page_no: int = 1, page_size: int = 100,
         project_id: str = None, tag_name: str = None, model: str = None) -> (List[EvaluationORM], int):
    """List evaluation tasks with optional filtering by project/tag/model."""
    query = session.query(EvaluationORM).filter(
        EvaluationORM.is_deleted == 0,
        EvaluationORM.group_id == current_user.group_id  # limit to user's group data:contentReference[oaicite:5]{index=5}
    )
    if project_id is not None:
        query = query.filter(EvaluationORM.project_id == project_id)
    if tag_name is not None:
        query = query.filter(EvaluationORM.tag_name == tag_name)
    if model is not None:
        query = query.filter(EvaluationORM.model == model)
    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total

def get(session: Session, current_user: User, id: str) -> Optional[EvaluationORM]:
    """Fetch a single evaluation task by ID (within the user's group)."""
    return session.query(EvaluationORM).filter(
        EvaluationORM.id == id,
        EvaluationORM.group_id == current_user.group_id,
        EvaluationORM.is_deleted == 0
    ).first()

def create(session: Session, current_user: User, evaluation: EvaluationORM) -> Optional[EvaluationORM]:
    """Create a new evaluation task record (without executing the evaluation)."""
    evaluation.id = str(uuid.uuid4())
    evaluation.user_id = current_user.id
    evaluation.group_id = current_user.group_id
    evaluation.created_at = int(time.time())
    evaluation.updated_at = int(time.time())
    session.add(evaluation)
    session.commit()
    session.refresh(evaluation)
    return evaluation  # return the saved EvaluationORM:contentReference[oaicite:6]{index=6}

def update(session: Session, current_user: User, id: str, update_data: dict) -> Optional[EvaluationORM]:
    """Update an existing evaluation task with given fields."""
    evaluation = get(session, current_user, id)
    if evaluation:
        for key, value in update_data.items():
            setattr(evaluation, key, value)
        evaluation.updated_at = int(time.time())
        session.commit()
        session.refresh(evaluation)
    return evaluation  # returns None if not found, or updated object:contentReference[oaicite:7]{index=7}

def delete(session: Session, current_user: User, id: str) -> Optional[EvaluationORM]:
    """Soft-delete an evaluation task by marking is_deleted with a timestamp."""
    evaluation = get(session, current_user, id)
    if evaluation:
        evaluation.is_deleted = int(time.time())
        session.commit()
        session.refresh(evaluation)
    return evaluation  # return the object for reference (None if not found):contentReference[oaicite:8]{index=8}
