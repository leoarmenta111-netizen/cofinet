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
    AdminPosCustomerResponse,
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
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    customer = PosCustomerService.create(
        db,
        name=data.name,
        phone=data.phone,
        email=data.email,
        birthday=data.birthday,
    )

    db.commit()
    db.refresh(customer)

    return customer


@router.get(
    "",
    response_model=list[AdminPosCustomerResponse],
)
def search_customers(
    q: str = "",
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return PosCustomerService.search(
        db,
        q=q,
    )



@router.get(
    "/{customer_uuid}",
    response_model=AdminPosCustomerResponse,
)
def get_customer(
    customer_uuid: str,
    _admin: Admin = Depends(require_super_admin),
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

    return customer
