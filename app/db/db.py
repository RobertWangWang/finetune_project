from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 启用连接健康检查
    pool_recycle=3600,  # 每小时回收连接
    connect_args={
        "connect_timeout": 30,  # 连接超时30秒
    }
)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)