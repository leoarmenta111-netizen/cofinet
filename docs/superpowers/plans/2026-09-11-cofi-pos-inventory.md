# COFI POS Inventory Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auditable per-branch finished-product inventory with strict online stock enforcement, offline resilience, idempotent movements, Admin adjustments, and full-sale reversals.

**Architecture:** Inventory uses Inventory Item + branch Balance + immutable Movement ledger. Online checkout validates and deducts stock in the same transaction as the paid order. Offline replay uses a separate sync endpoint and may expose negative stock as REVIEW.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, pytest, vanilla JavaScript, IndexedDB, HTML/CSS, Node 22 through Docker.

**Spec:** `docs/superpowers/specs/2026-09-11-cofi-pos-inventory-design.md`

## Global Constraints

- Existing products remain untracked after migration.
- Inventory is branch-specific.
- Phase 1 UI uses whole pieces; database quantities use decimal-capable numeric fields.
- Every stock mutation creates an immutable movement.
- Never change quantity_on_hand without its movement in the same transaction.
- Online sales cannot make tracked inventory negative.
- Offline replay may make inventory negative.
- Negative stock = REVIEW and blocks new sales.
- Zero stock = OUT_OF_STOCK and blocks new sales.
- Low stock remains sellable.
- SALE and SALE_REVERSAL are idempotent.
- PosBranchProduct.is_available remains independent from inventory.
- Modifiers do not consume inventory in Phase 1.
- Recipes, ingredients, transfers, suppliers, purchasing and partial refunds are out of scope.
- Inventory mutations require require_super_admin.
- Do not install Node on the host.
- Do not use git add .
- Keep the batch-PIN stash untouched.
- Do not use docker compose down, down -v, or production database initialization.

---

### Task 1: Inventory persistence foundation

**Files:**
- Create: `backend/app/models/pos_inventory.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260911_0001_pos_inventory_phase1.py`
- Create: `backend/tests/test_pos_inventory_models.py`

**Interfaces:**
- Produces `PosInventoryItem`.
- Produces `PosInventoryBalance`.
- Produces `PosInventoryMovement`.
- One Phase 1 inventory item per finished product.
- One balance per branch + inventory item.
- Automatic movement idempotency keys are unique.

- [ ] **Step 1: Write failing model tests**

Create tests proving:

```text
PosInventoryItem product_id is unique
PosInventoryBalance (branch_id, inventory_item_id) is unique
low_stock_threshold cannot be negative
quantity_on_hand may be negative
movement quantity_delta and balance_after preserve Decimal values
idempotency_key rejects duplicates when present
```

Keep inventory-specific fixtures inside this test file.

- [ ] **Step 2: Run Task 1 RED**

```bash
cd backend
python -m pytest tests/test_pos_inventory_models.py -q
```

Expected: FAIL because `app.models.pos_inventory` does not exist.

- [ ] **Step 3: Implement `PosInventoryItem`**

Fields:

```text
id Integer PK
product_id FK pos_products.id RESTRICT, nullable for future ingredients
name String(160), required
unit_code String(16), default EA
is_active Boolean, default true
created_at
updated_at
```

Constraints:

```text
UNIQUE product_id
unit_code IN (EA)
```

- [ ] **Step 4: Implement `PosInventoryBalance`**

Fields:

```text
id Integer PK
branch_id FK branches.id RESTRICT
inventory_item_id FK pos_inventory_items.id RESTRICT
quantity_on_hand Numeric(14,3), default 0
low_stock_threshold Numeric(14,3), default 0
is_tracked Boolean, default false
updated_at
```

Constraints:

```text
UNIQUE(branch_id, inventory_item_id)
low_stock_threshold >= 0
```

Do not constrain quantity_on_hand >= 0.

- [ ] **Step 5: Implement `PosInventoryMovement`**

Fields:

```text
id Integer PK
branch_id FK branches.id RESTRICT
inventory_item_id FK pos_inventory_items.id RESTRICT
movement_type String(32)
quantity_delta Numeric(14,3)
balance_after Numeric(14,3)
order_id nullable FK pos_orders.id SET NULL
order_item_id nullable FK pos_order_items.id SET NULL
idempotency_key String(180), nullable
note Text, nullable
created_by_admin_id nullable FK admins.id SET NULL
created_at
```

Allowed movement types:

```text
INITIAL
RECEIPT
SALE
SALE_REVERSAL
WASTE
ADJUSTMENT
```

Add UNIQUE(idempotency_key).
Normal movements are never edited or deleted; corrections use compensating movements.

- [ ] **Step 6: Export inventory models**

Modify `backend/app/models/__init__.py` so SQLAlchemy metadata imports all three inventory models.

- [ ] **Step 7: Create Alembic migration**

Create `backend/alembic/versions/20260911_0001_pos_inventory_phase1.py`.

Migration metadata:

```text
revision = 20260911_0001
down_revision = 20260908_0002
```

Upgrade order:

```text
1. pos_inventory_items
2. pos_inventory_balances
3. pos_inventory_movements
```

Downgrade in reverse order.

Create the same checks, unique constraints, foreign keys and indexes as the SQLAlchemy models.

Do not seed balances.
Do not turn tracking on for existing products.
Do not fabricate historical inventory movements.

- [ ] **Step 8: Run Task 1 GREEN**

```bash
cd backend
python -m pytest tests/test_pos_inventory_models.py -q
```

Expected: PASS.

- [ ] **Step 9: Verify migration chain**

Run Alembic inside the existing backend runtime/container, not on the host:

```bash
alembic heads
alembic history -r 20260908_0002:20260911_0001
```

Expected:

```text
20260911_0001 (head)
```

- [ ] **Step 10: Commit Task 1**

```bash
git add \
  backend/app/models/pos_inventory.py \
  backend/app/models/__init__.py \
  backend/alembic/versions/20260911_0001_pos_inventory_phase1.py \
  backend/tests/test_pos_inventory_models.py

git commit -m "feat(pos): add inventory persistence foundation"
```

---

### Task 2: Inventory service and movement invariants

**Files:**
- Create: `backend/app/services/pos_inventory_service.py`
- Create: `backend/tests/test_pos_inventory_service.py`

**Interfaces:**
- Produces `PosInventoryService.status_for(...)`.
- Produces `configure_tracking(...)`.
- Produces `record_receipt(...)`.
- Produces `record_waste(...)`.
- Produces `adjust_count(...)`.
- Produces `apply_sale(...)`.
- Produces `reverse_sale(...)`.
- Order and Admin code must call this service instead of mutating balances directly.

- [ ] **Step 1: Write failing status tests**

Required cases:

```text
tracked=false -> UNTRACKED
quantity < 0 -> REVIEW
quantity == 0 -> OUT_OF_STOCK
0 < quantity <= threshold -> LOW_STOCK
quantity > threshold -> AVAILABLE
```

Use Decimal values in every quantity assertion.

- [ ] **Step 2: Write failing movement tests**

Prove this sequence:

```text
first enable with initial 10 -> INITIAL +10, balance 10
receipt 5 -> RECEIPT +5, balance 15
waste 2 -> WASTE -2, balance 13
physical count 9 -> ADJUSTMENT -4, balance 9
```

Also prove:

```text
same SALE idempotency key twice -> one SALE movement
same SALE_REVERSAL key twice -> one reversal movement
strict sale greater than stock -> HTTP 409 and unchanged balance
offline sale may make balance negative
Branch A mutation does not change Branch B
```

- [ ] **Step 3: Run Task 2 RED**

```bash
cd backend
python -m pytest tests/test_pos_inventory_service.py -q
```

Expected: FAIL because `PosInventoryService` does not exist.

- [ ] **Step 4: Implement inventory status**

Use exact precedence:

```python
ZERO = Decimal("0")

if not tracked:
    return "UNTRACKED"
if quantity_on_hand < ZERO:
    return "REVIEW"
if quantity_on_hand == ZERO:
    return "OUT_OF_STOCK"
if quantity_on_hand <= threshold:
    return "LOW_STOCK"
return "AVAILABLE"
```

- [ ] **Step 5: Implement one private movement primitive**

Signature:

