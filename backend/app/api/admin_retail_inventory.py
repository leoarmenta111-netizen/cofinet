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

from app.auth.admin_security import (
    require_super_admin,
)
from app.database.deps import get_db
from app.models.admin import Admin
from app.models.branch import Branch
from app.models.retail_catalog import (
    RetailCatalogItem,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)
from app.schemas.admin_retail_inventory import (
    AdminRetailInventoryAdjustmentCreate,
    AdminRetailInventoryEntryCreate,
    AdminRetailInventoryMovementResponse,
    AdminRetailInventoryRemovalCreate,
    AdminRetailInventoryRowResponse,
)
from app.services.retail_inventory_service import (
    RetailInventoryService,
)


router = APIRouter(
    prefix="/admin/retail/inventory",
    tags=["Admin Retail Inventory"],
)


def _branch_by_code(
    db: Session,
    branch_code: str,
) -> Branch:
    normalized = branch_code.strip()

    branch = db.execute(
        select(Branch).where(
            Branch.code == normalized
        )
    ).scalar_one_or_none()

    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    return branch


def _item_for_branch(
    db: Session,
    *,
    item_id: int,
    branch: Branch,
) -> RetailCatalogItem:
    item = db.execute(
        select(RetailCatalogItem).where(
            RetailCatalogItem.id == item_id,
            RetailCatalogItem.branch_id
            == branch.id,
        )
    ).scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retail catalog item not found",
        )

    return item


def _balance_for(
    db: Session,
    *,
    item: RetailCatalogItem,
    branch: Branch,
) -> RetailInventoryBalance:
    balance = db.execute(
        select(RetailInventoryBalance).where(
            RetailInventoryBalance.branch_id
            == branch.id,
            RetailInventoryBalance.item_id
            == item.id,
        )
    ).scalar_one_or_none()

    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Retail inventory balance "
                "not found"
            ),
        )

    return balance


def _require_tracked_product(
    item: RetailCatalogItem,
) -> None:
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


def _row(
    *,
    branch: Branch,
    item: RetailCatalogItem,
    balance: RetailInventoryBalance,
) -> AdminRetailInventoryRowResponse:
    return AdminRetailInventoryRowResponse(
        item_id=item.id,
        sku=item.sku,
        item_name=item.name,
        branch_id=branch.id,
        branch_code=branch.code,
        branch_name=branch.name,
        inventory_tracked=(
            item.inventory_tracked
        ),
        quantity_on_hand=(
            balance.quantity_on_hand
        ),
        low_stock_threshold=(
            balance.low_stock_threshold
        ),
        max_stock=balance.max_stock,
        status=RetailInventoryService.status_for(
            quantity_on_hand=(
                balance.quantity_on_hand
            ),
            low_stock_threshold=(
                balance.low_stock_threshold
            ),
        ),
        updated_at=balance.updated_at,
    )


