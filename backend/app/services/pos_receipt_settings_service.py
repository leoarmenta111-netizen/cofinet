from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.pos_receipts import (
    PosBranchReceiptSettings,
    PosBusinessReceiptSettings,
)
from app.schemas.pos_receipts import (
    BranchReceiptSettingsUpdate,
    EffectiveReceiptSettings,
    ReceiptSettingsUpdate,
)
from app.services.branch_service import BranchService


class PosReceiptSettingsService:
    @staticmethod
    def _get_business(
        db: Session,
    ) -> PosBusinessReceiptSettings | None:
        return db.get(PosBusinessReceiptSettings, 1)

    @staticmethod
    def get_effective(
        db: Session,
        branch_code: str | None,
    ) -> EffectiveReceiptSettings:
        branch = BranchService.resolve(db, branch_code)
        business = PosReceiptSettingsService._get_business(db)

        if business is None:
            business_values = {
                "business_name": "CofiCenter",
                "logo_ref": None,
                "phone": None,
                "web_social": None,
                "footer_message": None,
                "currency": "MXN",
                "tax_mode": "NONE",
                "tax_rate": Decimal("0.0000"),
                "receipt_width_mm": 80,
                "timezone": "America/Bahia_Banderas",
                "folio_prefix": "CF",
                "auto_print_customer": False,
            }
        else:
            business_values = {
                "business_name": business.business_name,
                "logo_ref": business.logo_ref,
                "phone": business.phone,
                "web_social": business.web_social,
                "footer_message": business.footer_message,
                "currency": business.currency,
                "tax_mode": business.tax_mode,
                "tax_rate": business.tax_rate,
                "receipt_width_mm": business.receipt_width_mm,
                "timezone": business.timezone,
                "folio_prefix": business.folio_prefix,
                "auto_print_customer": business.auto_print_customer,
            }

        override = (
            db.query(PosBranchReceiptSettings)
            .filter(PosBranchReceiptSettings.branch_id == branch.id)
            .one_or_none()
        )

        effective_tax_mode = (
            override.tax_mode
            if override is not None and override.tax_mode is not None
            else business_values["tax_mode"]
        )

        effective_tax_rate = (
            override.tax_rate
            if override is not None and override.tax_rate is not None
            else business_values["tax_rate"]
        )

        if effective_tax_mode == "NONE":
            effective_tax_rate = Decimal("0.0000")

        return EffectiveReceiptSettings(
            business_name=business_values["business_name"],
            logo_ref=business_values["logo_ref"],
            phone=(
                override.phone
                if override is not None and override.phone is not None
                else business_values["phone"]
            ),
            web_social=(
                override.web_social
                if override is not None and override.web_social is not None
                else business_values["web_social"]
            ),
            footer_message=(
                override.footer_message
                if override is not None and override.footer_message is not None
                else business_values["footer_message"]
            ),
            branch_code=branch.code,
            branch_name=(
                override.display_name
                if override is not None and override.display_name is not None
                else branch.name
            ),
            address=(
                override.address
                if override is not None and override.address is not None
                else None
            ),
            currency=business_values["currency"],
            tax_mode=effective_tax_mode,
            tax_rate=effective_tax_rate,
            receipt_width_mm=business_values["receipt_width_mm"],
            timezone=(
                override.timezone
                if override is not None and override.timezone is not None
                else business_values["timezone"]
            ),
            folio_prefix=(
                override.folio_prefix
                if override is not None and override.folio_prefix is not None
                else business_values["folio_prefix"]
            ),
            auto_print_customer=(
                override.auto_print_customer
                if override is not None and override.auto_print_customer is not None
                else business_values["auto_print_customer"]
            ),
        )

    @staticmethod
    def update_business(
        db: Session,
        payload: ReceiptSettingsUpdate,
    ) -> PosBusinessReceiptSettings:
        settings = PosReceiptSettingsService._get_business(db)

        if settings is None:
            settings = PosBusinessReceiptSettings(id=1)
            db.add(settings)

        values = payload.model_dump()

        for field, value in values.items():
            if field == "tax_rate":
                value = Decimal(str(value))
            setattr(settings, field, value)

        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def update_branch(
        db: Session,
        branch_code: str,
        payload: BranchReceiptSettingsUpdate,
    ) -> EffectiveReceiptSettings:
        branch = BranchService.get_by_code(db, branch_code)

        settings = (
            db.query(PosBranchReceiptSettings)
            .filter(PosBranchReceiptSettings.branch_id == branch.id)
            .one_or_none()
        )

        if settings is None:
            settings = PosBranchReceiptSettings(branch_id=branch.id)
            db.add(settings)

        for field, value in payload.model_dump(exclude_unset=True).items():
            if field == "tax_rate" and value is not None:
                value = Decimal(str(value))
            setattr(settings, field, value)

        db.commit()

        return PosReceiptSettingsService.get_effective(
            db,
            branch.code,
        )
