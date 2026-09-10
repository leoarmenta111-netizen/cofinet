# POS Customer Receipts Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 customer receipt foundation: offline-safe public folios, immutable paid-sale snapshots, configurable receipt/tax settings, 80 mm receipt preview/printing, and historical reprinting.

**Architecture:** Operational Orders remain separate from immutable Receipt Snapshots. New sales generate their final public folio and commercial snapshot locally before synchronization. The backend validates and persists those frozen values instead of repricing completed offline sales from the current catalog.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, vanilla JavaScript, IndexedDB, Node.js built-in test runner, PWA/service worker, CSS `@media print`.

**Spec:** `docs/superpowers/specs/2026-09-08-pos-receipts-printing-design.md`

## Global Constraints

- Phase 1 only.
- Do not implement Print Jobs, ESC/POS, Kitchen/Bar automatic printing, or Print Bridge.
- This is a proof-of-sale receipt, not CFDI or SAT fiscal invoicing.
- New paid sales are immutable.
- Public folio is generated locally before synchronization.
- Existing legacy folios remain unchanged.
- `order_uuid` remains the technical idempotency key.
- Initial receipt width is exactly 80 mm.
- Tax modes are exactly `NONE`, `INCLUDED`, and `ADDED`.
- Tip is outside the V1 tax base.
- Customer receipt prints customer name only.
- Internal preparation notes never appear on customer receipts.
- Branch receipt settings override business defaults field-by-field.
- Historical receipts render only from stored snapshots.
- Printer failure never rolls back payment.
- Browser printing is manual by default.
- Offline receipts remain viewable and printable before sync.
- Existing Kitchen/Bar KDS behavior must remain unchanged.
- Preserve unrelated dirty POS redesign files.
- Never use `git add .`.
- Use `python -m pytest` for backend tests.
- Use temporary `node:22-alpine` for frontend tests.
- Do not install Node on the host.
- Never replace `httpx` with `httpx2`.
- Production DB migrations must be additive.
- Never delete or recreate the production PostgreSQL volume.

## Current Repo Facts

- Current Alembic head before this feature: `20260902_0002`.
- `PosOrder.folio` already exists.
- `PosOrderService.create()` currently calculates pricing and assigns folio.
- `PosOrderItem` already snapshots product name, prices, modifiers, notes, and preparation station.
- `PosPayment` already stores payment details.
- IndexedDB is currently version 2.
- Existing stores include `meta`, `catalogs`, `local_orders`, and `sync_queue`.
- Offline network failure currently queues the order for later synchronization.
- Orders UI already merges server orders and pending local orders.
- Success modal currently shows folio and `Iniciar nueva venta`.

## File Structure

### Backend — create

- `backend/app/models/pos_receipts.py`
  - Receipt settings models.
  - Immutable receipt snapshot model.

- `backend/app/schemas/pos_receipts.py`
  - Receipt configuration schemas.
  - Versioned receipt snapshot schemas.

- `backend/app/services/pos_receipt_settings_service.py`
  - Resolve business defaults and branch overrides.

- `backend/app/services/pos_receipt_service.py`
  - Validate, persist and retrieve immutable receipt snapshots.

- `backend/app/api/pos_receipts.py`
  - POS receipt settings and receipt retrieval endpoints.

- `backend/app/api/admin_pos_receipts.py`
  - Receipt configuration administration endpoints.

- `backend/tests/test_pos_receipt_settings.py`
- `backend/tests/test_pos_receipt_snapshots.py`

- `backend/alembic/versions/20260908_0001_pos_receipt_foundation.py`
  - Additive receipt settings foundation migration.
- `backend/alembic/versions/20260908_0002_pos_receipt_snapshots.py`
  - Additive immutable receipt snapshot migration.

### Backend — modify

- `backend/app/main.py`
- `backend/app/schemas/pos_orders.py`
- `backend/app/services/pos_order_service.py`

### POS — create

- `pos/js/folio.js`
- `pos/js/receipt-core.js`
- `pos/js/receipt-renderer.js`
- `pos/css/receipt.css`

- `pos/tests/receipt-folio.test.js`
- `pos/tests/receipt-core.test.js`
- `pos/tests/receipt-storage.test.js`
- `pos/tests/receipt-renderer.test.js`
- `pos/tests/receipt-print.test.js`
- `pos/tests/receipt-checkout.test.js`
- `pos/tests/receipt-settings-cache.test.js`
- `pos/tests/order-receipt.test.js`
- `pos/tests/order-receipt-offline.test.js`
- `pos/tests/receipt-offline.test.js`

### POS — modify

- `pos/js/db.js`
- `pos/js/sync.js`
- `pos/js/api.js`
- `pos/js/app.js`
- `pos/js/orders-local.js`
- `pos/js/orders.js`
- `pos/index.html`
- `pos/sw.js`

### Admin — create

- `admin/receipt-settings.html`
- `admin/tests/receipt-settings.test.js`

### Admin — modify

- `admin/admin.js`
- `admin/admin.css`

---

### Task 1: Receipt Settings Foundation

**Files:**
- Create: `backend/app/models/pos_receipts.py`
- Create: `backend/app/schemas/pos_receipts.py`
- Create: `backend/app/services/pos_receipt_settings_service.py`
- Create: `backend/app/api/pos_receipts.py`
- Create: `backend/app/api/admin_pos_receipts.py`
- Create: `backend/tests/test_pos_receipt_settings.py`
- Create: `backend/alembic/versions/20260908_0001_pos_receipt_foundation.py`
- Modify: `backend/app/main.py`

**Interfaces:**

Produces:

- `PosBusinessReceiptSettings`
- `PosBranchReceiptSettings`
- `ReceiptSettingsUpdate`
- `EffectiveReceiptSettings`
- `PosReceiptSettingsService.get_effective(db, branch_code)`
- `PosReceiptSettingsService.update_business(db, payload)`
- `PosReceiptSettingsService.update_branch(db, branch_code, payload)`
- `GET /pos/receipts/settings?branch_code=<code>`
- `GET /admin/pos/receipt-settings`
- `PUT /admin/pos/receipt-settings/business`
- `PUT /admin/pos/receipt-settings/branches/{branch_code}`

**Tenancy decision:**

The current repo does not yet have a first-class SaaS Business/Tenant model.

Phase 1 therefore uses:

- one `pos_business_receipt_settings` singleton row with `id=1`;
- one optional `pos_branch_receipt_settings` row per branch.

Branch settings inherit field-by-field from the business singleton.

This keeps the receipt feature independent from a future tenant migration.


- [ ] **Step 1: Write failing receipt-settings tests**

Create `backend/tests/test_pos_receipt_settings.py`.

Required first test:

```python
from decimal import Decimal

def test_business_defaults_are_resolved(db_session):
    settings = PosBusinessReceiptSettings(
        id=1,
        business_name="CofiCenter",
        currency="MXN",
        tax_mode="INCLUDED",
        tax_rate=Decimal("0.1600"),
        receipt_width_mm=80,
        timezone="America/Bahia_Banderas",
        folio_prefix="CF",
    )
    db_session.add(settings)
    db_session.commit()

    result = PosReceiptSettingsService.get_effective(
        db_session,
        "nuevo-vallarta",
    )

    assert result.business_name == "CofiCenter"
    assert result.tax_mode == "INCLUDED"
    assert result.tax_rate == Decimal("0.1600")
    assert result.receipt_width_mm == 80
```

Also test:

- branch values override business defaults;
- nullable branch values inherit business defaults;
- tax mode accepts only `NONE`, `INCLUDED`, and `ADDED`;
- negative tax rate is rejected;
- invalid timezone is rejected;
- unknown branch returns 404;
- folio prefix is uppercase and 2-8 alphanumeric characters;
- POS settings response exposes only receipt-safe fields.


- [ ] **Step 2: Run RED**

During implementation, build the backend test image with:

```bash
docker build \
  -f backend/Dockerfile \
  --target development \
  -t cofinet-backend-receipts:test \
  backend
```

Then run:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  python -m pytest \
    tests/test_pos_receipt_settings.py \
    -q