def _movement_row(
    movement: RetailInventoryMovement,
) -> AdminRetailInventoryMovementResponse:
    return AdminRetailInventoryMovementResponse(
        id=movement.id,
        branch_id=movement.branch_id,
        item_id=movement.item_id,
        movement_type=movement.movement_type,
        quantity_delta=movement.quantity_delta,
        balance_after=movement.balance_after,
        sale_id=movement.sale_id,
        sale_line_id=movement.sale_line_id,
        note=movement.note,
        actor_staff_id=movement.actor_staff_id,
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


def _idempotency_key(
    *,
    operation: str,
    branch_id: int,
    item_id: int,
    supplied: str,
) -> str:
    return (
        f"admin-retail:{operation}:"
        f"{branch_id}:{item_id}:"
        f"{supplied.strip()}"
    )


@router.get(
    "",
    response_model=list[
        AdminRetailInventoryRowResponse
    ],
)
def list_retail_inventory(
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> list[
    AdminRetailInventoryRowResponse
]:
    branch = _branch_by_code(
        db,
        branch_code,
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
        )
        .order_by(
            RetailCatalogItem.name,
            RetailCatalogItem.id,
        )
    ).all()

    return [
        _row(
            branch=branch,
            item=item,
            balance=balance,
        )
        for balance, item in rows
    ]


@router.get(
    "/{item_id}",
    response_model=(
        AdminRetailInventoryRowResponse
    ),
)
def get_retail_inventory(
    item_id: int,
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> AdminRetailInventoryRowResponse:
    branch = _branch_by_code(
        db,
        branch_code,
    )

    item = _item_for_branch(
        db,
        item_id=item_id,
        branch=branch,
    )

    balance = _balance_for(
        db,
        item=item,
        branch=branch,
    )

    return _row(
        branch=branch,
        item=item,
        balance=balance,
    )


@router.get(
    "/{item_id}/movements",
    response_model=list[
        AdminRetailInventoryMovementResponse
    ],
)
def list_retail_inventory_movements(
    item_id: int,
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> list[
    AdminRetailInventoryMovementResponse
]:
    branch = _branch_by_code(
        db,
        branch_code,
    )

    item = _item_for_branch(
        db,
        item_id=item_id,
        branch=branch,
    )

    _balance_for(
        db,
        item=item,
        branch=branch,
    )

    movements = db.execute(
        select(RetailInventoryMovement)
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
        _movement_row(movement)
        for movement in movements
    ]


@router.post(
    "/{item_id}/entry",
    response_model=(
        AdminRetailInventoryRowResponse
    ),
)
def record_retail_inventory_entry(
    item_id: int,
    data: AdminRetailInventoryEntryCreate,
    admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> AdminRetailInventoryRowResponse:
    branch = _branch_by_code(
        db,
        data.branch_code,
    )

    item = _item_for_branch(
        db,
        item_id=item_id,
        branch=branch,
    )

    _require_tracked_product(item)

    balance = _balance_for(
        db,
        item=item,
        branch=branch,
    )

    RetailInventoryService.apply_movement(
        db,
        balance=balance,
        movement_type="MANUAL_ENTRY",
        quantity_delta=data.quantity,
        idempotency_key=(
            _idempotency_key(
                operation="entry",
                branch_id=branch.id,
                item_id=item.id,
                supplied=data.idempotency_key,
            )
        ),
        note=data.note,
        created_by_admin_id=admin.id,
    )

    db.commit()
    db.refresh(balance)

    return _row(
        branch=branch,
        item=item,
        balance=balance,
    )


@router.post(
    "/{item_id}/removal",
    response_model=(
        AdminRetailInventoryRowResponse
    ),
)
def record_retail_inventory_removal(
    item_id: int,
    data: AdminRetailInventoryRemovalCreate,
    admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> AdminRetailInventoryRowResponse:
    branch = _branch_by_code(
        db,
        data.branch_code,
    )

    item = _item_for_branch(
        db,
        item_id=item_id,
        branch=branch,
    )

    _require_tracked_product(item)

    balance = _balance_for(
        db,
        item=item,
        branch=branch,
    )

    movement = (
        RetailInventoryService.apply_movement(
            db,
            balance=balance,
            movement_type="MANUAL_REMOVAL",
            quantity_delta=-Decimal(
                str(data.quantity)
            ),
            idempotency_key=(
                _idempotency_key(
                    operation="removal",
                    branch_id=branch.id,
                    item_id=item.id,
                    supplied=(
                        data.idempotency_key
                    ),
                )
            ),
            note=data.note,
            created_by_admin_id=admin.id,
        )
    )

    if (
        Decimal(
            str(movement.balance_after)
        )
        < Decimal("0.000")
    ):
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Inventory removal would "
                "drive stock below zero"
            ),
        )

    db.commit()
    db.refresh(balance)

    return _row(
        branch=branch,
        item=item,
        balance=balance,
    )


@router.post(
    "/{item_id}/adjust",
    response_model=(
        AdminRetailInventoryRowResponse
    ),
)
def adjust_retail_inventory(
    item_id: int,
    data: AdminRetailInventoryAdjustmentCreate,
    admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> AdminRetailInventoryRowResponse:
    branch = _branch_by_code(
        db,
        data.branch_code,
    )

    item = _item_for_branch(
        db,
        item_id=item_id,
        branch=branch,
    )

    _require_tracked_product(item)

    balance = _balance_for(
        db,
        item=item,
        branch=branch,
    )

    RetailInventoryService.adjust_to_physical_count(
        db,
        balance=balance,
        physical_quantity=data.physical_quantity,
        idempotency_key=(
            _idempotency_key(
                operation="adjust",
                branch_id=branch.id,
                item_id=item.id,
                supplied=data.idempotency_key,
            )
        ),
        note=data.note,
        created_by_admin_id=admin.id,
    )

    db.commit()
    db.refresh(balance)

    return _row(
        branch=branch,
        item=item,
        balance=balance,
    )
