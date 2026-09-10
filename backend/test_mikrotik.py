import os

from app.services.mikrotik_service import MikroTikService


def main() -> None:
    """Run only when explicitly invoked; pytest collection must stay offline."""
    mt = MikroTikService()
    try:
        mt.create_hotspot_user_strict(
            username=os.environ["MIKROTIK_TEST_HOTSPOT_USERNAME"],
            password=os.environ["MIKROTIK_TEST_HOTSPOT_PASSWORD"],
            duration_minutes=int(os.environ["MIKROTIK_TEST_DURATION_MINUTES"]),
            comment="CofiNet explicit MikroTik connectivity test",
        )
        print("USUARIO CREADO")
    finally:
        mt.disconnect()


if __name__ == "__main__":
    main()
