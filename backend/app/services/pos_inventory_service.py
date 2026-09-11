from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select

from app.models.pos_inventory import (
    PosInventoryBalance,
    PosInventoryItem,
    PosInventoryMovement,
)


ZERO = Decimal("0")


class PosInventoryService:
    @staticmethod
    def status_for(
        *,
        tracked,
        quantity_on_hand,
        threshold,
    ):
        quantity_on_hand = Decimal(quantity_on_hand)
        threshold = Decimal(threshold)

        if not tracked:
            return "UNTRACKED"
        if quantity_on_hand < ZERO:
            return "REVIEW"
        if quantity_on_hand == ZERO:
            return "OUT_OF_STOCK"
        if quantity_on_hand <= threshold:
            return "LOW_STOCK"
        return "AVAILABLE"

    @classmethod
    def _apply_movement(
        cls,
        db,
        *,
        balance,
        movement_type,
        quantity_delta,
        order_id=None,
        order_item_id=None,
        idempotency_key=None,
        note=None,
        created_by_admin_id=None,
    ):
        locked_balance = db.scalar(
            select(PosInventoryBalance)
            .where(PosInventoryBalance.id == balance.id)
            .with_for_update()
        )

        if locked_balance is None:
            raise ValueError("Inventory balance not found")

        if idempotency_key is not None:
            existing = db.scalar(
                select(PosInventoryMovement).where(
                    PosInventoryMovement.idempotency_key
                    == idempotency_key
                )
            )
            if existing is not None:
                return existing

        quantity_delta = Decimal(quantity_delta)
        current = Decimal(locked_balance.quantity_on_hand)
        balance_after = current + quantity_delta

        movement = PosInventoryMovement(
            branch_id=locked_balance.branch_id,
            inventory_item_id=locked_balance.inventory_item_id,
            movement_type=movement_type,
            quantity_delta=quantity_delta,
            balance_after=balance_after,
            order_id=order_id,
            order_item_id=order_item_id,
            idempotency_key=idempotency_key,
            note=note,
            created_by_admin_id=created_by_admin_id,
        )

        db.add(movement)
        locked_balance.quantity_on_hand = balance_after
        db.flush()

        return movement

    @classmethod
    def configure_tracking(
        cls,
        db,
        *,
        branch,
        product,
        is_tracked,
        initial_quantity,
        low_stock_threshold,
    ):
        threshold = Decimal(low_stock_threshold)

        item = db.scalar(
            select(PosInventoryItem).where(
                PosInventoryItem.product_id == product.id
            )
        )

        if item is None:
            item = PosInventoryItem(
                product_id=product.id,
                name=product.name,
            )
            db.add(item)
            db.flush()

        balance = db.scalar(
            select(PosInventoryBalance).where(
                PosInventoryBalance.branch_id == branch.id,
                PosInventoryBalance.inventory_item_id == item.id,
            )
        )

        if balance is None:
            balance = PosInventoryBalance(
                branch_id=branch.id,
                inventory_item_id=item.id,
                quantity_on_hand=Decimal("0.000"),
                low_stock_threshold=threshold,
                is_tracked=False,
            )
            db.add(balance)
            db.flush()

        initial_movement = db.scalar(
            select(PosInventoryMovement).where(
                PosInventoryMovement.branch_id == branch.id,
                PosInventoryMovement.inventory_item_id == item.id,
                PosInventoryMovement.movement_type == "INITIAL",
            )
        )

        balance.low_stock_threshold = threshold

        if not is_tracked:
            balance.is_tracked = False
            db.flush()
            return balance

        if initial_movement is None:
            if initial_quantity is None:
                raise ValueError(
                    "Initial quantity is required on first enable"
                )

            initial = Decimal(initial_quantity)

            if initial < ZERO:
                raise ValueError(
                    "Initial quantity cannot be negative"
                )

            balance.is_tracked = True

            cls._apply_movement(
                db,
                balance=balance,
                movement_type="INITIAL",
                quantity_delta=initial,
                idempotency_key=(
                    f"initial:{branch.id}:{item.id}"
                ),
            )
        else:
            balance.is_tracked = True
            db.flush()

        return balance

    @classmethod
    def record_receipt(
        cls,
        db,
        *,
        balance,
        quantity,
        note,
        admin_id,
    ):
        quantity = Decimal(quantity)

        if quantity <= ZERO:
            raise ValueError(
                "Receipt quantity must be greater than zero"
            )

        return cls._apply_movement(
            db,
            balance=balance,
            movement_type="RECEIPT",
            quantity_delta=quantity,
            note=note,
            created_by_admin_id=admin_id,
        )

    @classmethod
    def record_waste(
        cls,
        db,
        *,
        balance,
        quantity,
        note,
        admin_id,
    ):
        quantity = Decimal(quantity)

        if quantity <= ZERO:
            raise ValueError(
                "Waste quantity must be greater than zero"
            )

        if note is None or not note.strip():
            raise ValueError(
                "Waste note is required"
            )

        return cls._apply_movement(
            db,
            balance=balance,
            movement_type="WASTE",
            quantity_delta=-quantity,
            note=note,
            created_by_admin_id=admin_id,
        )

    @classmethod
    def adjust_count(
        cls,
        db,
        *,
        balance,
        physical_quantity,
        note,
        admin_id,
    ):
        if note is None or not note.strip():
            raise ValueError(
                "Adjustment note is required"
            )

        physical_quantity = Decimal(physical_quantity)

        locked_balance = db.scalar(
            select(PosInventoryBalance)
            .where(PosInventoryBalance.id == balance.id)
            .with_for_update()
        )

        if locked_balance is None:
            raise ValueError("Inventory balance not found")

        delta = (
            physical_quantity
            - Decimal(locked_balance.quantity_on_hand)
        )

        return cls._apply_movement(
            db,
            balance=locked_balance,
            movement_type="ADJUSTMENT",
            quantity_delta=delta,
            note=note,
            created_by_admin_id=admin_id,
        )

    @classmethod
    def apply_sale(
        cls,
        db,
        *,
        order,
        allow_negative: bool,
    ):
        pending = []

        for order_item in order.items:
            if order_item.product_id is None:
                continue

            inventory_item = db.scalar(
                select(PosInventoryItem).where(
                    PosInventoryItem.product_id
                    == order_item.product_id
                )
            )

            if inventory_item is None:
                continue

            balance = db.scalar(
                select(PosInventoryBalance)
                .where(
                    PosInventoryBalance.branch_id
                    == order.branch_id,
                    PosInventoryBalance.inventory_item_id
                    == inventory_item.id,
                    PosInventoryBalance.is_tracked.is_(True),
                )
                .with_for_update()
            )

            if balance is None:
                continue

            key = (
                f"sale:{order.order_uuid}:"
                f"{order_item.id}:{inventory_item.id}"
            )

            existing = db.scalar(
                select(PosInventoryMovement).where(
                    PosInventoryMovement.idempotency_key
                    == key
                )
            )

            if existing is not None:
                continue

            requested = Decimal(order_item.quantity)

            if (
                not allow_negative
                and Decimal(balance.quantity_on_hand)
                < requested
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Insufficient inventory stock",
                )

            pending.append(
                (
                    balance,
                    inventory_item,
                    order_item,
                    key,
                )
            )

        movements = []

        for (
            balance,
            inventory_item,
            order_item,
            key,
        ) in pending:
            movement = cls._apply_movement(
                db,
                balance=balance,
                movement_type="SALE",
                quantity_delta=-Decimal(order_item.quantity),
                order_id=order.id,
                order_item_id=order_item.id,
                idempotency_key=key,
            )
            movements.append(movement)

        return movements

    @classmethod
    def reverse_sale(
        cls,
        db,
        *,
        order,
        note=None,
        admin_id=None,
    ):
        sales = list(
            db.scalars(
                select(PosInventoryMovement)
                .where(
                    PosInventoryMovement.order_id == order.id,
                    PosInventoryMovement.movement_type == "SALE",
                )
                .order_by(PosInventoryMovement.id)
            )
        )

        reversals = []

        for sale in sales:
            balance = db.scalar(
                select(PosInventoryBalance).where(
                    PosInventoryBalance.branch_id
                    == sale.branch_id,
                    PosInventoryBalance.inventory_item_id
                    == sale.inventory_item_id,
                )
            )

            if balance is None:
                raise ValueError(
                    "Inventory balance not found for sale reversal"
                )

            key = (
                f"sale-reversal:{order.order_uuid}:"
                f"{sale.order_item_id}:"
                f"{sale.inventory_item_id}"
            )

            reversal = cls._apply_movement(
                db,
                balance=balance,
                movement_type="SALE_REVERSAL",
                quantity_delta=-Decimal(sale.quantity_delta),
                order_id=order.id,
                order_item_id=sale.order_item_id,
                idempotency_key=key,
                note=note,
                created_by_admin_id=admin_id,
            )
            reversals.append(reversal)

        return reversals
