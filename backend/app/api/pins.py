from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.pin import (
    PinValidationErrorResponse,
    PinValidationRequest,
    PinValidationResponse,
)
from app.services.pin_service import PinService

router = APIRouter(prefix="/pins", tags=["PINs"])


@router.post(
    "/validate",
    response_model=PinValidationResponse,
    summary="Validate a PIN and retrieve its access details",
    responses={
        404: {
            "model": PinValidationErrorResponse,
            "description": "PIN not found",
        },
        409: {
            "model": PinValidationErrorResponse,
            "description": "PIN inactive",
        },
        410: {
            "model": PinValidationErrorResponse,
            "description": "PIN expired",
        },
    },
)
def validate_pin(
    request: PinValidationRequest,
    db: Session = Depends(get_db),
) -> PinValidationResponse | JSONResponse:
    """Validate a paid, active, unexpired PIN without authentication."""
    try:
        return PinService.validate(db, request.pin)
    except HTTPException as exc:
        # Keep the public error body stable for captive-portal consumers.
        return JSONResponse(
            status_code=exc.status_code,
            content={"valid": False, "message": exc.detail},
        )
