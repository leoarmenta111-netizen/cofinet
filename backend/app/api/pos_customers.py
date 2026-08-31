from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pos_customers import (
    PosCustomerCreate,
    PosCustomerSummaryResponse,
)
from app.services.pos_customer_service import (
    PosCustomerService,
)


router = APIRouter(
    prefix="/pos/customers",
    tags=["POS Customers"],
)


@router.post(
    "",
    response_model=PosCustomerSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    data: PosCustomerCreate,
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
        PosCustomerSummaryResponse
    ],
)
def search_customers(
    q: str = Query(default=""),
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
    response_model=PosCustomerSummaryResponse,
)
def get_customer(
    customer_uuid: str,
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
