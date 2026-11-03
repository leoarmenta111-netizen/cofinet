# COFI Papelería POS, Sales & Cash Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the operational Papelería POS: held sales, barcode-first checkout, discounts with manager PIN, cash/card payment, inventory decrement, receipt snapshots, returns/cancellations, and a separate Papelería cash shift.

**Architecture:** Add a dedicated retail sales domain instead of reusing restaurant `PosOrder`. Checkout is server-authoritative and transactional: price items from catalog snapshots, authorize sensitive actions, lock/decrement inventory, record payment/cash ledger, and freeze a receipt snapshot in one controlled workflow. The new `papeleria/` frontend consumes these APIs and reuses COFI staff/cash session patterns without sharing restaurant cart/KDS logic.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, vanilla JavaScript, IndexedDB/localStorage only for recoverable client state, Node built-in test runner, pytest.

**Spec:** `docs/superpowers/specs/2026-11-03-cofi-papeleria-design.md`

## Global Constraints

- Phase 1 core/inventory plan must be implemented first.
- No production deployment during development.
- A held sale never changes inventory or cash.
- A paid sale is immutable; corrections are returns/cancellations, never hard deletes or in-place financial rewrites.
- Checkout, inventory movements and cash ledger entries must be idempotent.
- All discounts and price overrides require a Papelería `MANAGER` PIN.
- Returns, exchanges and cancellations require a Papelería `MANAGER` PIN.
- Supported payment methods are exactly `CASH` and `CARD` for V1.
- Card authorization remains external/manual in V1; store an optional external reference.
- Services do not decrement inventory.
- Exchanges are implemented as return + replacement sale.
- Papelería has its own cash shift because cash queries are scoped to `module_code=PAPELERIA`.
- The UI must be COFI-native and must not copy eleventa visuals.

## Review Focus

- Double-clicking checkout or retrying after a timeout must create only one paid sale, one inventory decrement set and one cash ledger entry.
- A held sale resumed after a catalog price change must be repriced at checkout unless the approved design explicitly freezes held-sale pricing; this plan chooses **reprice at checkout** and stores the final snapshot only when paid.
- A cashier cannot bypass a manager-approved discount by editing request payload fields; the server calculates and validates discounts.
- A partial return cannot exceed the quantity originally sold minus quantities already returned.
- Closing a Papelería cash shift must exclude Cafetería cash sales even on the same branch and terminal identifier.

---

### Task 1: Add retail sale, line, payment, return and receipt-snapshot models

**Files:**
- Create: `backend/alembic/versions/20261103_0004_retail_sales.py`
- Create: `backend/app/models/retail_sales.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/retail_sales.py`
- Test: `backend/tests/test_retail_sales_models.py`

**Interfaces:**
- Produces: `RetailSale` with `sale_uuid`, `branch_id`, `module_code=PAPELERIA`, `terminal_id`, `cashier_staff_id`, `status in {"HELD","PAID","PARTIALLY_RETURNED","RETURNED","CANCELLED"}`, `label`, `subtotal`, `discount_total`, `total`, `currency="MXN"`, `receipt_snapshot`, timestamps.
- Produces: `RetailSaleLine` with product/service snapshot fields: `item_id`, `item_type`, `sku`, `item_name`, `presentation_id`, `presentation_name`, `barcode`, `conversion_factor`, `quantity`, `unit_price`, `line_subtotal`, `discount_amount`, `line_total`, `unit_cost_snapshot`.
- Produces: `RetailPayment` with `payment_uuid`, `method in {"CASH","CARD"}`, `amount`, `amount_tendered`, `change_due`, `external_reference`.
- Produces: `RetailReturn` and `RetailReturnLine` referencing the original paid sale/line.
- Paid/cancelled/returned rows are never deleted.

- [ ] **Step 1: Write failing model tests for valid/invalid sale states and payment methods**

