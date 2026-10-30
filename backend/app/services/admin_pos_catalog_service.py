import re
import unicodedata
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosBranchProductVariant,
    PosCategory,
    PosModifierGroup,
    PosModifierOption,
    PosProduct,
    PosProductModifierGroup,
    PosProductVariant,
    PosVariant,
    PosVariantGroup,
)
from app.schemas.admin_pos_catalog import (
    AdminPosBranchProductUpdate,
    AdminPosBranchProductVariantUpdate,
    AdminPosCategoryCreate,
    AdminPosCategoryUpdate,
    AdminPosModifierGroupCreate,
    AdminPosModifierGroupUpdate,
    AdminPosModifierOptionCreate,
    AdminPosModifierOptionUpdate,
    AdminPosProductCreate,
    AdminPosProductModifierUpdate,
    AdminPosProductUpdate,
    AdminPosProductVariantUpdate,
    AdminPosVariantCreate,
    AdminPosVariantGroupCreate,
    AdminPosVariantGroupUpdate,
    AdminPosVariantUpdate,
)


class AdminPosCatalogService:

    @staticmethod
    def _slug(value: str) -> str:
        value = unicodedata.normalize("NFKD", value)
        value = value.encode("ascii", "ignore").decode("ascii")
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-")[:80]

    @staticmethod
    def _commit(db: Session):
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un registro con esos datos.",
            ) from exc

    @staticmethod
    def _category(db: Session, category_id: int) -> PosCategory:
        item = db.get(PosCategory, category_id)
        if item is None:
            raise HTTPException(404, "POS category not found")
        return item

    @staticmethod
    def _product(db: Session, product_id: int) -> PosProduct:
        item = db.get(PosProduct, product_id)
        if item is None:
            raise HTTPException(404, "POS product not found")
        return item

    @staticmethod
    def _group(db: Session, group_id: int) -> PosModifierGroup:
        item = db.get(PosModifierGroup, group_id)
        if item is None:
            raise HTTPException(404, "POS modifier group not found")
        return item

    @staticmethod
    def _option(db: Session, option_id: int) -> PosModifierOption:
        item = db.get(PosModifierOption, option_id)
        if item is None:
            raise HTTPException(404, "POS modifier option not found")
        return item

    @staticmethod
    def _variant_group(
        db: Session,
        group_id: int,
    ) -> PosVariantGroup:
        item = db.get(PosVariantGroup, group_id)
        if item is None:
            raise HTTPException(
                404,
                "POS variant group not found",
            )
        return item

    @staticmethod
    def _variant(
        db: Session,
        variant_id: int,
    ) -> PosVariant:
        item = db.get(PosVariant, variant_id)
        if item is None:
            raise HTTPException(
                404,
                "POS variant not found",
            )
        return item

    @classmethod
    def get_catalog(cls, db: Session) -> dict:
        branches = (
            db.execute(
                select(Branch)
                .where(Branch.is_active.is_(True))
                .order_by(Branch.id)
            )
            .scalars()
            .all()
        )

        categories = (
            db.execute(
                select(PosCategory)
                .order_by(
                    PosCategory.sort_order,
                    PosCategory.name,
                    PosCategory.id,
                )
            )
            .scalars()
            .all()
        )

        products = (
            db.execute(
                select(PosProduct)
                .order_by(
                    PosProduct.sort_order,
                    PosProduct.name,
                    PosProduct.id,
                )
            )
            .scalars()
            .all()
        )

        groups = (
            db.execute(
                select(PosModifierGroup)
                .order_by(
                    PosModifierGroup.sort_order,
                    PosModifierGroup.name,
                    PosModifierGroup.id,
                )
            )
            .scalars()
            .all()
        )

        variant_groups = (
            db.execute(
                select(PosVariantGroup)
                .order_by(
                    PosVariantGroup.sort_order,
                    PosVariantGroup.name,
                    PosVariantGroup.id,
                )
            )
            .scalars()
            .all()
        )

        product_rows = []

        for product in products:
            settings = {
                row.branch.id: row
                for row in product.branch_products
            }

            branch_rows = []

            for branch in branches:
                setting = settings.get(branch.id)

                override = (
                    Decimal(setting.price)
                    if setting is not None
                    and setting.price is not None
                    else None
                )

                branch_rows.append({
                    "branch_id": branch.id,
                    "branch_code": branch.code,
                    "branch_name": branch.name,
                    "price": override,
                    "effective_price": (
                        override
                        if override is not None
                        else Decimal(product.base_price)
                    ),
                    "is_available": (
                        bool(setting.is_available)
                        if setting is not None
                        else False
                    ),
                    "sort_order": (
                        setting.sort_order
                        if setting is not None
                        else 0
                    ),
                })

            product_variant_rows = []

            for product_variant in sorted(
                product.product_variants,
                key=lambda row: (
                    row.sort_order,
                    row.variant.sort_order,
                    row.variant.name.lower(),
                    row.id,
                ),
            ):
                branch_overrides = {
                    row.branch.id: row
                    for row in product_variant.branch_overrides
                }

                variant_branch_rows = []

                for branch in branches:
                    override_row = branch_overrides.get(
                        branch.id
                    )

                    price_override = (
                        Decimal(override_row.price_override)
                        if override_row is not None
                        and override_row.price_override is not None
                        else None
                    )

                    variant_branch_rows.append({
                        "branch_code": branch.code,
                        "branch_name": branch.name,
                        "price_override": price_override,
                        "effective_price": (
                            price_override
                            if price_override is not None
                            else Decimal(product_variant.price)
                        ),
                        "is_available": (
                            bool(override_row.is_available)
                            if override_row is not None
                            else True
                        ),
                    })

                product_variant_rows.append({
                    "product_variant_id": product_variant.id,
                    "variant_id": product_variant.variant.id,
                    "variant_name": product_variant.variant.name,
                    "price": Decimal(product_variant.price),
                    "is_active": product_variant.is_active,
                    "sort_order": product_variant.sort_order,
                    "branches": variant_branch_rows,
                })

            modifier_rows = []

            for link in sorted(
                product.modifier_links,
                key=lambda row: (
                    row.sort_order,
                    row.modifier_group.sort_order,
                    row.modifier_group.id,
                ),
            ):
                modifier_rows.append({
                    "group_id": link.modifier_group.id,
                    "group_name": link.modifier_group.name,
                    "sort_order": link.sort_order,
                })

            product_rows.append({
                "id": product.id,
                "category_id": product.category.id,
                "category_name": product.category.name,
                "name": product.name,
                "description": product.description,
                "sku": product.sku,
                "base_price": Decimal(product.base_price),
                "image_url": product.image_url,
                "preparation_station": product.preparation_station,
                "sort_order": product.sort_order,
                "is_active": product.is_active,
                "variant_group_id": product.variant_group_id,
                "variants": product_variant_rows,
                "branches": branch_rows,
                "modifiers": modifier_rows,
            })

        group_rows = []

        for group in groups:
            options = sorted(
                group.options,
                key=lambda row: (
                    row.sort_order,
                    row.name.lower(),
                    row.id,
                ),
            )

            group_rows.append({
                "id": group.id,
                "name": group.name,
                "required": group.required,
                "min_select": group.min_select,
                "max_select": group.max_select,
                "sort_order": group.sort_order,
                "is_active": group.is_active,
                "options": [
                    {
                        "id": option.id,
                        "name": option.name,
                        "price_delta": Decimal(option.price_delta),
                        "image_url": option.image_url,
                        "sort_order": option.sort_order,
                        "is_active": option.is_active,
                    }
                    for option in options
                ],
            })

        variant_group_rows = []

        for group in variant_groups:
            variants = sorted(
                group.variants,
                key=lambda row: (
                    row.sort_order,
                    row.name.lower(),
                    row.id,
                ),
            )

            variant_group_rows.append({
                "id": group.id,
                "name": group.name,
                "sort_order": group.sort_order,
                "is_active": group.is_active,
                "variants": [
                    {
                        "id": variant.id,
                        "variant_group_id": variant.variant_group_id,
                        "name": variant.name,
                        "sort_order": variant.sort_order,
                        "is_active": variant.is_active,
                    }
                    for variant in variants
                ],
            })

        return {
            "branches": [
                {
                    "id": branch.id,
                    "code": branch.code,
                    "name": branch.name,
                }
                for branch in branches
            ],
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "sort_order": category.sort_order,
                    "is_active": category.is_active,
                }
                for category in categories
            ],
            "products": product_rows,
            "modifier_groups": group_rows,
            "variant_groups": variant_group_rows,
        }

    @classmethod
    def create_variant_group(
        cls,
        db: Session,
        data: AdminPosVariantGroupCreate,
    ) -> dict:
        group = PosVariantGroup(
            name=data.name.strip(),
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        db.add(group)
        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_variant_group(
        cls,
        db: Session,
        group_id: int,
        data: AdminPosVariantGroupUpdate,
    ) -> dict:
        group = cls._variant_group(
            db,
            group_id,
        )
        values = data.model_dump(
            exclude_unset=True,
        )

        for key, value in values.items():
            if value is not None:
                if key == "name":
                    value = value.strip()
                setattr(group, key, value)

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def create_variant(
        cls,
        db: Session,
        group_id: int,
        data: AdminPosVariantCreate,
    ) -> dict:
        group = cls._variant_group(
            db,
            group_id,
        )
        variant = PosVariant(
            group=group,
            name=data.name.strip(),
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        db.add(variant)
        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_variant(
        cls,
        db: Session,
        variant_id: int,
        data: AdminPosVariantUpdate,
    ) -> dict:
        variant = cls._variant(
            db,
            variant_id,
        )
        values = data.model_dump(
            exclude_unset=True,
        )

        for key, value in values.items():
            if value is not None:
                if key == "name":
                    value = value.strip()
                setattr(variant, key, value)

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def create_category(
        cls,
        db: Session,
        data: AdminPosCategoryCreate,
    ) -> dict:
        slug = data.slug or cls._slug(data.name)

        category = PosCategory(
            name=data.name.strip(),
            slug=slug,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )

        db.add(category)
        cls._commit(db)

        return cls.get_catalog(db)

    @classmethod
    def update_category(
        cls,
        db: Session,
        category_id: int,
        data: AdminPosCategoryUpdate,
    ) -> dict:
        category = cls._category(db, category_id)

        values = data.model_dump(exclude_unset=True)

        if "name" in values and values["name"] is not None:
            values["name"] = values["name"].strip()

        if values.get("slug") == "":
            values["slug"] = cls._slug(
                values.get("name") or category.name
            )

        for key, value in values.items():
            if value is not None:
                setattr(category, key, value)

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def create_product(
        cls,
        db: Session,
        data: AdminPosProductCreate,
    ) -> dict:
        category = cls._category(db, data.category_id)

        product = PosProduct(
            category=category,
            name=data.name.strip(),
            description=data.description,
            sku=(data.sku.strip() if data.sku else None),
            base_price=data.base_price,
            image_url=data.image_url,
            preparation_station=data.preparation_station,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )

        db.add(product)
        db.flush()

        branches = (
            db.execute(
                select(Branch).where(
                    Branch.is_active.is_(True)
                )
            )
            .scalars()
            .all()
        )

        # Producto nuevo: disponible en todas las sucursales
        # activas usando el precio base.
        for branch in branches:
            db.add(
                PosBranchProduct(
                    branch=branch,
                    product=product,
                    price=None,
                    is_available=True,
                    sort_order=0,
                )
            )

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_product(
        cls,
        db: Session,
        product_id: int,
        data: AdminPosProductUpdate,
    ) -> dict:
        product = cls._product(db, product_id)
        values = data.model_dump(exclude_unset=True)

        if "category_id" in values:
            category_id = values.pop("category_id")
            if category_id is not None:
                product.category = cls._category(
                    db,
                    category_id,
                )

        if "name" in values and values["name"] is not None:
            values["name"] = values["name"].strip()

        if "sku" in values:
            values["sku"] = (
                values["sku"].strip()
                if values["sku"]
                else None
            )

        for key, value in values.items():
            setattr(product, key, value)

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def assign_variant_group(
        cls,
        db: Session,
        product_id: int,
        group_id: int,
    ) -> dict:
        product = cls._product(
            db,
            product_id,
        )
        group = cls._variant_group(
            db,
            group_id,
        )

        product.variant_group_id = group.id

        for row in product.product_variants:
            if (
                row.is_active
                and row.variant.variant_group_id != group.id
            ):
                row.is_active = False

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def remove_variant_group(
        cls,
        db: Session,
        product_id: int,
    ) -> dict:
        product = cls._product(
            db,
            product_id,
        )

        product.variant_group_id = None

        for row in product.product_variants:
            if row.is_active:
                row.is_active = False

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_product_variant(
        cls,
        db: Session,
        product_id: int,
        variant_id: int,
        data: AdminPosProductVariantUpdate,
    ) -> dict:
        product = cls._product(
            db,
            product_id,
        )
        variant = cls._variant(
            db,
            variant_id,
        )

        if (
            product.variant_group_id is None
            or variant.variant_group_id
            != product.variant_group_id
        ):
            raise HTTPException(
                422,
                "Variant does not belong to product variant group",
            )

        product_variant = next(
            (
                row
                for row in product.product_variants
                if row.variant_id == variant.id
            ),
            None,
        )

        if product_variant is None:
            product_variant = PosProductVariant(
                product=product,
                variant=variant,
                price=data.price,
                is_active=data.is_active,
                sort_order=data.sort_order,
            )
            db.add(product_variant)
        else:
            product_variant.price = data.price
            product_variant.is_active = data.is_active
            product_variant.sort_order = data.sort_order

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_branch_product_variant(
        cls,
        db: Session,
        product_id: int,
        variant_id: int,
        branch_code: str,
        data: AdminPosBranchProductVariantUpdate,
    ) -> dict:
        product = cls._product(
            db,
            product_id,
        )
        variant = cls._variant(
            db,
            variant_id,
        )

        if (
            product.variant_group_id is None
            or variant.variant_group_id
            != product.variant_group_id
        ):
            raise HTTPException(
                422,
                "Variant does not belong to product variant group",
            )

        product_variant = next(
            (
                row
                for row in product.product_variants
                if row.variant_id == variant.id
            ),
            None,
        )

        if product_variant is None:
            raise HTTPException(
                404,
                "POS product variant not found",
            )

        branch = db.execute(
            select(Branch).where(
                Branch.code
                == branch_code.strip().lower()
            )
        ).scalar_one_or_none()

        if branch is None:
            raise HTTPException(
                404,
                "Branch not found",
            )

        setting = next(
            (
                row
                for row in product_variant.branch_overrides
                if row.branch.id == branch.id
            ),
            None,
        )

        if (
            data.price_override is None
            and data.is_available is True
        ):
            if setting is not None:
                db.delete(setting)

            cls._commit(db)
            return cls.get_catalog(db)

        if setting is None:
            setting = PosBranchProductVariant(
                branch=branch,
                product_variant=product_variant,
            )
            db.add(setting)

        setting.price_override = data.price_override
        setting.is_available = data.is_available

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_branch_product(
        cls,
        db: Session,
        product_id: int,
        branch_code: str,
        data: AdminPosBranchProductUpdate,
    ) -> dict:
        product = cls._product(db, product_id)

        branch = db.execute(
            select(Branch).where(
                Branch.code == branch_code.strip().lower()
            )
        ).scalar_one_or_none()

        if branch is None:
            raise HTTPException(404, "Branch not found")

        setting = next(
            (
                row
                for row in product.branch_products
                if row.branch.id == branch.id
            ),
            None,
        )

        if setting is None:
            setting = PosBranchProduct(
                branch=branch,
                product=product,
            )
            db.add(setting)

        setting.price = data.price
        setting.is_available = data.is_available
        setting.sort_order = data.sort_order

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def create_group(
        cls,
        db: Session,
        data: AdminPosModifierGroupCreate,
    ) -> dict:
        if data.min_select > data.max_select:
            raise HTTPException(
                422,
                "min_select cannot exceed max_select",
            )

        group = PosModifierGroup(
            name=data.name.strip(),
            required=data.required,
            min_select=data.min_select,
            max_select=data.max_select,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )

        db.add(group)
        cls._commit(db)

        return cls.get_catalog(db)

    @classmethod
    def update_group(
        cls,
        db: Session,
        group_id: int,
        data: AdminPosModifierGroupUpdate,
    ) -> dict:
        group = cls._group(db, group_id)
        values = data.model_dump(exclude_unset=True)

        new_min = values.get(
            "min_select",
            group.min_select,
        )

        new_max = values.get(
            "max_select",
            group.max_select,
        )

        if new_min > new_max:
            raise HTTPException(
                422,
                "min_select cannot exceed max_select",
            )

        for key, value in values.items():
            if value is not None:
                setattr(group, key, value)

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def create_option(
        cls,
        db: Session,
        group_id: int,
        data: AdminPosModifierOptionCreate,
    ) -> dict:
        group = cls._group(db, group_id)

        option = PosModifierOption(
            group=group,
            name=data.name.strip(),
            price_delta=data.price_delta,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )

        db.add(option)
        cls._commit(db)

        return cls.get_catalog(db)

    @classmethod
    def update_option(
        cls,
        db: Session,
        option_id: int,
        data: AdminPosModifierOptionUpdate,
    ) -> dict:
        option = cls._option(db, option_id)

        values = data.model_dump(exclude_unset=True)

        for key, value in values.items():
            if value is not None:
                setattr(option, key, value)

        cls._commit(db)
        return cls.get_catalog(db)

    @classmethod
    def update_product_modifier(
        cls,
        db: Session,
        product_id: int,
        group_id: int,
        data: AdminPosProductModifierUpdate,
    ) -> dict:
        product = cls._product(db, product_id)
        group = cls._group(db, group_id)

        link = next(
            (
                row
                for row in product.modifier_links
                if row.modifier_group.id == group.id
            ),
            None,
        )

        if not data.enabled:
            if link is not None:
                db.delete(link)

            cls._commit(db)
            return cls.get_catalog(db)

        if link is None:
            link = PosProductModifierGroup(
                product=product,
                modifier_group=group,
                sort_order=data.sort_order,
            )
            db.add(link)
        else:
            link.sort_order = data.sort_order

        cls._commit(db)
        return cls.get_catalog(db)
