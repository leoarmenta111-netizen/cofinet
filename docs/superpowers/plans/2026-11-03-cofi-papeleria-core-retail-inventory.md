# COFI Papelería Core Retail & Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the module-aware retail foundation for COFI Papelería: isolated staff/cash/audit context, retail catalog, presentations, service pricing tiers, barcode search, and transactional inventory.

**Architecture:** Keep Cafetería behavior intact and add a dedicated `retail` domain for Papelería. Reuse existing POS staff, cash and audit infrastructure by adding an explicit operational module discriminator; create separate retail catalog/inventory models so restaurant orders, KDS routing, modifiers and self-order remain untouched.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-11-03-cofi-papeleria-design.md`

## Global Constraints

- No production deployment during initial development.
- Database changes go through Alembic.
- Existing Cafetería staff, cash, audit, POS orders, KDS and self-order behavior must remain backward-compatible.
- Operational modules are exactly `CAFE` and `PAPELERIA` in V1.
- Papelería employees cannot authenticate into Cafetería and Cafetería employees cannot authenticate into Papelería.
- Global administrator access remains separate from POS employee PIN sessions.
- Inventory movements are immutable; quantity changes happen only by appending movements.
- Money uses two decimal places; inventory quantities/conversion factors use `Decimal` and support three decimal places.
- Products and services are separate retail item kinds; services never decrement stock in V1.
- Purchases, suppliers, customer credit, abonos and computer rental are out of scope.
- Do not copy eleventa code, assets, branding or visual trade dress.

## Review Focus

- A valid Cafetería token must not be accepted by Papelería endpoints, and a Papelería token must not be accepted by Cafetería endpoints.
- Two simultaneous inventory mutations for the same item must serialize and produce the correct final balance.
- The same barcode may exist in another branch but must be unique within one branch/module.
- Presentation conversion must never use binary floating-point arithmetic; selling a box of 12 decrements exactly `12.000` base units.
- Service tier boundaries must be deterministic: for tiers 1–20 and 21–100, quantity 20 uses the first price and 21 uses the second.

---

### Task 1: Add operational-module isolation to staff, cash and audit

**Files:**
- Create: `backend/app/domain/operational_module.py`
- Create: `backend/alembic/versions/20261103_0001_papeleria_module_context.py`
- Modify: `backend/app/models/pos_staff.py`
- Modify: `backend/app/models/pos_cash.py`
- Modify: `backend/app/models/pos_audit.py`
- Modify: `backend/app/auth/pos_staff_security.py`
- Modify: `backend/app/schemas/pos_staff.py`
- Modify: `backend/app/services/pos_staff_service.py`
- Modify: `backend/app/services/pos_cash_service.py`
- Modify: `backend/app/services/pos_audit_service.py`
- Modify: `backend/app/api/pos_staff.py`
- Modify: `backend/app/api/admin_pos_staff.py`
- Test: `backend/tests/test_pos_staff_module_isolation.py`
- Test: `backend/tests/test_pos_cash_module_isolation.py`
- Test: `backend/tests/test_pos_audit.py`

**Interfaces:**
- Produces: `OperationalModule(str, Enum)` with `CAFE = "CAFE"` and `PAPELERIA = "PAPELERIA"`.
- Produces: `PosStaff.module_code: str`, default/server-default `CAFE`.
- Produces: `PosCashShift.module_code: str`, default/server-default `CAFE`.
- Produces: `PosAuditEvent.module_code: str`, default/server-default `CAFE`.
- Changes: staff access tokens include `module_code`.
- Changes: `PosStaffService.verify_pin(..., module_code: OperationalModule = OperationalModule.CAFE) -> PosStaff`.
- Changes: `PosStaffService.authorize_manager(..., module_code: OperationalModule = OperationalModule.CAFE) -> PosStaff`.
- Changes: `PosCashService.current_shift(..., module_code: OperationalModule = OperationalModule.CAFE) -> PosCashShift | None`.
- Changes: active cash-shift uniqueness becomes `(branch_id, terminal_id, module_code)`.
- Existing Cafetería callers that omit module continue to resolve to `CAFE`.

- [ ] **Step 1: Write failing staff module-isolation tests**

Add tests named:
- `test_cafe_staff_token_defaults_to_cafe_module`
- `test_papeleria_staff_token_contains_papeleria_module`
- `test_papeleria_staff_cannot_unlock_cafe_session`
- `test_cafe_staff_cannot_unlock_papeleria_session`

Assert exact HTTP 403/401 behavior for cross-module attempts and successful same-module unlock.

- [ ] **Step 2: Run the staff tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_pos_staff_module_isolation.py`

