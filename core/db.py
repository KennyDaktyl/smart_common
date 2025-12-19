from contextlib import asynccontextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, scoped_session, sessionmaker

from smart_common.core.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def transactional_session(session: Session):
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise