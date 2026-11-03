from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)


QUANTITY_QUANTUM = Decimal("0.001")
ZERO = Decimal("0.000")

VALID_MOVEMENT_TYPES = {
    "INITIAL",
    "MANUAL_ENTRY",
    "MANUAL_REMOVAL",
    "ADJUSTMENT",
    "SALE",
    "RETURN",
    "CANCELLATION_REVERSAL",
}


class RetailInventoryService:
    @staticmethod
    def _quantity(
        value: Decimal,
    ) -> Decimal:
        try:
            quantity = Decimal(
                str(value)
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail="Invalid inventory quantity",
            ) from exc

        if not quantity.is_finite():
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail="Invalid inventory quantity",
            )

        return quantity.quantize(
            QUANTITY_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _idempotency_key(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Idempotency key cannot be empty"
                ),
            )

        return normalized

    @staticmethod
    def status_for(
        *,
        quantity_on_hand: Decimal,
        low_stock_threshold: Decimal | None,
    ) -> str:
        quantity = Decimal(
            str(quantity_on_hand)
        )

        threshold = (
            Decimal(str(low_stock_threshold))
            if low_stock_threshold is not None
            else None
        )

        if quantity < ZERO:
            return "REVIEW"

        if quantity == ZERO:
            return "OUT_OF_STOCK"

        if (
            threshold is not None
            and quantity <= threshold
        ):
            return "LOW_STOCK"

        return "AVAILABLE"

    @staticmethod
    def _existing_movement(
        db: Session,
        *,
        idempotency_key: str | None,
    ) -> RetailInventoryMovement | None:
        if idempotency_key is None:
            return None

        return db.execute(
            select(RetailInventoryMovement).where(
                RetailInventoryMovement.idempotency_key
                == idempotency_key
            )
        ).scalar_one_or_none()

    @classmethod
    def apply_movement(
        cls,
        db: Session,
        *,
        balance: RetailInventoryBalance,
        movement_type: str,
        quantity_delta: Decimal,
        idempotency_key: str | None = None,
        note: str | None = None,
        actor_staff_id: int | None = None,
        authorizer_staff_id: int | None = None,
        created_by_admin_id: int | None = None,
        sale_id: int | None = None,
        sale_line_id: int | None = None,
    ) -> RetailInventoryMovement:
        if movement_type not in VALID_MOVEMENT_TYPES:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Invalid inventory movement type"
                ),
            )

        key = cls._idempotency_key(
            idempotency_key
        )

        # Serialize every mutation for this balance.
        locked_balance = db.execute(
            select(RetailInventoryBalance)
            .where(
                RetailInventoryBalance.id
                == balance.id
            )
            .with_for_update()
            .execution_options(
                populate_existing=True
            )
        ).scalar_one_or_none()

        if locked_balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found",
            )

        existing = cls._existing_movement(
            db,
            idempotency_key=key,
        )

        if existing is not None:
            return existing

        delta = cls._quantity(
            quantity_delta
        )

        current = cls._quantity(
            locked_balance.quantity_on_hand
        )

        balance_after = cls._quantity(
            current + delta
        )

        movement = RetailInventoryMovement(
            branch_id=locked_balance.branch_id,
            item_id=locked_balance.item_id,
            movement_type=movement_type,
            quantity_delta=delta,
            balance_after=balance_after,
            sale_id=sale_id,
            sale_line_id=sale_line_id,
            note=(
                note.strip()
                if note is not None
                and note.strip()
                else None
            ),
            actor_staff_id=actor_staff_id,
            authorizer_staff_id=(
                authorizer_staff_id
            ),
            created_by_admin_id=(
                created_by_admin_id
            ),
            idempotency_key=key,
        )

        db.add(movement)

        locked_balance.quantity_on_hand = (
            balance_after
        )

        db.flush()

        return movement

    @classmethod
    def adjust_to_physical_count(
        cls,
        db: Session,
        *,
        balance: RetailInventoryBalance,
        physical_quantity: Decimal,
        idempotency_key: str,
        note: str,
        actor_staff_id: int | None = None,
        authorizer_staff_id: int | None = None,
        created_by_admin_id: int | None = None,
    ) -> RetailInventoryMovement:
        normalized_note = note.strip()

        if not normalized_note:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Inventory adjustment note "
                    "is required"
                ),
            )

        physical = cls._quantity(
            physical_quantity
        )

        if physical < ZERO:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Physical quantity cannot "
                    "be negative"
                ),
            )

        key = cls._idempotency_key(
            idempotency_key
        )

        locked_balance = db.execute(
            select(RetailInventoryBalance)
            .where(
                RetailInventoryBalance.id
                == balance.id
            )
            .with_for_update()
            .execution_options(
                populate_existing=True
            )
        ).scalar_one_or_none()

        if locked_balance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory balance not found",
            )

        existing = cls._existing_movement(
            db,
            idempotency_key=key,
        )

        if existing is not None:
            return existing

        current = cls._quantity(
            locked_balance.quantity_on_hand
        )

        delta = cls._quantity(
            physical - current
        )

        return cls.apply_movement(
            db,
            balance=locked_balance,
            movement_type="ADJUSTMENT",
            quantity_delta=delta,
            idempotency_key=key,
            note=normalized_note,
            actor_staff_id=actor_staff_id,
            authorizer_staff_id=(
                authorizer_staff_id
            ),
            created_by_admin_id=(
                created_by_admin_id
            ),
        )

    @classmethod
    def decrement_for_sale(
        cls,
        db: Session,
        *,
        item: RetailCatalogItem,
        presentation: (
            RetailPresentation | None
        ),
        quantity: Decimal,
        sale_id: int,
        sale_line_id: int,
        idempotency_key: str,
    ) -> RetailInventoryMovement | None:
        if item.item_type == "SERVICE":
            return None

        if not item.inventory_tracked:
            return None

        if presentation is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Tracked product requires "
                    "a presentation"
                ),
            )

        if (
            presentation.item_id != item.id
            or presentation.branch_id
            != item.branch_id
            or not presentation.is_active
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Invalid retail presentation"
                ),
            )

        sale_quantity = cls._quantity(
            quantity
        )

        if sale_quantity <= ZERO:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Sale quantity must be positive"
                ),
            )

        conversion = cls._quantity(
            presentation.conversion_factor
        )

        base_quantity = cls._quantity(
            sale_quantity * conversion
        )

        key = cls._idempotency_key(
            idempotency_key
        )

        balance = db.execute(
            select(RetailInventoryBalance)
            .where(
                RetailInventoryBalance.branch_id
                == item.branch_id,
                RetailInventoryBalance.item_id
                == item.id,
            )
            .with_for_update()
            .execution_options(
                populate_existing=True
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

        # Idempotency must be checked before the stock
        # comparison. A retry of a successful sale must
        # return the original movement, not fail because
        # stock was already decremented.
        existing = cls._existing_movement(
            db,
            idempotency_key=key,
        )

        if existing is not None:
            return existing

        current = cls._quantity(
            balance.quantity_on_hand
        )

        if current < base_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Insufficient inventory stock",
            )

        return cls.apply_movement(
            db,
            balance=balance,
            movement_type="SALE",
            quantity_delta=-base_quantity,
            idempotency_key=key,
            sale_id=sale_id,
            sale_line_id=sale_line_id,
        )
