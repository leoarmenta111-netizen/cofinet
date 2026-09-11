from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.admin_security import require_super_admin
from app.database.deps import get_db
from app.models.admin import Admin
from app.models.branch import Branch
from app.models.pos_catalog import PosProduct
from app.models.pos_inventory import (
    PosInventoryBalance,
    PosInventoryItem,
    PosInventoryMovement,
)
from app.models.pos_orders import PosOrder
from app.schemas.admin_pos_inventory import (
    AdminInventoryAdjustmentCreate,
    AdminInventoryMovementResponse,
    AdminInventoryReceiptCreate,
    AdminInventoryRowResponse,
    AdminInventoryTrackingUpdate,
    AdminInventoryWasteCreate,
)
from app.services.pos_inventory_service import PosInventoryService


router = APIRouter(
    prefix="/admin/pos/inventory",
    tags=["Admin POS Inventory"],
)


def _branch_by_code(
    db: Session,
    branch_code: str,
) -> Branch:
    branch = db.scalar(
        select(Branch).where(
            Branch.code == branch_code
        )
    )

    if branch is None:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    return branch


def _balance_for(
    db: Session,
    *,
    item_id: int,
    branch_code: str,
) -> PosInventoryBalance:
    branch = _branch_by_code(db, branch_code)

    balance = db.scalar(
        select(PosInventoryBalance).where(
            PosInventoryBalance.inventory_item_id == item_id,
            PosInventoryBalance.branch_id == branch.id,
        )
    )

    if balance is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory balance not found",
        )

    return balance


def _row(
    db: Session,
    balance: PosInventoryBalance,
) -> dict:
    item = db.get(
        PosInventoryItem,
        balance.inventory_item_id,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found",
        )

    branch = db.get(
        Branch,
        balance.branch_id,
    )

    if branch is None:
        raise HTTPException(
            status_code=404,
            detail="Branch not found",
        )

    product = None

    if item.product_id is not None:
        product = db.get(
            PosProduct,
            item.product_id,
        )

    return {
        "item_id": item.id,
        "product_id": item.product_id,
        "product_name": (
            product.name
            if product is not None
            else item.name
        ),
        "branch_id": branch.id,
        "branch_code": branch.code,
        "branch_name": branch.name,
        "is_tracked": balance.is_tracked,
        "quantity_on_hand": balance.quantity_on_hand,
        "low_stock_threshold":
            balance.low_stock_threshold,
        "status": PosInventoryService.status_for(
            tracked=balance.is_tracked,
            quantity_on_hand=balance.quantity_on_hand,
            threshold=balance.low_stock_threshold,
        ),
        "updated_at": balance.updated_at,
    }


@router.get(
    "",
    response_model=list[AdminInventoryRowResponse],
)
def list_inventory(
    branch_code: str | None = None,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    statement = select(PosInventoryBalance)

    if branch_code is not None:
        branch = _branch_by_code(
            db,
            branch_code,
        )
        statement = statement.where(
            PosInventoryBalance.branch_id == branch.id
        )

    balances = list(
        db.scalars(
            statement.order_by(
                PosInventoryBalance.id
            )
        )
    )

    return [
        _row(db, balance)
        for balance in balances
    ]


@router.get(
    "/{item_id}",
    response_model=AdminInventoryRowResponse,
)
def get_inventory_detail(
    item_id: int,
    branch_code: str,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    balance = _balance_for(
        db,
        item_id=item_id,
        branch_code=branch_code,
    )

    return _row(db, balance)


@router.get(
    "/{item_id}/movements",
    response_model=list[AdminInventoryMovementResponse],
)
def list_inventory_movements(
    item_id: int,
    branch_code: str,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    balance = _balance_for(
        db,
        item_id=item_id,
        branch_code=branch_code,
    )

    movements = list(
        db.scalars(
            select(PosInventoryMovement)
            .where(
                PosInventoryMovement.inventory_item_id
                == item_id,
                PosInventoryMovement.branch_id
                == balance.branch_id,
            )
            .order_by(
                PosInventoryMovement.id.desc()
            )
        )
    )

    result = []

    for movement in movements:
        order = None

        if movement.order_id is not None:
            order = db.get(
                PosOrder,
                movement.order_id,
            )

        result.append(
            {
                "id": movement.id,
                "movement_type":
                    movement.movement_type,
                "quantity_delta":
                    movement.quantity_delta,
                "balance_after":
                    movement.balance_after,
                "order_id": movement.order_id,
                "order_item_id":
                    movement.order_item_id,
                "order_uuid": (
                    order.order_uuid
                    if order is not None
                    else None
                ),
                "folio": (
                    order.folio
                    if order is not None
                    else None
                ),
                "note": movement.note,
                "created_by_admin_id":
                    movement.created_by_admin_id,
                "created_at":
                    movement.created_at,
            }
        )

    return result


@router.put(
    "/products/{product_id}/branches/{branch_code}",
    response_model=AdminInventoryRowResponse,
)
def update_inventory_tracking(
    product_id: int,
    branch_code: str,
    data: AdminInventoryTrackingUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    product = db.get(
        PosProduct,
        product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    branch = _branch_by_code(
        db,
        branch_code,
    )

    try:
        balance = (
            PosInventoryService.configure_tracking(
                db,
                branch=branch,
                product=product,
                is_tracked=data.is_tracked,
                initial_quantity=data.initial_quantity,
                low_stock_threshold=
                    data.low_stock_threshold,
            )
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    db.refresh(balance)

    return _row(db, balance)


@router.post(
    "/{item_id}/receipt",
    response_model=AdminInventoryRowResponse,
)
def record_inventory_receipt(
    item_id: int,
    data: AdminInventoryReceiptCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    balance = _balance_for(
        db,
        item_id=item_id,
        branch_code=data.branch_code,
    )

    try:
        PosInventoryService.record_receipt(
            db,
            balance=balance,
            quantity=data.quantity,
            note=data.note,
            admin_id=_admin.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    db.refresh(balance)

    return _row(db, balance)


@router.post(
    "/{item_id}/waste",
    response_model=AdminInventoryRowResponse,
)
def record_inventory_waste(
    item_id: int,
    data: AdminInventoryWasteCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    balance = _balance_for(
        db,
        item_id=item_id,
        branch_code=data.branch_code,
    )

    try:
        PosInventoryService.record_waste(
            db,
            balance=balance,
            quantity=data.quantity,
            note=data.note,
            admin_id=_admin.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    db.refresh(balance)

    return _row(db, balance)


@router.post(
    "/{item_id}/adjust",
    response_model=AdminInventoryRowResponse,
)
def adjust_inventory_count(
    item_id: int,
    data: AdminInventoryAdjustmentCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    balance = _balance_for(
        db,
        item_id=item_id,
        branch_code=data.branch_code,
    )

    try:
        PosInventoryService.adjust_count(
            db,
            balance=balance,
            physical_quantity=
                data.physical_quantity,
            note=data.note,
            admin_id=_admin.id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    db.refresh(balance)

    return _row(db, balance)