```python
@classmethod
def _apply_movement(
    cls,
    db,
    *,
    balance,
    movement_type,
    quantity_delta,
    order_id=None,
    order_item_id=None,
    idempotency_key=None,
    note=None,
    created_by_admin_id=None,
):
```

Behavior:

```text
re-query the exact balance by balance.id using SELECT ... FOR UPDATE
if idempotency_key already exists -> return existing movement
calculate balance_after from the locked balance
insert PosInventoryMovement
set locked balance.quantity_on_hand = balance_after
flush
return movement
```

Do not call db.commit() inside `_apply_movement()`.

- [ ] **Step 6: Implement tracking configuration**

`configure_tracking()` must:

```text
create PosInventoryItem on first use
create branch balance on first use
first enable requires initial_quantity >= 0
first enable sets threshold and is_tracked=true
first enable creates one INITIAL movement
disable sets is_tracked=false and preserves quantity/history
re-enable preserves existing quantity and updates threshold
```

The first INITIAL movement must be created through the same movement primitive used by every other stock change.

- [ ] **Step 7: Implement manual inventory movements**

Required signatures:

```python
record_receipt(
    db,
    *,
    balance,
    quantity,
    note,
    admin_id,
)

record_waste(
    db,
    *,
    balance,
    quantity,
    note,
    admin_id,
)

adjust_count(
    db,
    *,
    balance,
    physical_quantity,
    note,
    admin_id,
)
```

Rules:

```text
RECEIPT requires quantity > 0
WASTE requires quantity > 0 and a nonblank note
WASTE stores negative quantity_delta
ADJUSTMENT requires a nonblank note
ADJUSTMENT delta = physical_quantity - current quantity_on_hand
physical count may be zero
```

- [ ] **Step 8: Implement strict and offline SALE application**

Signature:

```python
apply_sale(
    db,
    *,
    order,
    allow_negative: bool,
)
```

For each order item, resolve the tracked balance for the exact order branch.

Use deterministic key:

```python
key = (
    f"sale:{order.order_uuid}:"
    f"{order_item.id}:{inventory_item.id}"
)
```

For strict online mode:

```text
lock the relevant balance
if quantity_on_hand < requested quantity -> raise HTTP 409
do not create a movement
do not modify the balance
```

For offline replay mode:

```text
allow the SALE movement even when resulting quantity becomes negative
negative balance becomes REVIEW through status_for()
```

SALE delta:

```python
-Decimal(order_item.quantity)
```

Untracked products create no inventory movement.

- [ ] **Step 9: Implement SALE reversal**

Signature:

```python
reverse_sale(
    db,
    *,
    order,
    note=None,
    admin_id=None,
)
```

For each original SALE movement belonging to the order, create a compensating SALE_REVERSAL.

Use deterministic key:

```python
key = (
    f"sale-reversal:{order.order_uuid}:"
    f"{sale.order_item_id}:{sale.inventory_item_id}"
)
```

Delta:

```python
quantity_delta = -sale.quantity_delta
```

Each SALE_REVERSAL passes `note=note` and `created_by_admin_id=admin_id` to `_apply_movement()`.

If the reversal already exists, reuse it and do not change stock again.

- [ ] **Step 10: Run Task 2 GREEN**

```bash
cd backend
python -m pytest tests/test_pos_inventory_service.py -q
```

Expected: PASS.

- [ ] **Step 11: Commit Task 2**

```bash
git add \
  backend/app/services/pos_inventory_service.py \
  backend/tests/test_pos_inventory_service.py

git commit -m "feat(pos): add inventory movement service"
```

---

### Task 3: Admin Inventory API

**Files:**
- Create: `backend/app/schemas/admin_pos_inventory.py`
- Create: `backend/app/api/admin_pos_inventory.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_admin_pos_inventory.py`

**Interfaces:**
- GET `/admin/pos/inventory`
- GET `/admin/pos/inventory/{item_id}`
- GET `/admin/pos/inventory/{item_id}/movements`
- PUT `/admin/pos/inventory/products/{product_id}/branches/{branch_code}`
- POST `/admin/pos/inventory/{item_id}/receipt`
- POST `/admin/pos/inventory/{item_id}/waste`
- POST `/admin/pos/inventory/{item_id}/adjust`

- [ ] **Step 1: Write failing authorization tests**

Unauthenticated inventory mutations must return 401.

Example:

```python
response = client.post(
    f"/admin/pos/inventory/{item_id}/receipt",
    json={
        "branch_code": branch.code,
        "quantity": "5",
        "note": "Compra semanal",
    },
)
assert response.status_code == 401
```

Authenticated SUPER_ADMIN requests must succeed.

Use the existing `super_headers` fixture.

- [ ] **Step 2: Write failing behavior tests**

Cover:

```text
list inventory filtered by branch
detail returns exact branch balance
movement history ordered newest first
first tracking enable creates INITIAL exactly once
disabling tracking preserves quantity and history
re-enabling preserves quantity
receipt increases stock
waste decreases stock
adjustment sets stock to physical count through delta movement
manual mutation on wrong branch/item combination is rejected
```

- [ ] **Step 3: Run Task 3 RED**

```bash
cd backend
python -m pytest tests/test_admin_pos_inventory.py -q
```

Expected: FAIL because Admin inventory schemas/routes do not exist.

- [ ] **Step 4: Create tracking configuration schema**

```python
class AdminInventoryTrackingUpdate(BaseModel):
    is_tracked: bool
    low_stock_threshold: Decimal = Field(ge=0)
    initial_quantity: Decimal | None = Field(
        default=None,
        ge=0,
    )
```

`initial_quantity` is required by service logic only for first enable.

- [ ] **Step 5: Create manual movement request schemas**

```python
class AdminInventoryReceiptCreate(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class AdminInventoryWasteCreate(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    quantity: Decimal = Field(gt=0)
    note: str = Field(min_length=1, max_length=500)


class AdminInventoryAdjustmentCreate(BaseModel):
    branch_code: str = Field(min_length=1, max_length=50)
    physical_quantity: Decimal
    note: str = Field(min_length=1, max_length=500)
```

- [ ] **Step 6: Create response schemas**

Inventory row response exposes:

```text
item_id
product_id
product_name
branch_id
branch_code
branch_name
is_tracked
quantity_on_hand
low_stock_threshold
status
updated_at
```

Movement response exposes:

```text
id
movement_type
quantity_delta
balance_after
order_id
order_item_id
order_uuid
folio
note
created_by_admin_id
created_at
```

- [ ] **Step 7: Create Admin inventory router**

Create:

```python
router = APIRouter(
    prefix="/admin/pos/inventory",
    tags=["Admin POS Inventory"],
)
```

Every endpoint must require:

```python
_admin: Admin = Depends(require_super_admin)
```

Use `_admin.id` for manual movement audit ownership.

List endpoint accepts `branch_code` as an optional query filter.

Detail and movement endpoints must verify the requested item belongs to the requested branch context rather than returning another branch balance.

- [ ] **Step 8: Implement tracking configuration endpoint**

Route:

```text
PUT /admin/pos/inventory/products/{product_id}/branches/{branch_code}
```

Call `PosInventoryService.configure_tracking(...)`.

Rules:

```text
404 product missing
404 branch missing
first enable without initial_quantity -> 422
initial enable creates exactly one INITIAL movement
re-enable must not create a second INITIAL movement
```

- [ ] **Step 9: Implement manual movement endpoints**

Routes:

```text
POST /admin/pos/inventory/{item_id}/receipt
POST /admin/pos/inventory/{item_id}/waste
POST /admin/pos/inventory/{item_id}/adjust
```

Each route:

```text
resolve branch from branch_code
resolve exact balance for item + branch
404 when balance does not exist
call inventory service
commit once at API/service transaction boundary
return refreshed inventory row
```

- [ ] **Step 10: Register router in FastAPI**

In `backend/app/main.py` add:

```python
from app.api.admin_pos_inventory import (
    router as admin_pos_inventory_router,
)
```

and:

```python
app.include_router(admin_pos_inventory_router)
```

Place it beside the existing Admin POS routers.

- [ ] **Step 11: Run Task 3 GREEN**

```bash
cd backend
python -m pytest tests/test_admin_pos_inventory.py -q
```

