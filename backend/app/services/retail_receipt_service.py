from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from app.models.branch import Branch
from app.models.pos_staff import PosStaff
from app.models.retail_sales import RetailSale


class RetailReceiptService:
    SCHEMA_VERSION = 1

    @staticmethod
    def _money(value: Any) -> str:
        return f"{Decimal(str(value)):.2f}"

    @staticmethod
    def _quantity(value: Any) -> str:
        return f"{Decimal(str(value)):.3f}"

    @staticmethod
    def _iso(value: Any) -> str | None:
        if value is None:
            return None

        if hasattr(value, "isoformat"):
            return value.isoformat()

        return str(value)

    @staticmethod
    def _first_attr(
        obj: Any,
        *names: str,
        default: Any = None,
    ) -> Any:
        for name in names:
            if not hasattr(obj, name):
                continue

            value = getattr(obj, name)

            if value is not None:
                return value

        return default

    @classmethod
    def _column_text(
        cls,
        obj: Any,
        *,
        explicit: tuple[str, ...],
        required_tokens: tuple[str, ...],
        excluded_tokens: tuple[str, ...] = (),
        default: str | None = None,
    ) -> str | None:
        value = cls._first_attr(
            obj,
            *explicit,
            default=None,
        )

        if value is not None:
            return str(value)

        table = getattr(
            obj,
            "__table__",
            None,
        )

        if table is None:
            return default

        for column in table.columns:
            normalized = column.name.lower()

            if not all(
                token in normalized
                for token in required_tokens
            ):
                continue

            if any(
                token in normalized
                for token in excluded_tokens
            ):
                continue

            value = getattr(
                obj,
                column.name,
                None,
            )

            if value is not None:
                return str(value)

        return default

    @classmethod
    def _line_snapshot(
        cls,
        line: Any,
    ) -> dict[str, Any]:
        sku = cls._column_text(
            line,
            explicit=(
                "sku_snapshot",
                "item_sku_snapshot",
                "sku",
            ),
            required_tokens=("sku",),
            default=None,
        )

        name = cls._column_text(
            line,
            explicit=(
                "name_snapshot",
                "item_name_snapshot",
                "item_name",
                "name",
            ),
            required_tokens=("name",),
            excluded_tokens=(
                "presentation",
            ),
            default=None,
        )

        presentation_name = (
            cls._column_text(
                line,
                explicit=(
                    "presentation_name_snapshot",
                    "presentation_name",
                ),
                required_tokens=(
                    "presentation",
                    "name",
                ),
                default=None,
            )
        )

        snapshot = {
            "line_id": line.id,
            "item_id": line.item_id,
            "presentation_id": (
                line.presentation_id
            ),
            "item_type": cls._first_attr(
                line,
                "item_type",
                default=None,
            ),
            "sku": sku,
            "name": name,
            "presentation_name": (
                presentation_name
            ),
            "quantity": cls._quantity(
                line.quantity
            ),
            "unit_price": cls._money(
                line.unit_price
            ),
            "line_subtotal": cls._money(
                line.line_subtotal
            ),
            "discount_amount": cls._money(
                line.discount_amount
            ),
            "line_total": cls._money(
                line.line_total
            ),
        }

        unit_cost = cls._first_attr(
            line,
            "unit_cost_snapshot",
            "unit_cost",
            default=None,
        )

        if unit_cost is not None:
            snapshot[
                "unit_cost_snapshot"
            ] = cls._money(unit_cost)

        return snapshot

    @classmethod
    def _payment_snapshot(
        cls,
        payment: Any,
    ) -> dict[str, Any]:
        return {
            "payment_uuid": (
                payment.payment_uuid
            ),
            "method": payment.method,
            "amount": cls._money(
                payment.amount
            ),
            "amount_tendered": (
                cls._money(
                    payment.amount_tendered
                )
                if payment.amount_tendered
                is not None
                else None
            ),
            "change_due": (
                cls._money(
                    payment.change_due
                )
                if payment.change_due
                is not None
                else None
            ),
            "external_reference": (
                payment.external_reference
            ),
        }

    @classmethod
    def build_snapshot(
        cls,
        *,
        sale: RetailSale,
        branch: Branch,
        cashier: PosStaff,
        authorizer: PosStaff | None = None,
    ) -> dict[str, Any]:
        if sale.status != "PAID":
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Receipt snapshot requires "
                    "a paid sale"
                ),
            )

        if not sale.payments:
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "Receipt snapshot requires "
                    "a payment"
                ),
            )

        payment = sale.payments[0]

        folio_value = cls._first_attr(
            sale,
            "folio",
            default=None,
        )

        if folio_value is None:
            folio_value = (
                sale.id
                if sale.id is not None
                else sale.sale_uuid
            )

        snapshot: dict[str, Any] = {
            "schema_version": (
                cls.SCHEMA_VERSION
            ),
            "folio": str(folio_value),
            "sale_uuid": sale.sale_uuid,
            "sold_at": cls._iso(
                sale.paid_at
            ),
            "business": {
                "name": "COFI",
                "module_code": (
                    sale.module_code
                ),
            },
            "branch": {
                "id": branch.id,
                "code": branch.code,
                "name": branch.name,
            },
            "terminal_id": (
                sale.terminal_id
            ),
            "cashier": {
                "staff_id": cashier.id,
                "display_name": (
                    cashier.display_name
                ),
            },
            "authorizer": (
                {
                    "staff_id": (
                        authorizer.id
                    ),
                    "display_name": (
                        authorizer.display_name
                    ),
                }
                if authorizer is not None
                else None
            ),
            "lines": [
                cls._line_snapshot(line)
                for line in sale.lines
            ],
            "totals": {
                "subtotal": cls._money(
                    sale.subtotal
                ),
                "discount_total": (
                    cls._money(
                        sale.discount_total
                    )
                ),
                "total": cls._money(
                    sale.total
                ),
                "currency": sale.currency,
            },
            "payment": (
                cls._payment_snapshot(
                    payment
                )
            ),
        }

        # Fiscal data is intentionally omitted
        # until a configured retail fiscal source
        # exists. Historical receipt JSON must not
        # synthesize fiscal identity.
        return snapshot

    @staticmethod
    def stored_snapshot(
        *,
        sale: RetailSale,
    ) -> dict[str, Any]:
        snapshot = sale.receipt_snapshot

        if snapshot is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Receipt not found",
            )

        return snapshot