Expected: FAIL because module context does not exist yet.

- [ ] **Step 3: Add the operational-module enum, migration, model fields and token claim**

The migration must backfill existing rows with `CAFE` before making the fields non-null. Rebuild the active-shift unique index to include `module_code`.

- [ ] **Step 4: Make staff verification and cash/audit services module-aware**

Existing Cafetería routes must keep their current behavior through the `CAFE` default. Papelería-specific callers will pass `PAPELERIA`.

- [ ] **Step 5: Add cash and audit regression tests**

Add:
- `test_cafe_and_papeleria_can_have_separate_active_shift_on_same_terminal_id`
- `test_cash_shift_lookup_is_scoped_by_module`
- `test_audit_event_records_module_code`

- [ ] **Step 6: Run staff/cash/audit tests**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_pos_staff_auth.py backend/tests/test_pos_staff_module_isolation.py backend/tests/test_pos_cash_shifts.py backend/tests/test_pos_cash_module_isolation.py backend/tests/test_pos_audit.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/domain/operational_module.py backend/alembic/versions/20261103_0001_papeleria_module_context.py backend/app/models/pos_staff.py backend/app/models/pos_cash.py backend/app/models/pos_audit.py backend/app/auth/pos_staff_security.py backend/app/schemas/pos_staff.py backend/app/services/pos_staff_service.py backend/app/services/pos_cash_service.py backend/app/services/pos_audit_service.py backend/app/api/pos_staff.py backend/app/api/admin_pos_staff.py backend/tests/test_pos_staff_module_isolation.py backend/tests/test_pos_cash_module_isolation.py backend/tests/test_pos_audit.py
git commit -m "feat(retail): add module-isolated staff cash and audit"
```

### Task 2: Add the Papelería retail catalog and presentation model

**Files:**
- Create: `backend/alembic/versions/20261103_0002_retail_catalog.py`
- Create: `backend/app/models/retail_catalog.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/retail_catalog.py`
- Create: `backend/app/schemas/admin_retail_catalog.py`
- Create: `backend/app/services/retail_catalog_service.py`
- Create: `backend/app/services/retail_pricing_service.py`
- Test: `backend/tests/test_retail_catalog_models.py`
- Test: `backend/tests/test_retail_pricing.py`

**Interfaces:**
- Produces: `RetailCatalogItem` with `item_type in {"PRODUCT","SERVICE"}`, `branch_id`, `sku`, `name`, `description`, `category`, `base_unit_code`, `cost`, `inventory_tracked`, `low_stock_threshold`, `max_stock`, `is_active`.
- Produces: `RetailPresentation` with `item_id`, `branch_id`, `name`, `barcode`, `conversion_factor`, `sale_price`, `bulk_price`, `bulk_min_quantity`, `is_default`, `is_active`.
- Produces: `RetailServicePriceTier` with `item_id`, `min_quantity`, `max_quantity | None`, `unit_price`.
- Constraint: presentations are allowed only for `PRODUCT` items; service tiers are allowed only for `SERVICE` items.
- Constraint: `(branch_id, barcode)` is unique when barcode is non-null.
- Constraint: `conversion_factor > 0`.
- Produces: `RetailPriceQuote(unit_price: Decimal, line_total: Decimal, pricing_rule: str)`.
- Produces: `RetailPricingService.quote(db, *, item: RetailCatalogItem, quantity: Decimal, presentation_id: int | None = None) -> RetailPriceQuote`.

- [ ] **Step 1: Write failing catalog model tests**

Cover:
- product with piece/box presentations;
- branch-scoped barcode uniqueness;
- service without presentation;
- rejection of zero/negative conversion factors;
- inactive item behavior.

- [ ] **Step 2: Run catalog tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_catalog_models.py`

