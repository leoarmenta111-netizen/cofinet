from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_active_user
from app.database.deps import get_db
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.purchase import PurchaseCreate, PurchaseList, PurchaseResponse
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/purchases", tags=["Purchases"])


@router.post(
    "",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Invalid or missing bearer token"},
        403: {"description": "Inactive user"},
        404: {"description": "Plan not found"},
        500: {"description": "Could not generate a purchase PIN"},
    },
)
def create_purchase(
    purchase: PurchaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PurchaseResponse:
    """Create a paid purchase for the authenticated user and issue a PIN."""
    created_purchase = PurchaseService.create_purchase(db, current_user, purchase)
    return PurchaseService.to_response(created_purchase)


@router.get(
    "",
    response_model=PurchaseList,
    responses={
        401: {"description": "Invalid or missing bearer token"},
        403: {"description": "Inactive user"},
    },
)
def list_purchases(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PurchaseList:
    """List purchases belonging to the authenticated user."""
    purchases: Sequence[Purchase] = PurchaseService.list_purchases(db, current_user.id)
    return PurchaseList(
        purchases=[PurchaseService.to_response(purchase) for purchase in purchases]
    )


@router.get(
    "/{purchase_id}",
    response_model=PurchaseResponse,
    responses={
        401: {"description": "Invalid or missing bearer token"},
        403: {"description": "Inactive user"},
        404: {"description": "Purchase not found"},
    },
)
def get_purchase(
    purchase_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PurchaseResponse:
    """Get one purchase belonging to the authenticated user."""
    purchase = PurchaseService.get_purchase(db, current_user.id, purchase_id)
    return PurchaseService.to_response(purchase)
