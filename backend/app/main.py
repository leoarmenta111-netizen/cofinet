from fastapi import FastAPI
from app.api.plans import router as plans_router
from app.api.branches import router as branches_router
from app.api.guest_purchases import router as guest_purchases_router
from app.api.purchases import router as purchases_router
from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.payments import router as payments_router
from app.api.admin import router as admin_router
from app.api.pins import router as pins_router
from app.api.memberships import router as memberships_router
from app.api.pos_catalog import router as pos_catalog_router
from app.api.pos_orders import router as pos_orders_router
from app.api.pos_receipts import router as pos_receipts_router
from app.api.admin_pos_sales import router as admin_pos_sales_router
from app.api.admin_pos_catalog import router as admin_pos_catalog_router
from app.api.admin_pos_receipts import router as admin_pos_receipts_router
from app.api.admin_pos_customers import router as admin_pos_customers_router
from app.api.pos_customers import router as pos_customers_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(

    title=settings.APP_NAME,

    version=settings.APP_VERSION,

    description="Backend API for CofiNet+ Captive Portal"

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans_router)
app.include_router(branches_router)
app.include_router(guest_purchases_router)
app.include_router(purchases_router)
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(pins_router)
app.include_router(memberships_router)
app.include_router(pos_catalog_router)
app.include_router(pos_orders_router)
app.include_router(pos_receipts_router)
app.include_router(admin_pos_sales_router)
app.include_router(admin_pos_catalog_router)
app.include_router(admin_pos_receipts_router)
app.include_router(admin_pos_customers_router)
app.include_router(pos_customers_router)

@app.get("/")
async def root():
    return {
        "project": "CofiNet+",
        "status": "online",
        "version": settings.APP_VERSION
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }
