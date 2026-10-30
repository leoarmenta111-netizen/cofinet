from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.pos_catalog import (
    PosBranchProduct,
    PosProduct,
)


CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


@dataclass(frozen=True)
class PricingItemRequest:
    product_id: int
    quantity: int
    modifier_option_ids: list[int]
    notes: str | None = None


@dataclass(frozen=True)
class PricingModifierSnapshot:
    group_id: int
    option_id: int
    group_name: str
    option_name: str
    price_delta: Decimal


@dataclass(frozen=True)
class PricingResolvedItem:
    product: PosProduct
    product_id: int
    product_name: str
    preparation_station: str
    quantity: int
    unit_base_price: Decimal
    unit_modifier_total: Decimal
    unit_price: Decimal
    line_total: Decimal
    notes: str | None
    modifiers: list[PricingModifierSnapshot]


class PosPricingService:
    @staticmethod
    def _bad_request(detail: str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    @classmethod
    def resolve_items(
        cls,
        *,
        db: Session,
        branch: Branch,
        items: list[PricingItemRequest],
    ) -> list[PricingResolvedItem]:
        resolved: list[PricingResolvedItem] = []

        for requested in items:
            if requested.quantity <= 0:
                cls._bad_request(
                    "Product quantity must be positive"
                )

            selected_ids = list(
                requested.modifier_option_ids
            )

            if len(selected_ids) != len(set(selected_ids)):
                cls._bad_request(
                    "Duplicate modifier option selected"
                )

            branch_product = (
                db.execute(
                    select(PosBranchProduct).where(
                        PosBranchProduct.branch_id
                        == branch.id,
                        PosBranchProduct.product_id
                        == requested.product_id,
                    )
                )
                .scalar_one_or_none()
            )

            if (
                branch_product is None
                or not branch_product.is_available
            ):
                cls._bad_request(
                    "Product is not available at this branch"
                )

            product = branch_product.product

            if not product.is_active:
                cls._bad_request(
                    "Product is inactive"
                )

            if (
                product.category is None
                or not product.category.is_active
            ):
                cls._bad_request(
                    "Product category is inactive"
                )

            option_map = {}
            active_groups = {}

            for link in product.modifier_links:
                group = link.modifier_group

                if group.is_active:
                    active_groups[group.id] = group

                for option in group.options:
                    option_map[option.id] = (
                        group,
                        option,
                    )

            selected_by_group = {}

            for option_id in selected_ids:
                pair = option_map.get(option_id)

                if pair is None:
                    cls._bad_request(
                        "Modifier option is not available for product"
                    )

                group, option = pair

                if not group.is_active:
                    cls._bad_request(
                        "Modifier group is inactive"
                    )

                if not option.is_active:
                    cls._bad_request(
                        "Modifier option is inactive"
                    )

                selected_by_group.setdefault(
                    group.id,
                    [],
                ).append(option)

            for group in active_groups.values():
                selected = selected_by_group.get(
                    group.id,
                    [],
                )

                minimum = int(group.min_select)

                if group.required:
                    minimum = max(minimum, 1)

                if len(selected) < minimum:
                    cls._bad_request(
                        "Required modifier selection is missing"
                    )

                if len(selected) > int(group.max_select):
                    cls._bad_request(
                        "Too many modifier options selected"
                    )

            base_price = money(
                branch_product.price
                if branch_product.price is not None
                else product.base_price
            )

            modifier_total = Decimal("0.00")
            modifier_snapshots = []

            for option_id in selected_ids:
                group, option = option_map[option_id]

                delta = money(option.price_delta)
                modifier_total += delta

                modifier_snapshots.append(
                    PricingModifierSnapshot(
                        group_id=group.id,
                        option_id=option.id,
                        group_name=group.name,
                        option_name=option.name,
                        price_delta=delta,
                    )
                )

            modifier_total = money(
                modifier_total
            )

            unit_price = money(
                base_price + modifier_total
            )

            if unit_price < 0:
                cls._bad_request(
                    "Calculated product price is invalid"
                )

            line_total = money(
                unit_price * requested.quantity
            )

            resolved.append(
                PricingResolvedItem(
                    product=product,
                    product_id=product.id,
                    product_name=product.name,
                    preparation_station=(
                        product.preparation_station
                    ),
                    quantity=requested.quantity,
                    unit_base_price=base_price,
                    unit_modifier_total=modifier_total,
                    unit_price=unit_price,
                    line_total=line_total,
                    notes=requested.notes,
                    modifiers=modifier_snapshots,
                )
            )

        return resolved