```

Expected: FAIL because receipt settings models and services do not exist yet.

- [ ] **Step 3: Implement receipt settings models**

Create `PosBusinessReceiptSettings` with:

```python
id = Column(Integer, primary_key=True)
business_name = Column(String(160), nullable=False)
logo_ref = Column(String(500), nullable=True)
phone = Column(String(40), nullable=True)
web_social = Column(String(240), nullable=True)
footer_message = Column(String(500), nullable=True)
currency = Column(String(3), nullable=False, default="MXN")
tax_mode = Column(String(16), nullable=False, default="NONE")
tax_rate = Column(Numeric(8, 4), nullable=False, default=0)
receipt_width_mm = Column(Integer, nullable=False, default=80)
timezone = Column(String(64), nullable=False)
folio_prefix = Column(String(8), nullable=False)
auto_print_customer = Column(Boolean, nullable=False, default=False)
```

Database checks:

- singleton row must have `id = 1`;
- tax mode must be `NONE`, `INCLUDED`, or `ADDED`;
- tax rate must be nonnegative;
- receipt width must equal 80 in V1.

Create `PosBranchReceiptSettings` with:

```python
branch_id = Column(
    Integer,
    ForeignKey("branches.id", ondelete="CASCADE"),
    primary_key=True,
)
display_name = Column(String(160), nullable=True)
address = Column(String(500), nullable=True)
phone = Column(String(40), nullable=True)
web_social = Column(String(240), nullable=True)
footer_message = Column(String(500), nullable=True)
tax_mode = Column(String(16), nullable=True)
tax_rate = Column(Numeric(8, 4), nullable=True)
timezone = Column(String(64), nullable=True)
folio_prefix = Column(String(8), nullable=True)
auto_print_customer = Column(Boolean, nullable=True)
```

Do not add receipt-specific columns directly to `branches`.

- [ ] **Step 4: Implement receipt settings schemas and inheritance**

Create `EffectiveReceiptSettings` with:

```python
class EffectiveReceiptSettings(BaseModel):
    business_name: str
    logo_ref: str | None
    branch_code: str
    branch_name: str
    address: str | None
    phone: str | None
    web_social: str | None
    footer_message: str | None
    currency: str
    tax_mode: Literal["NONE", "INCLUDED", "ADDED"]
    tax_rate: Decimal
    receipt_width_mm: Literal[80]
    timezone: str
    folio_prefix: str
    auto_print_customer: bool
```

Validate timezones with `zoneinfo.ZoneInfo`.

Normalize folio prefix to uppercase ASCII alphanumeric.
Reject prefixes shorter than 2 or longer than 8 characters.

Inheritance rule for every nullable branch field:

```python
effective = branch_value if branch_value is not None else business_value
```

`NONE` resolves tax rate to `0.0000`.
`INCLUDED` and `ADDED` preserve the configured nonnegative tax rate.

Unknown branch must return HTTP 404.
Invalid timezone, tax mode, rate, or prefix must return HTTP 422.

- [ ] **Step 5: Add additive Alembic migration and initial settings seed**

Create `backend/alembic/versions/20260908_0001_pos_receipt_foundation.py`.

Migration identifiers:

```python
revision = "20260908_0001"
down_revision = "20260902_0002"
```

Create table `pos_business_receipt_settings`.

Create table `pos_branch_receipt_settings` with:

- `branch_id` FK to `branches.id`;
- one override row maximum per branch;
- `ON DELETE CASCADE`.

Seed exactly one business defaults row:

```text
id = 1
business_name = CofiCenter
currency = MXN
tax_mode = NONE
tax_rate = 0.0000
receipt_width_mm = 80
timezone = America/Bahia_Banderas
folio_prefix = CF
auto_print_customer = false
```

The migration must be additive.
Do not rewrite existing orders or folios.
Do not modify existing Kitchen/Bar routing data.
Do not create receipt snapshots yet in this step.

`downgrade()` removes only the two new receipt-settings tables.

- [ ] **Step 6: Add receipt settings API routes**

Create POS endpoint:

```text
GET /pos/receipts/settings?branch_code=<code>
```

Response uses `EffectiveReceiptSettings`.
The POS endpoint is read-only.

Create admin endpoints:

```text
GET /admin/pos/receipt-settings
PUT /admin/pos/receipt-settings/business
PUT /admin/pos/receipt-settings/branches/{branch_code}
```

Admin routes must use the same super-admin authorization pattern as the existing admin POS catalog API.

`GET /admin/pos/receipt-settings` returns:

- business defaults;
- every active branch;
- branch overrides when present;
- effective values for each branch.

Business update modifies only singleton row `id=1`.
Branch update creates or updates only that branch override row.
Submitting `null` for a nullable branch field restores inheritance.

Register both new routers in `backend/app/main.py`.

Do not add receipt routes to the existing catalog or order routers.

- [ ] **Step 7: Run GREEN and migration checks**

Run receipt-settings and order regression tests:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  python -m pytest \
    tests/test_pos_receipt_settings.py \
    tests/test_pos_order_management.py \
    -q
```

Expected: PASS.

Verify Alembic head:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  alembic heads
```

Expected head: `20260908_0001`.

- [ ] **Step 8: Commit Task 1 exact files**

Stage only:

```bash
git add \
  backend/app/models/pos_receipts.py \
  backend/app/schemas/pos_receipts.py \
  backend/app/services/pos_receipt_settings_service.py \
  backend/app/api/pos_receipts.py \
  backend/app/api/admin_pos_receipts.py \
  backend/app/main.py \
  backend/tests/test_pos_receipt_settings.py \
  backend/alembic/versions/20260908_0001_pos_receipt_foundation.py

git diff --cached --check

git commit -m "feat(pos): add receipt settings foundation"
```

Do not stage unrelated dirty POS files.

---

### Task 2: Offline Folio, Tax Math, and Receipt Snapshot Core

**Files:**
- Create: `pos/js/folio.js`
- Create: `pos/js/receipt-core.js`
- Create: `pos/tests/receipt-folio.test.js`
- Create: `pos/tests/receipt-core.test.js`

**Interfaces:**

Produces:

- `CofiPosFolio.generate(options)`
- `CofiPosReceipt.calculateTax(input)`
- `CofiPosReceipt.buildSnapshot(input)`
- `CofiPosReceipt.validateSnapshot(snapshot)`

Folio input contract:

```javascript
{
    branchPrefix: "NV",
    soldAt: new Date(),
    timeZone: "America/Bahia_Banderas"
}
```

Example output:

```text
NV-260908-7K3M9Q2F
```

Folio rules:

- uppercase branch prefix;
- branch-local `YYMMDD` date;
- 8-character Crockford Base32 random suffix;
- no ambiguous `I`, `L`, `O`, or `U` characters;
- generated before server persistence;
- stable once attached to an order;
- no database ID in new folios;
- legacy server folios remain supported.

Money rules:

- frontend calculations operate in integer cents;
- convert decimal product values to cents before arithmetic;
- convert cents back to two-decimal strings at snapshot boundaries;
- never use uncontrolled binary floating-point accumulation for totals.

Tax modes:

- `NONE`: tax = 0;
- `INCLUDED`: tax is informational and already contained in merchandise total;
- `ADDED`: tax is added to taxable merchandise total;
- tip is excluded from tax base in V1.

Receipt snapshot schema version is exactly `1`.

---

- [ ] **Step 1: Write failing folio and receipt-core tests**

Create `pos/tests/receipt-folio.test.js`.

Required folio cases:

- output matches `PREFIX-YYMMDD-XXXXXXXX`;
- prefix is uppercase;
- date uses configured branch timezone;
- suffix length is exactly 8;
- suffix uses Crockford Base32 characters only;
- suffix excludes `I`, `L`, `O`, and `U`;
- two generated folios for the same branch/time are different;
- generated folio does not contain a database order ID.

Create `pos/tests/receipt-core.test.js`.

Required tax cases:

```javascript
assert.deepEqual(
    CofiPosReceipt.calculateTax({
        merchandiseCents: 10000,
        taxMode: "NONE",
        taxRate: "0.1600",
        tipCents: 500
    }),
    {
        taxCents: 0,
        totalCents: 10500
    }
);
```

For `INCLUDED` with gross merchandise 11600 cents at 16%:

- tax is 1600 cents;
- total remains 11600 cents plus tip;
- tax is not added again.

For `ADDED` with merchandise 10000 cents at 16%:

- tax is 1600 cents;
- total is 11600 cents plus tip.

Also test:

- tip is excluded from tax base;
- discount field defaults to zero in V1;
- money is rounded deterministically to cents;
- invalid tax mode is rejected;
- negative merchandise is rejected;
- negative tip is rejected.

Required snapshot cases:

- `schema_version` equals `1`;
- snapshot includes `order_uuid` and final public `folio`;
- customer snapshot contains name only;
- item names, quantities, charged prices, and visible modifiers are frozen;
- internal preparation notes are absent from customer receipt data;
- branch/business effective settings are copied into the snapshot;
- tax mode, rate, tax amount, tip, and final total are frozen;
- payment method, cash received, and change are frozen;
- snapshot output is independent of later mutation of cart/settings input objects.

- [ ] **Step 2: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-folio.test.js \
    pos/tests/receipt-core.test.js
```

