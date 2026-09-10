from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.admin_security import require_super_admin
from app.database.deps import get_db
from app.models.admin import Admin
from app.schemas.pos_receipts import (
    BranchReceiptSettingsUpdate,
    EffectiveReceiptSettings,
    ReceiptSettingsUpdate,
)
from app.services.pos_receipt_settings_service import PosReceiptSettingsService


router = APIRouter(
    prefix="/admin/pos/receipt-settings",
    tags=["Admin POS Receipt Settings"],
)


@router.put("/business")
def update_business_receipt_settings(
    data: ReceiptSettingsUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    settings = PosReceiptSettingsService.update_business(
        db,
        data,
    )

    return {
        "business_name": settings.business_name,
        "logo_ref": settings.logo_ref,
        "phone": settings.phone,
        "web_social": settings.web_social,
        "footer_message": settings.footer_message,
        "currency": settings.currency,
        "tax_mode": settings.tax_mode,
        "tax_rate": float(settings.tax_rate),
        "receipt_width_mm": settings.receipt_width_mm,
        "timezone": settings.timezone,
        "folio_prefix": settings.folio_prefix,
        "auto_print_customer": settings.auto_print_customer,
    }


@router.put(
    "/branches/{branch_code}",
    response_model=EffectiveReceiptSettings,
)
def update_branch_receipt_settings(
    branch_code: str,
    data: BranchReceiptSettingsUpdate,
    _admin: Admin = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return PosReceiptSettingsService.update_branch(
        db,
        branch_code,
        data,
    )


@router.get("")
def get_receipt_settings(
    db: Session = Depends(get_db),
    _admin=Depends(require_super_admin),
):
    from app.models.branch import Branch
    from app.models.pos_receipts import (
        PosBranchReceiptSettings,
        PosBusinessReceiptSettings,
    )

    business = db.get(PosBusinessReceiptSettings, 1)

    if business is None:
        business_payload = None
    else:
        business_payload = {
            "id": business.id,
            "business_name": business.business_name,
            "logo_ref": business.logo_ref,
            "phone": business.phone,
            "web_social": business.web_social,
            "footer_message": business.footer_message,
            "currency": business.currency,
            "tax_mode": business.tax_mode,
            "tax_rate": float(business.tax_rate),
            "receipt_width_mm": business.receipt_width_mm,
            "timezone": business.timezone,
            "folio_prefix": business.folio_prefix,
            "auto_print_customer": business.auto_print_customer,
        }

    branches = (
        db.query(Branch)
        .filter(Branch.is_active.is_(True))
        .order_by(Branch.id.asc())
        .all()
    )

    branch_payloads = []

    for branch in branches:
        override = db.get(
            PosBranchReceiptSettings,
            branch.id,
        )

        if override is None:
            override_payload = None
        else:
            override_payload = {
                "display_name": override.display_name,
                "address": override.address,
                "phone": override.phone,
                "web_social": override.web_social,
                "footer_message": override.footer_message,
                "tax_mode": override.tax_mode,
                "tax_rate": (
                    float(override.tax_rate)
                    if override.tax_rate is not None
                    else None
                ),
                "timezone": override.timezone,
                "folio_prefix": override.folio_prefix,
                "auto_print_customer": (
                    override.auto_print_customer
                ),
            }

        effective = PosReceiptSettingsService.get_effective(
            db,
            branch.code,
        )

        branch_payloads.append(
            {
                "branch_code": branch.code,
                "branch_name": branch.name,
                "overrides": override_payload,
                "effective": effective.model_dump(mode="json"),
            }
        )

    return {
        "business": business_payload,
        "branches": branch_payloads,
    }
