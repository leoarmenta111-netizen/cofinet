# COFI Papelería Administration & Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the global COFI administrator one central place to manage Papelería products/services, stock, staff, sales history, authorizations and operational reports without mixing Papelería totals into Cafetería.

**Architecture:** Add `/admin/retail/*` APIs protected by the existing global admin security and a dedicated `admin/papeleria.html` workspace. Reporting queries read retail sales/inventory/cash/audit data scoped to `PAPELERIA`; existing Cafetería admin pages remain unchanged.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Pydantic, vanilla JavaScript, Node built-in test runner, pytest.

**Spec:** `docs/superpowers/specs/2026-11-03-cofi-papeleria-design.md`

## Global Constraints

- Core/inventory and POS/sales plans must be implemented first.
- Global administrators can manage both modules; POS employees remain module-exclusive.
- Admin APIs use existing global admin authentication, not a cashier PIN.
- POS sensitive actions still require a Papelería manager PIN and are auditable.
- Manual inventory entry/removal/adjustment requires a reason.
- No hard delete of financial sales, returns, payments, inventory movements or audit events.
- Reports default to Papelería-only data.
- A consolidated Cafetería + Papelería dashboard is optional and not part of V1.
- Purchases/suppliers, customer credit and computer rental remain out of scope.

## Review Focus

- Report totals must not include Cafetería rows even when date/branch/terminal overlap.
- Inventory valuation must use current quantity on hand and configured item cost without converting through `float`.
- Gross margin must exclude or clearly identify rows with missing cost rather than silently treating unknown cost as zero.
- Sales-history return/cancel actions must preserve the original transaction and show status/history instead of mutating it away.
- An admin adjusting stock twice with the same idempotency key must not create duplicate movement.

---

### Task 1: Add global-admin retail catalog management APIs

**Files:**
- Create: `backend/app/api/admin_retail_catalog.py`
- Create: `backend/app/services/admin_retail_catalog_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin_retail_catalog.py`

**Interfaces:**
- Produces endpoints:
  - `GET /admin/retail/catalog`
  - `POST /admin/retail/catalog/items`
  - `PATCH /admin/retail/catalog/items/{item_id}`
  - `POST /admin/retail/catalog/items/{item_id}/presentations`
  - `PATCH /admin/retail/catalog/presentations/{presentation_id}`
  - `PUT /admin/retail/catalog/items/{item_id}/service-tiers`
- Item create/update supports PRODUCT/SERVICE fields from the spec.
- Service-tier replacement validates no overlapping ranges and exactly one open-ended final tier when the service uses open-ended pricing.
- Presentation create/update validates branch, item type, conversion and barcode uniqueness.

- [ ] **Step 1: Write failing admin catalog API tests**

Cover admin auth, product/presentation CRUD, service tiers, duplicate barcode and invalid overlapping tiers.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_admin_retail_catalog.py`

Expected: FAIL.

- [ ] **Step 3: Implement service/router and register router**

Do not add supplier/purchase fields.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin_retail_catalog.py backend/app/services/admin_retail_catalog_service.py backend/app/main.py backend/tests/test_admin_retail_catalog.py
git commit -m "feat(retail-admin): add papeleria catalog management"
```

### Task 2: Add admin stock adjustment and Kardex APIs

**Files:**
- Create: `backend/app/api/admin_retail_inventory.py`
- Create: `backend/app/services/admin_retail_inventory_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin_retail_inventory.py`

**Interfaces:**
- Produces endpoints:
  - `GET /admin/retail/inventory`
  - `GET /admin/retail/inventory/{item_id}/movements`
  - `POST /admin/retail/inventory/{item_id}/entries`
  - `POST /admin/retail/inventory/{item_id}/removals`
  - `POST /admin/retail/inventory/{item_id}/adjustments`
- Entry/removal/adjustment payloads require `reason` and `idempotency_key`.
- Admin service calls `RetailInventoryService.apply_movement`; it does not directly assign `quantity_on_hand`.
- Movement stores `created_by_admin_id`.

- [ ] **Step 1: Write failing tests**

