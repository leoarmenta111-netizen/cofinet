from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.pos_staff_security import (
    get_current_pos_staff,
)
from app.auth.security import (
    get_current_token,
)
from app.database.deps import get_db
from app.models.branch import Branch
from app.models.pos_staff import (
    PosStaff,
    PosStaffRole,
)
from app.models.retail_catalog import (
    RetailCatalogItem,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)
from app.schemas.retail_manager import (
    RetailManagerInventoryAdjustmentRequest,
    RetailManagerInventoryEntryRequest,
    RetailManagerInventoryMovementResponse,
    RetailManagerInventoryRemovalRequest,
    RetailManagerInventoryRowResponse,
    RetailManagerStaffResponse,
)
from app.services.pos_staff_service import (
    PosStaffService,
)
from app.services.retail_inventory_service import (
    RetailInventoryService,
)


router = APIRouter(
    prefix="/retail/manager",
    tags=["Retail Manager"],
)


def _value(value) -> str:
    if hasattr(value, "value"):
        value = value.value

    return str(value).strip().upper()


def _session_branch(
    *,
    staff: PosStaff,
    token_payload: dict[str, object],
    db: Session,
) -> Branch:
    if _value(staff.module_code) != "PAPELERIA":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="POS staff module mismatch",
        )

    token_module = token_payload.get(
        "module_code"
    )

    branch_code = token_payload.get(
        "branch_code"
    )

    terminal_id = token_payload.get(
        "terminal_id"
    )

    if (
        not isinstance(
            token_module,
            str,
        )
        or token_module.strip().upper()
        != "PAPELERIA"
        or not isinstance(
            branch_code,
            str,
        )
        or not branch_code.strip()
        or not isinstance(
            terminal_id,
            str,
        )
        or not terminal_id.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
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
        or branch.code
        != branch_code
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Could not validate credentials"
            ),
        )

    return branch


def _item_and_balance(
    db: Session,
    *,
    branch: Branch,
    item_id: int,
) -> tuple[
    RetailCatalogItem,
    RetailInventoryBalance,
]:
    item = db.execute(
        select(
            RetailCatalogItem
        ).where(
            RetailCatalogItem.id
            == item_id,
            RetailCatalogItem.branch_id
            == branch.id,
        )
    ).scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retail catalog item not found",
        )

    if (
        item.item_type != "PRODUCT"
        or not item.inventory_tracked
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Inventory tracking is not "
                "enabled for this item"
            ),
        )

    balance = db.execute(
        select(
            RetailInventoryBalance
        ).where(
            RetailInventoryBalance.branch_id
            == branch.id,
            RetailInventoryBalance.item_id
            == item.id,
        )
    ).scalar_one_or_none()

    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Inventory balance is not "
                "configured"
            ),
        )

    return item, balance


def _inventory_row(
    *,
    item: RetailCatalogItem,
    balance: RetailInventoryBalance,
) -> RetailManagerInventoryRowResponse:
    return RetailManagerInventoryRowResponse(
        item_id=item.id,
        sku=item.sku,
        item_name=item.name,
        quantity_on_hand=(
            balance.quantity_on_hand
        ),
        low_stock_threshold=(
            balance.low_stock_threshold
        ),
        max_stock=balance.max_stock,
        status=(
            RetailInventoryService.status_for(
                quantity_on_hand=(
                    balance.quantity_on_hand
                ),
                low_stock_threshold=(
                    balance.low_stock_threshold
                ),
            )
        ),
    )


def _manager(
    db: Session,
    *,
    branch: Branch,
    staff_id: int,
    pin: str,
) -> PosStaff:
    return (
        PosStaffService.authorize_manager(
            db,
            staff_id=staff_id,
            pin=pin,
            branch_code=branch.code,
            module_code="PAPELERIA",
        )
    )


def _key(
    *,
    operation: str,
    branch_id: int,
    item_id: int,
    supplied: str,
) -> str:
    return (
        f"retail-manager:{operation}:"
        f"{branch_id}:{item_id}:"
        f"{supplied.strip()}"
    )


