"""User management for registration and retrieval."""
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


class UserManager:
    """Handle CRUD operations for user accounts."""

    def __init__(self) -> None:
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_user(self, session: Session, email: str, password: str) -> User:
        """Create a new user with hashed password."""

        password_hash = self.pwd_context.hash(password)
        new_user = User(email=email, password_hash=password_hash)
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

        user: Optional[User] = session.query(User).filter_by(email=email).first()
        if not user:
            return None
        if not self.pwd_context.verify(password, user.password_hash):
            return None
        return user

    def get_user_by_id(self, session: Session, user_id: int) -> Optional[User]:
        """Retrieve a user by their identifier."""

        return session.query(User).filter_by(id=user_id).first()


user_manager = UserManager()
