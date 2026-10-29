from decimal import Decimal

from app.models.pos_catalog import (
    PosBranchProduct,
    PosBranchProductVariant,
    PosCategory,
    PosProduct,
    PosProductVariant,
    PosVariant,
    PosVariantGroup,
)


def _seed_product(
    db_session,
    branch,
    *,
    name="Latte",
    base_price="50.00",
    branch_price=None,
    variant_group=None,
):
    category = PosCategory(
        name="Bebidas",
        slug="bebidas",
        sort_order=0,
        is_active=True,
    )
    product = PosProduct(
        category=category,
        variant_group=variant_group,
        name=name,
        base_price=Decimal(base_price),
        preparation_station="BAR",
        sort_order=0,
        is_active=True,
    )
    db_session.add_all([
        category,
        product,
    ])
    db_session.flush()

    branch_product = PosBranchProduct(
        branch_id=branch.id,
        product_id=product.id,
        price=(
            Decimal(branch_price)
            if branch_price is not None
            else None
        ),
        is_available=True,
        sort_order=0,
    )
    db_session.add(branch_product)
    db_session.commit()
    db_session.refresh(product)
    return product


def _seed_variant_group(
    db_session,
    *,
    is_active=True,
):
    group = PosVariantGroup(
        name="Tamanos Cafe",
        sort_order=10,
        is_active=is_active,
    )
    db_session.add(group)
    db_session.flush()
    return group


def _add_variant(
    db_session,
    product,
    group,
    *,
    name,
    price,
    variant_sort,
    product_sort,
    reusable_active=True,
    product_active=True,
    branch=None,
    price_override=None,
    branch_available=None,
):
    variant = PosVariant(
        group=group,
        name=name,
        sort_order=variant_sort,
        is_active=reusable_active,
    )
    db_session.add(variant)
    db_session.flush()

    product_variant = PosProductVariant(
        product_id=product.id,
        variant_id=variant.id,
        price=Decimal(price),
        is_active=product_active,
        sort_order=product_sort,
    )
    db_session.add(product_variant)
    db_session.flush()

    if branch is not None and (
        price_override is not None
        or branch_available is not None
    ):
        override = PosBranchProductVariant(
            branch_id=branch.id,
            product_variant_id=product_variant.id,
            price_override=(
                Decimal(price_override)
                if price_override is not None
                else None
            ),
            is_available=(
                branch_available
                if branch_available is not None
                else True
            ),
        )
        db_session.add(override)

    db_session.commit()
    db_session.refresh(product_variant)
    return product_variant


def _find_product(payload, product_id):
    for category in payload["categories"]:
        for product in category["products"]:
            if product["id"] == product_id:
                return product
    return None


