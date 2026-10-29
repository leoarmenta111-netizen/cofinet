import pytest
from pydantic import ValidationError

from app.schemas.pos_receipts import ReceiptSnapshotItemV1


def base_item(**overrides):
    data = {
        "product_id": 101,
        "product_name": "Latte",
        "quantity": 1,
        "unit_price_cents": 8000,
        "line_total_cents": 8000,
        "modifiers": [],
    }
    data.update(overrides)
    return data


def test_receipt_item_accepts_variant_identity():
    item = ReceiptSnapshotItemV1(
        **base_item(
            product_variant_id=22,
            variant_name="Grande 20 oz",
        )
    )

    assert item.product_variant_id == 22
    assert item.variant_name == "Grande 20 oz"


def test_receipt_item_allows_non_variant_product():
    item = ReceiptSnapshotItemV1(
        **base_item()
    )

    assert item.product_variant_id is None
    assert item.variant_name is None


@pytest.mark.parametrize(
    "extra",
    [
        {"product_variant_id": 22},
        {"variant_name": "Grande 20 oz"},
    ],
)
def test_receipt_variant_identity_requires_id_and_name(extra):
    with pytest.raises(ValidationError):
        ReceiptSnapshotItemV1(
            **base_item(**extra)
        )
