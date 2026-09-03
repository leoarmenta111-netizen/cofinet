# CofiCenter Kitchen + Bar Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route POS order items automatically to independent Kitchen and Bar preparation screens while preserving one commercial order and one payment.

**Architecture:** `PosProduct.preparation_station` defines the current routing configuration. `PosOrderItem.preparation_station` stores an immutable snapshot at sale time. Each order gets one `PosOrderStation` row for every required preparation station, allowing Kitchen and Bar to progress independently. The server recalculates the general order status after station updates.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL, vanilla JavaScript, HTML/CSS, Node test runner, pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-kitchen-bar-routing-design.md`

## Global Constraints

- Preparation stations are exactly `KITCHEN`, `BAR`, or `NONE`.
- A product has exactly one preparation station.
- An order remains one sale and one payment.
- `NONE` items never appear in Kitchen or Bar.
- Kitchen and Bar update their own status independently.
- Station states are exactly `NEW`, `PREPARING`, `READY`.
- General order status is server-calculated from station states.
- `DELIVERED` remains a separate action on the complete order.
- Branch isolation is mandatory.
- Pending offline POS orders do not reach stations until synchronized.
- No Kitchen/Bar tablet offline mode in v1.
- Existing dirty POS redesign files must not be overwritten or broadly staged.
- Never use `git add .`.
- Existing unrelated nginx changes remain untouched.

---

### Task 1: Product preparation station

**Files:**
- Create: `backend/alembic/versions/20260902_0001_pos_product_preparation_station.py`
- Modify: `backend/app/models/pos_catalog.py`
- Modify: `backend/app/schemas/pos_catalog.py`
- Modify: `backend/app/schemas/admin_pos_catalog.py`
- Modify: `backend/app/services/pos_catalog_service.py`
- Modify: `backend/app/services/admin_pos_catalog_service.py`
- Test: `backend/tests/test_pos_preparation_station.py`

**Interfaces:**
- Produces: `PosProduct.preparation_station: str`
- Valid values: `KITCHEN | BAR | NONE`
- Default for existing and new products: `NONE`
- Public catalog response exposes `preparation_station`
- Admin create/update/response exposes `preparation_station`

- [ ] Write failing model/schema/catalog tests.
- [ ] Verify tests fail because `preparation_station` does not exist.
- [ ] Add Alembic column:
      `pos_products.preparation_station VARCHAR(16) NOT NULL DEFAULT 'NONE'`.
- [ ] Add database check constraint allowing only `KITCHEN`, `BAR`, `NONE`.
- [ ] Add matching SQLAlchemy column and check constraint.
- [ ] Add Pydantic `Literal["KITCHEN", "BAR", "NONE"]` validation to admin create/update.
- [ ] Add field to admin product response.
- [ ] Add field to public POS catalog response.
- [ ] Include field in `AdminPosCatalogService` create/update/get catalog.
- [ ] Include field in `PosCatalogService.get_catalog`.
- [ ] Run focused tests.
- [ ] Run existing POS catalog/order tests.
- [ ] Commit only Task 1 files.

Expected commit:
`feat(pos): add product preparation stations`

---

### Task 2: Order routing persistence

**Files:**
- Create: `backend/alembic/versions/20260902_0002_pos_order_station_routing.py`
- Modify: `backend/app/models/pos_orders.py`
- Test: `backend/tests/test_pos_station_routing.py`

**Interfaces:**

`PosOrderItem.preparation_station: str`
- Snapshot copied from product at sale time.
- Valid: `KITCHEN | BAR | NONE`.

`PosOrderStation`
- `id: int`
- `order_id: int`
- `station: str`
- `status: str`
- `started_at: datetime | None`
- `ready_at: datetime | None`
- `created_at: datetime`
- `updated_at: datetime`
- Unique `(order_id, station)`.

Station values:
- `KITCHEN`
- `BAR`

Station status values:
- `NEW`
- `PREPARING`
- `READY`

Relationships:
- `PosOrder.station_states`
- `PosOrderStation.order`

- [ ] Write failing persistence tests.
- [ ] Verify failure before model exists.
- [ ] Add `preparation_station` snapshot to `pos_order_items`.
- [ ] Existing historical order items receive `NONE`.
- [ ] Create `pos_order_stations`.
- [ ] Add unique constraint for `(order_id, station)`.
- [ ] Add checks for station and station status.
- [ ] Add useful indexes for order, station, and status.
- [ ] Add SQLAlchemy relationships.
- [ ] Run focused tests.
- [ ] Commit exact Task 2 files.

Expected commit:
`feat(pos): persist order preparation routing`

---

### Task 3: Route new sales and calculate overall status

**Files:**
- Modify: `backend/app/schemas/pos_orders.py`
- Modify: `backend/app/services/pos_order_service.py`
- Test: `backend/tests/test_pos_station_routing.py`
- Test: `backend/tests/test_pos_order_management.py`

**Interfaces:**

`PosOrderItemResponse.preparation_station: str`

`PosOrderStationResponse`
- `station: Literal["KITCHEN", "BAR"]`
- `status: Literal["NEW", "PREPARING", "READY"]`
- `started_at: datetime | None`
- `ready_at: datetime | None`

`PosOrderResponse.stations: list[PosOrderStationResponse]`

Server function:
`PosOrderService._recalculate_preparation_status(order)`

Rules:
- no required stations -> `READY`
- all station states `NEW` -> `NEW`
- all station states `READY` -> `READY`
- every other mixed state -> `PREPARING`
- never replace `DELIVERED` or `CANCELLED`

Sale creation:
- Snapshot product `preparation_station` into each `PosOrderItem`.
- Determine unique required stations from all items.
- Ignore `NONE`.
- Create one `PosOrderStation` per required station.
- A mixed sale creates both `KITCHEN` and `BAR`.
- A BAR-only sale creates only BAR.
- A KITCHEN-only sale creates only KITCHEN.
- A NONE-only sale creates no station rows and general status becomes `READY`.

- [ ] Write failing tests for BAR-only, KITCHEN-only, mixed, and NONE-only sales.
- [ ] Verify RED.
- [ ] Snapshot station during price/item calculation.
- [ ] Create required station rows after order flush.
- [ ] Extend order responses.
- [ ] Implement aggregate status calculation.
- [ ] Verify mixed station status rules.
- [ ] Verify legacy order-management tests.
- [ ] Commit exact files.

Expected commit:
`feat(pos): route order items to preparation stations`

---

### Task 4: Kitchen and Bar station API

**Files:**
- Modify: `backend/app/schemas/pos_orders.py`
- Modify: `backend/app/services/pos_order_service.py`
- Modify: `backend/app/api/pos_orders.py`
- Test: `backend/tests/test_pos_station_api.py`

**Interfaces:**

GET:
`/pos/orders/stations/{station}`

Query:
- `branch_code`
- optional `status`
- optional `from_at`
- optional `to_at`
- `limit`

`station` accepts:
- `KITCHEN`
- `BAR`

Response ticket:
- `order_uuid`
- `folio`
- `branch_code`
- `customer_name`
- `created_at_client`
- `order_status`
- `station`
- `station_status`
- filtered `items`
- each item includes quantity, product name, notes, modifiers

Only items whose snapshot `preparation_station` equals requested station are returned.

PATCH:
`/pos/orders/{order_uuid}/stations/{station}`

Payload:
- `branch_code`
- `status: PREPARING | READY`

Transitions:
- `NEW -> PREPARING`
- `PREPARING -> READY`
- same-state update is idempotent
- backward transitions are rejected

Concurrency:
- Lock the parent `PosOrder` first with `FOR UPDATE`.
- Then obtain the requested station row.
- Update only that station.
- Recalculate general status in the same transaction.

- [ ] Write failing API tests.
- [ ] Test branch isolation.
- [ ] Test BAR response excludes KITCHEN items.
- [ ] Test KITCHEN response excludes BAR items.
- [ ] Test `NONE` never appears.
- [ ] Test invalid transitions.
- [ ] Test Kitchen READY does not mutate Bar.
- [ ] Test overall status recalculation.
- [ ] Implement schemas/service/routes.
- [ ] Run focused and existing order tests.
- [ ] Commit exact files.

Expected commit:
`feat(pos): add kitchen and bar station API`

---

### Task 5: Admin product station selector

**Files:**
- Modify: `admin/catalog.html`
- Modify: `admin/admin.js`
- Modify: `admin/admin.css`
- Test: add focused admin UI test under existing admin test location

**Behavior:**
Product create/edit form shows:

`Estación de preparación`

Options:
- `Sin preparación` -> `NONE`
- `Cocina` -> `KITCHEN`
- `Barra` -> `BAR`

Existing products display current persisted value.

Admin API payload sends exact enum value.

- [ ] Write failing UI/static contract test.
- [ ] Add selector to create/edit product UI.
- [ ] Hydrate value when editing.
- [ ] Include value in create/update payload.
- [ ] Display station in product management listing where useful.
- [ ] Run admin tests.
- [ ] Commit only admin/catalog preparation-station files.

Expected commit:
`feat(admin): configure product preparation station`

---

### Task 6: Shared Kitchen/Bar display

**Files:**
- Create: `pos/kitchen/index.html`
- Create: `pos/bar/index.html`
- Create: `pos/js/station.js`
- Create: `pos/css/station.css`
- Create: `pos/tests/station-screen.test.js`
- Modify: `pos/js/api.js`

**Architecture:**
Kitchen and Bar use separate URLs but share one JS controller and one stylesheet.

Kitchen:
`/pos/kitchen/?branch=nuevo-vallarta`

Bar:
`/pos/bar/?branch=nuevo-vallarta`

Each HTML shell declares its station using:
`data-station="KITCHEN"`
or
`data-station="BAR"`.

UI:
- station name
- branch
- live clock
- connection indicator
- columns/sections for Nueva, Preparando, Lista
- order cards
- folio
- elapsed time
- customer
- quantity
- product
- item notes
- modifiers
- action button

Behavior:
- poll station API every 5 seconds
- refresh immediately after status update
- preserve station state on browser reload because state lives on server
- no local offline queue
- show connection error without deleting existing visible tickets

Visual status:
- NEW blue
- PREPARING amber/orange
- READY green

- [ ] Write failing static/behavior tests.
- [ ] Add station API methods to `pos/js/api.js`.
- [ ] Build shared station controller.
- [ ] Build Kitchen shell.
- [ ] Build Bar shell.
- [ ] Build professional responsive station CSS.
- [ ] Verify each screen sends only its own station.
- [ ] Run all POS Node tests.
- [ ] Browser-test Kitchen and Bar separately.
- [ ] Commit only new station screen/API files.

Expected commit:
`feat(pos): add kitchen and bar displays`

---

### Task 7: Show station progress in main Orders view

**Files:**
- Modify carefully: `pos/js/orders.js`
- Modify carefully: `pos/css/pos.css`
- Modify if necessary: `pos/index.html`
- Test: `pos/tests/order-station-progress.test.js`

**Important:**
These files already contain uncommitted professional POS redesign work.
Do not reset them.
Do not replace broad sections unnecessarily.
Do not stage unrelated existing changes.

Order detail should show:

`Barra      Lista`
`Cocina     Preparando`

General badge continues to use server `order.status`.

- [ ] Write failing station-progress rendering test.
- [ ] Render each returned station and its state in order detail.
- [ ] Do not expose `NONE`.
- [ ] Preserve existing order actions.
- [ ] Run full POS Node suite.
- [ ] Browser-check existing Venta and Órdenes views for regression.
- [ ] Inspect `git diff` before any staging.
- [ ] Commit only when the professional POS redesign and this integration can be separated safely; otherwise leave the integration uncommitted for joint review.

---

### Task 8: Migration and end-to-end verification

**Backend checks:**
- Alembic upgrade succeeds from `20260827_0001`.
- Product defaults to `NONE`.
- BAR product routes to Bar only.
- KITCHEN product routes to Kitchen only.
- Mixed order creates both station rows.
- NONE-only order becomes READY.
- Kitchen/Bar concurrency does not lose updates.
- Branch isolation holds.

**Frontend checks:**
- Kitchen receives only kitchen items.
- Bar receives only bar items.
- Modifier names appear.
- Item notes appear.
- Status survives page refresh.
- Main POS shows station progress.
- Existing sale/payment/customer/order workflows still pass.

**Deployment safety:**
- Use `/opt/cofinet-candidate`.
- Use `backend/.env`.
- Preserve PostgreSQL volume `cofinet_postgres_data`.
- Never run `docker compose down -v`.
- Never run database initialization against existing production DB.
- Inspect Alembic current/head before production upgrade.
- Back up database before applying new migration.
- Recreate/restart only services required by the changed backend/frontend.
- Verify health/API after deployment.

- [ ] Run backend focused tests.
- [ ] Run affected backend regression suite.
- [ ] Run complete POS Node suite.
- [ ] Verify Alembic history/current/head.
- [ ] Take DB backup.
- [ ] Apply migration.
- [ ] Restart required service safely.
- [ ] Smoke-test catalog.
- [ ] Smoke-test one BAR order.
- [ ] Smoke-test one KITCHEN order.
- [ ] Smoke-test one mixed order.
- [ ] Verify Kitchen and Bar screens.
- [ ] Verify main Orders screen.
- [ ] Review `git status` and ensure unrelated dirty files remain untouched.
