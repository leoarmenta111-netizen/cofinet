from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.admin_security import get_current_active_admin
from app.auth.security import create_access_token
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminLogin,
    AdminPinCreate,
    AdminPinList,
    AdminPinResponse,
    AdminResponse,
    AdminTokenResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/login", response_model=AdminTokenResponse, responses={401: {"description": "Invalid credentials"}})
def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)) -> AdminTokenResponse:
    admin = AdminService.login(db, credentials.email, credentials.password)
    token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": "admin"})
    return AdminTokenResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=AdminResponse)
def admin_me(current_admin: Admin = Depends(get_current_active_admin)) -> Admin:
    return current_admin


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    _admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    return AdminService.dashboard(db)


@router.post("/pins", response_model=AdminPinResponse, status_code=status.HTTP_201_CREATED)
def create_admin_pin(
    pin_request: AdminPinCreate,
    _admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
) -> AdminPinResponse:
    return AdminService.create_cash_pin(db, pin_request)


@router.get("/pins", response_model=AdminPinList)
def list_admin_pins(
    _admin: Admin = Depends(get_current_active_admin),
    db: Session = Depends(get_db),
) -> AdminPinList:
    return AdminPinList(pins=AdminService.list_cash_pins(db))