Cover required reason, positive entry/removal quantities, physical-count adjustment, duplicate idempotency key and immutable movement history.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_admin_retail_inventory.py`

Expected: FAIL.

- [ ] **Step 3: Implement admin inventory router/service**

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin_retail_inventory.py backend/app/services/admin_retail_inventory_service.py backend/app/main.py backend/tests/test_admin_retail_inventory.py
git commit -m "feat(retail-admin): add stock adjustments and kardex"
```

### Task 3: Add Papelería staff management in the existing admin flow

**Files:**
- Modify: `backend/app/schemas/pos_staff.py`
- Modify: `backend/app/services/pos_staff_service.py`
- Modify: `backend/app/api/admin_pos_staff.py`
- Modify: `admin/staff.html`
- Modify: `admin/admin.js` only if shared API/navigation helpers are needed
- Modify: `admin/tests/staff-ui.test.js`
- Test: `backend/tests/test_admin_pos_staff.py`

**Interfaces:**
- Admin staff create/update/list supports `module_code`.
- UI filters employees by `CAFE` or `PAPELERIA`.
- A Papelería cashier/manager row visibly identifies the module.
- Global admin can create/reset PIN/disable both module types.
- Existing staff rows continue to display as Cafetería because migration default is `CAFE`.

- [ ] **Step 1: Add failing backend tests for module-specific staff CRUD**

- [ ] **Step 2: Implement backend schema/service/API changes**

- [ ] **Step 3: Add failing staff admin UI tests for module selector/filter**

Run:
`node --test admin/tests/staff-ui.test.js`

Expected: FAIL before UI change.

- [ ] **Step 4: Implement the module selector/filter in `admin/staff.html`**

Do not create a second administrator authentication system.

- [ ] **Step 5: Run backend and UI tests**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_admin_pos_staff.py`

and:
`node --test admin/tests/staff-ui.test.js`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/pos_staff.py backend/app/services/pos_staff_service.py backend/app/api/admin_pos_staff.py admin/staff.html admin/admin.js admin/tests/staff-ui.test.js backend/tests/test_admin_pos_staff.py
git commit -m "feat(retail-admin): manage papeleria staff"
```

### Task 4: Add retail sales history and audit APIs

**Files:**
- Create: `backend/app/api/admin_retail_sales.py`
- Create: `backend/app/services/admin_retail_sales_service.py`
- Create: `backend/app/schemas/admin_retail_sales.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin_retail_sales.py`

**Interfaces:**
- Produces: `GET /admin/retail/sales` filters `folio/sale_uuid`, date range, cashier, payment method, product/item and status.
- Produces: `GET /admin/retail/sales/{sale_uuid}`.
- Produces: `GET /admin/retail/audit` filters event type/date/staff/authorizer/target.
- Sale detail includes payment, returns, cancellation status, receipt snapshot and inventory effects.
- Admin history endpoints are read-only; return/cancel mutations continue to use the audited retail sale service.

- [ ] **Step 1: Write failing sales-history filter tests**

Include overlapping Cafetería data and prove no Cafetería rows appear. Also cover global-admin partial return/cancel authorization, required reason, idempotency, inventory restoration, and preservation of the original sale.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_admin_retail_sales.py`

Expected: FAIL.

- [ ] **Step 3: Implement sales/audit query service and router**

Use indexed date/status/staff/payment columns; avoid N+1 loading for lines/payments.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin_retail_sales.py backend/app/services/admin_retail_sales_service.py backend/app/schemas/admin_retail_sales.py backend/app/main.py backend/tests/test_admin_retail_sales.py
git commit -m "feat(retail-admin): add papeleria sales and audit history"
```

### Task 5: Add Papelería operational reports

**Files:**
- Create: `backend/app/api/admin_retail_reports.py`
- Create: `backend/app/services/retail_report_service.py`
- Create: `backend/app/schemas/retail_reports.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_retail_reports.py`

**Interfaces:**
- Produces endpoints:
  - `GET /admin/retail/reports/sales-summary`
  - `GET /admin/retail/reports/items`
  - `GET /admin/retail/reports/services`
  - `GET /admin/retail/reports/margin`
  - `GET /admin/retail/reports/inventory`
  - `GET /admin/retail/reports/cash-shifts`
  - `GET /admin/retail/reports/authorizations`
  - `GET /admin/retail/reports/returns-cancellations`
