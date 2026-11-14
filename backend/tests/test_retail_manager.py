from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.auth.pos_staff_security import (
    create_pos_staff_token,
)
from app.auth.security import (
    hash_password,
)
from app.models.branch import Branch
from app.models.pos_staff import (
    PosStaff,
)
from app.models.retail_catalog import (
    RetailCatalogItem,
)
from app.models.retail_inventory import (
    RetailInventoryBalance,
    RetailInventoryMovement,
)


def _branch(
    db_session,
    label,
):
    suffix = uuid4().hex[:8]

    branch = Branch(
        name=f"{label} {suffix}",
        code=f"{label.lower()}-{suffix}",
        is_active=True,
    )

    db_session.add(branch)
    db_session.commit()
    db_session.refresh(branch)

    return branch


def _staff(
    db_session,
    *,
    branch,
    name,
    role="CASHIER",
    module_code="PAPELERIA",
    pin="1234",
):
    staff = PosStaff(
        branch_id=branch.id,
        module_code=module_code,
        display_name=name,
        role=role,
        pin_hash=hash_password(pin),
        is_active=True,
    )

    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    return staff


def _headers(
    staff,
    branch,
    *,
    terminal="PAP-A3",
):
    token = create_pos_staff_token(
        staff,
        branch_code=branch.code,
        terminal_id=terminal,
    )

    return {
        "Authorization":
            f"Bearer {token}"
    }


def _product(
    db_session,
    *,
    branch,
    sku,
    stock="10.000",
    tracked=True,
):
    item = RetailCatalogItem(
        branch_id=branch.id,
        item_type="PRODUCT",
        sku=sku,
        name=f"Product {sku}",
        description=None,
        category="Test",
        base_unit_code="PIECE",
        cost=Decimal("1.00"),
        inventory_tracked=tracked,
        low_stock_threshold=(
            Decimal("2.000")
            if tracked
            else None
        ),
        max_stock=(
            Decimal("100.000")
            if tracked
            else None
        ),
        is_active=True,
    )

    db_session.add(item)
    db_session.flush()

    balance = None

    if tracked:
        balance = RetailInventoryBalance(
            branch_id=branch.id,
            item_id=item.id,
            quantity_on_hand=Decimal(stock),
            low_stock_threshold=(
                Decimal("2.000")
            ),
            max_stock=(
                Decimal("100.000")
            ),
        )
        db_session.add(balance)

    db_session.commit()
    db_session.refresh(item)

    if balance is not None:
        db_session.refresh(balance)

    return item, balance


def test_retail_manager_requires_authentication(
    client,
):
    response = client.get(
        "/retail/manager/inventory"
    )

    assert response.status_code == 401


def test_retail_manager_rejects_non_papeleria_session(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerCafe",
    )

    staff = _staff(
        db_session,
        branch=branch,
        name="Cafe Cashier",
        module_code="CAFE",
    )

    response = client.get(
        "/retail/manager/inventory",
        headers=_headers(
            staff,
            branch,
        ),
    )

    assert response.status_code == 403


def test_retail_manager_staff_list_is_branch_and_module_scoped(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerList",
    )

    other = _branch(
        db_session,
        "ManagerOther",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
    )

    manager = _staff(
        db_session,
        branch=branch,
        name="Pap Manager",
        role="MANAGER",
        pin="2468",
    )

    _staff(
        db_session,
        branch=branch,
        name="Cafe Manager",
        role="MANAGER",
        module_code="CAFE",
        pin="2468",
    )

    _staff(
        db_session,
        branch=other,
        name="Other Manager",
        role="MANAGER",
        pin="2468",
    )

    response = client.get(
        "/retail/manager/staff",
        headers=_headers(
            cashier,
            branch,
        ),
    )

    assert response.status_code == 200

    rows = response.json()

    assert rows == [
        {
            "id": manager.id,
            "display_name": (
                "Pap Manager"
            ),
            "role": "MANAGER",
        }
    ]


def test_retail_manager_inventory_is_branch_scoped(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerInventory",
    )

    other = _branch(
        db_session,
        "ManagerInventoryOther",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
    )

    item, _ = _product(
        db_session,
        branch=branch,
        sku="VISIBLE-001",
    )

    _product(
        db_session,
        branch=other,
        sku="HIDDEN-001",
    )

    _product(
        db_session,
        branch=branch,
        sku="UNTRACKED-001",
        tracked=False,
    )

    response = client.get(
        "/retail/manager/inventory",
        headers=_headers(
            cashier,
            branch,
        ),
    )

    assert response.status_code == 200

    rows = response.json()

    assert len(rows) == 1
    assert (
        rows[0]["item_id"]
        == item.id
    )
    assert (
        rows[0]["sku"]
        == "VISIBLE-001"
    )


def test_retail_manager_entry_is_idempotent_and_audited(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerEntry",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
        pin="1111",
    )

    manager = _staff(
        db_session,
        branch=branch,
        name="Manager",
        role="MANAGER",
        pin="2468",
    )

    item, balance = _product(
        db_session,
        branch=branch,
        sku="ENTRY-001",
        stock="10.000",
    )

    payload = {
        "authorizing_manager_staff_id":
            manager.id,
        "manager_pin": "2468",
        "idempotency_key":
            "delivery-001",
        "note":
            "Supplier delivery",
        "quantity": "5.000",
    }

    first = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/entry"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json=payload,
    )

    assert first.status_code == 200
    assert (
        Decimal(
            str(
                first.json()[
                    "quantity_on_hand"
                ]
            )
        )
        == Decimal("15.000")
    )

    replay = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/entry"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json=payload,
    )

    assert replay.status_code == 200

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("15.000")
    )

    movements = list(
        db_session.scalars(
            select(
                RetailInventoryMovement
            ).where(
                RetailInventoryMovement.item_id
                == item.id,
                RetailInventoryMovement
                .movement_type
                == "MANUAL_ENTRY",
            )
        )
    )

    assert len(movements) == 1

    movement = movements[0]

    assert (
        movement.actor_staff_id
        == cashier.id
    )
    assert (
        movement.authorizer_staff_id
        == manager.id
    )
    assert (
        movement.created_by_admin_id
        is None
    )


