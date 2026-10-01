"""User management for registration and retrieval."""
from typing import Optional

import bcrypt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


def normalise_email(email: str) -> str:
    """Treat addresses that differ only by case or outer spaces as the same account."""

    return email.strip().lower()


class UserManager:
    """Handle CRUD operations for user accounts."""

    def __init__(self) -> None:
        # Checked when the email is unknown, so a miss costs the same time as a wrong password.
        self._dummy_hash = bcrypt.hashpw(b"no-such-user", bcrypt.gensalt())

    def hash_password(self, password: str) -> str:
        """Hash a password with bcrypt and a fresh salt."""

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Check a password against a stored bcrypt hash."""

        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:  # over bcrypt's 72-byte limit, or a malformed hash
            return False

    def create_user(self, session: Session, email: str, password: str) -> User:
        """Create a new user with hashed password."""

        new_user = User(email=normalise_email(email), password_hash=self.hash_password(password))
        session.add(new_user)
        try:
            session.commit()
            session.refresh(new_user)
        except IntegrityError as exc:  # email uniqueness enforcement
            session.rollback()
            raise ValueError("Email already registered") from exc
        return new_user

    def authenticate_user(self, session: Session, email: str, password: str) -> Optional[User]:
        """Validate user credentials and return the user if valid."""

        user: Optional[User] = session.query(User).filter_by(email=normalise_email(email)).first()
        if not user:
            self.verify_password(password, self._dummy_hash.decode("utf-8"))
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user

    def get_user_by_id(self, session: Session, user_id: int) -> Optional[User]:
        """Retrieve a user by their identifier."""

        return session.query(User).filter_by(id=user_id).first()


user_manager = UserManager()