Expected: PASS.

- [ ] **Step 12: Commit Task 3**

```bash
git add \
  backend/app/schemas/admin_pos_inventory.py \
  backend/app/api/admin_pos_inventory.py \
  backend/app/main.py \
  backend/tests/test_admin_pos_inventory.py

git commit -m "feat(pos): add admin inventory api"
```

---

### Task 4: Catalog inventory contract

**Files:**
- Modify: `backend/app/schemas/pos_catalog.py`
- Modify: `backend/app/services/pos_catalog_service.py`
- Modify: `backend/app/schemas/admin_pos_catalog.py`
- Modify: `backend/app/services/admin_pos_catalog_service.py`
- Create: `backend/tests/test_pos_catalog_inventory.py`

**Interfaces:**
- Public POS product response gains `inventory`.
- Admin branch-product response gains read-only inventory metadata.
- Manual `PosBranchProduct.is_available` semantics remain unchanged.
- Zero-stock products remain in the catalog so the POS can show `Agotado`.

- [ ] **Step 1: Write failing public catalog tests**

For an untracked product assert:

```python
assert product_json["inventory"] == {
    "tracked": False,
    "quantity_available": None,
    "low_stock_threshold": None,
    "status": "UNTRACKED",
}
```

For a tracked product with stock zero assert:

```python
assert product_json["inventory"]["tracked"] is True
assert product_json["inventory"]["quantity_available"] == "0.000"
assert product_json["inventory"]["status"] == "OUT_OF_STOCK"
```

Also assert the zero-stock product is still present in the public catalog response.

- [ ] **Step 2: Write failing branch-isolation tests**

Prove:

```text
same product may have different stock in two branches
branch A catalog exposes only branch A inventory balance
branch B inventory never leaks into branch A response
untracked branch remains UNTRACKED even if another branch tracks the product
```

- [ ] **Step 3: Run Task 4 RED**

```bash
cd backend
python -m pytest tests/test_pos_catalog_inventory.py -q
```

Expected: FAIL because inventory fields are not present in catalog schemas.

- [ ] **Step 4: Add public inventory response schema**

In `backend/app/schemas/pos_catalog.py` add:

```python
class PosCatalogInventoryResponse(BaseModel):
    tracked: bool
    quantity_available: Decimal | None
    low_stock_threshold: Decimal | None
    status: Literal[
        "UNTRACKED",
        "AVAILABLE",
        "LOW_STOCK",
        "OUT_OF_STOCK",
        "REVIEW",
    ]
```

Add to the existing product response:

```python
inventory: PosCatalogInventoryResponse
```

- [ ] **Step 5: Enrich public catalog service**

For every branch product:

```text
resolve inventory item by product_id
resolve balance by current branch_id + inventory_item_id
if no balance or balance.is_tracked=false -> UNTRACKED
if tracked -> expose quantity, threshold and status_for(...)
```

Keep the existing manual availability filter:

```python
PosBranchProduct.is_available.is_(True)
```

Do not filter a product merely because inventory is zero or negative.

- [ ] **Step 6: Add read-only inventory metadata to Admin catalog schema**

Extend `AdminPosBranchSettingResponse` with:

```text
inventory_tracked: bool
inventory_quantity_on_hand: Decimal | None
inventory_low_stock_threshold: Decimal | None
inventory_status: UNTRACKED | AVAILABLE | LOW_STOCK | OUT_OF_STOCK | REVIEW
```

Do not add inventory mutation fields to `AdminPosBranchProductUpdate`.

- [ ] **Step 7: Enrich Admin catalog service**

For each product branch setting:

```text
resolve inventory item by product_id
resolve balance by branch_id + inventory_item_id
if no tracked balance -> inventory_tracked=false and status UNTRACKED
if tracked -> expose quantity, threshold and PosInventoryService.status_for(...)
```

Keep existing `price`, `is_available` and `sort_order` behavior unchanged.

- [ ] **Step 8: Add Admin catalog assertions**

Extend `test_pos_catalog_inventory.py` to prove:

```text
Admin catalog reports branch-specific stock
Admin catalog reports UNTRACKED when tracking is disabled
Admin catalog still reports manual is_available separately
zero-stock tracked product is present and OUT_OF_STOCK
negative tracked product is present and REVIEW
```

- [ ] **Step 9: Run Task 4 GREEN**

```bash
cd backend
python -m pytest tests/test_pos_catalog_inventory.py -q
```

Expected: PASS.

- [ ] **Step 10: Run existing catalog regression tests**

Run the repository catalog tests that already exercise public and Admin catalog behavior.

At minimum include:

```bash
cd backend
python -m pytest \
  tests/test_admin_pos_catalog_import_images.py \
  tests/test_pos_order_management.py \
  tests/test_pos_catalog_inventory.py \
  -q
```

If either existing filename differs in the repository, use the actual current catalog test filename rather than creating a duplicate test file.

- [ ] **Step 11: Commit Task 4**

```bash
git add \
  backend/app/schemas/pos_catalog.py \
  backend/app/services/pos_catalog_service.py \
  backend/app/schemas/admin_pos_catalog.py \
  backend/app/services/admin_pos_catalog_service.py \
  backend/tests/test_pos_catalog_inventory.py

git commit -m "feat(pos): expose branch inventory in catalog"
```

---

### Task 5: Paid-order inventory integration and refunds

**Files:**
- Modify: `backend/app/services/pos_order_service.py`
- Modify: `backend/app/api/pos_orders.py`
- Modify: `backend/app/schemas/admin_pos_sales.py`
- Modify: `backend/app/services/admin_pos_sales_service.py`
- Modify: `backend/app/api/admin_pos_sales.py`
- Create: `backend/tests/test_pos_inventory_order_integration.py`

**Interfaces:**
- Existing `POST /pos/orders` remains strict online checkout.
- New `POST /pos/orders/sync` replays already-paid offline sales.
- `PosOrderService.create(...)` uses strict inventory enforcement.
- `PosOrderService.sync_offline(...)` permits negative inventory.
- Admin adds `POST /admin/pos/sales/{order_uuid}/refund`.
- Refund is full-sale only in Phase 1.

- [ ] **Step 1: Write failing strict-online sale test**

Setup:

```text
tracked product
branch stock = 3
order quantity = 2
```

Assert:

```text
POST /pos/orders succeeds
order payment_status = PAID
inventory balance = 1
exactly one SALE movement exists
SALE movement references persisted order and order item
```

- [ ] **Step 2: Write failing insufficient-stock test**

Setup:

```text
tracked product
branch stock = 1
order quantity = 2
```

Assert:

```text
POST /pos/orders returns HTTP 409
no new PosOrder remains persisted
no new PosPayment remains persisted
no SALE movement exists
balance remains 1
```

The transaction must roll back completely.

- [ ] **Step 3: Write failing idempotent retry test**

Send the exact same `order_uuid` twice.

Assert:

```text
second request returns the existing order
only one order exists
only one payment exists
only one SALE movement exists
inventory was deducted once
```

- [ ] **Step 4: Write failing offline replay test**

Setup server stock at zero and send an already-paid offline order through:

```text
POST /pos/orders/sync
```

Assert:

```text
request succeeds
order is persisted once
payment is persisted once
SALE movement is persisted once
balance becomes -1
inventory status becomes REVIEW
```

Repeat the exact same sync payload and assert that no count changes.

- [ ] **Step 5: Write failing untracked-product regression test**

Assert an existing untracked product still completes through `POST /pos/orders` with no inventory movement.

- [ ] **Step 6: Write failing refund/reversal tests**

Create a paid tracked sale that changes stock from 5 to 3.

Call:

```text
POST /admin/pos/sales/{order_uuid}/refund
```

with a nonblank reason.

Assert:

```text
payment_status becomes REFUNDED
order status becomes CANCELLED
balance returns to 5
exactly one SALE_REVERSAL exists
SALE_REVERSAL references the original order/order item
```

Call refund again and assert stock remains 5 and only one reversal exists.

- [ ] **Step 7: Run Task 5 RED**

```bash
cd backend
python -m pytest tests/test_pos_inventory_order_integration.py -q
```

