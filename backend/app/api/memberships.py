from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.membership import MembershipCheckoutRequest, MembershipCheckoutResponse
from app.services.membership_service import MembershipService

router = APIRouter(prefix="/memberships", tags=["Memberships"])


@router.post("/checkout", response_model=MembershipCheckoutResponse, status_code=status.HTTP_201_CREATED)
def create_membership_checkout(request: MembershipCheckoutRequest, db: Session = Depends(get_db)) -> MembershipCheckoutResponse:
    membership, checkout_url = MembershipService.create_checkout(db, request)
    return MembershipCheckoutResponse(membership_id=membership.id, checkout_url=checkout_url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def membership_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    payload = await request.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    preapproval_id = data.get("id") if isinstance(data, dict) else None
    if isinstance(preapproval_id, str):
        MembershipService.process_webhook(db, preapproval_id)
    return {"status": "ok"}
