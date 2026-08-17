from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.admin_security import (
    get_current_active_admin,
    require_pin_access,
    require_super_admin,
)
from app.auth.security import create_access_token
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.admin import (
    AdminCreate,
    AdminDashboardResponse,
    AdminLogin,
    AdminPasswordReset,
    AdminPaymentList,
    AdminPaymentResponse,
    AdminPinCreate,
    AdminPinList,
    AdminPinResponse,
    AdminResponse,
    AdminRoleUpdate,
    AdminStatusUpdate,
    AdminTokenResponse,
)
from app.schemas.admin_access import (
    InternalAccessCreate,
    InternalAccessListResponse,
    InternalAccessResponse,
    InternalAccessStatusUpdate,
    PinBatchCreate,
    PinBatchDetailResponse,
    PinBatchListResponse,
    PinBatchPrintResponse,
)
from app.schemas.plan import AdminPlanUpdate, PlanResponse
from app.services.admin_access_service import AdminAccessService
from app.services.admin_access_query_service import AdminAccessQueryService
from app.services.admin_service import AdminService
from app.services.plan_service import PlanService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.patch(
    "/plans/{plan_id}",
    response_model=PlanResponse,
    responses={
        401: {"description": "Invalid or missing bearer token"},
        403: {"description": "Super administrator access required"},
        404: {"description": "Plan not found"},
        422: {"description": "Invalid price or duration"},
        500: {"description": "Database error"},
    },
)
def update_admin_plan(
    plan_id: int,
    update: AdminPlanUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> object:
    """Update only the price and duration used by future purchases."""
    return PlanService.update_admin_catalogue_plan(db, plan_id, update)


@router.post(
    "/login",
    response_model=AdminTokenResponse,
    responses={401: {"description": "Invalid credentials"}},
)
def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)) -> AdminTokenResponse:
    admin = AdminService.login(db, credentials.email, credentials.password)
    token = create_access_token(
        {
            "sub": str(admin.id),
            "email": admin.email,
            "role": "admin",
            "scope": "admin",
            "admin_role": admin.role.value,
        }
    )
    return AdminTokenResponse(access_token=token, token_type="bearer", role=admin.role)


@router.get("/me", response_model=AdminResponse)
def admin_me(current_admin: Admin = Depends(get_current_active_admin)) -> Admin:
    return current_admin


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    branch_code: str | None = None,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    return AdminService.dashboard(
        db,
        branch_code=branch_code,
    )


@router.post("/pins", response_model=AdminPinResponse, status_code=status.HTTP_201_CREATED)
def create_admin_pin(
    pin_request: AdminPinCreate,
    current_admin: Admin = Depends(require_pin_access),
    db: Session = Depends(get_db),
) -> AdminPinResponse:
    return AdminService.create_cash_pin(db, pin_request, current_admin)


@router.get("/pins", response_model=AdminPinList)
def list_admin_pins(
    current_admin: Admin = Depends(require_pin_access),
    db: Session = Depends(get_db),
) -> AdminPinList:
    return AdminPinList(pins=AdminService.list_cash_pins(db, current_admin))


@router.post(
    "/pin-batches",
    response_model=PinBatchDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Idempotency or unsafe-state conflict"},
        500: {"description": "One or more database confirmations failed"},
        502: {"description": "One or more MikroTik operations failed"},
    },
)
def create_admin_pin_batch(
    batch_request: PinBatchCreate,
    current_admin: Admin = Depends(require_pin_access),
    db: Session = Depends(get_db),
) -> PinBatchDetailResponse | JSONResponse:
    result = AdminAccessService.create_pin_batch(db, batch_request, current_admin)
    if result.failed:
        failure_codes = {item.error_code for item in result.failures}
        if failure_codes and failure_codes <= {"unique_pin_exhausted"}:
            failure_status = status.HTTP_409_CONFLICT
        elif "database_write_failed" in failure_codes:
            failure_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            failure_status = status.HTTP_502_BAD_GATEWAY
        return JSONResponse(
            status_code=failure_status,
            content=jsonable_encoder(
                {
                    "detail": "The batch completed with one or more unconfirmed PINs",
                    "batch": result,
                }
            ),
        )
    return result


@router.get("/pin-batches", response_model=PinBatchListResponse)
def list_admin_pin_batches(
    current_admin: Admin = Depends(require_pin_access),
    db: Session = Depends(get_db),
) -> PinBatchListResponse:
    return PinBatchListResponse(
        batches=AdminAccessQueryService.list_pin_batches(db, current_admin)
    )


@router.get("/pin-batches/{batch_id}", response_model=PinBatchDetailResponse)
def get_admin_pin_batch(
    batch_id: int,
    current_admin: Admin = Depends(require_pin_access),
    db: Session = Depends(get_db),
) -> PinBatchDetailResponse:
    return AdminAccessQueryService.get_pin_batch(db, batch_id, current_admin)


@router.get(
    "/pin-batches/{batch_id}/print-data", response_model=PinBatchPrintResponse
)
def get_admin_pin_batch_print_data(
    batch_id: int,
    current_admin: Admin = Depends(require_pin_access),
    db: Session = Depends(get_db),
) -> PinBatchPrintResponse:
    return AdminAccessQueryService.get_pin_batch_print_data(db, batch_id, current_admin)


@router.post(
    "/internal-access",
    response_model=InternalAccessResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_internal_access(
    request: InternalAccessCreate,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> InternalAccessResponse:
    return AdminAccessService.create_internal_access(db, request, current_admin)


@router.get("/internal-access", response_model=InternalAccessListResponse)
def list_internal_access(
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> InternalAccessListResponse:
    return InternalAccessListResponse(
        credentials=AdminAccessQueryService.list_internal_access(db)
    )


@router.patch(
    "/internal-access/{credential_id}/status", response_model=InternalAccessResponse
)
def update_internal_access_status(
    credential_id: int,
    update: InternalAccessStatusUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> InternalAccessResponse:
    return AdminAccessService.set_internal_access_status(
        db, credential_id, update.is_active
    )


@router.get("/payments", response_model=AdminPaymentList)
def list_admin_payments(
    branch_code: str | None = None,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> AdminPaymentList:
    return AdminPaymentList(
        payments=AdminService.list_payments(
            db,
            branch_code=branch_code,
        )
    )


@router.get("/payments/{payment_id}", response_model=AdminPaymentResponse)
def get_admin_payment(
    payment_id: int,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> AdminPaymentResponse:
    return AdminService.get_payment(db, payment_id)


@router.get("/accounts", response_model=list[AdminResponse])
def list_admin_accounts(
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[Admin]:
    return list(AdminService.list_admins(db))


@router.post("/accounts", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def create_admin_account(
    admin_data: AdminCreate,
    current_admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Admin:
    return AdminService.create_admin(db, admin_data, current_admin)


@router.patch("/accounts/{admin_id}/status", response_model=AdminResponse)
def update_admin_status(
    admin_id: int,
    update: AdminStatusUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Admin:
    return AdminService.set_admin_status(db, admin_id, update.is_active)


@router.patch("/accounts/{admin_id}/role", response_model=AdminResponse)
def update_admin_role(
    admin_id: int,
    update: AdminRoleUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Admin:
    return AdminService.set_admin_role(db, admin_id, update.role)


@router.post("/accounts/{admin_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_admin_password(
    admin_id: int,
    reset: AdminPasswordReset,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> None:
    AdminService.reset_admin_password(db, admin_id, reset.new_password)
