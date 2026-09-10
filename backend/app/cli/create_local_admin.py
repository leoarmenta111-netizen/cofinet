"""Provision an administrator only in an explicitly local or QA environment."""

import argparse
from getpass import getpass

from sqlalchemy import func, select

from app.auth.security import hash_password
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.admin import Admin, AdminRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument(
        "--role",
        choices=[role.value for role in AdminRole],
        default=AdminRole.PIN_OPERATOR.value,
    )
    parser.add_argument("--created-by-email")
    parser.add_argument("--confirm-super-admin", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if settings.APP_ENV not in {"development", "qa"}:
        raise SystemExit("Local administrator provisioning is disabled outside development/QA.")

    role = AdminRole(args.role)
    if role == AdminRole.SUPER_ADMIN and not args.confirm_super_admin:
        raise SystemExit("Use --confirm-super-admin to create a super administrator.")

    password = getpass("New administrator password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")

    with SessionLocal() as db:
        existing = db.execute(select(func.count(Admin.id))).scalar_one()
        creator = None
        if existing:
            if not args.created_by_email:
                raise SystemExit("Existing installations require --created-by-email.")
            creator = db.execute(
                select(Admin).where(
                    func.lower(Admin.email) == args.created_by_email.strip().lower(),
                    Admin.role == AdminRole.SUPER_ADMIN,
                    Admin.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if creator is None:
                raise SystemExit("The creator must be an active super administrator.")
        elif role != AdminRole.SUPER_ADMIN:
            raise SystemExit("The first local administrator must be a super administrator.")

        email = args.email.strip().lower()
        if db.execute(select(Admin.id).where(func.lower(Admin.email) == email)).scalar_one_or_none():
            raise SystemExit("An administrator with that email already exists.")

        db.add(
            Admin(
                email=email,
                full_name=args.full_name.strip(),
                password_hash=hash_password(password),
                role=role,
                is_active=True,
                created_by_admin_id=creator.id if creator else None,
            )
        )
        db.commit()
    print(f"Created local {role.value} account for {email}.")


if __name__ == "__main__":
    main()
