import pytest


pytestmark = pytest.mark.usefixtures("default_branch")


def test_public_receipt_settings_returns_effective_defaults(client):
    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["business_name"] == "CofiCenter"
    assert data["branch_code"] == "nuevo-vallarta"
    assert data["branch_name"] == "Nuevo Vallarta"
    assert data["currency"] == "MXN"
    assert data["tax_mode"] == "NONE"
    assert data["tax_rate"] == 0
    assert data["receipt_width_mm"] == 80
    assert data["timezone"] == "America/Bahia_Banderas"
    assert data["folio_prefix"] == "CF"
    assert data["auto_print_customer"] is False


def test_admin_business_settings_update_changes_effective_settings(
    client,
    super_headers,
):
    update = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter Test",
            "logo_ref": None,
            "phone": "322 000 0000",
            "web_social": "@coficenter",
            "footer_message": "Gracias por tu compra",
            "currency": "MXN",
            "tax_mode": "ADDED",
            "tax_rate": 0.16,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "NV",
            "auto_print_customer": True,
        },
    )

    assert update.status_code == 200

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["business_name"] == "CofiCenter Test"
    assert data["currency"] == "MXN"
    assert data["tax_mode"] == "ADDED"
    assert data["tax_rate"] == 0.16
    assert data["timezone"] == "America/Bahia_Banderas"
    assert data["folio_prefix"] == "NV"
    assert data["auto_print_customer"] is True


def test_branch_settings_override_only_selected_fields_and_inherit_rest(
    client,
    super_headers,
):
    business = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "logo_ref": None,
            "phone": "322 111 2233",
            "web_social": "@coficenter",
            "footer_message": "Gracias",
            "currency": "MXN",
            "tax_mode": "ADDED",
            "tax_rate": 0.16,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "CF",
            "auto_print_customer": False,
        },
    )
    assert business.status_code == 200

    override = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "display_name": "CofiCenter Nuevo Vallarta",
            "tax_mode": "INCLUDED",
            "tax_rate": 0.08,
            "folio_prefix": "NV",
        },
    )

    assert override.status_code == 200

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )
    assert response.status_code == 200

    data = response.json()

    assert data["business_name"] == "CofiCenter"
    assert data["branch_name"] == "CofiCenter Nuevo Vallarta"
    assert data["phone"] == "322 111 2233"
    assert data["currency"] == "MXN"
    assert data["tax_mode"] == "INCLUDED"
    assert data["tax_rate"] == 0.08
    assert data["timezone"] == "America/Bahia_Banderas"
    assert data["folio_prefix"] == "NV"
    assert data["auto_print_customer"] is False


def test_business_settings_reject_invalid_timezone(
    client,
    super_headers,
):
    response = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "logo_ref": None,
            "phone": None,
            "web_social": None,
            "footer_message": None,
            "currency": "MXN",
            "tax_mode": "ADDED",
            "tax_rate": 0.16,
            "receipt_width_mm": 80,
            "timezone": "Not/A-Timezone",
            "folio_prefix": "CF",
            "auto_print_customer": False,
        },
    )

    assert response.status_code == 422


def test_business_settings_normalizes_lowercase_folio_prefix(
    client,
    super_headers,
):
    update = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "currency": "MXN",
            "tax_mode": "NONE",
            "tax_rate": 0,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "nv",
            "auto_print_customer": False,
        },
    )

    assert update.status_code == 200

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200
    assert response.json()["folio_prefix"] == "NV"


def test_effective_tax_rate_is_zero_when_tax_mode_is_none(
    client,
    super_headers,
):
    update = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "currency": "MXN",
            "tax_mode": "NONE",
            "tax_rate": 0.16,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "CF",
            "auto_print_customer": False,
        },
    )
    assert update.status_code == 200

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200
    assert response.json()["tax_mode"] == "NONE"
    assert response.json()["tax_rate"] == 0


def test_branch_settings_reject_invalid_timezone(
    client,
    super_headers,
):
    response = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "timezone": "Not/A-Timezone",
        },
    )

    assert response.status_code == 422


def test_branch_settings_normalizes_lowercase_folio_prefix(
    client,
    super_headers,
):
    update = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={"folio_prefix": "nv"},
    )

    assert update.status_code == 200
    assert update.json()["folio_prefix"] == "NV"

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200
    assert response.json()["folio_prefix"] == "NV"


def test_business_settings_use_auto_print_customer_contract(
    client,
    super_headers,
):
    update = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "currency": "MXN",
            "tax_mode": "NONE",
            "tax_rate": 0,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "CF",
            "auto_print_customer": True,
        },
    )

    assert update.status_code == 200
    assert update.json()["auto_print_customer"] is True
    assert "auto_print" not in update.json()

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200
    assert response.json()["auto_print_customer"] is True
    assert "auto_print" not in response.json()


def test_effective_settings_expose_branch_address(
    client,
    super_headers,
):
    update = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "address": "Av. Cocoteros 123, Nuevo Vallarta",
        },
    )

    assert update.status_code == 200

    response = client.get(
        "/pos/receipts/settings",
        params={"branch_code": "nuevo-vallarta"},
    )

    assert response.status_code == 200
    assert (
        response.json()["address"]
        == "Av. Cocoteros 123, Nuevo Vallarta"
    )


def test_effective_settings_keep_tax_rate_as_decimal(
    db_session,
    default_branch,
):
    from decimal import Decimal

    from app.models.pos_receipts import PosBusinessReceiptSettings
    from app.services.pos_receipt_settings_service import (
        PosReceiptSettingsService,
    )

    settings = PosBusinessReceiptSettings(
        id=1,
        business_name="CofiCenter",
        currency="MXN",
        tax_mode="INCLUDED",
        tax_rate=Decimal("0.1600"),
        receipt_width_mm=80,
        timezone="America/Bahia_Banderas",
        folio_prefix="CF",
        auto_print_customer=False,
    )

    db_session.add(settings)
    db_session.commit()

    result = PosReceiptSettingsService.get_effective(
        db_session,
        "nuevo-vallarta",
    )

    assert isinstance(result.tax_rate, Decimal)
    assert result.tax_rate == Decimal("0.1600")


def test_business_settings_reject_non_80_receipt_width(
    client,
    super_headers,
):
    response = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "currency": "MXN",
            "tax_mode": "NONE",
            "tax_rate": 0,
            "receipt_width_mm": 58,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "CF",
            "auto_print_customer": False,
        },
    )

    assert response.status_code == 422


def test_business_settings_reject_negative_tax_rate(
    client,
    super_headers,
):
    response = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "currency": "MXN",
            "tax_mode": "ADDED",
            "tax_rate": -0.01,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "CF",
            "auto_print_customer": False,
        },
    )

    assert response.status_code == 422


def test_branch_settings_reject_negative_tax_rate(
    client,
    super_headers,
):
    response = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "tax_mode": "ADDED",
            "tax_rate": -0.01,
        },
    )

    assert response.status_code == 422


def test_branch_settings_reject_negative_tax_rate(
    client,
    super_headers,
):
    response = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "tax_mode": "ADDED",
            "tax_rate": -0.01,
        },
    )

    assert response.status_code == 422


def test_branch_receipt_settings_uses_branch_id_as_primary_key():
    from app.models.pos_receipts import PosBranchReceiptSettings

    table = PosBranchReceiptSettings.__table__

    assert "id" not in table.c
    assert table.c.branch_id.primary_key is True


def test_business_receipt_settings_model_matches_storage_contract():
    from app.models.pos_receipts import PosBusinessReceiptSettings

    table = PosBusinessReceiptSettings.__table__

    assert table.c.business_name.type.length == 160
    assert table.c.logo_ref.type.length == 500
    assert table.c.phone.type.length == 40
    assert table.c.web_social.type.length == 240
    assert table.c.footer_message.type.length == 500

    assert table.c.currency.type.length == 3
    assert table.c.currency.default.arg == "MXN"

    assert table.c.tax_mode.type.length == 16
    assert table.c.tax_mode.default.arg == "NONE"

    assert table.c.tax_rate.type.precision == 8
    assert table.c.tax_rate.type.scale == 4
    assert table.c.tax_rate.default.arg == 0

    assert table.c.receipt_width_mm.default.arg == 80
    assert table.c.timezone.type.length == 64
    assert table.c.folio_prefix.type.length == 8
    assert table.c.auto_print_customer.default.arg is False


def test_branch_receipt_settings_model_matches_storage_contract():
    from app.models.pos_receipts import PosBranchReceiptSettings

    table = PosBranchReceiptSettings.__table__

    assert table.c.display_name.type.length == 160
    assert table.c.address.type.length == 500
    assert table.c.phone.type.length == 40
    assert table.c.web_social.type.length == 240
    assert table.c.footer_message.type.length == 500

    assert table.c.tax_mode.type.length == 16

    assert table.c.tax_rate.type.precision == 8
    assert table.c.tax_rate.type.scale == 4

    assert table.c.timezone.type.length == 64
    assert table.c.folio_prefix.type.length == 8

    assert table.c.auto_print_customer.nullable is True


