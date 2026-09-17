from app.models.pos_catalog import PosVariant, PosVariantGroup


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