Expected: FAIL because `folio.js` and `receipt-core.js` do not exist yet.

- [ ] **Step 3: Implement offline-safe folio generation**

Create `pos/js/folio.js`.

Expose:

```javascript
window.CofiPosFolio = {
    generate
};
```

`generate({ branchPrefix, soldAt, timeZone })` must:

- validate prefix and timezone;
- format `soldAt` in the branch timezone;
- produce `YYMMDD`;
- generate 8 random Crockford Base32 characters;
- return `PREFIX-YYMMDD-XXXXXXXX`.

Use browser cryptographic randomness:

```javascript
crypto.getRandomValues(new Uint8Array(5))
Use all 5 random bytes to produce the 8-character Crockford Base32 suffix (40 bits).
```

Do not use `Math.random()` for public folios.

- [ ] **Step 4: Implement deterministic tax math**

Create `pos/js/receipt-core.js`.

Expose:

```javascript
window.CofiPosReceipt = {
    calculateTax,
    buildSnapshot,
    validateSnapshot
};
```

`calculateTax()` receives integer cents.
`rate` is a decimal fraction: `0.16` means 16%. Validate it as non-negative before calculation.

Rules:

- `NONE`: `taxCents = 0`;
- `netMerchandiseCents = subtotalCents - discountCents`; reject discount above subtotal;
- tax is calculated from the post-discount merchandise amount;
- `INCLUDED`: `taxCents = round(netMerchandiseCents * rate / (1 + rate))`;
- `ADDED`: `taxCents = round(netMerchandiseCents * rate)`;
- tip is added after tax calculation;
- return integer cents only.

Use one explicit rounding helper and reuse it everywhere.
Reject negative merchandise, discount, or tip values.

- [ ] **Step 5: Implement immutable receipt snapshot builder**

`buildSnapshot(input)` must return a new detached object.

Required top-level fields:

```javascript
{
    schema_version: 1,
    order_uuid,
    folio,
    sold_at,
    currency,
    business,
    branch,
    terminal,
    customer,
    items,
    totals,
    payment
}
```

Customer snapshot contains only:

```javascript
{ name: "Customer Name" }
```

or `null` when no customer is selected.

Each customer receipt item freezes:

- product ID;
- product name;
- quantity;
- actual charged unit price;
- line total;
- customer-visible modifiers and charged price deltas.

Do not copy internal preparation notes into customer receipt items.

Totals freeze:

- subtotal;
- discount;
- tax mode;
- tax rate;
- tax amount;
- tip;
- final total.

Payment freezes:

- method;
- amount;
- amount tendered for cash;
- change due for cash.

Clone nested arrays and objects so later cart/settings mutations cannot change the snapshot.

`validateSnapshot(snapshot)` must reject:

- schema version other than 1;
- missing order UUID or folio;
- negative monetary values;
- inconsistent line totals;
- inconsistent subtotal/tax/total arithmetic;
- unsupported tax mode;
- customer fields other than `name` in V1.

- [ ] **Step 6: Run GREEN**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-folio.test.js \
    pos/tests/receipt-core.test.js
```

Expected: PASS.

Also run the existing affected POS tests:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/payment-shortcuts.test.js \
    pos/tests/orders-local.test.js \
    pos/tests/orders-api.test.js
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2 exact files**

Stage only:

```bash
git add \
  pos/js/folio.js \
  pos/js/receipt-core.js \
  pos/tests/receipt-folio.test.js \
  pos/tests/receipt-core.test.js

git diff --cached --check

git commit -m "feat(pos): add offline receipt core"
```

Do not stage `pos/index.html`, `pos/css/pos.css`, `pos/js/app.js`, or other unrelated dirty files in this task.

---

### Task 3: Persist Immutable Receipt Snapshots and Accept Frozen Offline Sales

**Files:**
- Modify: `backend/app/models/pos_receipts.py`
- Modify: `backend/app/schemas/pos_receipts.py`
- Create: `backend/app/services/pos_receipt_service.py`
- Modify: `backend/app/schemas/pos_orders.py`
- Modify: `backend/app/services/pos_order_service.py`
- Modify: `backend/app/api/pos_receipts.py`
- Create: `backend/alembic/versions/20260908_0002_pos_receipt_snapshots.py`
- Create: `backend/tests/test_pos_receipt_snapshots.py`

**Interfaces:**

Produces:

- `PosReceiptSnapshot`
- `ReceiptSnapshotV1`
- `PosReceiptService.validate_snapshot(snapshot)`
- `PosReceiptService.create_for_order(db, order, snapshot)`
- `PosReceiptService.get_for_order(db, order_uuid)`
- `GET /pos/receipts/{order_uuid}`

New-order payload additions:

- `folio: str | None`;
- `receipt_snapshot: ReceiptSnapshotV1 | None`.

Compatibility rule:

- old clients may omit both fields;
- legacy path keeps existing server pricing and sequential folio behavior;
- new clients send both final folio and receipt snapshot;
- never reinterpret an old queued order as a new frozen-sale payload.

Immutable snapshot persistence:

- one receipt snapshot maximum per order;
- snapshot JSON is versioned;
- snapshot is created in the same database transaction as the order;
- no update endpoint exists;
- historical retrieval returns the stored snapshot exactly.

New frozen-sale path must preserve:

- client-generated public folio;
- charged item prices;
- modifier price deltas;
- subtotal;
- tax;
- tip;
- final total;
- payment amounts.

Server validates arithmetic and known IDs but does not replace frozen charged prices with current catalog prices.

---

- [ ] **Step 1: Write failing backend receipt snapshot tests**

Create `backend/tests/test_pos_receipt_snapshots.py`.

Required cases:

- new frozen-sale payload accepts client-generated `folio`;
- server stores exactly that public folio;
- duplicate folio for a different order is rejected;
- retry with the same `order_uuid` returns the existing order;
- retry does not create a second receipt snapshot;
- one receipt snapshot maximum per order;
- stored snapshot `schema_version` equals `1`;
- customer snapshot contains name only;
- receipt snapshot cannot be updated through any API;
- `GET /pos/receipts/{order_uuid}` returns the stored snapshot;
- unknown order UUID returns 404.

No-repricing test:

1. Create catalog product at price 100.00.
2. Build frozen paid payload charging 100.00.
3. Change current catalog product price to 150.00.
4. Submit the frozen paid payload.
5. Assert stored order item price remains 100.00.
6. Assert stored subtotal/total remain the frozen paid values.

Also test modifier price preservation:

- original frozen modifier delta remains unchanged even if current catalog modifier price changes before sync.

Arithmetic validation tests:

- inconsistent line total is rejected;
- inconsistent subtotal is rejected;
- inconsistent tax is rejected;
- inconsistent final total is rejected;
- inconsistent cash change is rejected.

Compatibility tests:

- legacy payload without `folio` and `receipt_snapshot` still succeeds;
- legacy payload still receives old server-generated sequential folio;
- legacy retry behavior remains unchanged.

- [ ] **Step 2: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  python -m pytest \
    tests/test_pos_receipt_snapshots.py \
    -q
```

Expected: FAIL because receipt snapshot persistence and frozen-sale handling do not exist yet.

- [ ] **Step 3: Add immutable receipt snapshot model and schema**

Extend `backend/app/models/pos_receipts.py` with `PosReceiptSnapshot`.

Recommended model:

```python
class PosReceiptSnapshot(Base):
    __tablename__ = "pos_receipt_snapshots"

    id = Column(Integer, primary_key=True)
    order_id = Column(
        Integer,
        ForeignKey("pos_orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    schema_version = Column(
        Integer,
        nullable=False,
        default=1,
    )
    snapshot_json = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
```

Database constraints:

- one snapshot maximum per order;
- schema version must equal `1` in Phase 1;
- snapshot row is append-only after creation.

Do not add an update API for receipt snapshots.

Extend `ReceiptSnapshotV1` schema with:

