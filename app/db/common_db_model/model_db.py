import time
from contextlib import contextmanager

from sqlalchemy import create_engine, DateTime, JSON, TypeDecorator
from sqlalchemy.dialects.mssql import BIT
from sqlalchemy.orm import declarative_base, sessionmaker, mapped_column, Mapped, Session

from app.config.config import settings
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer

from app.models.user_model import User

engine = create_engine(
    settings.MODEL_DATABASE_URL,
    pool_pre_ping=True,  # 启用连接健康检查
    pool_recycle=3600,  # 每小时回收连接
    connect_args={
        "connect_timeout": 30,  # 连接超时30秒
    }
)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_model_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MySQLBitBoolean(TypeDecorator):
    impl = Integer

    def process_bind_param(self, value, dialect):
        return 1 if value else 0

    def process_result_value(self, value, dialect):
        if value[0] == 1:
            return True
        else:
            return False

class ProviderORM(Base):
    __tablename__ = "provider"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="提供商"
    )
    account_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="",
        comment="接入名称"
    )
    is_valid: Mapped[bool] = mapped_column(MySQLBitBoolean, nullable=True)
    create_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="创建时间"
    )
    update_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="更新时间"
    )
    create_by: Mapped[Optional[str]] = mapped_column(String(255))
    update_by: Mapped[Optional[str]] = mapped_column(String(255))

    access_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        comment="接入配置"
    )

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


def get_provider(session: Session, current_user: User, id: str) -> Optional[ProviderORM]:
    return session.query(ProviderORM).filter(
        ProviderORM.id == id).first()


def create_provider(session: Session, current_user: User, provider: ProviderORM) -> Optional[ProviderORM]:
    provider.create_by = "admin"
    provider.update_by = "admin"
    provider.create_time = datetime.now()
    provider.update_time = datetime.now()
    session.add(provider)
    session.commit()
    session.refresh(provider)
    return provider


def update_provider(session: Session, current_user: User, id: str, update_data: dict) -> Optional[ProviderORM]:
    provider = get_provider(session, current_user, id)
    if provider:
        for key, value in update_data.items():
            setattr(provider, key, value)
        provider.update_time = datetime.now()
        session.commit()
        session.refresh(provider)
    return provider


def list_provider(session: Session, current_user: User = None, page_no: int = 1, page_size: int = 10,
                  ids: list[str] = None) -> (List[ProviderORM], int):
    query = session.query(ProviderORM).filter(ProviderORM.provider_name == "open_ai",
                                              ProviderORM.is_valid == True)

    if ids is not None:
        query = query.filter(ProviderORM.id.in_(ids))

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def delete_provider(session: Session, current_user: User, id: str) -> Optional[ProviderORM]:
    provider = get_provider(session, current_user, id)
    if provider is not None:
        session.delete(provider)
        session.commit()  # 确保提交事务
        session.flush()  # 可选，确保操作立即执行
    return None


class ProviderModelORM(Base):
    __tablename__ = "provider_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_name: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String)
    model_type: Mapped[str] = mapped_column(String)
    config: Mapped[dict] = mapped_column(JSON)
    is_valid: Mapped[bool] = mapped_column(MySQLBitBoolean, nullable=False, comment="是否有效")
    is_default: Mapped[bool | None] = mapped_column(MySQLBitBoolean, comment="是否作为默认模型")

    account_name: Mapped[str] = mapped_column(String)
    provider_id: Mapped[int] = mapped_column(Integer)
    create_time: Mapped[datetime] = mapped_column(DateTime)
    update_time: Mapped[datetime] = mapped_column(DateTime)
    create_by: Mapped[str] = mapped_column(String)
    update_by: Mapped[str] = mapped_column(String)
    capability: Mapped[list[str]] = mapped_column(JSON)

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result


def get_model(session: Session, current_user: User, id: str) -> Optional[ProviderModelORM]:
    return session.query(ProviderModelORM).filter(
        ProviderModelORM.id == id).first()


def create_model(session: Session, current_user: User, provider_model: ProviderModelORM) -> Optional[ProviderModelORM]:
    provider_model.create_by = "admin"
    provider_model.update_by = "admin"
    provider_model.create_time = datetime.now()
    provider_model.update_time = datetime.now()
    session.add(provider_model)
    session.commit()
    session.refresh(provider_model)
    return provider_model


def update_model(session: Session, current_user: User, id: str, update_data: dict) -> Optional[ProviderModelORM]:
    model = get_model(session, current_user, id)
    if model:
        for key, value in update_data.items():
            setattr(model, key, value)
        model.update_time = datetime.now()
        session.commit()
        session.refresh(model)
    return model


def delete_model(session: Session, current_user: User, id: str) -> Optional[ProviderModelORM]:
    model = get_model(session, current_user, id)
    if model is not None:
        session.delete(model)
        session.commit()  # 确保提交事务
        session.flush()  # 可选，确保操作立即执行
    return None


def list_model(session: Session, current_user: User = None, page_no: int = 1,
               page_size: int = 10) -> (List[ProviderModelORM], int):
    query = session.query(ProviderModelORM).filter(ProviderModelORM.provider_name == "open_ai",
                                                   ProviderModelORM.model_type == "text-generation",
                                                   ProviderModelORM.is_valid == True)

    total = query.count()
    skip = (page_no - 1) * page_size
    return query.offset(skip).limit(page_size).all(), total


def get_provider_model() -> Optional[ProviderModelORM]:
    models = get_provider_models()
    for model in models:
        if model.is_default == 1:
            return model
    if len(models) > 0:
        return models[0]
    return None


def get_provider_models():
    with get_model_db() as session:
        query = session.query(ProviderModelORM).filter(ProviderModelORM.is_valid == True,
                                                       ProviderModelORM.provider_name == "open_ai",
                                                       ProviderModelORM.model_type == "text-generation")

        return query.all()
