from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.admin_security import require_super_admin
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.admin_pos_catalog import (
    AdminPosBranchProductUpdate,
    AdminPosCatalogResponse,
    AdminPosCategoryCreate,
    AdminPosCategoryUpdate,
    AdminPosModifierGroupCreate,
    AdminPosModifierGroupUpdate,
    AdminPosModifierOptionCreate,
    AdminPosModifierOptionUpdate,
    AdminPosProductCreate,
    AdminPosProductModifierUpdate,
    AdminPosProductUpdate,
)
from app.services.admin_pos_catalog_service import (
    AdminPosCatalogService,
)


router = APIRouter(
    prefix="/admin/pos/catalog",
    tags=["Admin POS Catalog"],
)


@router.get(
    "",
    response_model=AdminPosCatalogResponse,
)
def get_admin_pos_catalog(
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.get_catalog(db)


@router.post(
    "/categories",
    response_model=AdminPosCatalogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: AdminPosCategoryCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.create_category(
        db,
        data,
    )


@router.patch(
    "/categories/{category_id}",
    response_model=AdminPosCatalogResponse,
)
def update_category(
    category_id: int,
    data: AdminPosCategoryUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.update_category(
        db,
        category_id,
        data,
    )


@router.post(
    "/products",
    response_model=AdminPosCatalogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    data: AdminPosProductCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.create_product(
        db,
        data,
    )


@router.patch(
    "/products/{product_id}",
    response_model=AdminPosCatalogResponse,
)
def update_product(
    product_id: int,
    data: AdminPosProductUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.update_product(
        db,
        product_id,
        data,
    )


@router.put(
    "/products/{product_id}/branches/{branch_code}",
    response_model=AdminPosCatalogResponse,
)
def update_product_branch(
    product_id: int,
    branch_code: str,
    data: AdminPosBranchProductUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.update_branch_product(
        db,
        product_id,
        branch_code,
        data,
    )


@router.post(
    "/modifier-groups",
    response_model=AdminPosCatalogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_modifier_group(
    data: AdminPosModifierGroupCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.create_group(
        db,
        data,
    )


@router.patch(
    "/modifier-groups/{group_id}",
    response_model=AdminPosCatalogResponse,
)
def update_modifier_group(
    group_id: int,
    data: AdminPosModifierGroupUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.update_group(
        db,
        group_id,
        data,
    )


@router.post(
    "/modifier-groups/{group_id}/options",
    response_model=AdminPosCatalogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_modifier_option(
    group_id: int,
    data: AdminPosModifierOptionCreate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.create_option(
        db,
        group_id,
        data,
    )


@router.patch(
    "/modifier-options/{option_id}",
    response_model=AdminPosCatalogResponse,
)
def update_modifier_option(
    option_id: int,
    data: AdminPosModifierOptionUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.update_option(
        db,
        option_id,
        data,
    )


@router.put(
    "/products/{product_id}/modifier-groups/{group_id}",
    response_model=AdminPosCatalogResponse,
)
def update_product_modifier(
    product_id: int,
    group_id: int,
    data: AdminPosProductModifierUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return AdminPosCatalogService.update_product_modifier(
        db,
        product_id,
        group_id,
        data,
    )