- `schema_version: Literal[1]`;
- `order_uuid: UUID`;
- `folio: str`;
- `sold_at: datetime`;
- `currency: str`;
- business snapshot;
- branch snapshot;
- terminal snapshot;
- customer name snapshot or null;
- items;
- totals;
- payment.

Use integer-cent fields for all monetary snapshot amounts in backend validation. Do not convert frozen receipt amounts to floating-point currency values.
Do not expose internal preparation notes in customer receipt item schema.

Create migration `20260908_0002` with `down_revision = "20260908_0001"` to create `pos_receipt_snapshots`.

The migration remains additive and must not rewrite existing orders.

- [ ] **Step 4: Add dual-path order creation for frozen paid sales**

Extend `PosOrderCreate` with optional fields:

```python
folio: str | None = Field(default=None, min_length=8, max_length=40)
receipt_snapshot: ReceiptSnapshotV1 | None = None
```

Payload mode rules:

- legacy mode: both fields are absent;
- frozen-sale mode: both fields are present;
- reject payloads where only one of the two fields is present.

Frozen-sale validation must assert:

- payload `order_uuid` equals snapshot `order_uuid`;
- payload `folio` equals snapshot `folio`;
- payload branch matches snapshot branch;
- terminal ID matches snapshot terminal;
- payment method/amounts match snapshot payment;
- item quantities match;
- modifier selections match known IDs;
- line arithmetic is internally consistent;
- subtotal, tax, tip, and total are internally consistent.

For frozen-sale mode:

- preserve snapshot product names and charged values;
- preserve snapshot modifier names and charged deltas;
- do not recalculate prices from the current catalog;
- use current catalog only to validate referenced product/modifier identities and branch availability where appropriate;
- persist the client public folio unchanged;
- rely on the existing unique folio database constraint as the final collision guard.

For legacy mode:

- keep current server-side catalog repricing;
- keep current sequential folio generation after order insert;
- keep existing API behavior for old queued POS builds.

Idempotency remains keyed by `order_uuid` in both modes.

On retry of an existing frozen sale:

- return the existing order;
- do not create a second payment;
- do not create a second receipt snapshot;
- do not change the original folio or totals.

- [ ] **Step 5: Implement receipt snapshot service and retrieval API**

`PosReceiptService.create_for_order(db, order, snapshot)` must:

- validate snapshot schema version;
- validate order UUID and folio identity;
- validate customer privacy shape;
- validate line, subtotal, tax, tip, total, tendered, and change arithmetic;
- create exactly one snapshot row;
- reject a conflicting second snapshot;
- participate in the same DB transaction as order/payment creation.

`PosReceiptService.get_for_order(db, order_uuid)` must:

- find the order by UUID;
- enforce existing branch/POS authorization rules;
- return stored immutable snapshot;
- return 404 when order or modern snapshot does not exist.

Expose:

```text
GET /pos/receipts/{order_uuid}
```

Do not expose PUT, PATCH, or DELETE receipt snapshot endpoints.
Declare the static `/pos/receipts/settings` route before the dynamic `/pos/receipts/{order_uuid}` route so `settings` is never interpreted as an order UUID.

- [ ] **Step 6: Run GREEN and compatibility regression**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  python -m pytest \
    tests/test_pos_receipt_snapshots.py \
    tests/test_pos_receipt_settings.py \
    tests/test_pos_order_management.py \
    tests/test_pos_customer_order_link.py \
    -q
```

Expected: PASS.

Verify migration head is now `20260908_0002`.

- [ ] **Step 7: Commit Task 3 exact files**

Stage only Task 3 backend files, including:

- `backend/app/models/pos_receipts.py`;
- `backend/app/schemas/pos_receipts.py`;
- `backend/app/services/pos_receipt_service.py`;
- `backend/app/schemas/pos_orders.py`;
- `backend/app/services/pos_order_service.py`;
- `backend/app/api/pos_receipts.py`;
- `backend/tests/test_pos_receipt_snapshots.py`;
- `backend/alembic/versions/20260908_0002_pos_receipt_snapshots.py`.

Run `git diff --cached --check` before commit.

Commit message:

```text
feat(pos): persist immutable receipt snapshots
```

---

### Task 4: Atomic Offline Receipt Persistence and Synchronization

**Files:**
- Modify: `pos/js/db.js`
- Modify: `pos/js/sync.js`
- Modify: `pos/js/orders-local.js`
- Create: `pos/tests/receipt-storage.test.js`
- Create: `pos/tests/receipt-offline.test.js`

**Interfaces:**

Produces:

- IndexedDB version `3`;
- `receipts` object store keyed by `order_uuid`;
- `CofiPosDB.finalizePaidSale(record)`;
- `CofiPosDB.getReceipt(orderUuid)`;
- `CofiPosDB.getLocalOrder(orderUuid)`;
- frozen receipt snapshot carried through `sync_queue`;
- local Orders representation exposes its receipt snapshot.

IndexedDB v3 migration rules:

- preserve existing `meta` store;
- preserve existing `catalogs` store;
- preserve existing `local_orders` store;
- preserve existing `sync_queue` store;
- create new `receipts` store with keyPath `order_uuid`;
- do not delete or rebuild existing stores during upgrade.

`finalizePaidSale(record)` persists in one readwrite transaction:

- local order;
- immutable receipt snapshot;
- synchronization queue event.

If that transaction fails:

- reject the operation;
- do not report the sale as locally saved;
- do not clear the active cart;
- do not show a successful receipt state.

The sync queue payload must contain the exact frozen:

- order UUID;
- public folio;
- item and modifier charged values;
- payment values;
- receipt snapshot.

Sync retries must never regenerate folio or snapshot.

---

- [ ] **Step 1: Write failing IndexedDB and offline receipt tests**

Create `pos/tests/receipt-storage.test.js`.

Required storage cases:

- DB version upgrades from 2 to 3;
- existing `meta`, `catalogs`, `local_orders`, and `sync_queue` stores remain;
- new `receipts` store exists;
- `receipts` uses `order_uuid` as keyPath;
- existing records survive the upgrade;
- `getReceipt(orderUuid)` returns the stored snapshot;
- unknown receipt returns null.

Test `finalizePaidSale(record)` atomicity:

- local order is written;
- receipt snapshot is written;
- sync queue event is written;
- all three use the same order UUID;
- a transaction failure leaves none of the three partially committed.

Create `pos/tests/receipt-offline.test.js`.

Required offline cases:

- queued payload contains the original final folio;
- queued payload contains the exact receipt snapshot;
- retry does not generate a new folio;
- retry does not rebuild the snapshot from current cart/catalog;
- pending local order exposes its receipt snapshot;
- receipt remains available while sync status is pending;
- sync success preserves the same order UUID and folio.

- [ ] **Step 2: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-storage.test.js \
    pos/tests/receipt-offline.test.js
```

Expected: FAIL because IndexedDB v3 receipt persistence does not exist yet.

- [ ] **Step 3: Upgrade IndexedDB to version 3**

Modify `pos/js/db.js`.

Change:

```javascript
const DB_VERSION = 3;
```

During `onupgradeneeded`:

- preserve all existing stores;
- create `receipts` only when it does not already exist;
- use `{ keyPath: "order_uuid" }`;
- do not delete or recreate `local_orders` or `sync_queue`.

Expose:

```javascript
async function getReceipt(orderUuid)
async function getLocalOrder(orderUuid)
async function finalizePaidSale(record)
```

- [ ] **Step 4: Implement atomic local paid-sale finalization**

`finalizePaidSale(record)` opens one readwrite transaction over:

- `local_orders`;
- `receipts`;
- `sync_queue`.

Record contract:

```javascript
{
    order_uuid,
    local_order,
    receipt_snapshot,
    sync_event
}
```

Within the same transaction:

1. put the local order;
2. put the immutable receipt snapshot;
3. put the sync queue event.

Resolve only after the IndexedDB transaction completes successfully.
Reject on request error, transaction error, or transaction abort.
Do not use three independent write transactions.

- [ ] **Step 5: Synchronize the exact frozen paid payload**

Modify `pos/js/sync.js`.

For new receipt-capable queued orders:

- read the already-stored sync event;
- send its original `order_uuid`;
- send its original public `folio`;
- send its original charged item/modifier values;
- send its original payment values;
- send its original `receipt_snapshot`;
- never call folio generation during retry;
- never rebuild the receipt snapshot during retry;
- never recalculate prices from the current catalog.

Keep compatibility with legacy queued events that do not contain receipt data.

On successful synchronization:

- mark/update the local order as synchronized using the existing pattern;
- preserve the same order UUID;
- preserve the same public folio;
- preserve the local receipt snapshot for offline historical access;
- remove only the completed sync queue event according to the existing queue lifecycle.

- [ ] **Step 6: Expose local receipt snapshots through Orders**

Modify `pos/js/orders-local.js`.

When converting a pending local order into the Orders UI shape:

- attach its stored receipt snapshot;
- preserve `folio` from the local paid sale;
- preserve pending synchronization metadata;
- do not fabricate server IDs;
- do not rebuild receipt values from the current catalog.

- [ ] **Step 7: Run GREEN and affected offline regression**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-storage.test.js \
    pos/tests/receipt-offline.test.js \
    pos/tests/orders-local.test.js \
    pos/tests/orders-api.test.js
```

Expected: PASS.

- [ ] **Step 8: Commit Task 4 exact files**

Stage only:

```bash
git add \
  pos/js/db.js \
  pos/js/sync.js \
  pos/js/orders-local.js \
  pos/tests/receipt-storage.test.js \
  pos/tests/receipt-offline.test.js

git diff --cached --check

git commit -m "feat(pos): persist offline receipt snapshots"
```

Do not stage `pos/index.html`, `pos/css/pos.css`, `pos/js/app.js`, or `pos/js/orders.js` in this task.

---

### Task 5: Integrate Receipt Settings, Tax, Folio, and Finalization into Checkout

**Files:**
- Modify: `pos/js/api.js`
- Modify: `pos/js/db.js`
- Modify: `pos/js/app.js`
- Modify: `pos/index.html`
- Modify: `pos/sw.js`
- Create: `pos/tests/receipt-checkout.test.js`
- Create: `pos/tests/receipt-settings-cache.test.js`

**Interfaces:**

Produces:

- `CofiPosApi.getReceiptSettings(branchCode)`;
- branch-scoped cached effective receipt settings;
- checkout totals that respect `NONE`, `INCLUDED`, and `ADDED` tax modes;
- one locally generated public folio per finalized sale;
- one immutable receipt snapshot per finalized sale;
- atomic local persistence before remote synchronization.

Receipt settings lifecycle:

- fetch effective settings when a branch is loaded;
- cache the last valid settings by branch code in IndexedDB `meta`;
- use cached settings when offline;
- never silently substitute settings from another branch.

If the POS is offline and no cached receipt settings exist for the active branch:

- allow browsing the already-cached catalog;
- block payment finalization;
- show a clear message requiring one online connection to load ticket configuration.

Checkout tax behavior:

- `NONE`: tax is zero and does not change total;
- `INCLUDED`: tax is informational and already contained in merchandise total;
- `ADDED`: tax is added to the amount due before tip;
- tip is added after tax;
- payment modal amount due must equal the final frozen receipt total.

All checkout monetary calculations use the same receipt-core tax helper.
Do not duplicate tax formulas inside `app.js`.

---

- [ ] **Step 1: Write failing checkout and settings-cache tests**

Create `pos/tests/receipt-settings-cache.test.js`.

Required settings-cache cases:

- online branch load fetches effective receipt settings;
- valid settings are cached under a branch-specific key;
- offline load reuses cached settings for the same branch;
- settings cached for branch A are never used for branch B;
- malformed cached settings are rejected;
- offline checkout without cached settings cannot finalize payment.

Create `pos/tests/receipt-checkout.test.js`.

Required checkout total cases:

- `NONE` keeps tax at zero;
- `INCLUDED` exposes tax but does not add it again;
- `ADDED` increases amount due by calculated tax;
- tip is applied after tax;
- discount is applied consistently with receipt-core arithmetic;
- payment amount due equals frozen snapshot total.

Required finalization cases:

- public folio is generated once when the sale is finalized;
- snapshot uses that exact folio;
- sync payload uses that exact folio;
- snapshot is built once from the charged checkout state;
- `finalizePaidSale()` completes before cart reset;
- remote synchronization happens only after local finalization;
- local finalization failure leaves the cart and payment state intact;
- successful online sync never replaces the local folio;
- offline success still exposes the locally persisted receipt.

- [ ] **Step 2: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-settings-cache.test.js \
    pos/tests/receipt-checkout.test.js
```

Expected: FAIL because checkout is not yet wired to receipt settings, frozen tax totals, folio generation, or atomic receipt finalization.

- [ ] **Step 3: Load and cache effective receipt settings per branch**

Modify `pos/js/api.js` to expose:

```javascript
async function getReceiptSettings(branchCode)
```

It calls the Phase 1 effective receipt-settings endpoint for the active branch.

Modify `pos/js/db.js` with branch-scoped helpers:

```javascript
async function setReceiptSettings(branchCode, settings)
async function getReceiptSettings(branchCode)
```

Store settings in `meta` using a key equivalent to:

```text
receipt_settings:<branch-code>
```

Rules:

- validate settings before caching;
- normalize branch code consistently;
- never return another branch settings as fallback;
- preserve the last valid cached configuration when a refresh request fails;
- online refresh replaces the cache only after validation succeeds.

When the active branch loads:

1. read cached receipt settings;
2. make them immediately available when valid;
3. attempt an online refresh;
4. replace the cache only with a valid server response.

If neither cached nor online settings are available, mark checkout receipt configuration as unavailable.

- [ ] **Step 4: Use receipt-core as the single checkout tax calculator**

Modify `pos/js/app.js` so checkout totals are derived from `CofiPosReceipt.calculateTax()`.

Convert merchandise, discount, tax, tip, tendered amount, and change to integer cents before calculations.

The checkout result must contain:

```javascript
{
    subtotalCents,
    discountCents,
    taxMode,
    taxRate,
    taxCents,
    tipCents,
    totalCents
}
```

Rules:

- `NONE` does not add tax;
- `INCLUDED` reports the embedded tax without increasing amount due;
- `ADDED` adds tax before tip;
- payment modal displays the same `totalCents` later frozen into the receipt snapshot;
- cash tender/change calculations use that same final total;
- do not maintain a second tax formula in checkout code.

If effective receipt settings are unavailable, payment confirmation must remain disabled and the cart must remain untouched.

- [ ] **Step 5: Freeze the paid sale exactly once at payment confirmation**

Modify the `confirmPayment()` flow in `pos/js/app.js`.

After payment values are valid and before any remote request:

1. obtain the already-calculated checkout totals;
2. generate one public folio with `CofiPosFolio.generate()`;
3. capture one `sold_at` timestamp;
4. build one immutable snapshot with `CofiPosReceipt.buildSnapshot()`;
5. validate the snapshot;
6. build the final API/sync payload from those frozen values;
7. call `CofiPosDB.finalizePaidSale()`;
8. only after local transaction success, attempt remote synchronization.

Do not generate the folio earlier while the cart is still editable.
Do not generate another folio after network failure or retry.

The frozen snapshot must use:

- active branch effective receipt settings;
- active branch code and name;
- current terminal identifier;
- selected customer name only, or null;
- exact charged products and customer-visible modifiers;
- exact subtotal/discount/tax/tip/total;
- exact payment method;
- tendered amount and change when cash applies.

Never include internal kitchen/bar preparation notes in the customer snapshot.

- [ ] **Step 6: Persist locally before changing the checkout UI state**

The cart and payment state remain intact until `finalizePaidSale()` succeeds.

If local persistence fails:

- do not clear the cart;
- do not close payment as successful;
- do not call the server;
- display a recoverable local-save error;
- allow the cashier to retry without creating a second completed sale.

If local persistence succeeds:

- the sale is considered locally finalized;
- preserve its folio and receipt even when offline;
- attempt synchronization using the frozen queued payload;
- network failure changes only sync status, not sale identity or totals;
- clear the active cart only after local finalization is confirmed.

The success state must use the locally frozen folio and receipt, never a replacement generated from the server response.

- [ ] **Step 7: Load receipt modules and cache them for offline POS use**

Modify `pos/index.html` so receipt dependencies load before `app.js`:

- `js/folio.js`;
- `js/receipt-core.js`.

Preserve the existing script dependency order for DB, API, catalog, sync, Orders, station, and app modules.

Modify `pos/sw.js` so the Phase 1 offline shell includes:

- `js/folio.js`;
- `js/receipt-core.js`;
- any receipt-specific assets required by checkout.

Increment the service-worker cache version using the existing project naming convention.
Do not remove existing cached POS assets.

- [ ] **Step 8: Run GREEN and checkout regression**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-folio.test.js \
    pos/tests/receipt-core.test.js \
    pos/tests/receipt-storage.test.js \
    pos/tests/receipt-offline.test.js \
    pos/tests/receipt-settings-cache.test.js \
    pos/tests/receipt-checkout.test.js \
    pos/tests/payment-shortcuts.test.js \
    pos/tests/orders-local.test.js \
    pos/tests/orders-api.test.js
```

Expected: PASS.

- [ ] **Step 9: Commit Task 5 without staging unrelated POS redesign work**

Files `pos/js/app.js` and `pos/index.html` already contain unrelated uncommitted redesign changes.
Do not stage those files wholesale.

Stage clean Task 5 files normally:

```bash
git add \
  pos/js/api.js \
  pos/js/db.js \
  pos/sw.js \
  pos/tests/receipt-checkout.test.js \
  pos/tests/receipt-settings-cache.test.js
```

Stage only Task 5 hunks from dirty shared files:

```bash
git add -p pos/js/app.js
git add -p pos/index.html
```

Review staged content before committing:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached -- pos/js/app.js pos/index.html
```

Commit message:

```text
feat(pos): finalize sales with receipt snapshots
```

Do not stage `pos/css/pos.css`, `pos/js/orders.js`, or existing unrelated POS redesign tests.

---

### Task 6: Customer Receipt Renderer, Preview, and 80mm Printing

**Files:**
- Create: `pos/js/receipt-renderer.js`
- Create: `pos/css/receipt.css`
- Create: `pos/tests/receipt-renderer.test.js`
- Create: `pos/tests/receipt-print.test.js`
- Modify: `pos/index.html`
- Modify: `pos/js/app.js`
- Modify: `pos/sw.js`

**Interfaces:**

Produces:

- `CofiPosReceiptRenderer.render(snapshot, options)`;
- `CofiPosReceiptRenderer.open(snapshot, options)`;
- `CofiPosReceiptRenderer.print(snapshot)`;
- customer receipt preview modal;
- 80mm browser-print layout;
- post-payment actions: View Receipt, Print Receipt, New Sale.

Customer receipt content:

- business name and optional logo;
- branch name and configured contact/address;
- public folio;
- original sale date/time in configured branch timezone;
- customer name only when selected;
- products, quantities, charged prices, and visible modifiers;
- subtotal and discount;
- tax line according to configured mode;
- tip;
- final total;
- payment method;
- cash tendered and change when applicable;
- configured footer message.

Never render customer phone/email or internal kitchen/bar preparation notes.

Renderer must use the immutable snapshot only.
Do not query the current catalog or current receipt settings while rendering a historical receipt.

Printing is manual browser printing in Phase 1.

`auto_print` defaults to false.
When effective `auto_print` is true, successful local sale finalization may automatically open the normal browser print dialog once using the frozen receipt snapshot.
This is not silent printing: the browser print dialog remains in control.
Canceling or failing that print dialog never changes sale, receipt, payment, or synchronization state.
Orders reprints are always explicit user actions.
The auto-print trigger belongs only to the post-local-finalization success flow and must never run from synchronization callbacks.
Do not implement silent printing, Print Jobs, ESC/POS, or the local Print Bridge in this task.

---

- [ ] **Step 1: Write failing customer receipt renderer tests**

Create `pos/tests/receipt-renderer.test.js`.

Required rendering cases:

- renders business name;
- renders optional logo when `logo_ref` exists;
- still renders correctly when no logo exists;
- renders branch name, address, and configured contact information;
- renders exact public folio from snapshot;
- renders original `sold_at` using snapshot branch timezone;
- renders customer name when present;
- omits customer section when customer is null;
- renders product quantity, name, unit price, and line total;
- renders customer-visible modifiers and charged deltas;
- renders subtotal, discount, tax, tip, and final total;
- renders payment method;
- renders cash tendered and change only for applicable cash payment;
- renders configured footer message.

Privacy and isolation cases:

- customer phone is never rendered;
- customer email is never rendered;
- internal preparation notes are never rendered;
- current catalog values are never consulted;
- current receipt settings are never consulted;
- HTML-sensitive customer/product/settings text is safely escaped.

Tax presentation cases:

- `NONE` does not invent a tax charge;
- `INCLUDED` clearly shows tax as included;
- `ADDED` shows the frozen added tax amount;
- rendered total always equals snapshot final total.

- [ ] **Step 2: Write failing 80mm print and post-payment action tests**

Create `pos/tests/receipt-print.test.js`.

Required print cases:

- receipt stylesheet defines an 80mm print layout;
- `@media print` hides normal POS application chrome;
- only the customer receipt remains printable;
- print output does not include pending-sync UI labels;
- printing uses the already-frozen snapshot;
- offline printing does not require a server request;
- `print(snapshot)` renders the receipt before invoking browser print;
- browser print remains manual in Phase 1.

Required post-payment action cases:

- successful local finalization exposes `Ver ticket`;
- successful local finalization exposes `Imprimir ticket`;
- successful local finalization exposes `Nueva venta`;
- `Ver ticket` opens the receipt preview without changing the sale;
- `Imprimir ticket` prints the same frozen receipt;
- `Nueva venta` starts a fresh sale without deleting the completed receipt;
- pending synchronization may be visible on screen but is not printed.
- effective `auto_print = false` does not invoke browser print automatically;
- effective `auto_print = true` opens the browser print dialog exactly once after successful local finalization;
- synchronization retries or reconnects never reopen the print dialog;
- canceling or failing printing does not alter the finalized sale or sync queue.

- [ ] **Step 3: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-renderer.test.js \
    pos/tests/receipt-print.test.js
```

Expected: FAIL because the receipt renderer, preview, 80mm print layout, and post-payment receipt actions do not exist yet.

- [ ] **Step 4: Implement the snapshot-only customer receipt renderer**

Create `pos/js/receipt-renderer.js`.

Expose:

```javascript
window.CofiPosReceiptRenderer = {
    render,
    open,
    close,
    print
};
```

`render(snapshot)` must be deterministic and use only the supplied immutable snapshot.

Renderer sections, in order:

1. business/logo header;
2. branch contact/address;
3. folio and original sale date/time;
4. optional customer name;
5. item and modifier lines;
6. subtotal/discount/tax/tip/total;
7. payment details;
8. footer message.

Formatting rules:

- format money using snapshot currency;
- format time using snapshot branch timezone;
- escape all user/configurable text before inserting HTML;
- omit empty optional sections instead of printing blank labels;
- do not mutate the supplied snapshot.

- [ ] **Step 5: Implement dedicated 80mm receipt styles**

Create `pos/css/receipt.css`.

Screen preview must:

- remain readable on desktop, tablet, and phone;
- visually resemble the printed receipt;
- scroll internally when receipt content exceeds viewport height.

Print rules must include:

```css
@page {
    margin: 0;
}
```

Set the printable receipt container to `width: 80mm`; let the browser and thermal-printer driver control the roll page length.

Under `@media print`:

- hide all normal POS chrome;
- hide receipt modal controls;
- hide sync-status-only UI;
- print only the receipt document;
- use an 80mm paper width;
- avoid fixed viewport heights;
- avoid clipping long receipts;
- preserve black text suitable for thermal printers.

Do not depend on network fonts or remote assets for printable text.

- [ ] **Step 6: Add receipt preview and post-payment actions**

Modify `pos/index.html` and `pos/js/app.js`.

After successful local finalization, show:

- `Ver ticket`;
- `Imprimir ticket`;
- `Nueva venta`.

`Ver ticket` must:

- open the customer receipt modal;
- render the already-frozen snapshot;
- preserve current sync status;
- never modify order or receipt data.

`Imprimir ticket` must:

- use the same frozen snapshot;
- call `CofiPosReceiptRenderer.print(snapshot)`;
- work while offline;
- never trigger synchronization or rebuild receipt data.

`Nueva venta` must:

- close receipt/success UI;
- create a fresh empty cart state;
- preserve the completed local order and receipt;
- preserve pending sync queue state when offline.

Add the receipt modal markup to `pos/index.html` with:

- receipt document container;
- close control;
- print control;
- no editable receipt fields.

- [ ] **Step 7: Load renderer and receipt stylesheet offline**

Modify `pos/index.html` to load:

- `css/receipt.css`;
- `js/receipt-renderer.js` before `app.js`.

Modify `pos/sw.js` to cache both assets.
Increment cache version using the existing naming convention.

- [ ] **Step 8: Run GREEN and receipt regression**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/receipt-renderer.test.js \
    pos/tests/receipt-print.test.js \
    pos/tests/receipt-checkout.test.js \
    pos/tests/receipt-offline.test.js
```

