from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.admin_security import require_super_admin
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.admin_pos_customers import (
    AdminPosCustomerCreate,
    AdminPosCustomerProfileResponse,
    AdminPosCustomerResponse,
    AdminPosCustomerUpdate,
    AdminPosLoyaltyAdjustmentCreate,
    AdminPosLoyaltyEntryResponse,
)
from app.services.pos_customer_service import (
    PosCustomerService,
)


router = APIRouter(
    prefix="/admin/pos/customers",
    tags=["Admin POS Customers"],
)


@router.post(
    "",
    response_model=AdminPosCustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    data: AdminPosCustomerCreate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    try:
        customer = PosCustomerService.create(
            db,
            name=data.name,
            phone=data.phone,
            email=data.email,
            birthday=data.birthday,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    db.commit()
    db.refresh(customer)

    return PosCustomerService.summary(
        db,
        customer,
    )


@router.get(
    "",
    response_model=list[
        AdminPosCustomerResponse
    ],
)
def search_customers(
    q: str = "",
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    customers = PosCustomerService.search(
        db,
        q=q,
    )

    return [
        PosCustomerService.summary(
            db,
            customer,
        )
        for customer in customers
    ]


@router.get(
    "/{customer_uuid}",
    response_model=AdminPosCustomerResponse,
)
def get_customer(
    customer_uuid: str,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    customer = PosCustomerService.get_by_uuid(
        db,
        customer_uuid=customer_uuid,
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return PosCustomerService.summary(
        db,
        customer,
    )


@router.patch(
    "/{customer_uuid}",
    response_model=AdminPosCustomerResponse,
)
def update_customer(
    customer_uuid: str,
    data: AdminPosCustomerUpdate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    try:
        customer = PosCustomerService.update(
            db,
            customer_uuid=customer_uuid,
            values=data.model_dump(
                exclude_unset=True
            ),
        )
    except ValueError as exc:
        status_code = (
            status.HTTP_409_CONFLICT
            if "already exists" in str(exc)
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    db.commit()
    db.refresh(customer)

    return PosCustomerService.summary(
        db,
        customer,
    )


@router.get(
    "/{customer_uuid}/profile",
    response_model=(
        AdminPosCustomerProfileResponse
    ),
)
def get_customer_profile(
    customer_uuid: str,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    customer = PosCustomerService.get_by_uuid(
        db,
        customer_uuid=customer_uuid,
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return PosCustomerService.profile(
        db,
        customer,
    )


@router.post(
    "/{customer_uuid}/loyalty-adjustments",
    response_model=(
        AdminPosLoyaltyEntryResponse
    ),
    status_code=status.HTTP_201_CREATED,
)
def adjust_customer_loyalty(
    customer_uuid: str,
    data: AdminPosLoyaltyAdjustmentCreate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
):
    entry = PosCustomerService.adjust_loyalty(
        db,
        customer_uuid=customer_uuid,
        points=data.points,
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    db.commit()
    db.refresh(entry)

    return entry
