from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate

from fastapi import HTTPException
from sqlalchemy import select

from app.auth.security import verify_password


class AuthService:

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:

        existing_user = db.execute(
            select(User).where(User.email == user.email)
        ).scalar_one_or_none()
        if existing_user is not None:
            raise HTTPException(
                status_code=409,
                detail="Email already registered",
            )

        db_user = User(
            name=user.name,
            email=user.email,
            password_hash=hash_password(user.password)
        )

        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Email already registered",
            ) from exc
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Could not create user",
            ) from exc

        return db_user


    @staticmethod
    def login(db: Session, email: str, password: str) -> User:

        user = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        return user
