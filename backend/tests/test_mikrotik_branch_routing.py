from app.services.mikrotik_service import MikroTikService


def test_for_branch_ixtapa_uses_branch_specific_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "MIKROTIK_IXTAPA_HOST",
        "10.100.0.3",
    )
    monkeypatch.setenv(
        "MIKROTIK_IXTAPA_USERNAME",
        "cofinet-ixtapa",
    )
    monkeypatch.setenv(
        "MIKROTIK_IXTAPA_PASSWORD",
        "test-secret",
    )
    monkeypatch.setenv(
        "MIKROTIK_IXTAPA_PORT",
        "8728",
    )

    captured = {}

    def fake_init(
        self,
        host=None,
        username=None,
        password=None,
        port=None,
    ):
        captured.update({
            "host": host,
            "username": username,
            "password": password,
            "port": port,
        })

    monkeypatch.setattr(
        MikroTikService,
        "__init__",
        fake_init,
    )

    service = MikroTikService.for_branch("ixtapa")

    assert isinstance(service, MikroTikService)
    assert captured == {
        "host": "10.100.0.3",
        "username": "cofinet-ixtapa",
        "password": "test-secret",
        "port": 8728,
    }
