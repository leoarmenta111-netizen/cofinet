import os

import routeros_api


class MikroTikService:
    def __init__(self) -> None:
        self.pool = routeros_api.RouterOsApiPool(
            host=os.environ["MIKROTIK_HOST"],
            username=os.environ["MIKROTIK_USERNAME"],
            password=os.environ["MIKROTIK_PASSWORD"],
            port=int(os.getenv("MIKROTIK_PORT", "8728")),
            plaintext_login=True,
        )
        self.api = self.pool.get_api()

    def create_hotspot_user(
        self,
        username: str,
        password: str,
        duration_minutes: int,
        profile: str = "default",
    ) -> None:
        users = self.api.get_resource("/ip/hotspot/user")

        existing = users.get(name=username)
        if existing:
            return

        users.add(
            name=username,
            password=password,
            profile=profile,
            limit_uptime=f"{duration_minutes}m",
            comment="CofiCenter automated purchase",
        )

    def remove_hotspot_user(self, username: str) -> None:
        users = self.api.get_resource("/ip/hotspot/user")
        existing = users.get(name=username)

        for user in existing:
            users.remove(id=user[".id"])

    def disconnect(self) -> None:
        self.pool.disconnect()
