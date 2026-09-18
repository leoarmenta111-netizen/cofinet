import os

import routeros_api


class MikroTikUserExistsError(RuntimeError):
    """Raised when strict credential creation finds an existing Hotspot user."""


class MikroTikBranchNotConfiguredError(RuntimeError):
    """Raised when a branch does not have a MikroTik configured yet."""


class MikroTikService:
    _BRANCH_PREFIXES = {
        "bucerias": "MIKROTIK_BUCERIAS",
        "ixtapa": "MIKROTIK_IXTAPA",
    }

    @classmethod
    def for_branch(cls, branch_code: str) -> "MikroTikService":
        normalized = branch_code.strip().lower()

        # Nuevo Vallarta keeps the existing production variables.
        if normalized in {"nuevo-vallarta", "principal"}:
            return cls(
                host=os.environ["MIKROTIK_HOST"],
                username=os.environ["MIKROTIK_USERNAME"],
                password=os.environ["MIKROTIK_PASSWORD"],
                port=int(os.getenv("MIKROTIK_PORT", "8728")),
            )

        prefix = cls._BRANCH_PREFIXES.get(normalized)
        if prefix is None:
            raise MikroTikBranchNotConfiguredError(
                f"MikroTik is not configured for branch {normalized!r}"
            )

        try:
            host = os.environ[f"{prefix}_HOST"]
            username = os.environ[f"{prefix}_USERNAME"]
            password = os.environ[f"{prefix}_PASSWORD"]
        except KeyError as exc:
            raise MikroTikBranchNotConfiguredError(
                f"MikroTik environment is incomplete for branch {normalized!r}"
            ) from exc

        return cls(
            host=host,
            username=username,
            password=password,
            port=int(os.getenv(f"{prefix}_PORT", "8728")),
        )

    def __init__(
        self,
        host: str | None = None,
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
    ) -> None:
        self.pool = routeros_api.RouterOsApiPool(
            host=host or os.environ["MIKROTIK_HOST"],
            username=username or os.environ["MIKROTIK_USERNAME"],
            password=password or os.environ["MIKROTIK_PASSWORD"],
            port=port if port is not None else int(os.getenv("MIKROTIK_PORT", "8728")),
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


    def set_hotspot_user_disabled(
        self,
        username: str,
        disabled: bool,
    ) -> bool:
        """Enable or disable an existing Hotspot user.

        Returns False when the user does not exist.
        """
        users = self.api.get_resource("/ip/hotspot/user")
        matches = users.get(name=username)

        if not matches:
            return False

        user = matches[0]

        # routeros_api normally exposes `.id` as `id`.
        routeros_id = user.get("id") or user.get(".id")

        if not routeros_id:
            raise RuntimeError(
                f"RouterOS user {username!r} has no usable id. "
                f"Available fields: {sorted(user.keys())}"
            )

        expected = "true" if disabled else "false"

        users.set(
            id=routeros_id,
            disabled=expected,
        )

        updated = users.get(name=username)

        if not updated:
            raise RuntimeError(
                f"RouterOS user {username!r} disappeared after status update"
            )

        actual_value = str(
            updated[0].get("disabled", "false")
        ).strip().lower()

        actual_disabled = actual_value in {
            "true",
            "yes",
            "1",
        }

        if actual_disabled != disabled:
            raise RuntimeError(
                f"RouterOS did not confirm disabled={expected} "
                f"for user {username!r}"
            )

        return True

    def get_hotspot_diagnostics(self, username: str) -> tuple[list[dict], list[dict]]:
        """Read a Hotspot user and active sessions without changing RouterOS state."""
        users = self.api.get_resource("/ip/hotspot/user").get(name=username)
        sessions = self.api.get_resource("/ip/hotspot/active").get(user=username)
        return users, sessions

    def disconnect(self) -> None:
        self.pool.disconnect()