def test_business_receipt_settings_has_required_check_constraints():
    from sqlalchemy import CheckConstraint

    from app.models.pos_receipts import PosBusinessReceiptSettings

    table = PosBusinessReceiptSettings.__table__

    checks = {
        str(constraint.sqltext).replace(" ", "").lower()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert any("id=1" in check for check in checks)
    assert any(
        "tax_modein('none','included','added')" in check
        for check in checks
    )
    assert any("tax_rate>=0" in check for check in checks)
    assert any("receipt_width_mm=80" in check for check in checks)


def test_branch_receipt_settings_has_required_check_constraints():
    from sqlalchemy import CheckConstraint

    from app.models.pos_receipts import PosBranchReceiptSettings

    table = PosBranchReceiptSettings.__table__

    checks = {
        str(constraint.sqltext).replace(" ", "").lower()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert any(
        "tax_modeisnullor"
        "tax_modein('none','included','added')" in check
        for check in checks
    )

    assert any(
        "tax_rateisnullortax_rate>=0" in check
        for check in checks
    )


def test_receipt_settings_models_use_only_approved_columns():
    from app.models.pos_receipts import (
        PosBranchReceiptSettings,
        PosBusinessReceiptSettings,
    )

    business_columns = set(
        PosBusinessReceiptSettings.__table__.c.keys()
    )
    branch_columns = set(
        PosBranchReceiptSettings.__table__.c.keys()
    )

    assert business_columns == {
        "id",
        "business_name",
        "logo_ref",
        "phone",
        "web_social",
        "footer_message",
        "currency",
        "tax_mode",
        "tax_rate",
        "receipt_width_mm",
        "timezone",
        "folio_prefix",
        "auto_print_customer",
    }

    assert branch_columns == {
        "branch_id",
        "display_name",
        "address",
        "phone",
        "web_social",
        "footer_message",
        "tax_mode",
        "tax_rate",
        "timezone",
        "folio_prefix",
        "auto_print_customer",
    }


def test_receipt_foundation_migration_has_correct_revision_chain():
    import importlib.util
    from pathlib import Path

    migration_path = Path(
        "alembic/versions/"
        "20260908_0001_pos_receipt_foundation.py"
    )

    assert migration_path.exists()

    spec = importlib.util.spec_from_file_location(
        "receipt_foundation_migration",
        migration_path,
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20260908_0001"
    assert migration.down_revision == "20260902_0002"


def test_receipt_foundation_migration_creates_tables_and_seed():
    import importlib.util
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration_path = Path(
        "alembic/versions/"
        "20260908_0001_pos_receipt_foundation.py"
    )

    spec = importlib.util.spec_from_file_location(
        "receipt_foundation_migration_contract",
        migration_path,
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = sa.create_engine("sqlite://")

    with engine.begin() as connection:
        metadata = sa.MetaData()

        sa.Table(
            "branches",
            metadata,
            sa.Column("id", sa.Integer(), primary_key=True),
        )
        metadata.create_all(connection)

        context = MigrationContext.configure(connection)
        operations = Operations(context)

        original_op = migration.op
        migration.op = operations

        try:
            migration.upgrade()

            inspector = sa.inspect(connection)

            assert "pos_business_receipt_settings" in inspector.get_table_names()
            assert "pos_branch_receipt_settings" in inspector.get_table_names()

            business_columns = {
                column["name"]
                for column in inspector.get_columns(
                    "pos_business_receipt_settings"
                )
            }
            assert business_columns == {
                "id",
                "business_name",
                "logo_ref",
                "phone",
                "web_social",
                "footer_message",
                "currency",
                "tax_mode",
                "tax_rate",
                "receipt_width_mm",
                "timezone",
                "folio_prefix",
                "auto_print_customer",
            }

            branch_columns = {
                column["name"]
                for column in inspector.get_columns(
                    "pos_branch_receipt_settings"
                )
            }
            assert branch_columns == {
                "branch_id",
                "display_name",
                "address",
                "phone",
                "web_social",
                "footer_message",
                "tax_mode",
                "tax_rate",
                "timezone",
                "folio_prefix",
                "auto_print_customer",
            }

            branch_pk = inspector.get_pk_constraint(
                "pos_branch_receipt_settings"
            )
            assert branch_pk["constrained_columns"] == ["branch_id"]

            foreign_keys = inspector.get_foreign_keys(
                "pos_branch_receipt_settings"
            )
            assert len(foreign_keys) == 1
            assert foreign_keys[0]["constrained_columns"] == ["branch_id"]
            assert foreign_keys[0]["referred_table"] == "branches"
            assert foreign_keys[0]["referred_columns"] == ["id"]
            assert (
                foreign_keys[0]["options"].get("ondelete")
                == "CASCADE"
            )

            row = connection.execute(
                sa.text(
                    """
                    SELECT
                        id,
                        business_name,
                        currency,
                        tax_mode,
                        tax_rate,
                        receipt_width_mm,
                        timezone,
                        folio_prefix,
                        auto_print_customer
                    FROM pos_business_receipt_settings
                    WHERE id = 1
                    """
                )
            ).mappings().one()

            assert row["id"] == 1
            assert row["business_name"] == "CofiCenter"
            assert row["currency"] == "MXN"
            assert row["tax_mode"] == "NONE"
            assert float(row["tax_rate"]) == 0.0
            assert row["receipt_width_mm"] == 80
            assert row["timezone"] == "America/Bahia_Banderas"
            assert row["folio_prefix"] == "CF"
            assert bool(row["auto_print_customer"]) is False

            migration.downgrade()

            remaining_tables = inspector.get_table_names()
            inspector = sa.inspect(connection)
            remaining_tables = inspector.get_table_names()

            assert "pos_business_receipt_settings" not in remaining_tables
            assert "pos_branch_receipt_settings" not in remaining_tables
            assert "branches" in remaining_tables

        finally:
            migration.op = original_op


def test_admin_receipt_settings_returns_business_branches_overrides_and_effective(
    client,
    super_headers,
):
    business_update = client.put(
        "/admin/pos/receipt-settings/business",
        headers=super_headers,
        json={
            "business_name": "CofiCenter",
            "currency": "MXN",
            "tax_mode": "INCLUDED",
            "tax_rate": 0.16,
            "receipt_width_mm": 80,
            "timezone": "America/Bahia_Banderas",
            "folio_prefix": "CF",
            "auto_print_customer": False,
        },
    )
    assert business_update.status_code == 200

    branch_update = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "display_name": "CofiCenter Nuevo Vallarta",
            "phone": "3221234567",
        },
    )
    assert branch_update.status_code == 200

    response = client.get(
        "/admin/pos/receipt-settings",
        headers=super_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert set(data) == {"business", "branches"}

    assert data["business"]["business_name"] == "CofiCenter"
    assert data["business"]["tax_mode"] == "INCLUDED"
    assert data["business"]["tax_rate"] == 0.16

    assert len(data["branches"]) == 1

    branch = data["branches"][0]

    assert branch["branch_code"] == "nuevo-vallarta"
    assert branch["branch_name"] == "Nuevo Vallarta"

    assert branch["overrides"]["display_name"] == (
        "CofiCenter Nuevo Vallarta"
    )
    assert branch["overrides"]["phone"] == "3221234567"

    assert branch["effective"]["branch_code"] == "nuevo-vallarta"
    assert branch["effective"]["branch_name"] == (
        "CofiCenter Nuevo Vallarta"
    )
    assert branch["effective"]["phone"] == "3221234567"
    assert branch["effective"]["tax_mode"] == "INCLUDED"
    assert branch["effective"]["tax_rate"] == 0.16


def test_branch_update_distinguishes_omitted_fields_from_explicit_null(
    client,
    super_headers,
):
    first = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "display_name": "CofiCenter Vallarta",
            "phone": "3221111111",
        },
    )
    assert first.status_code == 200

    partial = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "phone": "3222222222",
        },
    )
    assert partial.status_code == 200

    after_partial = client.get(
        "/admin/pos/receipt-settings",
        headers=super_headers,
    )
    assert after_partial.status_code == 200

    branch = after_partial.json()["branches"][0]

    assert branch["overrides"]["display_name"] == "CofiCenter Vallarta"
    assert branch["overrides"]["phone"] == "3222222222"
    assert branch["effective"]["branch_name"] == "CofiCenter Vallarta"

    clear = client.put(
        "/admin/pos/receipt-settings/branches/nuevo-vallarta",
        headers=super_headers,
        json={
            "display_name": None,
        },
    )
    assert clear.status_code == 200

    after_clear = client.get(
        "/admin/pos/receipt-settings",
        headers=super_headers,
    )
    assert after_clear.status_code == 200

    branch = after_clear.json()["branches"][0]

    assert branch["overrides"]["display_name"] is None
    assert branch["overrides"]["phone"] == "3222222222"
    assert branch["effective"]["branch_name"] == "Nuevo Vallarta"
