# app/services/evaluation_services/evaluation_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.db.model_evaluation_db_model import evaluation_db
from app.db.model_evaluation_db_model.evaluation_db import EvaluationORM
from app.lib.i18n.config import i18n
from app.models.evaluation_models.evaluation_model import EvaluationItem, EvaluationList, EvaluationCreate, EvaluationUpdate
from app.models.user_model import User

def evaluation_orm_to_item(orm: EvaluationORM) -> EvaluationItem:
    """Convert EvaluationORM to Pydantic EvaluationItem."""
    return EvaluationItem(
        id=orm.id,
        project_id=orm.project_id,
        tag_name=orm.tag_name,
        model=orm.model,
        bleu=orm.bleu,
        rouge=orm.rouge,
        accuracy=orm.accuracy,
        latency=orm.latency,
        throughput=orm.throughput,
        created_at=orm.created_at,
        updated_at=orm.updated_at
    )

def create_evaluation(session: Session, current_user: User, create: EvaluationCreate) -> EvaluationItem:
    """Create a new evaluation task (does not execute the evaluation)."""
    # Prepare ORM object; metrics start as None (not yet executed)
    evaluation = EvaluationORM(
        project_id=create.project_id,
        tag_name=create.tag_name,
        model=create.model,
        bleu=None, rouge=None, accuracy=None, latency=None, throughput=None
    )
    orm = evaluation_db.create(session, current_user, evaluation)
    return evaluation_orm_to_item(orm)

def get_evaluation(session: Session, current_user: User, id: str) -> EvaluationItem:
    """Retrieve a single evaluation task by ID."""
    orm = evaluation_db.get(session, current_user, id)
    if orm is None:
        # Raise error if not found (consistent with other services):contentReference[oaicite:18]{index=18}
        raise HTTPException(status_code=500, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))
    return evaluation_orm_to_item(orm)

def list_evaluations(session: Session, current_user: User, page_no: int, page_size: int, project_id: str) -> EvaluationList:
    """List evaluation tasks (paginated) for a given project."""
    evaluation_list, total = evaluation_db.list(session, current_user, page_no, page_size, project_id=project_id)
    items = [evaluation_orm_to_item(e) for e in evaluation_list]  # convert each ORM to Pydantic model:contentReference[oaicite:19]{index=19}
    return EvaluationList(data=items, count=total)

def update_evaluation(session: Session, current_user: User, id: str, update: EvaluationUpdate) -> EvaluationItem:
    """Update an evaluation task (e.g. fill in metrics or modify filters)."""
    update_data = update.model_dump(exclude_unset=True)  # get provided fields only:contentReference[oaicite:20]{index=20}
    orm = evaluation_db.update(session, current_user, id, update_data)
    if orm is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))
    return evaluation_orm_to_item(orm)

def delete_evaluation(session: Session, current_user: User, id: str) -> EvaluationItem:
    """Delete (soft-delete) an evaluation task."""
    orm = evaluation_db.get(session, current_user, id)
    if orm is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Evaluation task not found. id: {id}").format(id=id))
    # Since evaluation tasks are not auto-running, no need to check a running status before deletion
    deleted = evaluation_db.delete(session, current_user, id)
    return evaluation_orm_to_item(deleted if deleted else orm)
