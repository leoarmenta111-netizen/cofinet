"""Read-only PostgreSQL and MikroTik diagnostics for one CofiNet+ PIN."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.session import SessionLocal
from app.models.purchase import Purchase
from app.services.mikrotik_service import MikroTikService


def display(value: Any) -> str:
    if value is None or value == "":
        return "no disponible"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def inspect_postgresql(db: Session, pin: str) -> Purchase | None:
    purchase = db.execute(
        select(Purchase)
        .options(joinedload(Purchase.plan))
        .where(Purchase.pin_code == pin)
    ).scalar_one_or_none()
    print("\nPostgreSQL")
    if purchase is None:
        print("[INFO] Purchase no encontrada")
        return None
    print("[OK] Purchase encontrada")
    print(f"[OK] Purchase ID: {purchase.id}")
    print(f"[OK] PIN: {purchase.pin_code}")
    print(f"[OK] Estado: {purchase.status.value}")
    print(f"[OK] Plan: {purchase.plan.name}")
    print(f"[OK] Importe: {display(purchase.amount)} MXN")
    print(f"[OK] Emitido: {display(purchase.issued_at)}")
    print(f"[OK] Expira: {display(purchase.expires_at)}")
    print(f"[OK] Duración actual del plan: {purchase.plan.duration_minutes} minutos")
    return purchase


def _first(rows: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    return rows[0] if rows else None


def inspect_mikrotik(mikrotik: MikroTikService, pin: str) -> None:
    users, sessions = mikrotik.get_hotspot_diagnostics(pin)
    user = _first(users)
    print("\nMikroTik")
    if user is None:
        print("[INFO] Usuario no encontrado")
    else:
        print("[OK] Usuario existe")
        print(f"[OK] Profile: {display(user.get('profile'))}")
        print(f"[OK] Disabled: {display(user.get('disabled'))}")
        print(f"[OK] Limit uptime: {display(user.get('limit-uptime'))}")
        print(f"[OK] Comment: {display(user.get('comment'))}")

    print("\nSesión")
    if not sessions:
        print("[INFO] El usuario no está conectado actualmente")
        return
    for index, session in enumerate(sessions, start=1):
        print(f"[OK] Sesión activa {index}")
        print(f"[OK] IP: {display(session.get('address'))}")
        print(f"[OK] MAC: {display(session.get('mac-address'))}")
        print(f"[OK] Uptime: {display(session.get('uptime'))}")


def verify(pin: str) -> int:
    print(f"PIN: {pin}")
    success = True
    try:
        with SessionLocal() as db:
            inspect_postgresql(db, pin)
            db.rollback()
    except Exception as exc:
        print(f"\nPostgreSQL\n[ERROR] No fue posible consultar PostgreSQL: {type(exc).__name__}")
        success = False

    mikrotik = None
    try:
        mikrotik = MikroTikService()
        inspect_mikrotik(mikrotik, pin)
    except Exception as exc:
        print(f"\nMikroTik\n[ERROR] No fue posible consultar MikroTik: {type(exc).__name__}")
        success = False
    finally:
        if mikrotik is not None:
            try:
                mikrotik.disconnect()
            except Exception:
                print("[WARN] No fue posible cerrar limpiamente la conexión de MikroTik")
    return 0 if success else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pin", help="PIN de seis dígitos que se consultará sin modificarlo")
    args = parser.parse_args()
    if not args.pin.isdigit() or len(args.pin) != 6:
        parser.error("pin debe contener exactamente seis dígitos")
    return args


if __name__ == "__main__":
    raise SystemExit(verify(parse_args().pin))