@router.get(
    "/staff",
    response_model=list[
        RetailManagerStaffResponse
    ],
)
def list_retail_managers(
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> list[RetailManagerStaffResponse]:
    branch = _session_branch(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    managers = db.execute(
        select(PosStaff)
        .where(
            PosStaff.branch_id
            == branch.id,
            PosStaff.module_code
            == "PAPELERIA",
            PosStaff.role
            == PosStaffRole.MANAGER,
            PosStaff.is_active
            .is_(True),
        )
        .order_by(
            PosStaff.display_name,
            PosStaff.id,
        )
    ).scalars().all()

    return [
        RetailManagerStaffResponse(
            id=manager.id,
            display_name=(
                manager.display_name
            ),
            role="MANAGER",
        )
        for manager in managers
    ]


@router.get(
    "/inventory",
    response_model=list[
        RetailManagerInventoryRowResponse
    ],
)
def list_retail_manager_inventory(
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> list[
    RetailManagerInventoryRowResponse
]:
    branch = _session_branch(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    rows = db.execute(
        select(
            RetailInventoryBalance,
            RetailCatalogItem,
        )
        .join(
            RetailCatalogItem,
            RetailCatalogItem.id
            == RetailInventoryBalance.item_id,
        )
        .where(
            RetailInventoryBalance.branch_id
            == branch.id,
            RetailCatalogItem.branch_id
            == branch.id,
            RetailCatalogItem.item_type
            == "PRODUCT",
            RetailCatalogItem.inventory_tracked
            .is_(True),
        )
        .order_by(
            RetailCatalogItem.name,
            RetailCatalogItem.id,
        )
    ).all()

    return [
        _inventory_row(
            item=item,
            balance=balance,
        )
        for balance, item in rows
    ]


@router.get(
    "/inventory/{item_id}/movements",
    response_model=list[
        RetailManagerInventoryMovementResponse
    ],
)
def list_retail_manager_inventory_movements(
    item_id: int,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> list[
    RetailManagerInventoryMovementResponse
]:
    branch = _session_branch(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    item, _ = _item_and_balance(
        db,
        branch=branch,
        item_id=item_id,
    )

    movements = db.execute(
        select(
            RetailInventoryMovement
        )
        .where(
            RetailInventoryMovement.branch_id
            == branch.id,
            RetailInventoryMovement.item_id
            == item.id,
        )
        .order_by(
            RetailInventoryMovement.id.desc()
        )
        .limit(limit)
    ).scalars().all()

    return [
        RetailManagerInventoryMovementResponse(
            id=movement.id,
            item_id=movement.item_id,
            movement_type=(
                movement.movement_type
            ),
            quantity_delta=(
                movement.quantity_delta
            ),
            balance_after=(
                movement.balance_after
            ),
            note=movement.note,
            actor_staff_id=(
                movement.actor_staff_id
            ),
            authorizer_staff_id=(
                movement.authorizer_staff_id
            ),
            created_by_admin_id=(
                movement.created_by_admin_id
            ),
            idempotency_key=(
                movement.idempotency_key
            ),
            created_at=movement.created_at,
        )
        for movement in movements
    ]


@router.post(
    "/inventory/{item_id}/entry",
    response_model=(
        RetailManagerInventoryRowResponse
    ),
)
def retail_manager_inventory_entry(
    item_id: int,
    payload: RetailManagerInventoryEntryRequest,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailManagerInventoryRowResponse:
    branch = _session_branch(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    item, balance = _item_and_balance(
        db,
        branch=branch,
        item_id=item_id,
    )

    try:
        manager = _manager(
            db,
            branch=branch,
            staff_id=(
                payload
                .authorizing_manager_staff_id
            ),
            pin=payload.manager_pin,
        )

        RetailInventoryService.apply_movement(
            db,
            balance=balance,
            movement_type="MANUAL_ENTRY",
            quantity_delta=payload.quantity,
            idempotency_key=_key(
                operation="entry",
                branch_id=branch.id,
                item_id=item.id,
                supplied=(
                    payload.idempotency_key
                ),
            ),
            note=payload.note,
            actor_staff_id=staff.id,
            authorizer_staff_id=manager.id,
        )

        db.commit()
        db.refresh(balance)

    except Exception:
        db.rollback()
        raise

    return _inventory_row(
        item=item,
        balance=balance,
    )


@router.post(
    "/inventory/{item_id}/removal",
    response_model=(
        RetailManagerInventoryRowResponse
    ),
)
def retail_manager_inventory_removal(
    item_id: int,
    payload: RetailManagerInventoryRemovalRequest,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailManagerInventoryRowResponse:
    branch = _session_branch(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    item, balance = _item_and_balance(
        db,
        branch=branch,
        item_id=item_id,
    )

    try:
        manager = _manager(
            db,
            branch=branch,
            staff_id=(
                payload
                .authorizing_manager_staff_id
            ),
            pin=payload.manager_pin,
        )

        movement = (
            RetailInventoryService
            .apply_movement(
                db,
                balance=balance,
                movement_type=(
                    "MANUAL_REMOVAL"
                ),
                quantity_delta=-Decimal(
                    str(payload.quantity)
                ),
                idempotency_key=_key(
                    operation="removal",
                    branch_id=branch.id,
                    item_id=item.id,
                    supplied=(
                        payload.idempotency_key
                    ),
                ),
                note=payload.note,
                actor_staff_id=staff.id,
                authorizer_staff_id=(
                    manager.id
                ),
            )
        )

        if (
            Decimal(
                str(
                    movement.balance_after
                )
            )
            < Decimal("0.000")
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Inventory removal would "
                    "drive stock below zero"
                ),
            )

        db.commit()
        db.refresh(balance)

    except Exception:
        db.rollback()
        raise

    return _inventory_row(
        item=item,
        balance=balance,
    )


@router.post(
    "/inventory/{item_id}/adjust",
    response_model=(
        RetailManagerInventoryRowResponse
    ),
)
def retail_manager_inventory_adjust(
    item_id: int,
    payload: RetailManagerInventoryAdjustmentRequest,
    staff: PosStaff = Depends(
        get_current_pos_staff
    ),
    token_payload: dict[str, object] = Depends(
        get_current_token
    ),
    db: Session = Depends(get_db),
) -> RetailManagerInventoryRowResponse:
    branch = _session_branch(
        staff=staff,
        token_payload=token_payload,
        db=db,
    )

    item, balance = _item_and_balance(
        db,
        branch=branch,
        item_id=item_id,
    )

    try:
        manager = _manager(
            db,
            branch=branch,
            staff_id=(
                payload
                .authorizing_manager_staff_id
            ),
            pin=payload.manager_pin,
        )

        (
            RetailInventoryService
            .adjust_to_physical_count(
                db,
                balance=balance,
                physical_quantity=(
                    payload.physical_quantity
                ),
                idempotency_key=_key(
                    operation="adjust",
                    branch_id=branch.id,
                    item_id=item.id,
                    supplied=(
                        payload.idempotency_key
                    ),
                ),
                note=payload.note,
                actor_staff_id=staff.id,
                authorizer_staff_id=(
                    manager.id
                ),
            )
        )

        db.commit()
        db.refresh(balance)

    except Exception:
        db.rollback()
        raise

    return _inventory_row(
        item=item,
        balance=balance,
    )