Expected: PASS.

- [ ] **Step 9: Commit Task 6 without mixing existing redesign changes**

Stage new Task 6 files normally:

```bash
git add \
  pos/js/receipt-renderer.js \
  pos/css/receipt.css \
  pos/tests/receipt-renderer.test.js \
  pos/tests/receipt-print.test.js \
  pos/sw.js
```

Stage only Task 6 hunks from shared dirty files:

```bash
git add -p pos/index.html
git add -p pos/js/app.js
```

Then verify:

```bash
git diff --cached --check
git diff --cached --stat
```

Commit message:

```text
feat(pos): add customer receipt preview and printing
```

Do not stage `pos/css/pos.css`, `pos/js/orders.js`, or unrelated redesign tests.

---

### Task 7: View and Reprint Receipts from Orders

**Files:**
- Modify: `pos/js/api.js`
- Modify: `pos/js/orders-local.js`
- Modify: `pos/js/orders.js`
- Modify: `pos/index.html`
- Create: `pos/tests/order-receipt.test.js`
- Create: `pos/tests/order-receipt-offline.test.js`

**Interfaces:**

Produces:

- `CofiPosApi.getReceipt(orderUuid)`;
- receipt action inside Order detail;
- local-first receipt lookup for pending offline orders;
- server receipt lookup for synchronized orders;
- View Receipt and Reprint Receipt from Orders.

Receipt lookup order:

1. check IndexedDB `receipts` by `order_uuid`;
2. if found, use that immutable snapshot immediately;
3. if not found and online, request `GET /pos/receipts/{order_uuid}`;
4. validate the returned snapshot before rendering;
5. optionally cache a valid server snapshot locally for later offline viewing.

Never rebuild a receipt from the current catalog or current receipt settings.

Pending offline orders:

- receipt must remain viewable;
- receipt must remain printable;
- screen may show `Pendiente de sincronizar`;
- pending-sync text must not appear on printed receipt.

Synchronized modern orders:

- show `Ver ticket`;
- show `Reimprimir ticket`;
- use the original immutable snapshot and original folio.

Legacy orders created before receipt snapshots:

- do not fabricate a historical receipt from current settings;
- if no immutable snapshot exists, show a clear `Ticket no disponible para esta venta anterior` state;
- keep the rest of Order detail functional.

---

- [ ] **Step 1: Write failing Orders receipt tests**

Create `pos/tests/order-receipt.test.js`.

Required synchronized-order cases:

- Order detail exposes `Ver ticket` when immutable receipt exists;
- Order detail exposes `Reimprimir ticket` when immutable receipt exists;
- local IndexedDB receipt is preferred over server fetch;
- server fetch occurs only when no local receipt exists;
- valid server receipt is rendered with its original folio;
- valid server receipt may be cached locally after retrieval;
- reprint uses the same immutable snapshot;
- viewing/reprinting never changes order status or totals;
- current catalog and current receipt settings are never used to rebuild receipt data.

Server failure cases:

- receipt 404 leaves normal Order detail usable;
- malformed receipt response is rejected;
- network error shows receipt unavailable without breaking Orders;
- legacy order without snapshot shows `Ticket no disponible para esta venta anterior`.

Create `pos/tests/order-receipt-offline.test.js`.

Required pending/offline cases:

- pending local order finds receipt by `order_uuid`;
- pending local receipt opens while fully offline;
- pending local receipt can be printed while fully offline;
- original local folio is preserved;
- pending-sync indicator may display outside receipt document;
- pending-sync indicator is excluded from print output;
- no API request is attempted when a valid local receipt already exists.

- [ ] **Step 2: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/order-receipt.test.js \
    pos/tests/order-receipt-offline.test.js
```

Expected: FAIL because Orders does not yet expose immutable receipt lookup, preview, or reprint.

- [ ] **Step 3: Add receipt API and local-first resolver**

Modify `pos/js/api.js` to expose:

```javascript
async function getReceipt(orderUuid)
```

It calls:

```text
GET /pos/receipts/{order_uuid}
```

Add a receipt resolver used by Orders:

1. call `CofiPosDB.getReceipt(orderUuid)`;
2. validate local snapshot when present;
3. return local snapshot immediately when valid;
4. only when absent and online, call `CofiPosApi.getReceipt(orderUuid)`;
5. validate server snapshot;
6. cache valid server snapshot locally without changing it;
7. return immutable snapshot to the renderer.

Do not call the server when a valid local receipt already exists.
Do not rebuild missing receipts from catalog/settings.

- [ ] **Step 4: Add receipt actions to Order detail**

Modify `pos/js/orders.js` and existing Order detail markup.

For orders with an immutable receipt:

- show `Ver ticket`;
- show `Reimprimir ticket`.

`Ver ticket` calls `CofiPosReceiptRenderer.open(snapshot)`.
`Reimprimir ticket` calls `CofiPosReceiptRenderer.print(snapshot)`.

For pending local orders:

- preserve the existing pending-sync indicator;
- keep receipt actions available offline.

For legacy orders with no snapshot:

- show `Ticket no disponible para esta venta anterior`;
- do not disable or hide unrelated Order detail controls.

Receipt lookup errors must stay scoped to the receipt area and must not break Orders navigation.

- [ ] **Step 5: Run GREEN and Orders receipt regression**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test \
    pos/tests/order-receipt.test.js \
    pos/tests/order-receipt-offline.test.js \
    pos/tests/receipt-renderer.test.js \
    pos/tests/receipt-print.test.js \
    pos/tests/orders-local.test.js \
    pos/tests/orders-api.test.js
```

Expected: PASS.

- [ ] **Step 6: Commit Task 7 without mixing existing Orders redesign work**

Stage clean Task 7 files normally:

```bash
git add \
  pos/js/api.js \
  pos/js/orders-local.js \
  pos/tests/order-receipt.test.js \
  pos/tests/order-receipt-offline.test.js
```

Stage only Task 7 hunks from shared dirty files:

```bash
git add -p pos/js/orders.js
git add -p pos/index.html
```

Verify exactly what is staged:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached -- pos/js/orders.js pos/index.html
```

Commit message:

```text
feat(pos): add receipt reprints from orders
```

Do not stage unrelated POS redesign tests or `pos/css/pos.css`.

---

### Task 8: Admin Receipt and Tax Settings UI

**Files:**
- Create: `admin/receipt-settings.html`
- Modify: `admin/admin.js`
- Modify: `admin/admin.css`
- Create: `admin/tests/receipt-settings.test.js`

**Interfaces:**

Produces an admin screen for:

- business receipt defaults;
- branch-specific receipt overrides;
- tax configuration;
- receipt header/footer configuration;
- customer receipt auto-print preference.

Business-level editable fields:

- business name;
- optional logo reference;
- phone;
- web/social text;
- footer message;
- currency;
- tax mode: `NONE`, `INCLUDED`, or `ADDED`;
- tax rate;
- receipt width fixed to 80mm in Phase 1;
- timezone;
- folio prefix;
- customer receipt auto-print preference.

Branch override fields:

- display name;
- address;
- phone;
- web/social text;
- footer message;
- tax mode;
- tax rate;
- timezone;
- folio prefix;
- auto-print preference.

Each branch override field must support inheritance from business defaults.

UI must clearly distinguish:

- inherited value;
- branch override value;
- effective value used by the POS.

Tax UI rules:

- `NONE` forces effective rate to zero;
- `INCLUDED` and `ADDED` require a valid non-negative rate;
- invalid values cannot be saved;
- show percentage in human-readable form while preserving backend precision.

Do not add CFDI/fiscal invoice settings in Phase 1.
Do not add Kitchen/Bar Print Jobs or Print Bridge configuration here yet.

---

- [ ] **Step 1: Write failing admin receipt-settings tests**

Create `admin/tests/receipt-settings.test.js`.

Required business-settings cases:

- loads current business receipt defaults;
- displays business name, contact, footer, currency, timezone, and folio prefix;
- displays current tax mode and tax rate;
- saves valid business changes through the existing admin-authenticated API;
- shows backend validation errors without discarding typed values.

Required branch-override cases:

- loads available branches;
- selecting a branch loads its overrides and effective values;
- inherited fields are visually distinguishable from overridden fields;
- clearing an override restores inheritance;
- branch A changes never mutate branch B;
- effective preview updates after valid override changes.

Required tax-validation cases:

- `NONE` resolves effective rate to zero;
- `INCLUDED` accepts a valid non-negative percentage;
- `ADDED` accepts a valid non-negative percentage;
- negative tax rate is rejected;
- malformed tax rate is rejected;
- invalid timezone is rejected;
- invalid folio prefix is rejected;
- save remains disabled while client-side values are invalid.

Required scope cases:

- no CFDI/fiscal controls are shown;
- no Kitchen/Bar Print Job controls are shown;
- no Print Bridge controls are shown.

- [ ] **Step 2: Run RED**

During implementation run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/receipt-settings.test.js
```

