from app.main import app  # noqa: F401

from app.services.retail_public_catalog_service import (
    RetailPublicCatalogService,
)


class FakeResult:
    def scalars(self):
        return self

    def unique(self):
        return self

    def all(self):
        return []


class FakeDb:
    def execute(
        self,
        statement,
    ):
        del statement
        return FakeResult()


def test_public_catalog_query_builds_with_real_model_fields():
    result = (
        RetailPublicCatalogService
        .list_active(
            FakeDb(),
            branch_id=1,
        )
    )

    assert result == []
