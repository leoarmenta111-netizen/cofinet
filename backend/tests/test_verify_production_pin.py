from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.purchase import Purchase, PurchaseCreationSource, PurchaseStatus
from scripts.verify_production_pin import inspect_mikrotik, inspect_postgresql


class ReadOnlyMikroTik:
    def __init__(self):
        self.calls = []

    def get_hotspot_diagnostics(self, username):
        self.calls.append(username)
        return (
            [{"profile": "default", "disabled": "false", "limit-uptime": "31m", "comment": "cash"}],
            [{"address": "10.0.0.2", "mac-address": "00:11:22:33:44:55", "uptime": "2m"}],
        )


def test_diagnostic_reads_database_and_mikrotik_without_writes(
    db_session, client, super_admin, capsys
):
    plan = client.get("/plans").json()[0]
    issued = datetime.now(UTC)
    db_session.add(
        Purchase(
            plan_id=plan["id"],
            amount=Decimal("25.00"),
            status=PurchaseStatus.PAID,
            pin_code="654321",
            issued_at=issued,
            expires_at=issued + timedelta(minutes=31),
            creation_source=PurchaseCreationSource.SYSTEM,
        )
    )
    db_session.commit()
    before_new = tuple(db_session.new)
    before_dirty = tuple(db_session.dirty)

    purchase = inspect_postgresql(db_session, "654321")
    mikrotik = ReadOnlyMikroTik()
    inspect_mikrotik(mikrotik, "654321")

    output = capsys.readouterr().out
    assert purchase is not None
    assert "Purchase encontrada" in output
    assert "Limit uptime: 31m" in output
    assert "IP: 10.0.0.2" in output
    assert mikrotik.calls == ["654321"]
    assert tuple(db_session.new) == before_new
    assert tuple(db_session.dirty) == before_dirty
    assert "password" not in output.lower()
