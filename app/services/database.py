"""Database management using SQLAlchemy for PostgreSQL."""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import get_settings


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self) -> None:
        settings = get_settings()
        self.engine = create_engine(settings.database_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.Base = declarative_base()

    def create_all(self) -> None:
        """Create tables in the configured database."""

        self.Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""

        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


db_manager = DatabaseManager()
Base = db_manager.Base


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""

    with db_manager.session_scope() as session:
        yield session
