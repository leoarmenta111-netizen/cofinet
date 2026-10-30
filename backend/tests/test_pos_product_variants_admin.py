from decimal import Decimal

from app.models.pos_catalog import (
    PosBranchProductVariant,
    PosCategory,
    PosProduct,
    PosProductVariant,
    PosVariant,
    PosVariantGroup,
)


def _seed_product_variant_context(db_session):
    category = PosCategory(
        name="Bebidas",
        slug="bebidas",
        sort_order=0,
        is_active=True,
    )
    group_a = PosVariantGroup(
        name="Tamanos Cafe",
        sort_order=10,
        is_active=True,
    )
    group_b = PosVariantGroup(
        name="Tamanos Frios",
        sort_order=20,
        is_active=True,
    )
    variant_a = PosVariant(
        group=group_a,
        name="Grande 20 oz",
        sort_order=10,
        is_active=True,
    )
    variant_b = PosVariant(
        group=group_b,
        name="Grande Frio 24 oz",
        sort_order=10,
        is_active=True,
    )
    product = PosProduct(
        category=category,
        name="Latte",
        base_price=Decimal("50.00"),
        preparation_station="BAR",
        sort_order=0,
        is_active=True,
    )

    db_session.add_all([
        category,
        group_a,
        group_b,
        variant_a,
        variant_b,
        product,
    ])
    db_session.commit()

    for item in (
        group_a,
        group_b,
        variant_a,
        variant_b,
        product,
    ):
        db_session.refresh(item)

    return {
        "product": product,
        "group_a": group_a,
        "group_b": group_b,
        "variant_a": variant_a,
        "variant_b": variant_b,
    }


def test_admin_catalog_exposes_empty_variant_groups(client, super_headers):
    response = client.get(
        "/admin/pos/catalog",
        headers=super_headers,
    )

    assert response.status_code == 200
    assert response.json()["variant_groups"] == []