Include unique `sale_uuid`, unique `payment_uuid`, nonnegative totals and immutable relationship expectations.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_sales_models.py`

Expected: FAIL.

- [ ] **Step 3: Implement migration, models and schemas**

Store receipt snapshot as JSON on `RetailSale` only when status becomes `PAID`.

- [ ] **Step 4: Run model tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/20261103_0004_retail_sales.py backend/app/models/retail_sales.py backend/app/models/__init__.py backend/app/schemas/retail_sales.py backend/tests/test_retail_sales_models.py
git commit -m "feat(retail): add papeleria sale models"
```

### Task 2: Implement held sales

**Files:**
- Create: `backend/app/services/retail_sale_service.py`
- Create: `backend/app/api/retail_sales.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_retail_held_sales.py`

**Interfaces:**
- Produces: `RetailSaleService.hold(db, *, payload: RetailHeldSaleUpsert, staff: PosStaff, terminal_id: str) -> RetailSale`.
- Produces: `RetailSaleService.resume(db, *, sale_uuid: str, staff: PosStaff) -> RetailSale`.
- Produces endpoints:
  - `POST /retail/sales/held`
  - `PUT /retail/sales/held/{sale_uuid}`
  - `GET /retail/sales/held`
  - `GET /retail/sales/{sale_uuid}`
- Held-sale payload stores item/presentation identifiers and quantities plus optional label; checkout reprices against current catalog.
- Held sales do not create `RetailPayment`, inventory movements or cash ledger entries.

- [ ] **Step 1: Write failing held-sale tests**

Cover create, update, list scoped by branch/module, resume, and proof that stock does not change.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_held_sales.py`

Expected: FAIL.

- [ ] **Step 3: Implement held-sale service and API**

A cashier may only mutate held sales in their branch/module; manager is not required.

- [ ] **Step 4: Run held-sale tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retail_sale_service.py backend/app/api/retail_sales.py backend/app/main.py backend/tests/test_retail_held_sales.py
git commit -m "feat(retail): add held papeleria sales"
```

### Task 3: Implement server-authoritative checkout with discounts and inventory

**Files:**
- Modify: `backend/app/services/retail_sale_service.py`
- Modify: `backend/app/schemas/retail_sales.py`
- Modify: `backend/app/api/retail_sales.py`
- Modify: `backend/app/services/retail_inventory_service.py`
- Modify: `backend/app/services/pos_cash_service.py`
- Test: `backend/tests/test_retail_checkout.py`
- Test: `backend/tests/test_retail_checkout_idempotency.py`

**Interfaces:**
- Produces: `RetailSaleService.checkout(db, *, payload: RetailCheckoutRequest, staff: PosStaff, terminal_id: str, manager: PosStaff | None) -> RetailSale`.
- Produces: `POST /retail/sales/checkout`.
- `RetailCheckoutRequest` carries `sale_uuid`, optional `held_sale_uuid`, item/presentation IDs, quantities, optional requested line/sale discount, payment UUID/method, cash tendered or card reference, and manager credentials only when authorization is required.
- Server loads current catalog, calls `RetailPricingService.quote`, calculates discounts, locks inventory, writes `RetailSale`/lines/payment, inventory movements and cash ledger, then commits once.
- Cash checkout requires an OPEN Papelería shift for current branch/terminal.
- Card checkout does not change the cash ledger.
- Manager authorization uses `PosStaffService.authorize_manager(..., module_code=PAPELERIA)`.
- Cash ledger call: `PosCashService.append_ledger_entry(..., entry_type="RETAIL_SALE", amount=total, idempotency_key=f"retail-sale:{sale_uuid}", reference_type="retail_sale", reference_id=sale_uuid)`.

- [ ] **Step 1: Write failing checkout tests**

Include:
- cash sale with exact change;
- cash sale with change due;
- card sale with external reference;
- product inventory decrement using presentation conversion;
- service sale with tier pricing and no inventory movement;
- sale without an open Papelería cash shift rejected;
- Cafetería shift does not satisfy Papelería checkout;
- insufficient stock returns HTTP 409;
- discount without manager credentials returns 403/422;
- valid manager PIN records authorizer in audit;
- client-supplied price is ignored/rejected.

