from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosProduct,
)
from app.schemas.pos_orders import PosOrderCreate
from app.services.pos_order_service import PosOrderService
from app.services.pos_pricing_service import PosPricingService


def _seed_catalog(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Shared Pricing {suffix}",
        code=f"shared-pricing-{suffix}",
        is_active=True,
    )

    category = PosCategory(
        name=f"Coffee {suffix}",
        slug=f"coffee-{suffix}",
        is_active=True,
    )

    db_session.add_all([branch, category])
    db_session.flush()

    product = PosProduct(
        category_id=category.id,
        name=f"Americano {suffix}",
        base_price=Decimal("40.00"),
        preparation_station="BAR",
        is_active=True,
    )

    db_session.add(product)
    db_session.flush()

    db_session.add(
        PosBranchProduct(
            branch_id=branch.id,
            product_id=product.id,
            price=Decimal("47.00"),
            is_available=True,
        )
    )

    db_session.commit()
    db_session.refresh(branch)
    db_session.refresh(product)

    return branch, product


def test_online_pos_order_uses_shared_pricing_resolver(
    db_session,
    monkeypatch,
):
    branch, product = _seed_catalog(db_session)

    original = PosPricingService.resolve_items
    calls = []

    def tracked_resolve_items(*, db, branch, items):
        calls.append(
            {
                "branch_id": branch.id,
                "item_count": len(items),
            }
        )

        return original(
            db=db,
            branch=branch,
            items=items,
        )

    monkeypatch.setattr(
        PosPricingService,
        "resolve_items",
        staticmethod(tracked_resolve_items),
    )

    now = datetime.now(timezone.utc)

    payload = PosOrderCreate(
        order_uuid=uuid4(),
        branch_code=branch.code,
        terminal_id="SHARED-PRICING-TEST",
        created_at_client=now,
        items=[
            {
                "product_id": product.id,
                "quantity": 2,
            }
        ],
        payment={
            "payment_uuid": uuid4(),
            "method": "CASH",
            "amount_tendered": "100.00",
            "created_at_client": now,
        },
    )

    result = PosOrderService.create(
        db_session,
        payload,
    )

    assert len(calls) == 1
    assert calls[0]["branch_id"] == branch.id
    assert calls[0]["item_count"] == 1

    assert result.subtotal == Decimal("94.00")
    assert result.total == Decimal("94.00")
