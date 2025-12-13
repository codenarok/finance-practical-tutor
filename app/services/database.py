"""Database management using SQLAlchemy for PostgreSQL."""
from contextlib import contextmanager
from time import sleep
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(self) -> None:
        settings = get_settings()
        self.engine = create_engine(settings.database_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.Base = declarative_base()

    def create_all(self, max_attempts: int = 5, delay_seconds: float = 2.0) -> None:
        """Create tables in the configured database, retrying until the DB is ready."""

        for attempt in range(1, max_attempts + 1):
            try:
                self.Base.metadata.create_all(bind=self.engine)
            except OperationalError:
                if attempt == max_attempts:
                    raise
                sleep(delay_seconds)
            else:
                break

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
