from fastapi import APIRouter, Depends, status

from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.user import (
    LogoutResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

from app.auth.security import (
    create_access_token,
    get_current_active_user,
    get_current_token,
)
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Email already registered"},
        500: {"description": "Database error"},
    },
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    return AuthService.create_user(db, user)

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"description": "Invalid email or password"}},
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):

    user = AuthService.login(
        db,
        credentials.email,
        credentials.password
    )

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"description": "Invalid or missing bearer token"},
        403: {"description": "Inactive user"},
        404: {"description": "User no longer exists"},
    },
)
def read_current_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Return the profile for the authenticated user."""
    return current_user


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={401: {"description": "Invalid or missing bearer token"}},
)
def logout(_token_payload: dict[str, object] = Depends(get_current_token)) -> LogoutResponse:
    """Validate the current token; a blacklist hook can be added here later."""
    return LogoutResponse(message="Logged out successfully")
