from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.self_orders import SelfOrderDevice


SELF_ORDER_DEVICE_SEEDS = (
    ('KIOSK-IXTAPA-01', 'KIOSK'),
    ('BAR-TABLET-IXTAPA-01', 'BAR_TABLET'),
)


def ensure_self_order_devices(db: Session) -> None:
    branch = (
        db.query(Branch)
        .filter(
            Branch.code == 'ixtapa',
            Branch.is_active.is_(True),
        )
        .one_or_none()
    )

    if branch is None:
        return

    changed = False

    for device_code, source in SELF_ORDER_DEVICE_SEEDS:
        existing = (
            db.query(SelfOrderDevice)
            .filter(
                SelfOrderDevice.device_code == device_code,
            )
            .one_or_none()
        )

        if existing is not None:
            continue

        db.add(
            SelfOrderDevice(
                device_code=device_code,
                branch_id=branch.id,
                source=source,
                is_active=True,
            )
        )
        changed = True

    if changed:
        db.commit()
