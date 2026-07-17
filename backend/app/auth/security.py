from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.user import User
SECRET_KEY = "CAMBIAR_ESTO_DESPUES_EN_.ENV"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# This scheme both validates the Authorization header format and documents the
# Bearer authentication requirement in Swagger UI.
bearer_scheme = HTTPBearer(auto_error=False)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def hash_password(password: str) -> str:

    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:

    return pwd_context.verify(password, hashed_password)


def create_access_token(data: dict[str, Any]) -> str:

    payload = data.copy()

    expire = datetime.now(UTC) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload.update({"exp": expire})

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Extract and validate the JWT supplied in the Authorization header."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_exception()

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise _credentials_exception()
    except JWTError as exc:
        raise _credentials_exception() from exc

    return payload


def get_current_user(
    token_payload: dict[str, Any] = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user represented by a validated JWT."""
    try:
        user_id = int(token_payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _credentials_exception() from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Reject authenticated accounts that have been disabled."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return current_user
