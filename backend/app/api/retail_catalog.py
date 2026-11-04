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
from app.auth.security import (
    get_current_token,
)
from app.database.deps import get_db
from app.models.pos_staff import PosStaff
from app.models.retail_catalog import RetailCatalogItem
from app.schemas.retail_catalog import (
    RetailCatalogItemResponse,
)
from app.services.branch_service import (
    BranchService,
)
from app.services.retail_public_catalog_service import (
    RetailPublicCatalogService,
)


router = APIRouter(
    prefix="/retail",
    tags=["Retail Catalog"],
)


def _module_code(
    staff: PosStaff,
) -> str:
    value = staff.module_code

    if hasattr(
        value,
        "value",
    ):
        value = value.value

    return (
        str(value)
        .strip()
        .upper()
    )


@router.get(
    "/catalog",
    response_model=list[
        RetailCatalogItemResponse
    ],
)
def get_retail_catalog(
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> list[RetailCatalogItem]:

    if (
        _module_code(staff)
        != "PAPELERIA"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "POS staff module mismatch"
            ),
        )

    branch = (
        BranchService.get_by_id(
            db,
            staff.branch_id,
        )
    )

    branch_code = (
        token_payload.get(
            "branch_code"
        )
    )

    terminal_id = (
        token_payload.get(
            "terminal_id"
        )
    )

    if (
        not isinstance(
            branch_code,
            str,
        )
        or branch_code
        != branch.code
        or not isinstance(
            terminal_id,
            str,
        )
        or not terminal_id.strip()
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Could not validate "
                "credentials"
            ),
        )

    return (
        RetailPublicCatalogService
        .list_active(
            db,
            branch_id=staff.branch_id,
        )
    )
