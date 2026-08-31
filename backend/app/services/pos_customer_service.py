import re
import uuid
from decimal import Decimal

from app.models.pos_customers import (
    Customer,
    LoyaltyLedgerEntry,
)
from app.models.pos_orders import PosOrder


def normalize_customer_phone(
    phone: str,
) -> str:
    raw = str(phone or "").strip()

    if not raw:
        raise ValueError(
            "Customer phone is required"
        )

    digits = re.sub(
        r"\D",
        "",
        raw,
    )

    if len(digits) == 10:
        digits = "52" + digits

    if (
        len(digits) != 12
        or not digits.startswith("52")
    ):
        raise ValueError(
            "Invalid Mexican phone number"
        )

    return "+" + digits


class PosCustomerService:
    @staticmethod
    def create(
        db,
        *,
        name,
        phone,
        email=None,
        birthday=None,
    ):
        normalized_phone = (
            normalize_customer_phone(phone)
        )

        existing = (
            db.query(Customer)
            .filter(
                Customer.phone_normalized
                == normalized_phone
            )
            .first()
        )

        if existing:
            return existing

        clean_name = str(
            name or ""
        ).strip()

        if not clean_name:
            raise ValueError(
                "Customer name is required"
            )

        clean_email = None

        if email:
            clean_email = (
                str(email)
                .strip()
                .lower()
            ) or None

        customer = Customer(
            customer_uuid=str(uuid.uuid4()),
            name=clean_name,
            phone=str(phone).strip(),
            phone_normalized=normalized_phone,
            email=clean_email,
            birthday=birthday,
        )

        db.add(customer)
        db.flush()

        return customer

    @staticmethod
    def search(
        db,
        *,
        q,
    ):
        query = str(
            q or ""
        ).strip()

        if not query:
            return (
                db.query(Customer)
                .order_by(
                    Customer.created_at.desc(),
                    Customer.id.desc(),
                )
                .limit(100)
                .all()
            )

        try:
            normalized_phone = (
                normalize_customer_phone(
                    query
                )
            )
        except ValueError:
            return (
                db.query(Customer)
                .filter(
                    Customer.name.ilike(
                        f"%{query}%"
                    )
                )
                .order_by(
                    Customer.name.asc(),
                    Customer.id.asc(),
                )
                .limit(100)
                .all()
            )

        return (
            db.query(Customer)
            .filter(
                Customer.phone_normalized
                == normalized_phone
            )
            .limit(100)
            .all()
        )

    @staticmethod
    def get_by_uuid(
        db,
        *,
        customer_uuid,
    ):
        return (
            db.query(Customer)
            .filter(
                Customer.customer_uuid
                == str(customer_uuid)
            )
            .first()
        )

    @staticmethod
    def loyalty_points(
        customer,
    ) -> int:
        return sum(
            int(entry.points)
            for entry
            in customer.loyalty_entries
        )

    @staticmethod
    def eligible_orders(
        db,
        *,
        customer_id,
    ):
        return (
            db.query(PosOrder)
            .filter(
                PosOrder.customer_id
                == customer_id,
                PosOrder.payment_status
                == "PAID",
                PosOrder.status
                != "CANCELLED",
            )
            .order_by(
                PosOrder.created_at_client.desc(),
                PosOrder.id.desc(),
            )
            .all()
        )

    @staticmethod
    def all_orders(
        db,
        *,
        customer_id,
    ):
        return (
            db.query(PosOrder)
            .filter(
                PosOrder.customer_id
                == customer_id
            )
            .order_by(
                PosOrder.created_at_client.desc(),
                PosOrder.id.desc(),
            )
            .all()
        )

    @classmethod
    def metrics(
        cls,
        db,
        *,
        customer,
    ):
        orders = cls.eligible_orders(
            db,
            customer_id=customer.id,
        )

        total_spent = sum(
            (
                Decimal(
                    str(order.total)
                )
                for order in orders
            ),
            Decimal("0.00"),
        )

        return {
            "loyalty_points":
                cls.loyalty_points(
                    customer
                ),
            "visits":
                len(orders),
            "total_spent":
                total_spent,
            "last_purchase_at":
                (
                    orders[
                        0
                    ].created_at_client
                    if orders
                    else None
                ),
        }

    @classmethod
    def summary(
        cls,
        db,
        customer,
    ):
        return {
            "customer_uuid":
                customer.customer_uuid,
            "name":
                customer.name,
            "phone":
                customer.phone,
            "phone_normalized":
                customer.phone_normalized,
            "email":
                customer.email,
            "birthday":
                customer.birthday,
            "last_activity_at":
                customer.last_activity_at,
            "created_at":
                customer.created_at,
            **cls.metrics(
                db,
                customer=customer,
            ),
        }

    @classmethod
    def update(
        cls,
        db,
        *,
        customer_uuid,
        values,
    ):
        customer = cls.get_by_uuid(
            db,
            customer_uuid=customer_uuid,
        )

        if customer is None:
            return None

        if "name" in values:
            clean_name = str(
                values["name"] or ""
            ).strip()

            if not clean_name:
                raise ValueError(
                    "Customer name is required"
                )

            customer.name = clean_name

        if "phone" in values:
            phone = values["phone"]

            normalized_phone = (
                normalize_customer_phone(
                    phone
                )
            )

            duplicate = (
                db.query(Customer)
                .filter(
                    Customer.phone_normalized
                    == normalized_phone,
                    Customer.id
                    != customer.id,
                )
                .first()
            )

            if duplicate is not None:
                raise ValueError(
                    "Customer phone already exists"
                )

            customer.phone = str(
                phone
            ).strip()

            customer.phone_normalized = (
                normalized_phone
            )

        if "email" in values:
            email = values["email"]

            customer.email = (
                str(email)
                .strip()
                .lower()
                if email
                else None
            )

        if "birthday" in values:
            customer.birthday = (
                values["birthday"]
            )

        db.flush()

        return customer

    @classmethod
    def adjust_loyalty(
        cls,
        db,
        *,
        customer_uuid,
        points,
    ):
        customer = cls.get_by_uuid(
            db,
            customer_uuid=customer_uuid,
        )

        if customer is None:
            return None

        points = int(points)

        if points == 0:
            raise ValueError(
                "Loyalty adjustment cannot be zero"
            )

        adjustment_uuid = str(
            uuid.uuid4()
        )

        entry = LoyaltyLedgerEntry(
            entry_uuid=adjustment_uuid,
            customer_id=customer.id,
            points=points,
            entry_type=(
                "EARN"
                if points > 0
                else "REDEEM"
            ),
            order_uuid=None,
            branch_id=None,
            idempotency_key=(
                "ADMIN:"
                + adjustment_uuid
            ),
        )

        db.add(entry)
        db.flush()
        db.refresh(entry)

        return entry

    @classmethod
    def profile(
        cls,
        db,
        customer,
    ):
        summary = cls.summary(
            db,
            customer,
        )

        orders = cls.all_orders(
            db,
            customer_id=customer.id,
        )

        loyalty_history = sorted(
            customer.loyalty_entries,
            key=lambda entry: (
                entry.created_at.isoformat()
                if entry.created_at
                else ""
            ),
            reverse=True,
        )

        return {
            **summary,
            "orders": [
                {
                    "order_uuid":
                        order.order_uuid,
                    "folio":
                        order.folio,
                    "created_at_client":
                        order.created_at_client,
                    "branch_code":
                        (
                            order.branch.code
                            if order.branch
                            else None
                        ),
                    "total":
                        order.total,
                    "status":
                        order.status,
                    "payment_status":
                        order.payment_status,
                }
                for order in orders
            ],
            "loyalty_history": [
                {
                    "entry_uuid":
                        entry.entry_uuid,
                    "points":
                        entry.points,
                    "entry_type":
                        entry.entry_type,
                    "order_uuid":
                        entry.order_uuid,
                    "created_at":
                        entry.created_at,
                }
                for entry
                in loyalty_history
            ],
        }
