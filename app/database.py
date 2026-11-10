from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import ON_VERCEL, settings

# Serverless instances freeze between requests, so don't keep pooled connections there (Neon's pooler does that job)
engine = (create_engine(settings.database_url, poolclass=NullPool) if ON_VERCEL
          else create_engine(settings.database_url, pool_pre_ping=True))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
