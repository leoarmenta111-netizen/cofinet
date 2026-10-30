from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosModifierGroup,
    PosProduct,
)
from app.schemas.pos_catalog import (
    PosCatalogBranchResponse,
    PosCatalogCategoryResponse,
    PosCatalogProductResponse,
    PosCatalogProductVariantResponse,
    PosCatalogResponse,
    PosModifierGroupResponse,
    PosModifierOptionResponse,
)


class PosCatalogService:
    @staticmethod
    def get_catalog(
        db: Session,
        branch_code: str,
    ) -> PosCatalogResponse:
        normalized = branch_code.strip().lower()

        # Compatibility with the original branch alias.
        if normalized == "principal":
            normalized = "nuevo-vallarta"

        branch = db.execute(
            select(Branch).where(
                Branch.code == normalized,
                Branch.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )

        branch_products = (
            db.execute(
                select(PosBranchProduct)
                .join(
                    PosBranchProduct.product,
                )
                .where(
                    PosBranchProduct.branch_id == branch.id,
                    PosBranchProduct.is_available.is_(True),
                    PosProduct.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )

        categories: dict[int, dict] = {}

        for branch_product in branch_products:
            product = branch_product.product
            category = product.category

            if not category.is_active:
                continue

            effective_price = (
                branch_product.price
                if branch_product.price is not None
                else product.base_price
            )

            effective_sort_order = (
                branch_product.sort_order
                if branch_product.sort_order != 0
                else product.sort_order
            )

            resolved_variants = []
            has_variants = (
                product.variant_group_id is not None
            )
            display_price = Decimal(
                effective_price
            )

            if has_variants:
                variant_group = product.variant_group

                if (
                    variant_group is None
                    or not variant_group.is_active
                ):
                    continue

                for product_variant in sorted(
                    product.product_variants,
                    key=lambda item: (
                        item.sort_order,
                        item.variant.sort_order,
                        item.variant.id,
                    ),
                ):
                    variant = product_variant.variant

                    if not product_variant.is_active:
                        continue

                    if not variant.is_active:
                        continue

                    if (
                        variant.variant_group_id
                        != product.variant_group_id
                    ):
                        continue

                    branch_override = next(
                        (
                            row
                            for row
                            in product_variant.branch_overrides
                            if row.branch_id == branch.id
                        ),
                        None,
                    )

                    if (
                        branch_override is not None
                        and not branch_override.is_available
                    ):
                        continue

                    variant_price = (
                        branch_override.price_override
                        if (
                            branch_override is not None
                            and branch_override.price_override
                            is not None
                        )
                        else product_variant.price
                    )

                    resolved_variants.append(
                        PosCatalogProductVariantResponse(
                            product_variant_id=(
                                product_variant.id
                            ),
                            variant_id=variant.id,
                            name=variant.name,
                            price=Decimal(
                                variant_price
                            ),
                            sort_order=(
                                product_variant.sort_order
                            ),
                        )
                    )

                if not resolved_variants:
                    continue

                display_price = min(
                    row.price
                    for row in resolved_variants
                )

                effective_price = display_price

            modifier_groups = []

            for link in sorted(
                product.modifier_links,
                key=lambda item: (
                    item.sort_order,
                    item.modifier_group.sort_order,
                    item.modifier_group.id,
                ),
            ):
                group: PosModifierGroup = link.modifier_group

                if not group.is_active:
                    continue

                active_options = [
                    option
                    for option in group.options
                    if option.is_active
                ]

                active_options.sort(
                    key=lambda option: (
                        option.sort_order,
                        option.id,
                    )
                )

                # A required modifier with no selectable options
                # should never be offered to the cashier.
                if not active_options:
                    continue

                modifier_groups.append(
                    PosModifierGroupResponse(
                        id=group.id,
                        name=group.name,
                        required=group.required,
                        min_select=group.min_select,
                        max_select=group.max_select,
                        sort_order=link.sort_order,
                        options=[
                            PosModifierOptionResponse(
                                id=option.id,
                                name=option.name,
                                price_delta=Decimal(
                                    option.price_delta
                                ),
                                image_url=option.image_url,
                                sort_order=option.sort_order,
                            )
                            for option in active_options
                        ],
                    )
                )

            product_response = PosCatalogProductResponse(
                id=product.id,
                name=product.name,
                description=product.description,
                sku=product.sku,
                price=Decimal(effective_price),
                display_price=Decimal(display_price),
                has_variants=has_variants,
                variants=resolved_variants,
                image_url=product.image_url,
                preparation_station=product.preparation_station,
                sort_order=effective_sort_order,
                modifiers=modifier_groups,
            )

            category_entry = categories.setdefault(
                category.id,
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "sort_order": category.sort_order,
                    "products": [],
                },
            )

            category_entry["products"].append(
                product_response
            )

        category_responses = []

        for category in categories.values():
            category["products"].sort(
                key=lambda product: (
                    product.sort_order,
                    product.name.lower(),
                    product.id,
                )
            )

            category_responses.append(
                PosCatalogCategoryResponse(
                    **category
                )
            )

        category_responses.sort(
            key=lambda category: (
                category.sort_order,
                category.name.lower(),
                category.id,
            )
        )

        return PosCatalogResponse(
            branch=PosCatalogBranchResponse(
                id=branch.id,
                code=branch.code,
                name=branch.name,
            ),
            categories=category_responses,
        )