- Sales summary returns totals by date, cashier and payment method.
- Inventory report returns current stock, low-stock status and valuation.
- Margin report returns revenue, known cost and gross margin; rows with unknown cost expose `cost_complete=false`.
- Cash-shift report includes opening, cash sales, movements, expected, counted and variance for `PAPELERIA` only.

- [ ] **Step 1: Write failing report aggregation tests**

Use known fixtures with both CAFE and PAPELERIA data and exact expected totals.

- [ ] **Step 2: Run tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_reports.py`

Expected: FAIL.

- [ ] **Step 3: Implement report service and API**

All monetary aggregation stays `Decimal`.

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin_retail_reports.py backend/app/services/retail_report_service.py backend/app/schemas/retail_reports.py backend/app/main.py backend/tests/test_retail_reports.py
git commit -m "feat(retail-admin): add papeleria operational reports"
```

### Task 6: Build the central COFI Papelería admin workspace

**Files:**
- Create: `admin/papeleria.html`
- Create: `admin/papeleria.js`
- Modify: `admin/admin.css`
- Modify: `admin/dashboard.html`
- Create: `admin/tests/papeleria-admin.test.js`
- Create: `admin/tests/papeleria-reports.test.js`

**Interfaces:**
- Dashboard adds a COFI Papelería entry visible to global admin.
- `admin/papeleria.html` contains tabs/sections for Catalog, Services, Inventory/Kardex, Sales, Reports and Audit.
- Catalog UI creates products, presentations, barcodes, costs, normal/bulk pricing and service tiers.
- Inventory UI exposes current/low stock plus admin-only entry/removal/adjustment with mandatory reason.
- Sales UI filters history, opens sale detail, reprints stored receipt, and exposes global-admin return/cancel actions with required reason.
- Reports UI consumes the endpoints from Task 5.
- No Cafetería totals are shown in Papelería report cards.

- [ ] **Step 1: Write failing admin navigation/catalog/inventory UI tests**

Run:
`node --test admin/tests/papeleria-admin.test.js`

Expected: FAIL.

- [ ] **Step 2: Implement admin page shell, navigation and API adapter**

- [ ] **Step 3: Write failing report rendering tests**

Run:
`node --test admin/tests/papeleria-reports.test.js`

Expected: FAIL.

- [ ] **Step 4: Implement reports/audit/sales history views**

- [ ] **Step 5: Run admin tests**

Run:
`node --test admin/tests/*.test.js`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add admin/papeleria.html admin/papeleria.js admin/admin.css admin/dashboard.html admin/tests/papeleria-admin.test.js admin/tests/papeleria-reports.test.js
git commit -m "feat(retail-admin): add cofi papeleria administration"
```

### Task 7: Operational-pilot verification

**Files:**
- Create: `docs/operations/cofi-papeleria-pilot-checklist.md`
- No production deployment.

**Interfaces:**
- Produces a repeatable pre-production checklist covering the complete success criteria in the approved design.

- [ ] **Step 1: Run complete backend regression suite**

`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q`

Expected: PASS.

- [ ] **Step 2: Run Cafetería POS, Papelería POS and admin frontend tests**

```bash
node --test pos/tests/*.test.js
node --test papeleria/tests/*.test.js
node --test admin/tests/*.test.js
```

Expected: PASS.

- [ ] **Step 3: Write the pilot checklist**

Checklist must verify:
1. Papelería employee can only enter Papelería.
2. Cafetería employee cannot enter Papelería.
3. Admin can manage both.
4. Papelería cash shift opens independently.
5. Barcode/SKU/name/category search works.
6. Piece/package conversion decrements exact stock.
7. Service tier price changes at exact quantity boundary.
8. Held sale has no stock effect until checkout.
9. CASH and CARD checkout work.
10. Manager PIN is required for discounts.
11. Manager PIN is required for return/cancel.
12. Return restores stock correctly.
13. Receipt reprint preserves original snapshot.
14. Inventory/Kardex movement history is complete.
15. Papelería reports exclude Cafetería totals.
16. Cash close expected/count/variance reconcile.

- [ ] **Step 4: Commit**

```bash
git add docs/operations/cofi-papeleria-pilot-checklist.md
git commit -m "docs(retail): add papeleria pilot checklist"
```