Expected: FAIL because the admin receipt-settings screen does not exist yet.

- [ ] **Step 3: Implement the receipt-settings admin screen**

Create `admin/receipt-settings.html`.

The page must reuse the existing admin authentication/session behavior and existing admin visual shell.

Provide two configuration sections:

1. Business defaults;
2. Branch overrides.

Business form includes all Phase 1 business receipt fields defined in Task 1.

Branch section includes:

- branch selector;
- override controls for each nullable branch setting;
- inherited-value indicator;
- effective-value preview.

For nullable branch overrides:

- an empty override means inherit;
- do not copy the inherited value into the override field automatically;
- show the inherited/effective value separately.

Tax-rate input is displayed as a percentage for the administrator.
Backend/API `tax_rate` uses the decimal-fraction representation (`0.16` = 16%); the Admin UI converts between that value and the human-readable percentage.
Convert to the exact backend representation only at the API boundary.

- [ ] **Step 4: Wire admin loading, validation, and saves**

Modify `admin/admin.js`.

Use the Task 1 authenticated receipt-settings endpoints for:

- reading business defaults;
- updating business defaults;
- reading branch overrides/effective settings;
- updating branch overrides.

Re-use the existing admin branch source rather than creating a duplicate branch registry.

Client validation must mirror backend constraints for:

- tax mode;
- tax rate;
- timezone;
- folio prefix;
- required business name;
- 80mm Phase 1 receipt width.

After a successful save:

- reload the saved server representation;
- refresh inherited/effective values;
- show success feedback;
- do not claim success from local form state alone.

Modify `admin/admin.css` only for receipt-settings layout and inheritance/effective-value states.

- [ ] **Step 5: Run GREEN**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  node --test admin/tests/receipt-settings.test.js
```

Expected: PASS.

- [ ] **Step 6: Commit Task 8 exact files**

Stage only:

```bash
git add \
  admin/receipt-settings.html \
  admin/admin.js \
  admin/admin.css \
  admin/tests/receipt-settings.test.js

git diff --cached --check
git diff --cached --stat

git commit -m "feat(admin): configure customer receipt settings"
```

Do not stage POS files or unrelated admin work.

---

### Task 9: Phase 1 Full Verification and Acceptance Gate

**Goal:** Prove the complete customer receipt flow works without regressing existing POS, Orders, offline sales, Kitchen/Bar, or Admin behavior.

- [ ] **Step 1: Build a fresh backend verification image**

Run:

```bash
docker build \
  --target development \
  -t cofinet-backend-receipts:test \
  backend/
```

Expected: build succeeds using the real `development` Dockerfile target.

- [ ] **Step 2: Run the complete backend test suite**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  python -m pytest -q
```

Expected: PASS with zero failed tests.

Use `python -m pytest`, never the bare `pytest` console command.

- [ ] **Step 3: Verify the Alembic migration chain**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD/backend:/app" \
  -w /app \
  cofinet-backend-receipts:test \
  alembic heads
```

Expected final head:

```text
20260908_0002
```

Also verify:

- `20260908_0001` depends on existing production head `20260902_0002`;
- `20260908_0002` depends on `20260908_0001`;
- there is exactly one Alembic head;
- both migrations are additive;
- neither migration rewrites or deletes existing paid orders.

- [ ] **Step 4: Run the complete POS and Admin JavaScript suites**

Run:

```bash
docker run --rm \
  --network none \
  -v "$PWD:/work:ro" \
  -w /work \
  node:22-alpine \
  sh -lc "node --test pos/tests/*.test.js admin/tests/*.test.js"
```

Expected: PASS with zero failed tests.

Do not remove or skip existing Kitchen/Bar, Orders, mobile, payment, customer, or redesign tests to make this gate pass.

- [ ] **Step 5: Run manual checkout acceptance tests**

Use a non-production test branch/account and verify:

Tax mode `NONE`:

- sale completes;
- tax is zero;
- ticket total equals charged amount;
- View Receipt and Print Receipt work.

Tax mode `INCLUDED`:

- included tax is displayed;
- tax is not added twice;
- payment amount equals receipt total.

Tax mode `ADDED`:

- configured tax is added before tip;
- payment modal amount matches receipt total;
- cash tender/change uses the taxed final total.

Customer/privacy:

- selected customer prints name only;
- no customer phone or email appears;
- no internal Kitchen/Bar notes appear.

- [ ] **Step 6: Run manual offline acceptance tests**

After receipt settings and catalog have been cached:

1. disconnect network;
2. complete a sale;
3. confirm one local public folio is shown;
4. open the receipt;
5. print using browser print;
6. open the same sale from Orders;
7. confirm the same folio and totals remain;
8. reconnect network;
9. allow synchronization;
10. confirm the server keeps the same folio and frozen totals.

Also verify:

- retry does not create a duplicate sale;
- retry does not create a second receipt snapshot;
- pending-sync text is visible only in UI, not on the printed ticket.

- [ ] **Step 7: Run manual Orders and reprint acceptance tests**

Verify:

- modern synchronized order opens its original receipt;
- Reprint uses the original folio and totals;
- pending offline order opens and prints locally;
- legacy pre-snapshot order shows ticket unavailable without breaking Order detail.

- [ ] **Step 8: Run manual Admin receipt-settings acceptance tests**

Verify:

- business defaults save and reload;
- branch override saves and reloads;
- clearing an override restores inheritance;
- branch A overrides do not affect branch B;
- invalid tax rate cannot be saved;
- `NONE` produces effective zero tax;
- timezone and folio prefix validation work;
- POS receives the resulting effective settings.

- [ ] **Step 9: Inspect the physical/browser 80mm print preview**

Verify:

- receipt width is suitable for 80mm;
- long product names wrap without clipping;
- long receipts continue vertically;
- POS controls are absent from print output;
- sync status is absent from print output;
- optional missing logo does not leave a broken layout;
- printed text remains legible on a thermal-printer-style output.

- [ ] **Step 10: Verify Git integrity and preserve unrelated dirty work**

Run:

```bash
git diff --check
git diff --cached --check
git status --short
```

Expected:

- no whitespace errors introduced by Phase 1;
- no accidental staging of unrelated redesign files/tests;
- existing unrelated dirty POS redesign work remains present unless intentionally committed in its own prior scope.

Specifically inspect shared dirty files:

```bash
git diff -- pos/index.html
git diff -- pos/js/app.js
git diff -- pos/js/orders.js
git diff -- pos/css/pos.css
```

Confirm Phase 1 work did not reset or overwrite unrelated pre-existing redesign hunks.

- [ ] **Step 11: Verify Phase 1 scope boundaries**

Confirm implementation contains customer receipt functionality only.

Must exist:

- receipt settings;
- immutable receipt snapshots;
- client-generated public folio;
- offline receipt persistence;
- tax modes `NONE`, `INCLUDED`, `ADDED`;
- customer receipt preview;
- manual browser printing;
- Orders view/reprint;
- Admin receipt settings.

Must not exist yet:

- automatic Kitchen printer dispatch;
- automatic Bar printer dispatch;
- station Print Jobs;
- ESC/POS transport;
- USB/network printer bridge;
- silent printing daemon;
- CFDI or fiscal invoicing.

- [ ] **Step 12: Final acceptance gate before deployment**

Phase 1 is ready for deployment only when all of the following are true:

- backend full suite passes;
- POS full suite passes;
- Admin suite passes;
- Alembic has exactly one head at `20260908_0002`;
- manual online checkout passes;
- manual offline checkout and later sync pass;
- receipt preview and 80mm print preview pass;
- Orders reprint passes;
- Admin inheritance/settings tests pass;
- Git diff integrity checks pass;
- unrelated dirty redesign work is preserved.

Do not deploy from a partially passing state.
Do not run production migrations until the operator explicitly approves deployment.

---
