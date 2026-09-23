from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosCategory,
    PosModifierGroup,
    PosModifierOption,
    PosProduct,
    PosProductModifierGroup,
)


def _pricing():
    from app.services.pos_pricing_service import (
        PosPricingService,
        PricingItemRequest,
    )

    return PosPricingService, PricingItemRequest


def _seed_catalog(db_session):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"Pricing Branch {suffix}",
        code=f"pricing-{suffix}",
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
        name=f"Latte {suffix}",
        base_price=Decimal("50.00"),
        preparation_station="BAR",
        is_active=True,
    )

    db_session.add(product)
    db_session.flush()

    branch_product = PosBranchProduct(
        branch_id=branch.id,
        product_id=product.id,
        price=Decimal("55.00"),
        is_available=True,
    )

    group = PosModifierGroup(
        name=f"Extras {suffix}",
        required=True,
        min_select=1,
        max_select=2,
        is_active=True,
    )

    db_session.add_all([branch_product, group])
    db_session.flush()

    db_session.add(
        PosProductModifierGroup(
            product_id=product.id,
            modifier_group_id=group.id,
            sort_order=0,
        )
    )

    shot = PosModifierOption(
        group_id=group.id,
        name=f"Extra shot {suffix}",
        price_delta=Decimal("10.00"),
        is_active=True,
    )

    milk = PosModifierOption(
        group_id=group.id,
        name=f"Oat milk {suffix}",
        price_delta=Decimal("5.00"),
        is_active=True,
    )

    syrup = PosModifierOption(
        group_id=group.id,
        name=f"Syrup {suffix}",
        price_delta=Decimal("3.00"),
        is_active=True,
    )

    db_session.add_all([shot, milk, syrup])
    db_session.commit()

    for row in (
        branch,
        category,
        product,
        branch_product,
        group,
        shot,
        milk,
        syrup,
    ):
        db_session.refresh(row)

    return {
        "branch": branch,
        "category": category,
        "product": product,
        "branch_product": branch_product,
        "group": group,
        "shot": shot,
        "milk": milk,
        "syrup": syrup,
    }


def _request(product_id, option_ids, quantity=1):
    _, PricingItemRequest = _pricing()

    return PricingItemRequest(
        product_id=product_id,
        quantity=quantity,
        modifier_option_ids=option_ids,
        notes=None,
    )


def test_branch_override_and_modifier_prices_are_authoritative(
    db_session,
):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    result = PosPricingService.resolve_items(
        db=db_session,
        branch=data["branch"],
        items=[
            _request(
                data["product"].id,
                [data["shot"].id],
                quantity=2,
            )
        ],
    )

    assert len(result) == 1

    item = result[0]

    assert item.unit_base_price == Decimal("55.00")
    assert item.unit_modifier_total == Decimal("10.00")
    assert item.unit_price == Decimal("65.00")
    assert item.line_total == Decimal("130.00")
    assert item.product_name == data["product"].name
    assert item.preparation_station == "BAR"
    assert item.modifiers[0].option_id == data["shot"].id


def test_unavailable_branch_product_is_rejected(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    data["branch_product"].is_available = False
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [data["shot"].id],
                )
            ],
        )

    assert exc.value.status_code == 400


def test_inactive_product_is_rejected(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    data["product"].is_active = False
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [data["shot"].id],
                )
            ],
        )

    assert exc.value.status_code == 400


def test_required_modifier_group_is_enforced(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [],
                )
            ],
        )

    assert exc.value.status_code == 400


def test_modifier_max_select_is_enforced(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [
                        data["shot"].id,
                        data["milk"].id,
                        data["syrup"].id,
                    ],
                )
            ],
        )

    assert exc.value.status_code == 400


def test_duplicate_modifier_option_ids_are_rejected(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [
                        data["shot"].id,
                        data["shot"].id,
                    ],
                )
            ],
        )

    assert exc.value.status_code == 400


def test_option_from_unlinked_group_is_rejected(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    suffix = uuid4().hex[:8]

    other_group = PosModifierGroup(
        name=f"Unlinked {suffix}",
        required=False,
        min_select=0,
        max_select=1,
        is_active=True,
    )

    db_session.add(other_group)
    db_session.flush()

    other_option = PosModifierOption(
        group_id=other_group.id,
        name=f"Foreign option {suffix}",
        price_delta=Decimal("99.00"),
        is_active=True,
    )

    db_session.add(other_option)
    db_session.commit()
    db_session.refresh(other_option)

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [other_option.id],
                )
            ],
        )

    assert exc.value.status_code == 400


def test_inactive_modifier_option_is_rejected(db_session):
    PosPricingService, _ = _pricing()
    data = _seed_catalog(db_session)

    data["shot"].is_active = False
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        PosPricingService.resolve_items(
            db=db_session,
            branch=data["branch"],
            items=[
                _request(
                    data["product"].id,
                    [data["shot"].id],
                )
            ],
        )

    assert exc.value.status_code == 400