- [ ] **Step 2: Run checkout tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_checkout.py`

Expected: FAIL.

- [ ] **Step 3: Implement the minimal transactional checkout**

Do not commit inventory or cash separately from the sale. One database transaction owns all effects.

- [ ] **Step 4: Write duplicate-submission tests**

Add:
- `test_duplicate_sale_uuid_returns_same_paid_sale_without_double_stock`
- `test_duplicate_payment_uuid_does_not_duplicate_payment`
- `test_checkout_retry_does_not_duplicate_cash_ledger`

- [ ] **Step 5: Run checkout/idempotency tests**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_checkout.py backend/tests/test_retail_checkout_idempotency.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/retail_sale_service.py backend/app/schemas/retail_sales.py backend/app/api/retail_sales.py backend/app/services/retail_inventory_service.py backend/app/services/pos_cash_service.py backend/tests/test_retail_checkout.py backend/tests/test_retail_checkout_idempotency.py
git commit -m "feat(retail): add transactional papeleria checkout"
```

### Task 4: Freeze and reprint retail receipt snapshots

**Files:**
- Create: `backend/app/services/retail_receipt_service.py`
- Modify: `backend/app/services/retail_sale_service.py`
- Modify: `backend/app/api/retail_sales.py`
- Test: `backend/tests/test_retail_receipts.py`

**Interfaces:**
- Produces: `RetailReceiptService.build_snapshot(*, sale: RetailSale, branch, cashier, authorizer=None) -> dict`.
- Snapshot includes folio/sale UUID, sold_at, business/branch/terminal, cashier, line snapshots, subtotal, discounts, total, payment method/tendered/change/reference, and fiscal settings only when configured.
- Produces: `GET /retail/sales/{sale_uuid}/receipt`.
- Reprint always returns the stored snapshot; it never reconstructs historical prices/names from current catalog.

- [ ] **Step 1: Write failing receipt snapshot tests**

Change a product name/price after a paid sale and assert receipt output remains unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_receipts.py`

Expected: FAIL.

- [ ] **Step 3: Implement receipt snapshot creation and retrieval**

Build/freeze snapshot before final checkout commit.

- [ ] **Step 4: Run receipt tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retail_receipt_service.py backend/app/services/retail_sale_service.py backend/app/api/retail_sales.py backend/tests/test_retail_receipts.py
git commit -m "feat(retail): add immutable papeleria receipts"
```

### Task 5: Add manager-authorized returns, cancellations and exchange primitives

**Files:**
- Modify: `backend/app/services/retail_sale_service.py`
- Modify: `backend/app/schemas/retail_sales.py`
- Modify: `backend/app/api/retail_sales.py`
- Modify: `backend/app/models/pos_audit.py`
- Modify: `backend/app/services/pos_audit_service.py`
- Test: `backend/tests/test_retail_returns.py`
- Test: `backend/tests/test_retail_cancellations.py`

**Interfaces:**
- Produces: `RetailSaleService.return_items(db, *, sale_uuid, payload: RetailReturnRequest, staff, manager) -> RetailReturn`.
- Produces: `RetailSaleService.cancel_paid_sale(db, *, sale_uuid, payload: RetailCancellationRequest, staff, manager) -> RetailSale`.
- Produces endpoints:
  - `POST /retail/sales/{sale_uuid}/returns`
  - `POST /retail/sales/{sale_uuid}/cancel`
- Return quantity cannot exceed net remaining sold quantity.
- Product returns create positive `RETURN` inventory movements.
- Cancellation creates `CANCELLATION_REVERSAL` movements for remaining stock effect.
- Cash refund writes negative cash ledger entry; card refund records external/manual reference and does not automatically call a payment provider in V1.
- Exchange uses the return endpoint followed by a normal replacement checkout.
- Audit event stores actor, manager authorizer, reason, sale ID, quantities and monetary effect.