Expected: FAIL because retail catalog models do not exist.

- [ ] **Step 3: Implement migration and retail catalog models**

Use `Numeric(14, 3)` for conversion factors/quantities and `Numeric(12, 2)` for money.

- [ ] **Step 4: Write failing pricing tests**

Add:
- `test_product_uses_sale_price_before_bulk_threshold`
- `test_product_uses_bulk_price_at_threshold`
- `test_service_tier_boundary_20_and_21`
- `test_service_uses_open_ended_final_tier`
- `test_quote_accepts_positive_decimal_quantity_without_float_rounding`\n- `test_quote_rejects_zero_or_negative_quantity`

- [ ] **Step 5: Implement `RetailPricingService.quote`**

For products, use the selected/default presentation and bulk threshold. For services, choose exactly one matching tier. Quantize money to `0.01` and never cast price math through `float`.

- [ ] **Step 6: Run catalog and pricing tests**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_catalog_models.py backend/tests/test_retail_pricing.py`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions/20261103_0002_retail_catalog.py backend/app/models/retail_catalog.py backend/app/models/__init__.py backend/app/schemas/retail_catalog.py backend/app/schemas/admin_retail_catalog.py backend/app/services/retail_catalog_service.py backend/app/services/retail_pricing_service.py backend/tests/test_retail_catalog_models.py backend/tests/test_retail_pricing.py
git commit -m "feat(retail): add papeleria catalog and pricing"
```

### Task 3: Add transactional retail inventory and immutable movements

**Files:**
- Create: `backend/alembic/versions/20261103_0003_retail_inventory.py`
- Create: `backend/app/models/retail_inventory.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/retail_inventory.py`
- Create: `backend/app/services/retail_inventory_service.py`
- Test: `backend/tests/test_retail_inventory_models.py`
- Test: `backend/tests/test_retail_inventory_service.py`
- Reference only: `backend/app/models/pos_inventory.py` from `feature/cofi-pos-inventory`
- Reference only: `backend/app/services/pos_inventory_service.py` from `feature/cofi-pos-inventory`

**Interfaces:**
- Produces: `RetailInventoryBalance(branch_id, item_id, quantity_on_hand, low_stock_threshold, max_stock)`.
- Produces: `RetailInventoryMovement` with types `INITIAL`, `MANUAL_ENTRY`, `MANUAL_REMOVAL`, `ADJUSTMENT`, `SALE`, `RETURN`, `CANCELLATION_REVERSAL`.
- Movement stores `quantity_delta`, `balance_after`, optional `sale_id`, `sale_line_id`, `note`, `actor_staff_id`, `authorizer_staff_id`, `created_by_admin_id`, `idempotency_key`.
- Produces: `RetailInventoryService.apply_movement(db, *, balance, movement_type, quantity_delta, idempotency_key=None, note=None, actor_staff_id=None, authorizer_staff_id=None, created_by_admin_id=None, sale_id=None, sale_line_id=None) -> RetailInventoryMovement`.
- Produces: `RetailInventoryService.decrement_for_sale(db, *, item, presentation, quantity, sale_id, sale_line_id, idempotency_key) -> RetailInventoryMovement | None`.
- Products with `inventory_tracked=False` and all `SERVICE` items return `None` and do not create inventory movement.
- Default policy: sale cannot drive stock below zero; return/authorized adjustment may restore stock.

- [ ] **Step 1: Write failing inventory tests**

Cover:
- initial balance;
- manual entry/removal;
- adjustment to physical count;
- immutable movement history;
- low-stock status;
- service item ignored by inventory;
- presentation conversion `2 boxes * 12 = -24.000`;
- duplicate idempotency key does not double-apply;
- insufficient stock raises HTTP 409.

