from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api import retail_catalog
from app.main import app


def test_retail_catalog_get_route_is_registered():
    schema = app.openapi()

    assert (
        "/retail/catalog"
        in schema["paths"]
    )

    assert (
        "get"
        in schema["paths"][
            "/retail/catalog"
        ]
    )


def test_retail_catalog_has_no_branch_query_parameter():
    route = (
        app.openapi()
        ["paths"]
        ["/retail/catalog"]
        ["get"]
    )

    query_names = {
        parameter["name"]
        for parameter
        in route.get(
            "parameters",
            [],
        )
        if parameter.get("in")
        == "query"
    }

    assert (
        "branch_code"
        not in query_names
    )


def test_retail_catalog_response_is_array():
    route = (
        app.openapi()
        ["paths"]
        ["/retail/catalog"]
        ["get"]
    )

    response_schema = (
        route["responses"]
        ["200"]
        ["content"]
        ["application/json"]
        ["schema"]
    )

    assert (
        response_schema["type"]
        == "array"
    )


def test_retail_catalog_uses_staff_branch(
    monkeypatch,
):
    staff = SimpleNamespace(
        branch_id=44,
        module_code="PAPELERIA",
    )

    branch = SimpleNamespace(
        code="ixtapa",
    )

    captured = {}

    monkeypatch.setattr(
        retail_catalog.BranchService,
        "get_by_id",
        staticmethod(
            lambda db, branch_id:
                branch
        ),
    )

    def fake_list(
        db,
        *,
        branch_id,
    ):
        captured["branch_id"] = (
            branch_id
        )
        return []

    monkeypatch.setattr(
        retail_catalog
        .RetailPublicCatalogService,
        "list_active",
        staticmethod(fake_list),
    )

    result = (
        retail_catalog
        .get_retail_catalog(
            staff=staff,
            token_payload={
                "branch_code": "ixtapa",
                "terminal_id": "PAP-01",
            },
            db=object(),
        )
    )

    assert result == []

    assert (
        captured["branch_id"]
        == 44
    )


def test_retail_catalog_rejects_wrong_module():
    staff = SimpleNamespace(
        branch_id=44,
        module_code="CAFE",
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        (
            retail_catalog
            .get_retail_catalog(
                staff=staff,
                token_payload={
                    "branch_code":
                        "ixtapa",
                    "terminal_id":
                        "PAP-01",
                },
                db=object(),
            )
        )

    assert (
        exc.value.status_code
        == 403
    )


def test_retail_catalog_rejects_branch_mismatch(
    monkeypatch,
):
    staff = SimpleNamespace(
        branch_id=44,
        module_code="PAPELERIA",
    )

    monkeypatch.setattr(
        retail_catalog.BranchService,
        "get_by_id",
        staticmethod(
            lambda db, branch_id:
                SimpleNamespace(
                    code="ixtapa"
                )
        ),
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        (
            retail_catalog
            .get_retail_catalog(
                staff=staff,
                token_payload={
                    "branch_code":
                        "otra",
                    "terminal_id":
                        "PAP-01",
                },
                db=object(),
            )
        )

    assert (
        exc.value.status_code
        == 401
    )