Expected: FAIL because order creation does not yet apply inventory and sync/refund endpoints do not exist.

- [ ] **Step 8: Refactor paid-order creation behind one internal method**

Keep the existing public strict entry point:

```python
@classmethod
def create(
    cls,
    db: Session,
    payload: PosOrderCreate,
) -> PosOrderResponse:
    return cls._create_paid_order(
        db,
        payload,
        allow_inventory_negative=False,
    )
```

Add the offline replay entry point:

```python
@classmethod
def sync_offline(
    cls,
    db: Session,
    payload: PosOrderCreate,
) -> PosOrderResponse:
    return cls._create_paid_order(
        db,
        payload,
        allow_inventory_negative=True,
    )
```

Move the current creation body into:

```python
@classmethod
def _create_paid_order(
    cls,
    db: Session,
    payload: PosOrderCreate,
    *,
    allow_inventory_negative: bool,
) -> PosOrderResponse:
```

Preserve all current behavior for:

```text
order_uuid idempotency
folio uniqueness
customer lookup
branch normalization
catalog/product validation
modifier validation
frozen receipt snapshot
pricing
payment persistence
station routing
loyalty/customer linkage
```

- [ ] **Step 9: Apply inventory inside the existing order transaction**

After order items have been persisted and flushed so every order item has an ID, but before the final commit, call:

```python
PosInventoryService.apply_sale(
    db,
    order=order,
    allow_negative=allow_inventory_negative,
)
```

The existing final `db.commit()` must remain the single commit boundary for:

```text
order
order items
payment
receipt snapshot
customer/loyalty side effects
inventory SALE movements
inventory balances
```

If strict inventory validation raises HTTP 409, roll back the transaction before returning the error.

Do not commit inventory separately.

- [ ] **Step 10: Preserve order-level idempotency before inventory mutation**

The existing lookup by `PosOrder.order_uuid` must remain before new order creation.

If the order already exists:

```text
return the existing response
do not create another payment
do not call apply_sale again for a second deduction
```

Movement-level idempotency remains a second safety layer.

- [ ] **Step 11: Add explicit offline replay route**

In `backend/app/api/pos_orders.py` add a static route before any `/{order_uuid}` route:

```python
@router.post(
    "/sync",
    response_model=PosOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def sync_pos_order(
    payload: PosOrderCreate,
    db: Session = Depends(get_db),
) -> PosOrderResponse:
    return PosOrderService.sync_offline(
        db=db,
        payload=payload,
    )
```

`POST /pos/orders` remains strict.
`POST /pos/orders/sync` is only for replaying an already-paid local sale.

- [ ] **Step 12: Verify strict and replay transaction behavior**

Run only the order integration cases for:

```text
online stock success
online insufficient stock rollback
online duplicate order_uuid
offline negative stock replay
offline duplicate replay
untracked product regression
```

Command:

```bash
cd backend
python -m pytest tests/test_pos_inventory_order_integration.py -q -k "not refund"
```

Expected: all non-refund Task 5 cases PASS.

- [ ] **Step 13: Add full-sale refund request contract**

In `backend/app/schemas/admin_pos_sales.py` add:

```python
class AdminPosRefundRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
```

Phase 1 supports full-sale refund only.

- [ ] **Step 14: Implement atomic refund service**

Add this service contract:

```python
@classmethod
def refund_sale(
    cls,
    db: Session,
    *,
    order_uuid: str,
    reason: str,
    admin: Admin,
) -> AdminPosSaleDetailResponse:
```

Required behavior:

```text
resolve order by order_uuid using SELECT ... FOR UPDATE
404 if order does not exist
if payment_status == REFUNDED -> return existing refunded sale without another reversal
require current payment_status == PAID
call PosInventoryService.reverse_sale(
    db,
    order=order,
    note=reason,
    admin_id=admin.id
)
set order.payment_status = REFUNDED
set order.status = CANCELLED
persist reason in SALE_REVERSAL.note
persist refunding admin in SALE_REVERSAL.created_by_admin_id
commit exactly once
refresh and return sale detail
```

The inventory reversal and refund status changes must share the same transaction.

- [ ] **Step 15: Add protected Admin refund endpoint**

In `backend/app/api/admin_pos_sales.py` expose:

```text
POST /admin/pos/sales/{order_uuid}/refund
```

The route must require the existing SUPER_ADMIN dependency.

Pass the authenticated Admin identity and validated refund reason to `refund_sale(...)`.

- [ ] **Step 16: Prove refund idempotency**

Run the refund integration cases and assert:

```text
first refund restores stock exactly once
payment_status becomes REFUNDED
order.status becomes CANCELLED
one SALE_REVERSAL exists per original SALE movement
second identical refund does not change balance
second identical refund does not create another reversal
```

- [ ] **Step 17: Run all Task 5 tests GREEN**

```bash
cd backend
python -m pytest tests/test_pos_inventory_order_integration.py -q
```

Expected: PASS.

- [ ] **Step 18: Run existing order regressions**

Run the existing POS order, station, receipt and customer-link tests:

```bash
cd backend
python -m pytest \
  tests/test_pos_order_management.py \
  tests/test_pos_station_api.py \
  tests/test_pos_station_routing.py \
  tests/test_pos_receipt_snapshots.py \
  tests/test_pos_customer_order_link.py \
  -q
```

If an existing filename differs, use the actual existing test filename; do not create a duplicate merely to satisfy this command.

- [ ] **Step 19: Commit Task 5**

```bash
git add \
  backend/app/services/pos_order_service.py \
  backend/app/api/pos_orders.py \
  backend/app/schemas/admin_pos_sales.py \
  backend/app/services/admin_pos_sales_service.py \
  backend/app/api/admin_pos_sales.py \
  backend/tests/test_pos_inventory_order_integration.py

git commit -m "feat(pos): integrate inventory with paid sales"
```

---

### Task 6: POS local inventory accounting and availability UX

**Files:**
- Modify: `pos/js/orders-local.js`
- Modify: `pos/js/app.js`
- Modify: `pos/index.html`
- Create: `pos/tests/inventory-local.test.js`
- Create: `pos/tests/inventory-ui.test.js`

**Interfaces:**
- Extends `window.CofiPosOrdersLocal` with pure inventory helpers.
- Produces `pendingInventoryUsage(localOrders, branchCode)`.
- Produces `effectiveInventory(product, pendingUsage)`.
- Produces `inventoryStatus(product, pendingUsage)`.
- Produces `canSellProduct(product, pendingUsage)`.
- POS must subtract unsynced local paid sales from cached server stock.

- [ ] **Step 1: Write failing pending-usage tests**

Create `pos/tests/inventory-local.test.js`.

Prove:

```text
PENDING_SYNC sale in current branch contributes product quantity
SYNCED sale does not contribute pending quantity
pending sale from another branch does not contribute
multiple pending sales for same product are summed
different products remain separate
```

Expected result type:

```javascript
const usage = api.pendingInventoryUsage(localOrders, "nuevo-vallarta");

assert.equal(usage.get(10), 3);
assert.equal(usage.get(20), 1);
```

- [ ] **Step 2: Write failing effective-stock tests**

Tracked product example:

```javascript
const product = {
    id: 10,
    inventory: {
        tracked: true,
        quantity_available: "3.000",
        low_stock_threshold: "1.000",
        status: "AVAILABLE",
    },
};

const pending = new Map([[10, 2]]);

assert.equal(
    api.effectiveInventory(product, pending),
    1
);
```

Also prove:

```text
untracked product -> effectiveInventory returns null
cached 1 minus pending 1 -> 0
cached 1 minus pending 2 -> -1
no pending usage -> cached quantity
```

- [ ] **Step 3: Write failing local-status tests**

Expected precedence after pending deductions:

```text
untracked -> UNTRACKED
effective < 0 -> REVIEW
effective == 0 -> OUT_OF_STOCK
0 < effective <= low_stock_threshold -> LOW_STOCK
effective > threshold -> AVAILABLE
```

`canSellProduct(...)` returns false only for tracked REVIEW or OUT_OF_STOCK products.

