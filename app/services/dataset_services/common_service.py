from sqlalchemy.orm import Session

from app.db.dataset_db_model import question_db, dataset_db
from app.models.user_model import User


def check_and_update_question_has_dataset(session: Session, current_user: User, id: str):
    question_orm = question_db.get(session, current_user, id)
    dataset_list_orm, _ = dataset_db.list(session, current_user, 1, 9999, project_id=question_orm.project_id, question_id=question_orm.id)

    if dataset_list_orm and len(dataset_list_orm) > 0:
        question_db.update(session, current_user, id, {
            "has_dataset": True
        })
    else:
        question_db.update(session, current_user, id, {
            "has_dataset": False
        })