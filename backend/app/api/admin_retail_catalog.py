from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from app.auth.admin_security import (
    require_super_admin,
)
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.admin_retail_catalog import (
    AdminRetailCatalogItemCreate,
    AdminRetailCatalogItemUpdate,
    AdminRetailPresentationCreate,
    AdminRetailPresentationUpdate,
)
from app.schemas.retail_catalog import (
    RetailCatalogItemResponse,
    RetailPresentationResponse,
)
from app.services.admin_retail_catalog_service import (
    AdminRetailCatalogService,
)
from app.services.branch_service import (
    BranchService,
)


router = APIRouter(
    prefix="/admin/retail/catalog",
    tags=["Admin Retail Catalog"],
)


@router.get(
    "",
    response_model=list[
        RetailCatalogItemResponse
    ],
)
def list_admin_retail_catalog(
    branch_code: str = Query(
        min_length=1,
        max_length=50,
    ),
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> list[RetailCatalogItemResponse]:
    branch = BranchService.get_by_code(
        db,
        branch_code,
    )

    return (
        AdminRetailCatalogService
        .list_catalog(
            db,
            branch_id=branch.id,
        )
    )


@router.post(
    "/items",
    response_model=RetailCatalogItemResponse,
)
def create_admin_retail_item(
    data: AdminRetailCatalogItemCreate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> RetailCatalogItemResponse:
    branch = BranchService.get_by_id(
        db,
        data.branch_id,
    )

    item = (
        AdminRetailCatalogService
        .create_item(
            db,
            branch_id=branch.id,
            item_type=data.item_type,
            sku=data.sku,
            name=data.name,
            description=data.description,
            category=data.category,
            base_unit_code=(
                data.base_unit_code
            ),
            cost=data.cost,
            inventory_tracked=(
                data.inventory_tracked
            ),
            low_stock_threshold=(
                data.low_stock_threshold
            ),
            max_stock=data.max_stock,
            is_active=data.is_active,
        )
    )

    db.commit()
    db.refresh(item)

    return item


@router.patch(
    "/items/{item_id}",
    response_model=RetailCatalogItemResponse,
)
def update_admin_retail_item(
    item_id: int,
    data: AdminRetailCatalogItemUpdate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> RetailCatalogItemResponse:
    item = (
        AdminRetailCatalogService
        .get_item(
            db,
            item_id=item_id,
        )
    )

    item = (
        AdminRetailCatalogService
        .update_item(
            db,
            item=item,
            changes=data.model_dump(
                exclude_unset=True
            ),
        )
    )

    db.commit()
    db.refresh(item)

    return item


@router.post(
    "/items/{item_id}/presentations",
    response_model=RetailPresentationResponse,
)
def create_admin_retail_presentation(
    item_id: int,
    data: AdminRetailPresentationCreate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> RetailPresentationResponse:
    item = (
        AdminRetailCatalogService
        .get_item(
            db,
            item_id=item_id,
        )
    )

    presentation = (
        AdminRetailCatalogService
        .create_presentation(
            db,
            item=item,
            branch_id=data.branch_id,
            name=data.name,
            barcode=data.barcode,
            conversion_factor=(
                data.conversion_factor
            ),
            sale_price=data.sale_price,
            bulk_price=data.bulk_price,
            bulk_min_quantity=(
                data.bulk_min_quantity
            ),
            is_default=data.is_default,
            is_active=data.is_active,
        )
    )

    db.commit()
    db.refresh(presentation)

    return presentation


@router.patch(
    "/presentations/{presentation_id}",
    response_model=RetailPresentationResponse,
)
def update_admin_retail_presentation(
    presentation_id: int,
    data: AdminRetailPresentationUpdate,
    _admin: Admin = Depends(
        require_super_admin
    ),
    db: Session = Depends(get_db),
) -> RetailPresentationResponse:
    presentation = (
        AdminRetailCatalogService
        .get_presentation(
            db,
            presentation_id=(
                presentation_id
            ),
        )
    )

    presentation = (
        AdminRetailCatalogService
        .update_presentation(
            db,
            presentation=presentation,
            changes=data.model_dump(
                exclude_unset=True
            ),
        )
    )

    db.commit()
    db.refresh(presentation)

    return presentation
