from app.schemas.pos_receipts import (
    ReceiptSnapshotFiscalV1,
    ReceiptSnapshotV1,
)


def test_receipt_snapshot_supports_fiscal_context():
    assert "fiscal" in ReceiptSnapshotV1.model_fields

    fiscal = ReceiptSnapshotFiscalV1(
        rfc="HETA0203028E0",
        fiscal_address=(
            "CARR A LAS PALMAS 1179 E, "
            "LAS JUNTAS, JALISCO"
        ),
        billing_label="FACTURACIÓN",
        billing_message=(
            "Escanea el código QR "
            "para facturar tu compra"
        ),
        billing_url=(
            "https://forms.gle/"
            "V6UpN26P8wkSfYtT9"
        ),
        billing_qr_ref=(
            "./assets/"
            "facturacion-qr.png"
        ),
    )

    assert fiscal.rfc == "HETA0203028E0"
    assert fiscal.billing_qr_ref.endswith(
        "facturacion-qr.png"
    )