- [ ] **Step 4: Run Task 6 helper tests RED**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test pos/tests/inventory-local.test.js
```

Expected: FAIL because the inventory helpers do not exist.

- [ ] **Step 5: Implement pending local inventory usage**

Extend the existing `CofiPosOrdersLocal` module without creating a second IndexedDB store.

`pendingInventoryUsage(localOrders, branchCode)` must:

```text
consider only sync_status == PENDING_SYNC
consider only exact branch_code
read items from localOrder.payload.items
sum Number(item.quantity) by Number(item.product_id)
return Map<productId, quantity>
```

- [ ] **Step 6: Implement effective inventory helper**

`effectiveInventory(product, pendingUsage)` must:

```text
return null when product.inventory.tracked is false
parse quantity_available as Number
subtract pendingUsage.get(product.id) or zero
return the numeric result
```

- [ ] **Step 7: Implement local inventory status helper**

`inventoryStatus(product, pendingUsage)` uses effective stock and cached threshold.

Use exact status order:

```text
UNTRACKED
REVIEW
OUT_OF_STOCK
LOW_STOCK
AVAILABLE
```

- [ ] **Step 8: Run helper tests GREEN**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test pos/tests/inventory-local.test.js
```

Expected: PASS.

- [ ] **Step 9: Write failing POS inventory UI tests**

Create `pos/tests/inventory-ui.test.js`.

Assert the POS source supports these customer-facing states:

```text
Agotado
Stock bajo
Revisar inventario
```

Also prove:

```text
OUT_OF_STOCK product cannot be added to cart
REVIEW product cannot be added to cart
LOW_STOCK product remains sellable
AVAILABLE product remains sellable
UNTRACKED product keeps existing behavior
```

- [ ] **Step 10: Load pending inventory usage when catalog/cart state changes**

In `pos/js/app.js`, whenever catalog inventory availability must be recalculated:

```text
load local orders for the active branch
build pendingInventoryUsage(...)
derive effective stock from cached catalog quantity minus pending unsynced sales
```

Do not persist a second stock counter in IndexedDB.

- [ ] **Step 11: Enforce inventory before add-to-cart**

Before increasing cart quantity for a tracked product:

```text
calculate effective stock
include quantity already present in the current cart
block when requested cart quantity would exceed effective stock
```

Show a short customer-facing error instead of silently failing.

Use:

```text
Producto agotado
```

for zero stock, and:

```text
Inventario en revisión
```

for negative/REVIEW state.

- [ ] **Step 12: Render product inventory status**

On product cards:

```text
OUT_OF_STOCK -> Agotado
LOW_STOCK -> Stock bajo
REVIEW -> Revisar inventario
AVAILABLE -> no warning required
UNTRACKED -> no inventory warning
```

Do not hide zero-stock or REVIEW products from the product grid.

- [ ] **Step 13: Disable unavailable product interactions**

For OUT_OF_STOCK and REVIEW products:

```text
disable primary add action
prevent keyboard/click path from bypassing the disabled state
keep product visible
```

- [ ] **Step 14: Recalculate after local sale finalization**

After a sale becomes PENDING_SYNC locally:

```text
refresh pending local order count
recompute pending inventory usage
re-render product availability
```

This ensures the same offline terminal cannot oversell beyond its own cached stock.

- [ ] **Step 15: Run Task 6 UI tests GREEN**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
  pos/tests/inventory-local.test.js \
  pos/tests/inventory-ui.test.js
```

Expected: PASS.

- [ ] **Step 16: Run existing cart/offline regression tests**

Run the existing POS tests that cover cart and local-order behavior together with the new inventory tests.

At minimum:

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
  pos/tests/orders-local.test.js \
  pos/tests/receipt-offline.test.js \
  pos/tests/inventory-local.test.js \
  pos/tests/inventory-ui.test.js
```

Expected: PASS.

- [ ] **Step 17: Commit Task 6**

```bash
git add \
  pos/js/orders-local.js \
  pos/js/app.js \
  pos/index.html \
  pos/tests/inventory-local.test.js \
  pos/tests/inventory-ui.test.js

git commit -m "feat(pos): enforce local inventory availability"
```

---

### Task 7: Server-first online checkout with offline fallback

**Files:**
- Modify: `pos/js/api.js`
- Modify: `pos/js/db.js`
- Modify: `pos/js/sync.js`
- Modify: `pos/js/app.js`
- Modify: `pos/tests/orders-api.test.js`
- Create: `pos/tests/inventory-checkout.test.js`
- Modify: `pos/tests/receipt-offline.test.js`

**Interfaces:**
- `CofiPosAPI.createOrder(payload)` remains strict online checkout.
- Add `CofiPosAPI.syncOfflineOrder(payload)` for replay.
- Add `CofiPosDB.finalizeSyncedSale(...)` for a sale already committed by server.
- `CofiPosSync.syncPending()` uses the offline replay endpoint.
- Online checkout calls server before finalizing local success.
- Network failure reuses the exact frozen sale identity and falls back to PENDING_SYNC.

- [ ] **Step 1: Write failing API route tests**

Extend `pos/tests/orders-api.test.js`.

Prove:

```text
CofiPosAPI.createOrder(payload) -> POST /pos/orders
CofiPosAPI.syncOfflineOrder(payload) -> POST /pos/orders/sync
both send the original payload unchanged
```

- [ ] **Step 2: Write failing synced-local persistence test**

Add a DB test proving `finalizeSyncedSale(...)` atomically stores:

```text
local_orders row with sync_status = SYNCED
original payload
server_response
folio
receipt_snapshot
synced_at
receipt record
```

It must not create a PENDING_SYNC event in `sync_queue`.

- [ ] **Step 3: Write failing online checkout boundary tests**

Create `pos/tests/inventory-checkout.test.js`.

For an online successful sale prove this order:

```text
freeze one order_uuid/payment_uuid/timestamp/folio/receipt snapshot
call CofiPosAPI.createOrder(payload)
only after server success persist local sale as SYNCED
do not enqueue PENDING_SYNC
clear/complete checkout normally
```

For an HTTP 409 from strict inventory validation prove:

```text
do not call finalizePaidSale
do not call finalizeSyncedSale
do not enqueue sync event
keep cart intact
show backend stock error
```

- [ ] **Step 4: Write failing network-fallback tests**

For a network failure or timeout after the immutable payload has been frozen, prove:

```text
do not generate a new order_uuid
do not generate a new payment_uuid
do not generate a new folio
do not rebuild receipt_snapshot
call finalizePaidSale with the exact same payload
leave sale PENDING_SYNC
show sale success as pending synchronization
```

Also prove:

```text
server createOrder succeeds
finalizeSyncedSale fails locally
do not create PENDING_SYNC
do not call createOrder a second time
do not generate another sale identity
continue with the already-confirmed server sale
```

For `navigator.onLine == false`, skip strict API creation and finalize the frozen sale locally immediately.

- [ ] **Step 5: Run Task 7 RED**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
  pos/tests/orders-api.test.js \
  pos/tests/inventory-checkout.test.js \
  pos/tests/receipt-offline.test.js