def test_cashier_cannot_authorize_manager_inventory_action(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerRole",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
        pin="1111",
    )

    item, balance = _product(
        db_session,
        branch=branch,
        sku="ROLE-001",
    )

    response = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/entry"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json={
            "authorizing_manager_staff_id":
                cashier.id,
            "manager_pin": "1111",
            "idempotency_key":
                "role-001",
            "note": "Invalid",
            "quantity": "1.000",
        },
    )

    assert response.status_code == 403

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("10.000")
    )


def test_wrong_module_manager_cannot_authorize_papeleria_inventory(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerModule",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Pap Cashier",
    )

    cafe_manager = _staff(
        db_session,
        branch=branch,
        name="Cafe Manager",
        role="MANAGER",
        module_code="CAFE",
        pin="2468",
    )

    item, balance = _product(
        db_session,
        branch=branch,
        sku="MODULE-001",
    )

    response = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/entry"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json={
            "authorizing_manager_staff_id":
                cafe_manager.id,
            "manager_pin": "2468",
            "idempotency_key":
                "module-001",
            "note": "Invalid module",
            "quantity": "1.000",
        },
    )

    assert response.status_code == 403

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("10.000")
    )


def test_retail_manager_removal_cannot_drive_stock_negative(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerRemoval",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
    )

    manager = _staff(
        db_session,
        branch=branch,
        name="Manager",
        role="MANAGER",
        pin="2468",
    )

    item, balance = _product(
        db_session,
        branch=branch,
        sku="REMOVE-001",
        stock="3.000",
    )

    response = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/removal"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json={
            "authorizing_manager_staff_id":
                manager.id,
            "manager_pin": "2468",
            "idempotency_key":
                "remove-negative",
            "note": "Damaged",
            "quantity": "4.000",
        },
    )

    assert response.status_code == 409

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("3.000")
    )

    movement = db_session.execute(
        select(
            RetailInventoryMovement
        ).where(
            RetailInventoryMovement.item_id
            == item.id
        )
    ).scalar_one_or_none()

    assert movement is None


def test_retail_manager_adjustment_is_audited(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerAdjust",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
    )

    manager = _staff(
        db_session,
        branch=branch,
        name="Manager",
        role="MANAGER",
        pin="2468",
    )

    item, balance = _product(
        db_session,
        branch=branch,
        sku="ADJUST-001",
        stock="10.000",
    )

    response = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/adjust"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json={
            "authorizing_manager_staff_id":
                manager.id,
            "manager_pin": "2468",
            "idempotency_key":
                "physical-count-001",
            "note":
                "Physical count",
            "physical_quantity":
                "7.000",
        },
    )

    assert response.status_code == 200

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("7.000")
    )

    movement = db_session.execute(
        select(
            RetailInventoryMovement
        ).where(
            RetailInventoryMovement.item_id
            == item.id
        )
    ).scalar_one()

    assert (
        movement.movement_type
        == "ADJUSTMENT"
    )
    assert (
        movement.quantity_delta
        == Decimal("-3.000")
    )
    assert (
        movement.actor_staff_id
        == cashier.id
    )
    assert (
        movement.authorizer_staff_id
        == manager.id
    )


def test_retail_manager_cannot_mutate_other_branch_item(
    client,
    db_session,
):
    branch = _branch(
        db_session,
        "ManagerBranch",
    )

    other = _branch(
        db_session,
        "ManagerBranchOther",
    )

    cashier = _staff(
        db_session,
        branch=branch,
        name="Cashier",
    )

    manager = _staff(
        db_session,
        branch=branch,
        name="Manager",
        role="MANAGER",
        pin="2468",
    )

    item, balance = _product(
        db_session,
        branch=other,
        sku="OTHER-001",
    )

    response = client.post(
        (
            "/retail/manager/inventory/"
            f"{item.id}/entry"
        ),
        headers=_headers(
            cashier,
            branch,
        ),
        json={
            "authorizing_manager_staff_id":
                manager.id,
            "manager_pin": "2468",
            "idempotency_key":
                "other-branch",
            "note":
                "Wrong branch",
            "quantity":
                "1.000",
        },
    )

    assert response.status_code == 404

    db_session.refresh(balance)

    assert (
        balance.quantity_on_hand
        == Decimal("10.000")
    )


def test_retail_manager_routes_are_registered():
    from app.main import app

    paths = app.openapi()["paths"]

    expected = {
        "/retail/manager/staff":
            {"get"},
        "/retail/manager/inventory":
            {"get"},
        (
            "/retail/manager/inventory/"
            "{item_id}/movements"
        ):
            {"get"},
        (
            "/retail/manager/inventory/"
            "{item_id}/entry"
        ):
            {"post"},
        (
            "/retail/manager/inventory/"
            "{item_id}/removal"
        ):
            {"post"},
        (
            "/retail/manager/inventory/"
            "{item_id}/adjust"
        ):
            {"post"},
    }

    for path, methods in expected.items():
        assert path in paths

        assert methods <= set(
            paths[path].keys()
        )
