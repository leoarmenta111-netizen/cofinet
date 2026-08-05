from app.services.mikrotik_service import MikroTikService

mt = MikroTikService()

try:
    mt.create_hotspot_user(
        username="123456",
        password="123456"
    )

    print("USUARIO CREADO")
finally:
    mt.disconnect()