def test_admin_can_create_reusable_variant_group(client, super_headers):
    response = client.post(
        "/admin/pos/catalog/variant-groups",
        headers=super_headers,
        json={
            "name": "Tamaños Café",
            "sort_order": 10,
        },
    )

    assert response.status_code == 201
    groups = response.json()["variant_groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "Tamaños Café"
    assert groups[0]["sort_order"] == 10
    assert groups[0]["is_active"] is True
    assert groups[0]["variants"] == []


def test_admin_can_update_and_deactivate_variant_group(
    client,
    super_headers,
    db_session,
):
    group = PosVariantGroup(
        name="Tamaños Café",
        sort_order=10,
        is_active=True,
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.patch(
        f"/admin/pos/catalog/variant-groups/{group.id}",
        headers=super_headers,
        json={
            "name": "Tamaños Bebidas",
            "sort_order": 20,
            "is_active": False,
        },
    )

    assert response.status_code == 200
    groups = response.json()["variant_groups"]
    assert groups[0]["id"] == group.id
    assert groups[0]["name"] == "Tamaños Bebidas"
    assert groups[0]["sort_order"] == 20
    assert groups[0]["is_active"] is False


def test_admin_can_create_variant_inside_group(
    client,
    super_headers,
    db_session,
):
    group = PosVariantGroup(
        name="Tamaños Café",
        sort_order=10,
        is_active=True,
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    response = client.post(
        f"/admin/pos/catalog/variant-groups/{group.id}/variants",
        headers=super_headers,
        json={
            "name": "Grande 20 oz",
            "sort_order": 30,
        },
    )

    assert response.status_code == 201
    variants = response.json()["variant_groups"][0]["variants"]
    assert len(variants) == 1
    assert variants[0]["variant_group_id"] == group.id
    assert variants[0]["name"] == "Grande 20 oz"
    assert variants[0]["sort_order"] == 30
    assert variants[0]["is_active"] is True


def test_admin_can_update_and_deactivate_variant(
    client,
    super_headers,
    db_session,
):
    group = PosVariantGroup(
        name="Tamaños Café",
        sort_order=10,
        is_active=True,
    )
    db_session.add(group)
    db_session.flush()

    variant = PosVariant(
        variant_group_id=group.id,
        name="Grande 20 oz",
        sort_order=30,
        is_active=True,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(variant)

    response = client.patch(
        f"/admin/pos/catalog/variants/{variant.id}",
        headers=super_headers,
        json={
            "name": "Grande 22 oz",
            "sort_order": 40,
            "is_active": False,
        },
    )

    assert response.status_code == 200
    variants = response.json()["variant_groups"][0]["variants"]
    assert variants[0]["id"] == variant.id
    assert variants[0]["name"] == "Grande 22 oz"
    assert variants[0]["sort_order"] == 40
    assert variants[0]["is_active"] is False


def test_admin_can_assign_variant_group_to_product(
    client,
    super_headers,
    db_session,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group = ctx["group_a"]

    response = client.put(
        f"/admin/pos/catalog/products/{product.id}/variant-group/{group.id}",
        headers=super_headers,
    )

    assert response.status_code == 200
    row = next(
        item
        for item in response.json()["products"]
        if item["id"] == product.id
    )
    assert row["variant_group_id"] == group.id
    assert row["variants"] == []


def test_admin_rejects_variant_from_different_product_group(
    client,
    super_headers,
    db_session,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group = ctx["group_a"]
    wrong_variant = ctx["variant_b"]

    product.variant_group_id = group.id
    db_session.commit()

    response = client.put(
        f"/admin/pos/catalog/products/{product.id}/variants/{wrong_variant.id}",
        headers=super_headers,
        json={
            "price": "75.00",
            "is_active": True,
            "sort_order": 10,
        },
    )

    assert response.status_code == 422


def test_admin_reactivates_existing_valid_product_variant(
    client,
    super_headers,
    db_session,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group = ctx["group_a"]
    variant = ctx["variant_a"]

    product.variant_group_id = group.id
    existing = PosProductVariant(
        product_id=product.id,
        variant_id=variant.id,
        price=Decimal("65.00"),
        is_active=False,
        sort_order=50,
    )
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)
    original_id = existing.id

    response = client.put(
        f"/admin/pos/catalog/products/{product.id}/variants/{variant.id}",
        headers=super_headers,
        json={
            "price": "72.50",
            "is_active": True,
            "sort_order": 5,
        },
    )

    assert response.status_code == 200

    db_session.expire_all()
    saved = db_session.get(
        PosProductVariant,
        original_id,
    )
    assert saved is not None
    assert saved.is_active is True
    assert Decimal(saved.price) == Decimal("72.50")
    assert saved.sort_order == 5


def test_reassigning_variant_group_deactivates_mismatched_rows(
    client,
    super_headers,
    db_session,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group_a = ctx["group_a"]
    group_b = ctx["group_b"]
    variant_a = ctx["variant_a"]

    product.variant_group_id = group_a.id
    existing = PosProductVariant(
        product_id=product.id,
        variant_id=variant_a.id,
        price=Decimal("72.00"),
        is_active=True,
        sort_order=10,
    )
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)
    existing_id = existing.id

    response = client.put(
        f"/admin/pos/catalog/products/{product.id}/variant-group/{group_b.id}",
        headers=super_headers,
    )

    assert response.status_code == 200

    db_session.expire_all()
    saved_product = db_session.get(
        PosProduct,
        product.id,
    )
    saved_variant = db_session.get(
        PosProductVariant,
        existing_id,
    )

    assert saved_product.variant_group_id == group_b.id
    assert saved_variant is not None
    assert saved_variant.is_active is False


def test_removing_variant_group_deactivates_product_variants(
    client,
    super_headers,
    db_session,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group = ctx["group_a"]
    variant = ctx["variant_a"]

    product.variant_group_id = group.id
    existing = PosProductVariant(
        product_id=product.id,
        variant_id=variant.id,
        price=Decimal("72.00"),
        is_active=True,
        sort_order=10,
    )
    db_session.add(existing)
    db_session.commit()
    db_session.refresh(existing)
    existing_id = existing.id

    response = client.delete(
        f"/admin/pos/catalog/products/{product.id}/variant-group",
        headers=super_headers,
    )

    assert response.status_code == 200

    db_session.expire_all()
    saved_product = db_session.get(PosProduct, product.id)
    saved_variant = db_session.get(PosProductVariant, existing_id)

    assert saved_product.variant_group_id is None
    assert saved_variant is not None
    assert saved_variant.is_active is False


def test_admin_can_set_explicit_branch_variant_override(
    client,
    super_headers,
    db_session,
    default_branch,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group = ctx["group_a"]
    variant = ctx["variant_a"]

    product.variant_group_id = group.id
    product_variant = PosProductVariant(
        product_id=product.id,
        variant_id=variant.id,
        price=Decimal("72.00"),
        is_active=True,
        sort_order=10,
    )
    db_session.add(product_variant)
    db_session.commit()
    db_session.refresh(product_variant)

    response = client.put(
        f"/admin/pos/catalog/products/{product.id}/variants/{variant.id}/branches/{default_branch.code}",
        headers=super_headers,
        json={
            "price_override": "79.00",
            "is_available": False,
        },
    )

    assert response.status_code == 200

    row = next(
        item
        for item in response.json()["products"]
        if item["id"] == product.id
    )
    configured = next(
        item
        for item in row["variants"]
        if item["variant_id"] == variant.id
    )
    branch = next(
        item
        for item in configured["branches"]
        if item["branch_code"] == default_branch.code
    )

    assert Decimal(branch["price_override"]) == Decimal("79.00")
    assert Decimal(branch["effective_price"]) == Decimal("79.00")
    assert branch["is_available"] is False

    override = (
        db_session.query(PosBranchProductVariant)
        .filter_by(
            branch_id=default_branch.id,
            product_variant_id=product_variant.id,
        )
        .one()
    )
    assert Decimal(override.price_override) == Decimal("79.00")
    assert override.is_available is False


def test_admin_catalog_reads_product_variants_with_synthesized_branch_defaults(
    client,
    super_headers,
    db_session,
    default_branch,
):
    ctx = _seed_product_variant_context(db_session)
    product = ctx["product"]
    group = ctx["group_a"]
    variant = ctx["variant_a"]

    product.variant_group_id = group.id
    product_variant = PosProductVariant(
        product_id=product.id,
        variant_id=variant.id,
        price=Decimal("72.00"),
        is_active=True,
        sort_order=10,
    )
    db_session.add(product_variant)
    db_session.commit()
    db_session.refresh(product_variant)

    response = client.get(
        "/admin/pos/catalog",
        headers=super_headers,
    )

    assert response.status_code == 200

    row = next(
        item
        for item in response.json()["products"]
        if item["id"] == product.id
    )

    assert row["variant_group_id"] == group.id
    assert len(row["variants"]) == 1

    configured = row["variants"][0]
    assert configured["product_variant_id"] == product_variant.id
    assert configured["variant_id"] == variant.id
    assert configured["variant_name"] == variant.name
    assert Decimal(configured["price"]) == Decimal("72.00")
    assert configured["is_active"] is True
    assert configured["sort_order"] == 10

    assert len(configured["branches"]) == 1
    branch = configured["branches"][0]
    assert branch["branch_code"] == default_branch.code
    assert branch["branch_name"] == default_branch.name
    assert branch["price_override"] is None
    assert Decimal(branch["effective_price"]) == Decimal("72.00")
    assert branch["is_available"] is True
