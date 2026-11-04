from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models.retail_catalog import (
    RetailCatalogItem,
    RetailPresentation,
)


class RetailPublicCatalogService:
    @staticmethod
    def list_active(
        db: Session,
        *,
        branch_id: int,
    ) -> list[RetailCatalogItem]:
        statement = (
            select(RetailCatalogItem)
            .options(
                selectinload(
                    RetailCatalogItem
                    .presentations
                    .and_(
                        RetailPresentation
                        .is_active
                        .is_(True)
                    )
                ),
                selectinload(
                    RetailCatalogItem
                    .service_price_tiers
                ),
            )
            .where(
                RetailCatalogItem.branch_id
                == branch_id,
                RetailCatalogItem.is_active
                .is_(True),
            )
            .order_by(
                RetailCatalogItem.name,
                RetailCatalogItem.id,
            )
        )

        return list(
            db.execute(
                statement
            )
            .scalars()
            .unique()
            .all()
        )