- [ ] **Step 2: Run inventory tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_inventory_models.py backend/tests/test_retail_inventory_service.py`

Expected: FAIL.

- [ ] **Step 3: Implement inventory models and service using the proven locking/idempotency pattern from the old inventory branch**

Lock the balance row with `SELECT ... FOR UPDATE` before reading or changing `quantity_on_hand`.

- [ ] **Step 4: Add the concurrency regression test**

Create `test_two_competing_sales_cannot_oversell_same_balance`. The test must prove that when stock is 10 and two transactions each request 8 with negative stock disabled, only one succeeds.

- [ ] **Step 5: Run the inventory suite**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_inventory_models.py backend/tests/test_retail_inventory_service.py`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/20261103_0003_retail_inventory.py backend/app/models/retail_inventory.py backend/app/models/__init__.py backend/app/schemas/retail_inventory.py backend/app/services/retail_inventory_service.py backend/tests/test_retail_inventory_models.py backend/tests/test_retail_inventory_service.py
git commit -m "feat(retail): add transactional papeleria inventory"
```

### Task 4: Add retail catalog/search and stock-read APIs

**Files:**
- Create: `backend/app/api/retail_catalog.py`
- Create: `backend/app/api/retail_inventory.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/retail_catalog_service.py`
- Test: `backend/tests/test_retail_catalog_api.py`
- Test: `backend/tests/test_retail_inventory_api.py`

**Interfaces:**
- Produces: `GET /retail/catalog/search?branch_code=&q=&limit=` requiring a `PAPELERIA` staff token.
- Search matches exact barcode first, then SKU/name/category/presentation.
- Exact barcode result includes the matching presentation and `exact_barcode_match=true`.
- Produces: `GET /retail/catalog/items/{item_id}`.
- Produces: `GET /retail/inventory?branch_code=&status=` for employee stock lookup.
- Produces: `GET /retail/inventory/{item_id}/movements` for authorized Papelería manager use.\n- Produces manager-PIN endpoints `POST /retail/inventory/{item_id}/entries`, `POST /retail/inventory/{item_id}/removals`, and `POST /retail/inventory/{item_id}/adjustments`.\n- Each stock mutation requires a non-empty `reason`, idempotency key, acting Papelería staff session, and `PosStaffService.authorize_manager(..., module_code=PAPELERIA)`; it records both actor and authorizer on the immutable movement.

- [ ] **Step 1: Write failing API tests for module authorization and search ordering**

Include cross-module rejection, barcode exact-match precedence, branch-scoped barcode behavior, rejection of stock mutations without manager PIN, and successful manager-authorized entry/removal/physical-count adjustment.

- [ ] **Step 2: Run API tests to verify they fail**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_catalog_api.py backend/tests/test_retail_inventory_api.py`

Expected: FAIL.

- [ ] **Step 3: Implement routers and register them in `app.main`**

Use existing `get_current_pos_staff` plus a small Papelería-module guard rather than duplicating token parsing. Stock mutation routes must call the inventory service; they must never assign the balance directly.

- [ ] **Step 4: Run API and existing Cafetería regression tests**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q backend/tests/test_retail_catalog_api.py backend/tests/test_retail_inventory_api.py backend/tests/test_pos_catalog_inventory.py backend/tests/test_pos_staff_auth.py`

If `backend/tests/test_pos_catalog_inventory.py` does not exist on current `main`, omit that path and run `backend/tests/test_pos_product_variants_orders.py` instead.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/retail_catalog.py backend/app/api/retail_inventory.py backend/app/schemas/retail_inventory.py backend/app/main.py backend/app/services/retail_catalog_service.py backend/tests/test_retail_catalog_api.py backend/tests/test_retail_inventory_api.py
git commit -m "feat(retail): expose papeleria catalog and stock APIs"
```

### Task 5: Full backend regression gate for Phase 1

**Files:**
- No product files unless a failing regression requires a fix.
- Test: all backend tests.

**Interfaces:**
- Consumes all interfaces from Tasks 1–4.
- Produces a green backend baseline before retail sales work starts.

- [ ] **Step 1: Run the complete backend test suite**

Run:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q`

Expected: PASS.

- [ ] **Step 2: Verify Alembic can upgrade a fresh development database to head**

Run the repository's normal dev migration command:
`docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-migrate`

Expected: migration completes without error and the new retail tables/columns exist.

- [ ] **Step 3: Commit only if verification required a corrective change**

Use a focused commit message describing the regression fix.