def test_non_variant_product_remains_backward_compatible(
    client,
    db_session,
    default_branch,
):
    product = _seed_product(
        db_session,
        default_branch,
        branch_price="55.00",
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    row = _find_product(
        response.json(),
        product.id,
    )

    assert row is not None
    assert Decimal(row["price"]) == Decimal("55.00")
    assert Decimal(row["display_price"]) == Decimal("55.00")
    assert row["has_variants"] is False
    assert row["variants"] == []


def test_variant_product_returns_branch_resolved_variants_and_lowest_price(
    client,
    db_session,
    default_branch,
):
    group = _seed_variant_group(db_session)
    product = _seed_product(
        db_session,
        default_branch,
        variant_group=group,
    )

    small = _add_variant(
        db_session,
        product,
        group,
        name="Chico 12 oz",
        price="60.00",
        variant_sort=10,
        product_sort=10,
    )
    medium = _add_variant(
        db_session,
        product,
        group,
        name="Mediano 16 oz",
        price="70.00",
        variant_sort=20,
        product_sort=20,
    )
    large = _add_variant(
        db_session,
        product,
        group,
        name="Grande 20 oz",
        price="80.00",
        variant_sort=30,
        product_sort=30,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    row = _find_product(
        response.json(),
        product.id,
    )

    assert row is not None
    assert row["has_variants"] is True
    assert Decimal(row["display_price"]) == Decimal("60.00")
    assert Decimal(row["price"]) == Decimal("60.00")

    assert [
        item["product_variant_id"]
        for item in row["variants"]
    ] == [
        small.id,
        medium.id,
        large.id,
    ]

    assert [
        Decimal(item["price"])
        for item in row["variants"]
    ] == [
        Decimal("60.00"),
        Decimal("70.00"),
        Decimal("80.00"),
    ]


def test_missing_branch_variant_override_inherits_product_variant_price(
    client,
    db_session,
    default_branch,
):
    group = _seed_variant_group(db_session)
    product = _seed_product(
        db_session,
        default_branch,
        variant_group=group,
    )
    configured = _add_variant(
        db_session,
        product,
        group,
        name="Grande 20 oz",
        price="72.00",
        variant_sort=10,
        product_sort=10,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    row = _find_product(response.json(), product.id)

    assert row is not None
    assert len(row["variants"]) == 1
    assert row["variants"][0]["product_variant_id"] == configured.id
    assert Decimal(row["variants"][0]["price"]) == Decimal("72.00")


def test_branch_variant_price_override_replaces_default_price(
    client,
    db_session,
    default_branch,
):
    group = _seed_variant_group(db_session)
    product = _seed_product(
        db_session,
        default_branch,
        variant_group=group,
    )
    configured = _add_variant(
        db_session,
        product,
        group,
        name="Grande 20 oz",
        price="72.00",
        variant_sort=10,
        product_sort=10,
        branch=default_branch,
        price_override="79.00",
        branch_available=True,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    row = _find_product(response.json(), product.id)

    assert row is not None
    assert row["variants"][0]["product_variant_id"] == configured.id
    assert Decimal(row["variants"][0]["price"]) == Decimal("79.00")
    assert Decimal(row["display_price"]) == Decimal("79.00")


def test_unavailable_branch_variant_is_omitted(
    client,
    db_session,
    default_branch,
):
    group = _seed_variant_group(db_session)
    product = _seed_product(
        db_session,
        default_branch,
        variant_group=group,
    )

    available = _add_variant(
        db_session,
        product,
        group,
        name="Chico 12 oz",
        price="60.00",
        variant_sort=10,
        product_sort=10,
    )
    _add_variant(
        db_session,
        product,
        group,
        name="Grande 20 oz",
        price="80.00",
        variant_sort=20,
        product_sort=20,
        branch=default_branch,
        branch_available=False,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    row = _find_product(response.json(), product.id)

    assert row is not None
    assert [
        item["product_variant_id"]
        for item in row["variants"]
    ] == [available.id]


def test_variant_product_with_no_sellable_variants_is_excluded(
    client,
    db_session,
    default_branch,
):
    group = _seed_variant_group(db_session)
    product = _seed_product(
        db_session,
        default_branch,
        variant_group=group,
    )

    _add_variant(
        db_session,
        product,
        group,
        name="Grande 20 oz",
        price="80.00",
        variant_sort=10,
        product_sort=10,
        product_active=False,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    assert _find_product(
        response.json(),
        product.id,
    ) is None


def test_inactive_assigned_variant_group_excludes_product(
    client,
    db_session,
    default_branch,
):
    group = _seed_variant_group(
        db_session,
        is_active=False,
    )
    product = _seed_product(
        db_session,
        default_branch,
        variant_group=group,
    )

    _add_variant(
        db_session,
        product,
        group,
        name="Grande 20 oz",
        price="80.00",
        variant_sort=10,
        product_sort=10,
    )

    response = client.get(
        "/pos/catalog",
        params={"branch_code": default_branch.code},
    )

    assert response.status_code == 200
    assert _find_product(
        response.json(),
        product.id,
    ) is None