- [ ] **Step 1: Write failing authorization and quantity-bound tests**

Include manager PIN required, partial return, repeated partial return limit, service return with no stock effect, and cancellation never deleting original sale.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_returns.py backend/tests/test_retail_cancellations.py`

Expected: FAIL.

- [ ] **Step 3: Implement return/cancellation services and API**

Use idempotency keys per return/cancellation to avoid duplicate refund effects.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/retail_sale_service.py backend/app/schemas/retail_sales.py backend/app/api/retail_sales.py backend/app/models/pos_audit.py backend/app/services/pos_audit_service.py backend/tests/test_retail_returns.py backend/tests/test_retail_cancellations.py
git commit -m "feat(retail): add authorized returns and cancellations"
```

### Task 6: Build the COFI Papelería POS shell and scanner-first sale workspace

**Files:**
- Create: `papeleria/index.html`
- Create: `papeleria/css/papeleria.css`
- Create: `papeleria/js/api.js`
- Create: `papeleria/js/app.js`
- Create: `papeleria/js/scanner.js`
- Create: `papeleria/js/sale.js`
- Create: `papeleria/js/receipt.js`
- Create: `papeleria/manifest.webmanifest`
- Create: `papeleria/sw.js`
- Create: `papeleria/tests/scanner.test.js`
- Create: `papeleria/tests/sale.test.js`
- Create: `papeleria/tests/payment.test.js`
- Create: `papeleria/tests/held-sales.test.js`
- Create: `papeleria/tests/pwa.test.js`

**Interfaces:**
- Persistent scan/search input calls `GET /retail/catalog/search`.
- Exact barcode match adds the matching presentation directly.
- `CofiRetailSale` owns client cart state and exposes `addItem`, `setQuantity`, `removeLine`, `hold`, `resume`, `checkout`.
- Payment UI offers CASH and CARD only.
- Discount action opens manager PIN overlay and sends authorization to server; PIN is never persisted.
- Current Papelería staff and shift status are always visible.
- Held-sales drawer lists/resumes server-held sales.
- Receipt printing consumes stored receipt snapshot.
- Desktop/scanner use is primary; layout remains usable on tablet.

- [ ] **Step 1: Write failing Node tests for scanner and sale-domain behavior**

Run:
`node --test papeleria/tests/scanner.test.js papeleria/tests/sale.test.js`

Expected: FAIL because modules do not exist.

- [ ] **Step 2: Implement scanner and sale domain modules**

Keep DOM rendering separate from price/business rules; server remains authoritative.

- [ ] **Step 3: Write failing payment/held-sale tests**

Test manager overlay payload, CASH/CARD payloads, no PIN persistence, held-sale resume, and manager-authorized inventory adjustment payloads.

- [ ] **Step 4: Implement UI shell and API adapter**

Use COFI visual language but a dense retail table, large total, persistent search field and service quick buttons.

- [ ] **Step 5: Add receipt rendering and PWA assets**

Do not precache live API data.

- [ ] **Step 6: Run Papelería frontend tests**

Run:
`node --test papeleria/tests/*.test.js`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add papeleria/
git commit -m "feat(retail): add cofi papeleria pos workspace"
```

### Task 7: POS/cash end-to-end regression gate

**Files:**
- No product files unless verification exposes a defect.

**Interfaces:**
- Consumes all Phase 1 and Phase 2 interfaces.
- Produces a verified Papelería sale lifecycle ready for admin/reporting work.

- [ ] **Step 1: Run complete backend tests**

`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q`

Expected: PASS.

- [ ] **Step 2: Run all Papelería frontend tests**

`node --test papeleria/tests/*.test.js`

Expected: PASS.

- [ ] **Step 3: Run existing POS frontend tests to detect Cafetería regressions**

`node --test pos/tests/*.test.js`

Expected: PASS.
