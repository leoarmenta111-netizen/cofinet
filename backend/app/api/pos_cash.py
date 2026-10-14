from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.pos_staff_security import get_current_pos_staff
from app.auth.security import get_current_token
from app.database.deps import get_db
from app.models.pos_staff import PosStaff
from app.schemas.pos_cash import (
    PosCashCloseRequest,
    PosCashClosingCountRequest,
    PosCashMovementRequest,
    PosCashMovementResponse,
    PosCashReconciliation,
    PosCashShiftOpenRequest,
    PosCashShiftResponse,
)
from app.services.pos_cash_service import PosCashService
from app.services.pos_staff_service import PosStaffService


router = APIRouter(
    prefix="/pos/cash",
    tags=["POS Cash"],
)


def _session_context(
    token_payload: dict[str, object],
) -> tuple[str, str]:
    branch_code = token_payload.get("branch_code")
    terminal_id = token_payload.get("terminal_id")

    if (
        not isinstance(branch_code, str)
        or not branch_code.strip()
        or not isinstance(terminal_id, str)
        or not terminal_id.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    return branch_code, terminal_id


@router.post(
    "/shifts/open",
    response_model=PosCashShiftResponse,
)
def open_cash_shift(
    payload: PosCashShiftOpenRequest,
    requesting_staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> PosCashShiftResponse:
    branch_code, terminal_id = _session_context(
        token_payload
    )

    manager = PosStaffService.authorize_manager(
        db,
        staff_id=payload.authorizing_manager_staff_id,
        pin=payload.manager_pin,
        branch_code=branch_code,
    )

    shift = PosCashService.open_shift(
        db,
        branch_code=branch_code,
        terminal_id=terminal_id,
        opening_counts=payload.opening_counts,
        requesting_staff=requesting_staff,
        authorizing_manager=manager,
    )

    db.commit()
    db.refresh(shift)

    return PosCashShiftResponse.model_validate(shift)


@router.get(
    "/shifts/current",
    response_model=PosCashShiftResponse | None,
)
def get_current_cash_shift(
    requesting_staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> PosCashShiftResponse | None:
    del requesting_staff

    branch_code, terminal_id = _session_context(
        token_payload
    )

    shift = PosCashService.current_shift(
        db,
        branch_code=branch_code,
        terminal_id=terminal_id,
    )

    if shift is None:
        return None

    return PosCashShiftResponse.model_validate(shift)


@router.post(
    "/shifts/{shift_uuid}/movements",
    response_model=PosCashMovementResponse,
)
def record_cash_movement(
    shift_uuid: str,
    payload: PosCashMovementRequest,
    requesting_staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> PosCashMovementResponse:
    branch_code, _ = _session_context(
        token_payload
    )

    manager = PosStaffService.authorize_manager(
        db,
        staff_id=payload.authorizing_manager_staff_id,
        pin=payload.manager_pin,
        branch_code=branch_code,
    )

    movement = PosCashService.record_movement(
        db,
        shift_uuid=shift_uuid,
        direction=payload.direction,
        category=payload.category,
        amount=payload.amount,
        note=payload.note,
        idempotency_key=payload.idempotency_key,
        requesting_staff=requesting_staff,
        authorizing_manager=manager,
    )

    db.commit()
    db.refresh(movement)

    return PosCashMovementResponse.model_validate(
        movement
    )



@router.post(
    "/shifts/{shift_uuid}/closing-count",
    response_model=PosCashReconciliation,
)
def submit_cash_closing_count(
    shift_uuid: str,
    payload: PosCashClosingCountRequest,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    db: Session = Depends(get_db),
) -> PosCashReconciliation:
    reconciliation = (
        PosCashService.submit_closing_count(
            db,
            shift_uuid=shift_uuid,
            closing_counts=payload.closing_counts,
            staff=staff,
        )
    )

    db.commit()

    return reconciliation


@router.post(
    "/shifts/{shift_uuid}/close",
    response_model=PosCashShiftResponse,
)
def finalize_cash_shift(
    shift_uuid: str,
    payload: PosCashCloseRequest,
    requesting_staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> PosCashShiftResponse:
    del requesting_staff

    branch_code, _ = _session_context(
        token_payload
    )

    manager = PosStaffService.authorize_manager(
        db,
        staff_id=payload.authorizing_manager_staff_id,
        pin=payload.manager_pin,
        branch_code=branch_code,
    )

    shift = PosCashService.authorize_close(
        db,
        shift_uuid=shift_uuid,
        manager=manager,
        difference_note=payload.difference_note,
    )

    db.commit()
    db.refresh(shift)

    return PosCashShiftResponse.model_validate(
        shift
    )
