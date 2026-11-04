from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.auth.pos_staff_security import (
    get_current_pos_staff,
)
from app.auth.security import get_current_token
from app.database.deps import get_db
from app.models.branch import Branch
from app.models.pos_staff import PosStaff
from app.schemas.retail_sales import (
    RetailCheckoutRequest,
    RetailHeldSaleUpsert,
    RetailSaleResponse,
)
from app.services.pos_staff_service import (
    PosStaffService,
)
from app.services.retail_receipt_service import RetailReceiptService
from app.services.retail_sale_service import (
    RetailSaleService,
)


router = APIRouter(
    prefix="/retail/sales",
    tags=["Retail Sales"],
)


def _session_context(
    *,
    staff: PosStaff,
    token_payload: dict[str, object],
    db: Session,
) -> tuple[str, str]:
    branch_code = token_payload.get(
        "branch_code"
    )
    terminal_id = token_payload.get(
        "terminal_id"
    )

    if (
        not isinstance(branch_code, str)
        or not branch_code.strip()
        or not isinstance(terminal_id, str)
        or not terminal_id.strip()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Could not validate credentials"
            ),
        )

    branch = db.get(
        Branch,
        staff.branch_id,
    )

    if (
        branch is None
        or branch.code != branch_code
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Could not validate credentials"
            ),
        )

    return (
        branch_code,
        terminal_id.strip(),
    )


@router.post(
    "/held",
    response_model=RetailSaleResponse,
)
def create_held_sale(
    payload: RetailHeldSaleUpsert,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailSaleResponse:
    _, terminal_id = _session_context(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    sale = RetailSaleService.hold(
        db,
        payload=payload,
        staff=staff,
        terminal_id=terminal_id,
    )

    db.commit()

    sale = RetailSaleService.get_sale(
        db,
        sale_uuid=sale.sale_uuid,
        staff=staff,
    )

    return RetailSaleResponse.model_validate(
        sale
    )


@router.put(
    "/held/{sale_uuid}",
    response_model=RetailSaleResponse,
)
def update_held_sale(
    sale_uuid: str,
    payload: RetailHeldSaleUpsert,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailSaleResponse:
    _, terminal_id = _session_context(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    sale = RetailSaleService.update_held(
        db,
        sale_uuid=sale_uuid,
        payload=payload,
        staff=staff,
        terminal_id=terminal_id,
    )

    db.commit()

    sale = RetailSaleService.get_sale(
        db,
        sale_uuid=sale.sale_uuid,
        staff=staff,
    )

    return RetailSaleResponse.model_validate(
        sale
    )


@router.get(
    "/held",
    response_model=list[RetailSaleResponse],
)
def list_held_sales(
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> list[RetailSaleResponse]:
    _session_context(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    sales = RetailSaleService.list_held(
        db,
        staff=staff,
    )

    return [
        RetailSaleResponse.model_validate(
            sale
        )
        for sale in sales
    ]


@router.post(
    "/checkout",
    response_model=RetailSaleResponse,
)
def checkout_retail_sale(
    payload: RetailCheckoutRequest,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailSaleResponse:
    branch_code, terminal_id = _session_context(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    discount_required = (
        payload.sale_discount_amount > 0
        or any(
            line.discount_amount > 0
            for line in payload.lines
        )
    )

    manager = None

    try:
        if discount_required:
            if (
                payload.authorizing_manager_staff_id
                is None
                or payload.manager_pin is None
                or not payload.manager_pin.strip()
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_403_FORBIDDEN
                    ),
                    detail=(
                        "Manager authorization "
                        "required"
                    ),
                )

            manager = (
                PosStaffService.authorize_manager(
                    db,
                    staff_id=(
                        payload
                        .authorizing_manager_staff_id
                    ),
                    pin=payload.manager_pin,
                    branch_code=branch_code,
                    module_code="PAPELERIA",
                )
            )

        sale = RetailSaleService.checkout(
            db,
            payload=payload,
            staff=staff,
            terminal_id=terminal_id,
            manager=manager,
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    sale = RetailSaleService.get_sale(
        db,
        sale_uuid=sale.sale_uuid,
        staff=staff,
    )

    return RetailSaleResponse.model_validate(
        sale
    )


@router.get(
    "/{sale_uuid}/receipt",
)
def get_retail_sale_receipt(
    sale_uuid: str,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> dict:
    _session_context(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    sale = RetailSaleService.get_sale(
        db,
        sale_uuid=sale_uuid,
        staff=staff,
    )

    return RetailReceiptService.stored_snapshot(
        sale=sale,
    )


@router.get(
    "/{sale_uuid}",
    response_model=RetailSaleResponse,
)
def get_retail_sale(
    sale_uuid: str,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailSaleResponse:
    _session_context(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    sale = RetailSaleService.get_sale(
        db,
        sale_uuid=sale_uuid,
        staff=staff,
    )

    return RetailSaleResponse.model_validate(
        sale
    )
