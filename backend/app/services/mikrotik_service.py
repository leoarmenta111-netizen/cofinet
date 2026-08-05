import os

import routeros_api


class MikroTikUserExistsError(RuntimeError):
    """Raised when strict credential creation finds an existing Hotspot user."""


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

    def create_hotspot_user_strict(
        self,
        username: str,
        password: str,
        duration_minutes: int,
        profile: str = "default",
        comment: str = "CofiNet admin batch",
    ) -> None:
        users = self.api.get_resource("/ip/hotspot/user")
        if users.get(name=username):
            raise MikroTikUserExistsError("Hotspot username already exists")
        users.add(
            name=username,
            password=password,
            profile=profile,
            limit_uptime=f"{duration_minutes}m",
            comment=comment,
        )

    def create_permanent_hotspot_user_strict(
        self,
        username: str,
        password: str,
        profile: str,
        comment: str,
    ) -> None:
        users = self.api.get_resource("/ip/hotspot/user")
        if users.get(name=username):
            raise MikroTikUserExistsError("Hotspot username already exists")
        # Deliberately omit limit-uptime. The dedicated profile must be
        # provisioned in QA with shared-users=1 before credentials are issued.
        users.add(
            name=username,
            password=password,
            profile=profile,
            comment=comment,
        )

    def remove_hotspot_user(self, username: str) -> None:
        users = self.api.get_resource("/ip/hotspot/user")
        existing = users.get(name=username)

        for user in existing:
            users.remove(id=user[".id"])

    def get_hotspot_diagnostics(self, username: str) -> tuple[list[dict], list[dict]]:
        """Read a Hotspot user and active sessions without changing RouterOS state."""
        users = self.api.get_resource("/ip/hotspot/user").get(name=username)
        sessions = self.api.get_resource("/ip/hotspot/active").get(user=username)
        return users, sessions

    def disconnect(self) -> None:
        self.pool.disconnect()
