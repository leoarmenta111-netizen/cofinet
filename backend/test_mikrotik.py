import os

from app.services.mikrotik_service import MikroTikService

mt = MikroTikService()

try:
    mt.create_hotspot_user(
        username=os.environ["MIKROTIK_TEST_HOTSPOT_USERNAME"],
        password=os.environ["MIKROTIK_TEST_HOTSPOT_PASSWORD"],
    )

    print("USUARIO CREADO")
finally:
    mt.disconnect()
