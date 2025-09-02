from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.db import SessionLocal
from app.db.common_db_model.model_db import SessionLocal as ModelSessionLocal
from app.models.user_model import User
from fastapi import Request


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_model_db():
    db = ModelSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def manual_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_db)]
ModelSessionDep = Annotated[Session, Depends(get_model_db)]


def get_current_user(request: Request) -> User:
    token = request.headers.get("Authorization")
    return User(id="1", group_id="1")


CurrentUserDep = Annotated[User, Depends(get_current_user)]
