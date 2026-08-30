import re
import uuid

from app.models.pos_customers import Customer


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

        clean_name = str(name or "").strip()

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
        query = str(q or "").strip()

        if not query:
            return []

        try:
            normalized_phone = (
                normalize_customer_phone(query)
            )
        except ValueError:
            return (
                db.query(Customer)
                .filter(
                    Customer.name.ilike(
                        f"%{query}%"
                    )
                )
                .all()
            )

        return (
            db.query(Customer)
            .filter(
                Customer.phone_normalized
                == normalized_phone
            )
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
                == customer_uuid
            )
            .first()
        )
