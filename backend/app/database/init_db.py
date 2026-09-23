from app.database.self_order_seed import ensure_self_order_devices
from app.database.session import Base, SessionLocal, engine
from sqlalchemy import text
from app.models.admin import Admin
from app.models.admin_access import InternalHotspotCredential, PinBatch, PinBatchFailure
from app.models.plan import Plan
from app.models.payment import Payment
from app.models.membership import Membership
from app.models.purchase import Purchase
from app.models.user import User
from app.services.plan_service import PlanService

Base.metadata.create_all(bind=engine)

# Existing installations created purchases before guest checkout existed. These
# columns must allow pending guest records with no account, PIN, or expiry.
with engine.begin() as connection:
    connection.execute(text("ALTER TABLE purchases ALTER COLUMN user_id DROP NOT NULL"))
    connection.execute(text("ALTER TABLE purchases ALTER COLUMN pin_code DROP NOT NULL"))
    connection.execute(text("ALTER TABLE purchases ALTER COLUMN expires_at DROP NOT NULL"))
    connection.execute(text("ALTER TABLE purchases ADD COLUMN IF NOT EXISTS issued_at TIMESTAMP WITH TIME ZONE"))

with SessionLocal() as db:
    PlanService.seed_default_plans(db)
    ensure_self_order_devices(db)

print("Database created and default plans seeded successfully.")