```

Expected: FAIL because syncOfflineOrder/finalizeSyncedSale/server-first checkout do not exist yet.

- [ ] **Step 6: Add explicit offline replay API client**

In `pos/js/api.js` add:

```javascript
function syncOfflineOrder(payload) {
    return request("/pos/orders/sync", {
        method: "POST",
        body: JSON.stringify(payload),
        timeout: 12000,
    });
}
```

Export `syncOfflineOrder` beside `createOrder`.

- [ ] **Step 7: Add `finalizeSyncedSale(...)` to IndexedDB layer**

Add a transaction that writes only the stores required for a server-confirmed sale.

Signature:

```javascript
async function finalizeSyncedSale({
    order_uuid,
    local_order,
    receipt_snapshot,
    server_response,
})
```

Persist `local_order.sync_status = "SYNCED"` and `synced_at` in the same transaction as the receipt.

Do not insert a `sync_queue` event.

Export it through `window.CofiPosDB`.

- [ ] **Step 8: Change pending replay to dedicated sync endpoint**

In `pos/js/sync.js` replace the replay call:

```javascript
window.CofiPosAPI.createOrder(event.payload)
```

with:

```javascript
window.CofiPosAPI.syncOfflineOrder(event.payload)
```

Preserve existing retry counters, terminal-id repair, local order update and SYNCED marking.

- [ ] **Step 9: Refactor `confirmPayment()` to server-first when online**

Keep the existing immutable-sale preparation exactly once:

```text
buildOrderPayload()
freeze order_uuid
freeze payment_uuid
freeze sold_at timestamp
generate folio
build receipt_snapshot
attach folio/snapshot/timestamps to payload
```

After the payload is fully frozen, branch on network state.

When `navigator.onLine` is true:

```text
call CofiPosAPI.createOrder(payload)
wait for strict backend response
only after success call CofiPosDB.finalizeSyncedSale(...)
set pendingSync = false
```

Do not call `finalizePaidSale(...)` before the strict server request succeeds.

- [ ] **Step 10: Keep HTTP business errors out of offline fallback**

If `CofiPosAPI.createOrder(...)` throws an HTTP/API error, including inventory HTTP 409:

```text
do not treat it as offline
do not enqueue the order
do not store a paid local sale
do not clear the cart
show the API error to the cashier
```

Use the existing API error classification already provided by `pos/js/api.js`.

The server request and local persistence must use separate error boundaries:

```javascript
let response;

try {
    response = await window.CofiPosAPI.createOrder(payload);
} catch (error) {
    if (error.isHttpError) throw error;

    await window.CofiPosDB.finalizePaidSale({
        order_uuid: payload.order_uuid,
        local_order: localOrder,
        receipt_snapshot: receiptSnapshot,
        sync_event: syncEvent,
    });

    pendingSync = true;
}

if (response) {
    try {
        await window.CofiPosDB.finalizeSyncedSale({
            order_uuid: payload.order_uuid,
            local_order: localOrder,
            receipt_snapshot: receiptSnapshot,
            server_response: response,
        });
    } catch (localError) {
        console.warn("Server sale confirmed; local copy failed");
    }

    pendingSync = false;
}
Only a non-HTTP failure from `createOrder()` may become PENDING_SYNC.

A `finalizeSyncedSale()` failure happens after the authoritative server sale already exists. It must never enqueue another offline sale, call `createOrder()` again, or regenerate the sale identity.

- [ ] **Step 11: Keep already-offline checkout local-first**

When `navigator.onLine` is false:

```text
skip CofiPosAPI.createOrder()
call finalizePaidSale(...) immediately
store PENDING_SYNC event
preserve exact frozen payload identity
pendingSync = true
```

- [ ] **Step 12: Prevent duplicate persistence after online success**

For a strict server-successful sale:

```text
one local_orders row
one receipt record
zero pending sync events for that order
sync_status = SYNCED
```

Do not call `syncPending()` merely to persist the sale that just succeeded online.

- [ ] **Step 13: Refresh catalog inventory after server changes**

After strict online sale success:

```text
reload current branch catalog from API
persist refreshed catalog using existing catalog cache path
rebuild local pending inventory usage
re-render products
```

After `syncPending()` successfully syncs one or more pending sales:

```text
refresh the current branch catalog once after the sync batch
recalculate local pending usage from any events still pending
re-render availability
```

Do not refresh once per individual queued order.

- [ ] **Step 14: Preserve checkout success behavior**

Both successful strict-online sales and accepted offline-local sales must still call the existing success UI with:

```text
folio
receipt_snapshot
offline/pendingSync state
```

Printing, ticket preview and New Sale behavior must remain unchanged.

- [ ] **Step 15: Run Task 7 tests GREEN**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
  pos/tests/orders-api.test.js \
  pos/tests/inventory-checkout.test.js \
  pos/tests/receipt-offline.test.js
```

Expected: PASS.

- [ ] **Step 16: Run complete POS regression suite**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test pos/tests/*.test.js
```

Expected: all POS tests PASS.

- [ ] **Step 17: Commit Task 7**

```bash
git add \
  pos/js/api.js \
  pos/js/db.js \
  pos/js/sync.js \
  pos/js/app.js \
  pos/tests/orders-api.test.js \
  pos/tests/inventory-checkout.test.js \
  pos/tests/receipt-offline.test.js

git commit -m "feat(pos): make online checkout inventory strict"
```

---

### Task 8: Inventory configuration inside Catalog Admin

**Files:**
- Modify: `admin/catalog.html`
- Create: `admin/tests/catalog-inventory.test.js`

**Interfaces:**
- Catalog Admin configures inventory tracking per product + branch.
- Uses `PUT /admin/pos/inventory/products/{product_id}/branches/{branch_code}`.
- Does not perform operational receipt, waste or count adjustment.
- Existing price, availability and sort-order editing remains unchanged.

- [ ] **Step 1: Write failing Catalog Admin inventory tests**

Create `admin/tests/catalog-inventory.test.js`.

Assert the catalog UI contains:

```text
Controlar inventario
Stock mínimo
Stock inicial
```

Assert configuration uses:

```text
PUT /admin/pos/inventory/products/{product_id}/branches/{branch_code}
```

Also prove inventory controls are branch-specific rather than global product fields.

- [ ] **Step 2: Write failing existing-balance UI tests**

For an already initialized tracked product, assert:

```text
current stock is displayed read-only
Stock inicial input is not offered as a way to overwrite current stock
Stock mínimo remains editable
Controlar inventario may be disabled/re-enabled
operational stock changes direct the Admin to Inventario
```

- [ ] **Step 3: Run Task 8 RED**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/catalog-inventory.test.js
```

Expected: FAIL because inventory controls do not exist in Catalog Admin.

- [ ] **Step 4: Add branch-level inventory controls**

Inside each existing product branch configuration render:

```text
[ ] Controlar inventario

Stock mínimo
[ 5 ]

Stock inicial
[ 20 ]
```

Show `Stock inicial` only when the product/branch inventory balance has never been initialized.

For an existing balance show:

```text
Stock actual: 18
```

as read-only information.

- [ ] **Step 5: Preserve manual product availability semantics**

The existing branch control:

```text
is_available
```

must remain independent from `inventory_tracked`.

Examples:

```text
is_available=false + stock 10 -> manually unavailable
is_available=true + stock 0 -> visible but Agotado in POS
is_available=true + inventory untracked -> existing POS behavior
```

- [ ] **Step 6: Save tracking configuration through dedicated API**

For first enable send:

```javascript
{
    is_tracked: true,
    low_stock_threshold: "5",
    initial_quantity: "20",
}
```

For an existing balance send:

```javascript
{
    is_tracked: true,
    low_stock_threshold: "5",
    initial_quantity: null,
}
```

For disable send:

```javascript
{
    is_tracked: false,
    low_stock_threshold: currentThreshold,
    initial_quantity: null,
}
```

Use the existing authenticated Admin request helper.

- [ ] **Step 7: Refresh catalog after successful configuration**

After the inventory API succeeds:

```text
reload Admin catalog
refresh inventory metadata
preserve selected product/branch when practical
show existing Admin success feedback
```

Do not locally invent a new stock balance after save; use the server response/refreshed catalog.

- [ ] **Step 8: Run Task 8 GREEN**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/catalog-inventory.test.js
```

Expected: PASS.

- [ ] **Step 9: Run existing Admin catalog regressions**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
  admin/tests/catalog*.test.js
```

Expected: all Catalog Admin tests PASS.

- [ ] **Step 10: Commit Task 8**

```bash
git add \
  admin/catalog.html \
  admin/tests/catalog-inventory.test.js

