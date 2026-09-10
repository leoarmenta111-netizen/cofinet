from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_orders import PosOrder
from app.models.pos_receipts import PosReceiptSnapshot
from app.schemas.pos_receipts import ReceiptSnapshotV1


class PosReceiptService:
    @classmethod
    def validate_snapshot(
        cls,
        snapshot: ReceiptSnapshotV1,
    ) -> ReceiptSnapshotV1:
        if snapshot.schema_version != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported receipt snapshot schema version",
            )

        calculated_subtotal_cents = 0

        for item in snapshot.items:
            expected_line_total = (
                item.unit_price_cents
                * item.quantity
            )

            if (
                item.line_total_cents
                != expected_line_total
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Receipt item line total "
                        "is inconsistent"
                    ),
                )

            calculated_subtotal_cents += (
                item.line_total_cents
            )

        if (
            snapshot.totals.subtotal_cents
            != calculated_subtotal_cents
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Receipt subtotal is inconsistent"
                ),
            )

        net_cents = (
            snapshot.totals.subtotal_cents
            - snapshot.totals.discount_cents
        )

        if net_cents < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Receipt discount exceeds subtotal"
                ),
            )

        tax_rate = Decimal(
            snapshot.totals.tax_rate
        )

        if snapshot.totals.tax_mode == "NONE":
            expected_tax_cents = 0

        elif snapshot.totals.tax_mode == "ADDED":
            expected_tax_cents = int(
                (
                    Decimal(net_cents)
                    * tax_rate
                ).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP,
                )
            )

        elif snapshot.totals.tax_mode == "INCLUDED":
            expected_tax_cents = int(
                (
                    Decimal(net_cents)
                    * tax_rate
                    / (
                        Decimal("1")
                        + tax_rate
                    )
                ).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP,
                )
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported tax mode",
            )

        if (
            snapshot.totals.tax_cents
            != expected_tax_cents
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Receipt tax is inconsistent"
                ),
            )

        expected_total_cents = (
            net_cents
            + snapshot.totals.tip_cents
        )

        if snapshot.totals.tax_mode == "ADDED":
            expected_total_cents += (
                expected_tax_cents
            )

        if (
            snapshot.totals.total_cents
            != expected_total_cents
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Receipt total is inconsistent"
                ),
            )

        if (
            snapshot.payment.amount_cents
            != snapshot.totals.total_cents
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Receipt payment amount "
                    "is inconsistent"
                ),
            )

        if snapshot.payment.method == "CASH":
            if (
                snapshot.payment.amount_tendered_cents
                is None
                or snapshot.payment.change_due_cents
                is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cash receipt requires tendered "
                        "amount and change"
                    ),
                )

            if (
                snapshot.payment.amount_tendered_cents
                < snapshot.payment.amount_cents
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cash tendered amount "
                        "is insufficient"
                    ),
                )

            expected_change_cents = (
                snapshot.payment.amount_tendered_cents
                - snapshot.payment.amount_cents
            )

            if (
                snapshot.payment.change_due_cents
                != expected_change_cents
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Receipt cash change "
                        "is inconsistent"
                    ),
                )

        return snapshot

    @classmethod
    def create_for_order(
        cls,
        db: Session,
        order: PosOrder,
        snapshot: ReceiptSnapshotV1,
    ) -> PosReceiptSnapshot:
        cls.validate_snapshot(snapshot)

        if str(snapshot.order_uuid) != order.order_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receipt order UUID does not match order",
            )

        if snapshot.folio != order.folio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receipt folio does not match order",
            )

        existing = db.execute(
            select(PosReceiptSnapshot).where(
                PosReceiptSnapshot.order_id == order.id
            )
        ).scalar_one_or_none()

        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Receipt snapshot already exists",
            )

        row = PosReceiptSnapshot(
            order_id=order.id,
            schema_version=1,
            snapshot_json=snapshot.model_dump(
                mode="json",
            ),
        )

        db.add(row)
        db.flush()

        return row

    @classmethod
    def get_for_order(
        cls,
        db: Session,
        order_uuid: str,
        branch_code: str,
    ) -> PosReceiptSnapshot:
        normalized_branch_code = (
            branch_code.strip().lower()
        )

        if normalized_branch_code == "principal":
            normalized_branch_code = (
                "nuevo-vallarta"
            )

        branch = db.execute(
            select(Branch).where(
                Branch.code
                == normalized_branch_code,
                Branch.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        row = db.execute(
            select(PosReceiptSnapshot)
            .join(
                PosOrder,
                PosOrder.id
                == PosReceiptSnapshot.order_id,
            )
            .where(
                PosOrder.order_uuid == order_uuid,
                PosOrder.branch_id == branch.id,
            )
        ).scalar_one_or_none()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receipt not found",
            )

        return row
