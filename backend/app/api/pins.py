from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
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
        # Los PIN de ventas viven en purchases. Si no se encuentra allí,
        # buscar también las credenciales permanentes de dispositivos.
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            credential = db.execute(
                text(
                    """
                    SELECT
                        id,
                        label,
                        is_active
                    FROM internal_hotspot_credentials
                    WHERE pin_code = :pin
                    LIMIT 1
                    """
                ),
                {"pin": request.pin},
            ).mappings().first()

            if credential is not None:
                if not credential["is_active"]:
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={
                            "valid": False,
                            "message": "Este acceso permanente está deshabilitado.",
                            "permanent": True,
                        },
                    )

                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "valid": True,
                        "purchase_id": None,
                        "internal_access_id": credential["id"],
                        "plan": "Acceso permanente",
                        "minutes": 0,
                        "expires_at": None,
                        "permanent": True,
                        "device": credential["label"],
                    },
                )

        # Keep the public error body stable for captive-portal consumers.
        return JSONResponse(
            status_code=exc.status_code,
            content={"valid": False, "message": exc.detail},
        )