git commit -m "feat(admin): add product inventory settings"
```

---

### Task 9: Dedicated Inventory Admin workspace

**Files:**
- Create: `admin/inventory.html`
- Modify: `admin/admin.js`
- Create: `admin/tests/inventory-ui.test.js`

**Interfaces:**
- Adds SUPER_ADMIN navigation item `Inventario`.
- Consumes `GET /admin/pos/inventory`.
- Consumes `GET /admin/pos/inventory/{item_id}`.
- Consumes `GET /admin/pos/inventory/{item_id}/movements`.
- Daily stock operations stay on this page instead of Catalog Admin.

- [ ] **Step 1: Write failing navigation tests**

In `admin/tests/inventory-ui.test.js` assert SUPER_ADMIN navigation contains:

```javascript
["inventory", "inventory.html", "Inventario"]
```

Assert the non-SUPER_ADMIN PIN operator navigation does not contain Inventario.

- [ ] **Step 2: Write failing workspace structure tests**

Assert `admin/inventory.html` contains:

```text
Inventario
Productos controlados
Stock bajo
Agotados
Revisar inventario
Sucursal
Buscar producto
Estado
Entrada
Merma
Ajuste de conteo
Historial
```

Assert body uses:

```html
<body data-page="inventory" class="auth-pending">
```

- [ ] **Step 3: Write failing status/filter tests**

Prove the UI recognizes:

```text
AVAILABLE
LOW_STOCK
OUT_OF_STOCK
REVIEW
UNTRACKED
```

The main operational table shows tracked products only.

Search filters by product name or SKU.

Status filter supports at minimum:

```text
Todos
Stock bajo
Agotados
Revisar inventario
```

- [ ] **Step 4: Run Task 9 UI tests RED**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/inventory-ui.test.js
```

Expected: FAIL because `inventory.html` and the Admin nav item do not exist.

- [ ] **Step 5: Add Inventory navigation item**

In the existing SUPER_ADMIN `items` array inside `admin/admin.js`, add:

```javascript
["inventory", "inventory.html", "Inventario"],
```

Place it next to the other POS operational pages, after Catalog or Sales.

Do not add it to the PIN operator menu.

- [ ] **Step 6: Build Inventory page using the existing Admin shell**

Create `admin/inventory.html` using the same shared layout, header, navigation, authentication bootstrap and request helpers used by the current Admin pages.

Do not create a separate Admin framework or duplicated authentication flow.

Top workspace controls:

```text
Inventario
Sucursal selector
Buscar producto
Estado filter
```

- [ ] **Step 7: Add inventory summary metrics**

Render four summary cards:

```text
Productos controlados
Stock bajo
Agotados
Revisar inventario
```

Calculate them from the currently selected branch response.

Rules:

```text
Productos controlados = is_tracked true
Stock bajo = status LOW_STOCK
Agotados = status OUT_OF_STOCK
Revisar inventario = status REVIEW
```

- [ ] **Step 8: Add tracked inventory table**

Columns:

```text
Producto
SKU
Stock actual
Stock mínimo
Estado
```

Each row must retain `item_id` and branch context for loading detail/history.

Status labels:

```text
AVAILABLE -> Disponible
LOW_STOCK -> Stock bajo
OUT_OF_STOCK -> Agotado
REVIEW -> Revisar inventario
```

- [ ] **Step 9: Add branch/search/status filtering**

On branch change:

```text
fetch inventory for the selected branch
recalculate summary metrics
re-render table
clear stale selected-item detail
```

Search and status filters operate on the loaded branch inventory without mutating server data.

- [ ] **Step 10: Add selected-item detail panel**

When a row is selected, show:

```text
Producto
Sucursal
Stock actual
Stock mínimo
Estado
```

Provide action controls for:

```text
Entrada
Merma
Ajuste de conteo
Historial
```

Do not allow direct inline editing of `quantity_on_hand`.

- [ ] **Step 11: Implement Entrada operation**

Entrada form fields:

```text
Cantidad
Nota opcional
```

Send:

```text
POST /admin/pos/inventory/{item_id}/receipt
```

Payload:

```javascript
{
    branch_code: selectedBranchCode,
    quantity: enteredQuantity,
    note: enteredNote || null,
}
```

On success:

```text
refresh selected item
refresh inventory table
refresh summary metrics
refresh history when open
```

- [ ] **Step 12: Implement Merma operation**

Merma form fields:

```text
Cantidad
Motivo obligatorio
```

Send:

```text
POST /admin/pos/inventory/{item_id}/waste
```

Payload:

```javascript
{
    branch_code: selectedBranchCode,
    quantity: wasteQuantity,
    note: wasteReason,
}
```

Reject blank reason before sending the request.

- [ ] **Step 13: Implement Ajuste de conteo**

This action represents a physical count, not a direct delta.

Fields:

```text
Conteo físico
Motivo obligatorio
```

Send:

```text
POST /admin/pos/inventory/{item_id}/adjust
```

Payload:

```javascript
{
    branch_code: selectedBranchCode,
    physical_quantity: physicalCount,
    note: adjustmentReason,
}
```

The browser must not calculate or submit quantity_delta.
The backend inventory service calculates the delta against current locked stock.

- [ ] **Step 14: Implement movement history**

Load:

```text
GET /admin/pos/inventory/{item_id}/movements?branch_code={branch_code}
```

Render columns:

```text
Fecha
Tipo
Cambio
Saldo
Referencia
Nota
```

Movement labels:

```text
INITIAL -> Stock inicial
RECEIPT -> Entrada
SALE -> Venta
SALE_REVERSAL -> Reverso de venta
WASTE -> Merma
ADJUSTMENT -> Ajuste
```

For SALE and SALE_REVERSAL show available order/folio reference from the API response.

- [ ] **Step 15: Preserve immutable-history UX**

Do not add edit/delete controls to inventory movements.

Corrections must use a new Entrada, Merma or Ajuste de conteo operation.

- [ ] **Step 16: Handle REVIEW prominently**

When selected item status is REVIEW:

```text
show Revisar inventario prominently
show current negative quantity
offer Ajuste de conteo as the primary correction action
do not silently clamp the displayed value to zero
```

- [ ] **Step 17: Run Task 9 GREEN**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/inventory-ui.test.js
```

Expected: PASS.

- [ ] **Step 18: Run complete Admin regression suite**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/*.test.js
```

Expected: all Admin tests PASS.

- [ ] **Step 19: Commit Task 9**

```bash
git add \
  admin/inventory.html \
  admin/admin.js \
  admin/tests/inventory-ui.test.js

git commit -m "feat(admin): add inventory workspace"
```

---

### Task 10: Full-sale refund action in Sales Admin

**Files:**
- Modify: `admin/sales.html`
- Create: `admin/tests/sales-refund.test.js`

**Interfaces:**
- Consumes `POST /admin/pos/sales/{order_uuid}/refund`.
- Full-sale refund only in Phase 1.
- Refund requires a nonblank reason.
- Inventory restoration is performed by backend SALE_REVERSAL logic, not by browser code.

- [ ] **Step 1: Write failing refund UI tests**

Create `admin/tests/sales-refund.test.js`.

Assert Sales Admin contains:

```text
Reembolsar venta
Motivo del reembolso
```

Assert the request target is:

```text
POST /admin/pos/sales/{order_uuid}/refund
```

Assert the request body contains:

```javascript
{
    reason: refundReason,
}
```

- [ ] **Step 2: Write failing refund-eligibility tests**

Prove:

```text
PAID sale shows Reembolsar venta action
REFUNDED sale does not offer another active refund action
nonblank reason is required before request
successful refund refreshes sale detail and sales list
```

- [ ] **Step 3: Run Task 10 RED**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/sales-refund.test.js
```

Expected: FAIL because the Sales Admin refund action does not exist.

- [ ] **Step 4: Add refund action to paid sale detail**

Show:

```text
Reembolsar venta
```

only when:

```text
payment_status == PAID
```

The action opens a confirmation UI that clearly states the complete sale will be refunded.

- [ ] **Step 5: Require refund reason**

Confirmation UI contains:

```text
Motivo del reembolso
```

Reject blank or whitespace-only input before sending the request.

- [ ] **Step 6: Call protected refund endpoint**

Use the existing authenticated Admin request helper.

Request:

```javascript
await adminRequest(
    `/admin/pos/sales/${orderUuid}/refund`,
    {
        method: "POST",
        body: JSON.stringify({
            reason: refundReason,
        }),
    }
);
```

Adapt only the existing helper call signature if necessary; do not create a second Admin HTTP client.

- [ ] **Step 7: Refresh sale state after success**

After successful refund:

```text
refresh selected sale detail
refresh sales list
show payment status Reembolsada/REFUNDED
remove or disable refund action
```

Do not calculate or mutate inventory in the browser.

- [ ] **Step 8: Preserve existing sale/ticket behavior**

Refund UI must not break:

```text
sale list filters
sale detail rendering
receipt/ticket viewing
customer information
branch filtering
```

- [ ] **Step 9: Run Task 10 GREEN**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/sales-refund.test.js
```

