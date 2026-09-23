from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260923_0001_self_orders.py"
)


def test_self_order_migration_exists():
    assert MIGRATION.exists()


def test_self_order_migration_contains_required_schema_changes():
    text = MIGRATION.read_text(encoding="utf-8")

    required_tokens = (
        "self_order_devices",
        "self_orders",
        "self_order_items",
        "self_order_item_modifiers",
        "self_order_payment_attempts",
        "source",
        "self_order_id",
        "ck_pos_orders_source",
    )

    for token in required_tokens:
        assert token in text


def test_self_order_migration_has_downgrade():
    text = MIGRATION.read_text(encoding="utf-8")

    assert "def downgrade" in text
    assert "drop_table" in text
    assert "self_order_id" in text
    assert "source" in text
