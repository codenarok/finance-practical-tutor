"""SQLAlchemy model for application users."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.services.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Database model representing a registered user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utc_now)