Expected: PASS.

- [ ] **Step 10: Run Sales Admin regressions**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/sales*.test.js
```

Expected: all Sales Admin tests PASS.

- [ ] **Step 11: Commit Task 10**

```bash
git add \
  admin/sales.html \
  admin/tests/sales-refund.test.js

git commit -m "feat(admin): add full sale refund action"
```

---

### Task 11: Full regression, migration rehearsal, and rollout gate

**Files:**
- Modify only files required to correct regressions discovered by this task.
- Do not include unrelated cleanup.

**Interfaces:**
- Produces a release candidate with verified backend, POS, Admin, migration and inventory behavior.
- Production deployment is not allowed until every required gate in this task passes.

- [ ] **Step 1: Run complete backend test suite**

Run inside the existing backend Python test environment/container:

```bash
cd backend
python -m pytest tests -q
```

Expected: all tests PASS.

Do not install Python packages globally on the host to make this command work.

If the repository backend tests are normally executed through Docker, use that existing backend test container/runtime with the same pytest target.

- [ ] **Step 2: Run complete POS JavaScript suite**

From repository root:

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test pos/tests/*.test.js
```

Expected: all POS tests PASS.

- [ ] **Step 3: Run complete Admin JavaScript suite**

```bash
docker run --rm --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/*.test.js
```

Expected: all Admin tests PASS.

- [ ] **Step 4: Verify Alembic head using backend runtime**

Do not use host-global Alembic.

Inside the same Python runtime/container used by the backend:

```bash
alembic heads
```

Expected:

```text
20260911_0001 (head)
```

- [ ] **Step 5: Rehearse migration against a non-production database**

Use the existing test/staging PostgreSQL database, never the production database.

Run:

```bash
alembic upgrade head
```

Verify these tables exist:

```text
pos_inventory_items
pos_inventory_balances
pos_inventory_movements
```

Verify upgraded existing catalog data remains present.

- [ ] **Step 6: Verify backward compatibility after migration**

On a migrated non-production database containing existing products, prove:

```text
existing products have no fabricated inventory history
existing products remain untracked unless explicitly enabled
existing untracked products remain sellable
existing manual branch availability still works
existing receipt/ticket flow still works
existing customer-linked sale still works
```

- [ ] **Step 7: Verify strict online sale manually**

Prepare one tracked branch product with stock 1.

Verify:

```text
first online quantity-1 sale succeeds
one SALE movement is created
stock becomes 0
catalog refresh shows Agotado
second online sale is blocked
no second paid order is created for the blocked attempt
```

- [ ] **Step 8: Verify normal offline terminal accounting**

Prepare cached tracked stock 2, then disconnect the device.

Verify:

```text
first offline sale quantity 1 succeeds locally
effective local stock becomes 1
second offline sale quantity 1 succeeds locally
effective local stock becomes 0
third local sale is blocked
both completed sales remain PENDING_SYNC
```

Reconnect and sync.

Verify:

```text
both orders become SYNCED
exactly two server SALE movements exist
server balance reflects both sales
catalog refresh uses new server balance
```

- [ ] **Step 9: Verify two-device stale-stock oversell policy**

Use two isolated browser storage profiles that both cache server stock 1.

Take both offline and sell quantity 1 on each device.

Reconnect device A first:

```text
sync succeeds
server stock becomes 0
```

Reconnect device B second:

```text
sync also succeeds because sale was already physically completed
server stock becomes -1
inventory status becomes REVIEW
new sales are blocked
Admin Inventory prominently shows Revisar inventario
```

- [ ] **Step 10: Correct REVIEW through physical count**

From Inventory Admin perform Ajuste de conteo with the real physical count.

Verify:

```text
one ADJUSTMENT movement is added
negative history remains visible
balance becomes the physical count
status recalculates from the new balance
no prior movement is edited or deleted
```

- [ ] **Step 11: Verify full-sale refund manually**

Use one previously paid tracked sale.

Before refund record:

```text
order_uuid
payment_status = PAID
current inventory balance
original SALE movement count
```

From Sales Admin submit a full refund with a nonblank reason.

Verify:

```text
payment_status becomes REFUNDED
order status becomes CANCELLED
one SALE_REVERSAL exists for each original tracked SALE movement
stock is restored exactly once
SALE_REVERSAL.note equals the refund reason
SALE_REVERSAL.created_by_admin_id equals the refunding Admin id
```

Repeat the refund request.

Verify:

```text
request remains idempotent
balance does not increase again
no duplicate SALE_REVERSAL is created
```

- [ ] **Step 12: Verify inventory audit integrity**

For one tracked product with INITIAL, RECEIPT, SALE, WASTE, ADJUSTMENT and SALE_REVERSAL history, verify:

```text
each movement has quantity_delta
each movement has balance_after
movements remain chronological and immutable
current quantity_on_hand equals the final movement balance_after
manual corrections exist as new movements rather than edits
```

- [ ] **Step 13: Verify Git state and preserved stash**

Run:

```bash
git status --short
git log --oneline --decorate -20
git stash list
```

Required result:

```text
implementation worktree clean
all inventory task commits present
no unrelated files committed
batch-PIN stash still exists and remains untouched
```

- [ ] **Step 14: Review complete feature diff before release approval**

Compare the inventory feature branch against the main branch it started from:

```bash
git diff --check origin/main...HEAD
git diff --stat origin/main...HEAD
git log --oneline origin/main..HEAD
```

Expected:

```text
git diff --check produces no errors
diff contains only inventory/refund implementation and its tests/docs
commit history follows the task boundaries in this plan
```

- [ ] **Step 15: Enforce live-worktree release safety**

`/opt/cofinet-candidate` is live-mounted by production nginx for POS/Admin/static files.

Implementation work must therefore occur in an isolated non-live worktree created with the Superpowers using-git-worktrees workflow.

Do not implement Tasks 1-11 directly inside `/opt/cofinet-candidate`.

Before any implementation begins:

```text
leave /opt/cofinet-candidate serving production-equivalent static content
create a separate isolated implementation worktree
perform code edits and test runs in that isolated worktree
do not copy feature static files into the live-mounted candidate path during development
```

- [ ] **Step 16: Production rollout is a separate approval gate**

Completing this implementation plan produces a verified release candidate; it does not authorize production deployment.

Before production rollout require all of these to be true:

```text
backend tests PASS
POS tests PASS
Admin tests PASS
Alembic migration rehearsal PASS on non-production PostgreSQL
online/offline/manual/refund checks PASS
feature diff reviewed
feature branch integrated through the normal GitHub/main workflow
fresh production database backup created immediately before migration
```

Never run:

```text
docker compose down
docker compose down -v
production db-init
```

- [ ] **Step 17: Route any regression back to its owning task**

If Task 11 finds a regression, stop the release gate, return to the owning task, add the failing RED test there, apply the smallest fix, rerun that task GREEN, then resume Task 11.

Task 11 does not create a generic regression-fix commit. If no regressions are found, continue without an empty commit.

---

## Implementation Order

Execute strictly in this order:

```text
1. Inventory persistence foundation
2. Inventory service and movement invariants
3. Admin Inventory API
4. Catalog inventory contract
5. Paid-order inventory integration and refunds
6. POS local inventory accounting and availability UX
7. Server-first online checkout with offline fallback
8. Inventory configuration inside Catalog Admin
9. Dedicated Inventory Admin workspace
10. Full-sale refund action in Sales Admin
11. Full regression, migration rehearsal, and rollout gate
```

Critical transaction boundary:

```text
ONLINE
frozen sale identity
  -> POST /pos/orders
  -> strict locked stock validation
  -> order + payment + SALE movements
  -> one commit
  -> local SYNCED copy

OFFLINE
frozen sale identity
  -> IndexedDB paid local sale
  -> PENDING_SYNC
  -> POST /pos/orders/sync
  -> idempotent replay
  -> negative stock allowed only because sale was already completed
```
