from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.auth.security import hash_password
from app.models.branch import Branch
from app.models.pos_cash import PosCashLedgerEntry
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.models.pos_staff import PosStaff, PosStaffRole
from app.schemas.pos_cash import CashDenominationCount
from app.schemas.pos_orders import PosOrderCreate
from app.services.pos_cash_service import PosCashService
from app.services.pos_order_service import PosOrderService


def test_cash_sale_is_added_once_to_open_shift_ledger(
    db_session,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Cash Sale {suffix}",
        code=f"cash-sale-{suffix}",
        is_active=True,
    )
    category = PosCategory(
        name=f"Cash Sale Category {suffix}",
        slug=f"cash-sale-category-{suffix}",
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"Cash Sale Product {suffix}",
        base_price=Decimal("89.00"),
        preparation_station="BAR",
        is_active=True,
    )

    cashier = PosStaff(
        branch_id=branch.id,
        display_name="Cash Sale Cashier",
        role=PosStaffRole.CASHIER,
        pin_hash=hash_password("1111"),
        is_active=True,
    )
    manager = PosStaff(
        branch_id=branch.id,
        display_name="Cash Sale Manager",
        role=PosStaffRole.MANAGER,
        pin_hash=hash_password("2468"),
        is_active=True,
    )

    db_session.add_all(
        [product, cashier, manager]
    )
    db_session.flush()

    db_session.add(
        PosBranchProduct(
            branch_id=branch.id,
            product_id=product.id,
            price=None,
            is_available=True,
        )
    )
    db_session.commit()

    terminal_id = "CASH-SALE-TEST-01"

    shift = PosCashService.open_shift(
        db_session,
        branch_code=branch.code,
        terminal_id=terminal_id,
        opening_amount=Decimal("500.00"),
        requesting_staff=cashier,
        authorizing_manager=manager,
    )
    db_session.commit()
    db_session.refresh(shift)

    now = datetime.now(timezone.utc)
    order_uuid = uuid4()
    payment_uuid = uuid4()

    payload = PosOrderCreate(
        order_uuid=order_uuid,
        branch_code=branch.code,
        terminal_id=terminal_id,
        created_at_client=now,
        items=[
            {
                "product_id": product.id,
                "quantity": 1,
            }
        ],
        payment={
            "payment_uuid": payment_uuid,
            "method": "CASH",
            "amount_tendered": "100.00",
            "created_at_client": now,
        },
    )

    first = PosOrderService.create(
        db_session,
        payload,
    )

    assert first.total == Decimal("89.00")

    entries = (
        db_session
        .query(PosCashLedgerEntry)
        .filter(
            PosCashLedgerEntry.shift_id == shift.id
        )
        .all()
    )

    assert len(entries) == 1

    entry = entries[0]

    assert entry.entry_type == "CASH_SALE"
    assert entry.amount == Decimal("89.00")
    assert entry.idempotency_key == (
        f"CASH_SALE:{payment_uuid}"
    )
    assert entry.reference_type == "pos_order"
    assert entry.reference_id == str(order_uuid)

    # Replaying the same offline/sync payload must not
    # add the cash sale to the drawer twice.
    replay = PosOrderService.create(
        db_session,
        payload,
    )

    assert replay.order_uuid == str(order_uuid)

    entries_after_replay = (
        db_session
        .query(PosCashLedgerEntry)
        .filter(
            PosCashLedgerEntry.shift_id == shift.id
        )
        .all()
    )

    assert len(entries_after_replay) == 1

    reconciliation = (
        PosCashService.submit_closing_count(
            db_session,
            shift_uuid=shift.shift_uuid,
            closing_counts=[
                CashDenominationCount(
                    denomination_cents=50000,
                    quantity=1,
                ),
                CashDenominationCount(
                    denomination_cents=5000,
                    quantity=1,
                ),
                CashDenominationCount(
                    denomination_cents=2000,
                    quantity=1,
                ),
                CashDenominationCount(
                    denomination_cents=1000,
                    quantity=1,
                ),
                CashDenominationCount(
                    denomination_cents=500,
                    quantity=1,
                ),
                CashDenominationCount(
                    denomination_cents=200,
                    quantity=2,
                ),
            ],
            staff=cashier,
        )
    )

    assert reconciliation.counted_cash == Decimal(
        "589.00"
    )
    assert reconciliation.expected_cash == Decimal(
        "589.00"
    )
    assert reconciliation.difference == Decimal(
        "0.00"
    )
