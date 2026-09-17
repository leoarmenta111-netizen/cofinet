# POS Product Price Variants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reusable product size/price variants to Cofi POS with product-specific prices, branch-specific availability and overrides, authoritative server validation, frozen offline receipt pricing, and historical variant snapshots.

**Architecture:** A product optionally references one reusable `PosVariantGroup`. `PosProductVariant` defines the allowed variant subset and default price for that product; optional `PosBranchProductVariant` rows override availability or price per branch. Orders snapshot variant identity/name and resolved base price, while valid frozen receipt snapshots preserve original cents.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, SQLite migration tests, Pydantic 2, vanilla JavaScript, Node 20, PWA/IndexedDB.

**Spec:** `docs/superpowers/specs/2026-09-17-pos-product-price-variants-design.md`

## Global Constraints

- Version 1 supports zero or one variant group per product.
- `PosProduct.variant_group_id = NULL` means a normal non-variant product.
- Non-NULL `variant_group_id` means variant selection is mandatory.
- `PosProduct.base_price` is authoritative only for non-variant products.
- Variant products use `PosProductVariant.price`.
- Optional branch `price_override` replaces the product-variant default.
- Missing branch override row means available and inherited default price.
- Inactive assigned groups make the product unsellable.
- Variant products with no sellable active variants are excluded from POS.
- Never fall back from a variant product to `PosProduct.base_price`.
- Non-variant checkout with `product_variant_id` rejects.
- Variant checkout without `product_variant_id` rejects.
- Selected variant must belong to the product and assigned group.
- Selected variant and product-variant link must be active.
- Selected variant must be available at the requested branch.
- Historically referenced variant records are deactivated, not hard-deleted.
- Group reassignment atomically deactivates mismatched active links.
- `PosOrderItem.unit_base_price` remains the base-price snapshot.
- Orders add nullable `product_variant_id` and `variant_name`.
- Receipt snapshot schema remains `v1`.
- Receipt variant ID/name additions are optional for backward compatibility.
- Valid frozen snapshots preserve their frozen cents.
- Snapshot `product_variant_id` must match checkout variant ID.
- No frozen snapshot means current server-resolved pricing is authoritative.
- No multiple variant groups, variant inventory, recipes, combos, or time pricing in v1.
- Do not modify `/opt/cofinet-inventory`.
- Do not touch the shared stash.
- Do not install Python or Node tooling on the host.
- Do not deploy this feature branch directly to production.
- TDD RED must precede production implementation.

---

### Task 1: Persistence foundation

**Files:**
- Create: `backend/alembic/versions/20260917_0001_pos_product_variants.py`
- Modify: `backend/app/models/pos_catalog.py`
- Modify: `backend/app/models/pos_orders.py`
- Create: `backend/tests/test_pos_product_variants_migration.py`
- Create: `backend/tests/test_pos_product_variants_models.py`

**Interfaces:**
- Produces `PosVariantGroup`.
- Produces `PosVariant`.
- Produces `PosProductVariant`.
- Produces `PosBranchProductVariant`.
- Produces nullable `PosProduct.variant_group_id`.
- Produces nullable `PosOrderItem.product_variant_id`.
- Produces nullable `PosOrderItem.variant_name`.
- `PosProduct.variant_group_id` uses `ON DELETE SET NULL` to preserve products when a reusable group is removed administratively.
- `PosOrderItem.product_variant_id` uses `ON DELETE SET NULL` so historical order rows survive catalog-record removal.
- Application behavior still prefers deactivation over hard deletion for historically referenceable variant records.

- [x] Migration-chain RED demonstrated for missing `20260917_0001`.
- [x] Minimal migration-chain GREEN demonstrated.
- [x] Schema RED demonstrated because variant tables were absent.
- [x] Migration schema GREEN demonstrated with previous-migration regression.
- [x] ORM RED demonstrated with seven failing model contracts.
- [ ] Add the four SQLAlchemy models and new product/order columns.
- [ ] Run `tests/test_pos_product_variants_models.py`; expect 7 passed.
- [ ] Run migration, station-routing, and order-management regressions.
- [ ] Verify `Base.metadata.create_all()` with the complete model set.
- [ ] Stage only the five Task 1 files.
- [ ] Commit `feat(pos): add product variant persistence`.

---

### Task 2: Reusable variant groups and variants API

**Files:**
- Modify: `backend/app/schemas/admin_pos_catalog.py`
- Modify: `backend/app/services/admin_pos_catalog_service.py`
- Modify: `backend/app/api/admin_pos_catalog.py`
- Create: `backend/tests/test_pos_product_variants_admin.py`

**Interfaces:**
- Admin can create reusable variant groups.
- Admin can update group name, sort order, and active state.
- Admin can create variants inside a group.
- Admin can update variant name, sort order, and active state.
- Deactivation is used instead of destructive deletion.
- Reuse the existing `GET /admin/pos/catalog` as the read endpoint; do not add a parallel catalog-read route.
- Extend `AdminPosCatalogResponse` with `variant_groups: list[AdminPosVariantGroupResponse]`.
- `AdminPosVariantGroupResponse` exposes `id`, `name`, `sort_order`, `is_active`, and `variants`.
- `AdminPosVariantResponse` exposes `id`, `variant_group_id`, `name`, `sort_order`, and `is_active`.
- Create group: `POST /admin/pos/catalog/variant-groups`.
- Update/deactivate group: `PATCH /admin/pos/catalog/variant-groups/{group_id}`.
- Create reusable variant: `POST /admin/pos/catalog/variant-groups/{group_id}/variants`.
- Update/deactivate reusable variant: `PATCH /admin/pos/catalog/variants/{variant_id}`.

- [ ] Write RED tests for create/update/deactivate group operations.
- [ ] Write RED tests for create/update/deactivate variant operations.
- [ ] Verify RED with `test_pos_product_variants_admin.py`.
- [ ] Add exact Pydantic request/response schemas.
- [ ] Add service methods using current transaction/error patterns.
- [ ] Add admin catalog endpoints using existing super-admin authorization.
- [ ] Run new tests plus `test_plan_catalogue_and_pin_flow.py`.
- [ ] Run `test_admin_pos_catalog_import_images.py`.
- [ ] Commit `feat(pos): manage reusable product variants`.

---

### Task 3: Product variant assignment and branch overrides

**Files:**
- Modify: `backend/app/schemas/admin_pos_catalog.py`
- Modify: `backend/app/services/admin_pos_catalog_service.py`
- Modify: `backend/app/api/admin_pos_catalog.py`
- Extend: `backend/tests/test_pos_product_variants_admin.py`

**Interfaces:**

Product group assignment:

`PUT /admin/pos/catalog/products/{product_id}/variant-group/{group_id}`
`DELETE /admin/pos/catalog/products/{product_id}/variant-group`

Product variant configuration:

`PUT /admin/pos/catalog/products/{product_id}/variants/{variant_id}`

Branch variant configuration:

`PUT /admin/pos/catalog/products/{product_id}/variants/{variant_id}/branches/{branch_code}`

Product-variant values:
- `price: Decimal`
- `is_active: bool`
- `sort_order: int`

Branch override values:
- `price_override: Decimal | None`
- `is_available: bool`

Required behavior:
- Assigned variants must belong to the product assigned group.
- Product-specific price is stored in `PosProductVariant.price`.
- Existing valid product-variant rows may be reactivated.
- Group reassignment atomically deactivates mismatched active rows.
- Removing a group deactivates active product-variant rows.
- Historical product-variant rows are never hard-deleted.
- Missing branch override means available with inherited default price.
- Branch override row exists only for an explicit branch override.
- Extend `AdminPosProductResponse` with nullable `variant_group_id` and `variants: list[AdminPosProductVariantResponse]`.
- `AdminPosProductVariantResponse` exposes `product_variant_id`, `variant_id`, `variant_name`, `price`, `is_active`, `sort_order`, and `branches`.
- `AdminPosBranchProductVariantResponse` exposes `branch_code`, `branch_name`, `price_override`, `effective_price`, and `is_available`.
- Existing `GET /admin/pos/catalog` returns product variant configuration so the editor can reopen saved state.
- For a branch with no override row, the Admin response synthesizes `price_override = null`, `effective_price = PosProductVariant.price`, and `is_available = true`.
- Add RED coverage proving catalog readback returns saved product variants and synthesized default branch settings.

- [ ] RED: group assignment stores `variant_group_id`.
- [ ] RED: variant from another group rejects.
- [ ] RED: product variant price persists exactly.
- [ ] RED: reassignment deactivates mismatched rows.
- [ ] RED: removing group preserves historical rows.
- [ ] RED: branch override persists nullable price and availability.
- [ ] RED: unknown branch rejects.
- [ ] Implement admin schemas, service methods, and routes.
- [ ] Run `test_pos_product_variants_admin.py`.
- [ ] Run `test_plan_catalogue_and_pin_flow.py`.
- [ ] Run `test_admin_pos_catalog_import_images.py`.
- [ ] Commit `feat(pos): configure product variant pricing`.

---

### Task 4: Branch-resolved public POS catalog

**Files:**
- Modify: `backend/app/schemas/pos_catalog.py`
- Modify: `backend/app/services/pos_catalog_service.py`
- Create: `backend/tests/test_pos_product_variants_catalog.py`

**Interfaces:**

Add `PosCatalogVariantResponse` with:
- `product_variant_id: int`
- `variant_id: int`
- `name: str`
- `price: Decimal`
- `sort_order: int`

Extend each product response with:
- `has_variants: bool`
- `display_price: Decimal`
- `variants: list[PosCatalogVariantResponse]`

Compatibility rules:
- Non-variant `price` keeps current branch/product effective price.
- Non-variant `display_price = price`.
- Non-variant `has_variants = false` and `variants = []`.
- Variant product `price = display_price` for compatibility.
- Variant `display_price` is the lowest available resolved variant price.

Branch resolution rules:
- Missing `PosBranchProductVariant` row means available by default.
- Missing override row inherits `PosProductVariant.price`.
- Existing row with `is_available = false` excludes that variant.
- Existing non-NULL `price_override` replaces the default price.
- NULL `price_override` inherits the default price.

Catalog exclusion rules:
- Inactive assigned variant group excludes the whole product.
- No active sellable product variants excludes the whole product.
- Inactive reusable variant is excluded.
- Inactive product-variant row is excluded.
- Variant outside the assigned product group is never exposed.
- Existing product-level branch availability still applies.

Variant ordering:
- Product-variant `sort_order` first.
- Reusable variant `sort_order` second.
- Variant ID as stable final tie-breaker.

- [ ] RED: non-variant catalog response remains backward compatible.
- [ ] RED: Latte returns three branch-resolved variants.
- [ ] RED: `display_price` is the lowest available variant price.
- [ ] RED: missing branch override inherits default price.
- [ ] RED: branch price override replaces default price.
- [ ] RED: unavailable branch variant is omitted.
- [ ] RED: inactive assigned group excludes the product.
- [ ] RED: zero sellable variants excludes the product.
- [ ] RED: Frappé can expose only Mediano and Grande.
- [ ] Implement branch-resolved catalog logic.
- [ ] Run `test_pos_product_variants_catalog.py`.
- [ ] Run existing catalog and admin regressions.
- [ ] Commit `feat(pos): expose branch resolved product variants`.

---

### Task 5: Authoritative order validation and online pricing

**Files:**
- Modify: `backend/app/schemas/pos_orders.py`
- Modify: `backend/app/services/pos_order_service.py`
- Modify: `backend/app/api/pos_orders.py`
- Create: `backend/tests/test_pos_product_variants_orders.py`

**Interfaces:**

Extend order request item with:
- `product_variant_id: int | None = None`

Extend order response item with:
- `product_variant_id: int | None`
- `variant_name: str | None`

Online validation rules:
- Non-variant product with `product_variant_id` rejects.
- Variant product without `product_variant_id` rejects.
- Product variant must belong to the selected product.
- Reusable variant must belong to the product assigned group.
- Reusable variant must be active.
- Product-variant link must be active.
- Explicit unavailable branch variant rejects.

Online base-price resolution:
- If branch override exists and `price_override` is non-NULL, use it.
- Otherwise use `PosProductVariant.price`.
- Modifiers are added after the resolved variant base price.
- Non-variant products keep current pricing behavior.

Persist on each variant order line:
- `PosOrderItem.product_variant_id`
- `PosOrderItem.variant_name`
- `PosOrderItem.unit_base_price = resolved variant base price`
- `PosOrderItem.unit_modifier_total = existing modifier total`
- `PosOrderItem.unit_price = base price + modifier total`

- [ ] RED: variant product without selection rejects.
- [ ] RED: non-variant product with variant ID rejects.
- [ ] RED: variant belonging to another product rejects.
- [ ] RED: variant from wrong assigned group rejects.
- [ ] RED: inactive reusable variant rejects.
- [ ] RED: inactive product-variant row rejects.
- [ ] RED: unavailable branch variant rejects.
- [ ] RED: default variant price becomes `unit_base_price`.
- [ ] RED: branch override becomes `unit_base_price`.
- [ ] RED: modifiers are added after variant base price.
- [ ] RED: order stores variant ID and variant name snapshot.
- [ ] RED: existing non-variant order behavior remains unchanged.
- [ ] Implement server-authoritative validation and pricing.
- [ ] Run `test_pos_product_variants_orders.py`.
- [ ] Run `test_pos_order_management.py`.
- [ ] Run `test_pos_station_routing.py`.
- [ ] Run `test_pos_station_api.py`.
- [ ] Commit `feat(pos): validate variant order pricing`.

---

### Task 6: Frozen receipt snapshot and offline variant pricing

**Files:**
- Modify: `backend/app/schemas/pos_receipts.py:161-171`
- Modify: `backend/app/services/pos_order_service.py:672-710`
- Modify: `backend/app/services/pos_order_service.py:969-1005`
- Extend: `backend/tests/test_pos_receipt_snapshots.py`
- Extend: `backend/tests/test_pos_product_variants_orders.py`

**Interfaces:**

Extend `ReceiptSnapshotItemV1` with optional fields:
- `product_variant_id: int | None = None`
- `variant_name: str | None = None`

Keep receipt snapshot schema version exactly:
- `schema_version: Literal[1]`

Backward compatibility:
- Existing v1 snapshots without variant fields remain valid.
- Old non-variant frozen orders require no migration.
- `extra = forbid` remains enabled for snapshot item validation.

Frozen variant identity validation:
- Snapshot `product_id` must continue matching request `product_id`.
- Snapshot quantity must continue matching request quantity.
- Snapshot `product_variant_id` must equal request `product_variant_id`.
- Variant product still requires a valid server-side product-variant relationship.
- Variant must still be eligible for the requested branch.
- Frozen pricing does not bypass identity or branch validation.

Frozen pricing rules:
- A valid frozen snapshot keeps `unit_price_cents` even if the current catalog price changed.
- A valid frozen snapshot keeps `line_total_cents` even if the current catalog price changed.
- Current variant price and current branch override must not reprice a valid frozen sale.
- Frozen modifier deltas continue coming from snapshot `price_delta_cents`.

Frozen monetary reconstruction:
- `modifier_total = sum(snapshot modifier price_delta_cents) / 100`.
- `unit_price = snapshot unit_price_cents / 100`.
- `unit_base_price = unit_price - modifier_total`.
- `line_total = snapshot line_total_cents / 100`.
- Reject if reconstructed `unit_base_price` would be negative.
- Existing line-total, subtotal, tax, payment, and final-total consistency checks remain active.

Variant name snapshot behavior:
- Online checkout snapshots the current reusable variant name into `PosOrderItem.variant_name`.
- Frozen checkout preserves snapshot `variant_name` when supplied.
- Current variant renames must not rewrite an already frozen historical receipt label.
- Old v1 snapshots with no variant fields continue through the existing non-variant path.

- [ ] RED: v1 receipt item accepts optional variant ID and name.
- [ ] RED: old v1 receipt item without variant fields remains valid.
- [ ] RED: frozen variant ID mismatch with request rejects.
- [ ] RED: valid frozen variant sale does not reprice from current product-variant price.
- [ ] RED: valid frozen variant sale does not reprice from current branch override.
- [ ] RED: frozen modifier deltas reconstruct `unit_base_price` correctly.
- [ ] RED: frozen variant name is preserved as historical snapshot text.
- [ ] RED: invalid product or branch variant eligibility still rejects frozen checkout.
- [ ] Extend `ReceiptSnapshotItemV1` with the two nullable variant fields.
- [ ] Extend snapshot/order matching with `product_variant_id` equality validation.
- [ ] Preserve frozen cents while retaining current identity and branch validation.
- [ ] Run `test_pos_receipt_snapshots.py`.
- [ ] Run `test_pos_product_variants_orders.py`.
- [ ] Commit `feat(pos): preserve frozen variant receipt pricing`.

---

### Task 7: Admin Variantes UI

**Files:**
- Modify: `admin/catalog.html`
- Create: `admin/tests/catalog-variants.test.js`

**Existing integration points:**
- Catalog tabs use `.catalog-tab` with `data-tab`.
- Existing panels use IDs such as `tab-products`, `tab-categories`, and `tab-modifiers`.
- Product editor already contains `product-branches-section` and `product-modifiers-section`.
- Existing catalog state already stores products, branches, and modifier groups.
- Existing API helper remains the shared admin request path; do not introduce a second client.

**Variantes tab:**
- Add a fourth catalog tab with `data-tab="variants"`.
- Add matching panel `id="tab-variants"`.
- Label the tab `Variantes`.
- Reusable groups are managed here, separate from modifier groups.
- Change the Modificadores description so it no longer describes `Tamaños` as a modifier use case.
- Keep modifiers for milk types, extras, add-ons, and other incremental options.

**Reusable variant group UI:**
- Show active and inactive reusable variant groups.
- Group editor exposes `name`, `sort_order`, and `is_active`.
- Each group lists its reusable variants.
- Variant editor exposes `name`, `sort_order`, and `is_active`.
- Deactivation is the destructive-looking action; do not add hard-delete UI.

**Product editor variant section:**
- Add `id="product-variants-section"` near the existing branch and modifier sections.
- Add reusable-group selector `id="product-variant-group"`.
- Add variant configuration container `id="product-variant-settings"`.
- Group selector includes `Sin variantes` plus active reusable groups.
- Existing non-variant products default to `Sin variantes`.
- Selecting a group renders only variants belonging to that group.
- Each product variant row carries `data-variant-id`.
- Each row exposes product-specific `price`, `is_active`, and `sort_order`.
- A product may activate only a subset of variants from the reusable group.
- Variant product UI must not imply that `base_price` is its selling price.

**Branch overrides inside each product variant:**
- Render branch rows from the existing `catalog.branches` list.
- Each branch row carries `data-branch-code` and `data-variant-id`.
- Branch row exposes nullable `price_override`.
- Branch row exposes `is_available`.
- Blank override displays inherited product-variant price.
- Explicit unavailable branch variant remains visible in Admin but disabled for POS sale.

**Save flow:**
- Save the base product first so a product ID exists.
- Changed group uses `PUT /admin/pos/catalog/products/{product_id}/variant-group/{group_id}`.
- `Sin variantes` uses `DELETE /admin/pos/catalog/products/{product_id}/variant-group`.
- Product variant rows use `PUT /admin/pos/catalog/products/{product_id}/variants/{variant_id}`.
- Branch rows use `PUT /admin/pos/catalog/products/{product_id}/variants/{variant_id}/branches/{branch_code}`.
- Refresh catalog state after successful variant saves.
- Do not partially update local catalog state after a failed API request.

- [ ] RED: catalog has a `Variantes` tab and matching `tab-variants` panel.
- [ ] RED: Modificadores copy no longer lists `Tamaños`.
- [ ] RED: reusable variant group editor exposes name, order, and active state.
- [ ] RED: product editor exposes `product-variant-group` and `product-variant-settings`.
- [ ] RED: product variant rows expose price, active state, and sort order.
- [ ] RED: branch override rows expose nullable price and availability.
- [ ] RED: non-variant product can remain on `Sin variantes`.
- [ ] Implement the Variantes tab and reusable-group editor in `admin/catalog.html`.
- [ ] Implement product group assignment and product-specific variant controls.
- [ ] Implement branch override controls using Task 3 API routes.
- [ ] Run `node --test admin/tests/catalog-variants.test.js`.
- [ ] Run `node --test admin/tests/catalog-preparation-station.test.js`.
- [ ] Run `node --test admin/tests/catalog-styles.test.js`.
- [ ] Commit `feat(admin): manage product price variants`.

---

### Task 8: POS product cards and mandatory variant selection

**Files:**
- Modify: `pos/index.html:679-686`
- Modify: `pos/js/app.js:389-862`
- Create: `pos/tests/product-variants.test.js`
- Verify: `pos/tests/product-card-responsive-fit.test.js`
- Verify: `pos/tests/professional-sale-layout.test.js`

**Existing integration points:**
- `renderProducts()` renders product cards.
- Product card price currently reads `product.price`.
- Product click flows through `selectProduct(product)`.
- `selectProduct(product)` currently opens the existing modifier modal when customization is required.
- `state.modifierProduct` stores the product being customized.
- `updateModifierTotal()` currently calculates from `product.price` plus modifier deltas.
- `addCartItem()` currently snapshots the product base price from `product.price`.

**Product card pricing:**
- Non-variant products continue displaying the existing formatted `product.price`.
- Variant products display `Desde {money(product.display_price)}`.
- `display_price` comes from the branch-resolved catalog response from Task 4.
- Do not calculate the lowest variant price again in the browser.
- Product card responsive dimensions and existing two-column mobile behavior remain unchanged.

**Variant selection state:**
- Add `state.modifierVariant = null` alongside `state.modifierProduct`.
- Reset `state.modifierVariant` whenever `selectProduct(product)` starts a new product selection.
- Non-variant products keep `state.modifierVariant = null`.
- Variant products require one selected entry from `product.variants` before adding to cart.

**Variant selector inside existing modifier modal:**
- Add `id="variant-section"` before `modifier-groups`.
- Add `id="variant-options"` inside the variant section.
- Hide `variant-section` for non-variant products.
- Show `variant-section` when `product.has_variants === true`.
- Render one selectable control for each entry in `product.variants`.
- Each control carries `data-product-variant-id`.
- Each control displays variant name and its branch-resolved price.
- Selecting a variant stores the complete selected variant object in `state.modifierVariant`.
- Variant selection updates the modal base-price label immediately.
- Variant selection recalculates the add-button total immediately.

**Base-price calculation:**
- Add helper `selectedBasePrice(product)`.
- For non-variant products it returns `Number(product.price)`.
- For variant products with a selection it returns `Number(state.modifierVariant.price)`.
- For variant products without a selection it returns `null`.
- `updateModifierTotal()` uses `selectedBasePrice(product)` instead of directly reading `product.price`.
- Existing modifier deltas are added after the selected variant base price.

**Mandatory-selection behavior:**
- `selectProduct(product)` must open the modal for every variant product, even when it has zero modifier groups.
- Non-variant product with zero modifier groups keeps the current direct-add behavior.
- `modifier-add` rejects a variant product while `state.modifierVariant` is null.
- Validation message is shown in existing `modifier-error`.
- Do not silently select the cheapest or first variant.
- User must explicitly choose the size/variant before the item can enter the cart.

- [ ] RED: variant product card renders `Desde` with `display_price`.
- [ ] RED: non-variant product card keeps normal price display.
- [ ] RED: variant product opens personalization modal even with no modifiers.
- [ ] RED: variant selector renders all branch-resolved `product.variants`.
- [ ] RED: variant controls expose `data-product-variant-id`.
- [ ] RED: add action rejects variant product with no selected variant.
- [ ] RED: selected variant price becomes the customization base price.
- [ ] RED: modifier deltas are added after selected variant price.
- [ ] RED: non-variant direct-add path remains unchanged.
- [ ] Add variant selector markup to the existing personalization modal.
- [ ] Implement `selectedBasePrice(product)` and variant rendering in `app.js`.
- [ ] Update `selectProduct()`, `updateModifierTotal()`, and add-button validation.
- [ ] Run `node --test pos/tests/product-variants.test.js`.
- [ ] Run `node --test pos/tests/product-card-responsive-fit.test.js`.
- [ ] Run `node --test pos/tests/professional-sale-layout.test.js`.
- [ ] Commit `feat(pos): require product variant selection`.

---

### Task 9: Cart, checkout, and frozen local receipt variant identity

**Files:**
- Modify: `pos/js/app.js:822-854`
- Modify: `pos/js/app.js:1449-1916`
- Modify: `pos/js/receipt-core.js:226-306`
- Modify: `pos/js/orders-local.js:103-242`
- Extend: `pos/tests/product-variants.test.js`
- Extend: `pos/tests/receipt-checkout.test.js`
- Extend: `pos/tests/orders-local.test.js`
- Extend: `pos/tests/receipt-core.test.js`
- Extend: `pos/tests/receipt-offline.test.js`
- Extend: `pos/tests/receipt-storage.test.js`

**Cart item contract:**
- Change `addCartItem(product, modifiers, quantity)` to `addCartItem(product, modifiers, quantity, variant = null)`.
- Non-variant direct-add calls pass `variant = null`.
- Variant modal add passes `state.modifierVariant`.
- Persist `product_variant_id: variant?.product_variant_id ?? null`.
- Persist `variant_name: variant?.name ?? null`.
- Persist `base_price` from the selected variant price when variant is non-null.
- Persist existing product price as `base_price` when variant is null.
- Persist `unit_price = base_price + modifierTotal`.
- Keep quantity and modifier snapshots unchanged.

**Checkout request contract:**
- Each checkout item includes nullable `product_variant_id`.
- Do not send browser-computed variant price as authoritative catalog pricing.
- Online backend still resolves current variant base price from Task 5.
- Frozen offline checkout uses the receipt snapshot pricing exception from Task 6.

**Frozen receipt item contract in the browser:**
- Receipt snapshot item includes nullable `product_variant_id`.
- Receipt snapshot item includes nullable `variant_name`.
- Variant cart item copies both fields into the frozen receipt item.
- Non-variant cart item writes both fields as `null` or omits them compatibly with schema v1.
- `unit_price_cents` continues snapshotting the final per-unit price including modifiers.
- `line_total_cents` continues snapshotting quantity multiplied by final unit price.
- Snapshot variant name is historical text and must not be looked up again after sale creation.

**`receipt-core.js` behavior:**
- `buildItems(items)` copies optional `product_variant_id` and `variant_name` into each normalized snapshot item.
- Snapshot validation accepts missing or null variant fields for legacy non-variant v1 receipts.
- When present, `product_variant_id` must be a positive integer.
- When present, `variant_name` must be a non-empty string.
- Receipt schema version remains exactly `1`.
- Existing money, quantity, modifier, and total validation remains unchanged.

**Offline and local-order behavior:**
- Offline queue stores the exact receipt snapshot containing variant ID and historical variant name.
- Retry sends the same frozen `receipt_snapshot`; it must not rebuild variant pricing from a later catalog.
- `orders-local.js` copies variant identity from `receiptSnapshot.items` when reconstructing a frozen local order.
- Local reconstructed item exposes nullable `product_variant_id` and `variant_name`.
- Legacy locally stored orders without variant fields remain readable.

**Checkout consistency:**
- Request item `product_variant_id` and receipt item `product_variant_id` must originate from the same cart line.
- Variant cart line sends the selected `product_variant_id` in the order payload.
- Variant cart line freezes the selected `variant_name` only in the receipt snapshot and local display state.
- Server remains authoritative for online variant identity, availability, and current price.
- Frozen receipt cents remain authoritative only under the Task 6 frozen-snapshot exception.

- [ ] RED: variant cart line stores `product_variant_id`, `variant_name`, selected base price, and final unit price.
- [ ] RED: non-variant cart line remains backward compatible.
- [ ] RED: checkout payload sends nullable `product_variant_id` for every order item.
- [ ] RED: variant receipt item freezes `product_variant_id` and `variant_name`.
- [ ] RED: `receipt-core` accepts legacy v1 items without variant fields.
- [ ] RED: `receipt-core` preserves valid variant ID and name without mutation.
- [ ] RED: offline receipt storage preserves variant fields exactly.
- [ ] RED: offline retry preserves the original frozen variant snapshot.
- [ ] RED: `orders-local` reconstructs variant ID and variant name from frozen receipt items.
- [ ] Update `addCartItem()` and checkout item serialization.
- [ ] Update receipt snapshot construction in `app.js`.
- [ ] Update `buildItems()` and snapshot validation in `receipt-core.js`.
- [ ] Update frozen-order reconstruction in `orders-local.js`.
- [ ] Run `node --test pos/tests/product-variants.test.js`.
- [ ] Run `node --test pos/tests/receipt-checkout.test.js`.
- [ ] Run `node --test pos/tests/receipt-core.test.js`.
- [ ] Run `node --test pos/tests/receipt-offline.test.js`.
- [ ] Run `node --test pos/tests/receipt-storage.test.js`.
- [ ] Run `node --test pos/tests/orders-local.test.js`.
- [ ] Commit `feat(pos): preserve product variants through checkout`.

---

### Task 10: Variant display in Orders, KDS, and receipts

**Files:**
- Modify: `pos/js/orders.js`
- Modify: `pos/js/station.js`
- Modify: `pos/js/receipt-renderer.js`
- Modify: `pos/index.html`
- Modify: `pos/sw.js`
- Modify: `pos/kitchen/index.html`
- Modify: `pos/bar/index.html`
- Modify: `pos/kitchen/sw.js`
- Modify: `pos/bar/sw.js`
- Extend: `pos/tests/orders-ui.test.js`
- Extend: `pos/tests/station-delivered.test.js`
- Extend: `pos/tests/receipt-renderer.test.js`

**Display contract:**
- Historical displays consume persisted `variant_name`; they do not query the current catalog.
- With variant: render `product_name · variant_name`.
- Example: `Latte · Grande 20 oz`.
- Without variant: render only `product_name`.
- Blank or missing `variant_name` behaves exactly like a non-variant item.
- Modifier names remain separate below the product/variant label.

**Orders POS:**
- Add helper `orderItemDisplayName(item)` in `pos/js/orders.js`.
- Helper returns `product_name` when `variant_name` is absent.
- Helper returns `product_name + " · " + variant_name` when present.
- Replace existing `${item.quantity} × ${item.product_name}` render paths with the helper.
- Quantity formatting and preparation-status UI remain unchanged.

**KDS Cocina / Barra:**
- Add helper `stationItemDisplayName(item)` in `pos/js/station.js`.
- Return `product_name` when `variant_name` is absent.
- Return `product_name + " · " + variant_name` when `variant_name` is present.
- `renderItem(item)` uses `stationItemDisplayName(item)` instead of raw `product_name`.
- Continue escaping the composed label with the existing HTML escaping path.
- Quantity, notes, modifiers, station status, sound alerts, and READY/DELIVERED behavior remain unchanged.

**Receipt renderer:**
- Extend existing `itemName(item)` in `pos/js/receipt-renderer.js`.
- Resolve the existing base item name first using current fallback order.
- If `variant_name` is blank or missing, return the existing base item name unchanged.
- If `variant_name` exists, return `baseName + " · " + variant_name`.
- Do not query product or variant catalog data while rendering historical receipts.
- Modifier lines, quantity, unit price, and line total remain unchanged.

**Static asset versioning:**
- Bump `orders.js` in `pos/index.html` from `v=15` to `v=16`.
- Bump `receipt-renderer.js` in `pos/index.html` from `v=1` to `v=2`.
- Update matching precache URLs in `pos/sw.js`.
- Bump the main POS shell cache version after changing those precached assets.
- Bump `station.js` in both `pos/kitchen/index.html` and `pos/bar/index.html` from `v=3` to `v=4`.
- Update both KDS service workers to precache `station.js?v=4`.
- Bump kitchen and bar shell cache versions from `v3` to `v4`.

- [ ] RED: Orders renders `Latte · Grande 20 oz` when `variant_name` exists.
- [ ] RED: Orders renders only `Latte` when `variant_name` is absent.
- [ ] RED: KDS `renderItem()` includes persisted variant name in the item label.
- [ ] RED: KDS non-variant item output remains unchanged.
- [ ] RED: receipt `itemName()` appends `variant_name` to the frozen product name.
- [ ] RED: receipt without variant remains backward compatible.
- [ ] RED: KDS HTML and service workers reference `station.js?v=4`.
- [ ] RED: main POS references bumped Orders and receipt-renderer assets.
- [ ] Implement `orderItemDisplayName(item)` in `orders.js`.
- [ ] Implement `stationItemDisplayName(item)` and use it from `renderItem()`.
- [ ] Extend receipt `itemName(item)` with historical variant text.
- [ ] Bump POS and KDS asset/cache versions.
- [ ] Run `node --test pos/tests/orders-ui.test.js`.
- [ ] Run `node --test pos/tests/station-delivered.test.js`.
- [ ] Run `node --test pos/tests/receipt-renderer.test.js`.
- [ ] Run `node --test pos/tests/station-pwa.test.js`.
- [ ] Commit `feat(pos): display product variants across order views`.

---

### Task 11: Full regression and migration verification

**Files:**
- Verify: `backend/tests/test_pos_product_variants_migration.py`
- Verify: `backend/tests/test_pos_product_variants_models.py`
- Verify: `backend/tests/test_pos_product_variants_admin.py`
- Verify: `backend/tests/test_pos_product_variants_catalog.py`
- Verify: `backend/tests/test_pos_product_variants_orders.py`
- Verify: `backend/tests/test_pos_receipt_snapshots.py`
- Verify: `admin/tests/*.test.js`
- Verify: `pos/tests/*.test.js`

**Backend verification:**
- Use `cofinet-backend-product-variants-devtest:local` with the current backend bind-mounted read-only.
- First run all five product-variant test modules plus receipt snapshot regressions.
- Then run the complete backend test suite.
- Run with `-p no:cacheprovider` so the read-only bind mount creates no pytest cache noise.
- Migration revision must remain `20260917_0001` with down revision `20260915_0001`.
- Migration upgrade and downgrade contract tests must pass.
- Full SQLAlchemy metadata creation must succeed with all variant models registered.

**Frontend verification:**
- Run the complete Admin Node test suite.
- Run the complete POS Node test suite.
- Product card responsive tests must remain green.
- Existing checkout, receipt, offline, Orders, KDS, Delivered, PWA, and sound-alert tests must remain green.
- Products without variants must retain their existing UI and checkout behavior.

**Regression commands:**
- Backend targeted: `docker run --rm --network none -v "$PWD/backend:/app:ro" -w /app cofinet-backend-product-variants-devtest:local python -m pytest -q -p no:cacheprovider tests/test_pos_product_variants_migration.py tests/test_pos_product_variants_models.py tests/test_pos_product_variants_admin.py tests/test_pos_product_variants_catalog.py tests/test_pos_product_variants_orders.py tests/test_pos_receipt_snapshots.py`.
- Backend full: `docker run --rm --network none -v "$PWD/backend:/app:ro" -w /app cofinet-backend-product-variants-devtest:local python -m pytest -q -p no:cacheprovider`.
- Admin full: `node --test admin/tests/*.test.js`.
- POS full: `node --test pos/tests/*.test.js`.

- [ ] Run `git diff --check`.
- [ ] Run targeted backend product-variant and receipt tests.
- [ ] Run the complete backend pytest suite.
- [ ] Run the complete Admin Node test suite.
- [ ] Run the complete POS Node test suite.
- [ ] Verify no inventory-worktree or shared-stash changes occurred.
- [ ] Verify feature worktree contains only intentional product-variant changes.
- [ ] Do not proceed to merge while any regression is failing.

---

### Task 12: Merge, production migration, deploy, verification, and rollback

**Pre-merge gate:**
- Feature branch must contain only intentional product-variant commits.
- `git diff --check` must be clean.
- Task 11 targeted and full backend, Admin, and POS suites must all be green.
- Fetch latest `origin/main` and integrate it into the feature branch before final verification.
- Resolve conflicts in the feature worktree only; never modify the paused inventory worktree.
- Push the verified feature branch and merge it into `main` through the reviewed PR flow.
- Record the resulting merged-main SHA as `MERGED_SHA`.

**Production pre-deploy capture:**
- Production checkout is `/opt/cofinet-candidate`.
- Stop if `/opt/cofinet-candidate` has unexpected local modifications.
- Record current production Git SHA as `ROLLBACK_SHA` before checkout changes.
- Record the currently running `cofinet-api` backend image ID before replacement.
- Tag that existing backend image with a rollback tag before building the new image.
- Do not touch `/opt/cofinet`, its unrelated dirty files, or the shared stash.

**Production compose contract:**
- Export `POSTGRES_VOLUME_NAME=cofinet_postgres_data`.
- Use `--env-file backend/.env`.
- Use `docker-compose.yml`.
- Use `docker-compose.prod.yml`.
- Use `docker-compose.network-prod.yml`.
- Never run `docker compose down`, `down -v`, or `db-init`.

**Deploy sequence:**
- Fetch `origin` in `/opt/cofinet-candidate` and checkout detached `MERGED_SHA`.
- Build the backend from merged main with the production compose stack.
- Run `alembic upgrade head` against production before exposing variant-order writes.
- Expected Alembic head after upgrade is `20260917_0001`.
- Start or recreate only the required backend/nginx services; do not destroy the database volume.
- Verify production containers report healthy/running state.
- Verify candidate Git HEAD equals `MERGED_SHA`.
- Verify Alembic current revision equals `20260917_0001`.

**Production smoke verification:**
- Confirm Admin opens the new `Variantes` tab.
- Confirm a reusable size group can be viewed without altering existing products.
- Confirm a variant product card displays `Desde $X`.
- Confirm variant selection is mandatory before adding that product.
- Confirm modifiers add on top of the selected variant price.
- Confirm a completed variant order shows `product_name · variant_name` in Orders.
- Confirm Cocina/Barra display the same persisted variant label.
- Confirm the receipt displays the same persisted variant label.
- Confirm a normal non-variant product still sells through the unchanged path.

**Rollback contract:**
- Application rollback restores `/opt/cofinet-candidate` to `ROLLBACK_SHA`.
- Application rollback restores the previously tagged backend image.
- Restart only backend/nginx with the restored code/image.
- Leave additive variant schema in place during normal application rollback.
- Do not run destructive Alembic downgrade after variant orders or configuration data exist.
- Database downgrade is allowed only before variant data exists or after an explicit controlled data-conversion decision.

- [ ] Merge verified feature branch into `main` and record `MERGED_SHA`.
- [ ] Capture `ROLLBACK_SHA` and old backend image before deployment.
- [ ] Checkout merged main in `/opt/cofinet-candidate`.
- [ ] Build the production backend image.
- [ ] Run production Alembic upgrade to `20260917_0001`.
- [ ] Recreate only required application services.
- [ ] Verify Git SHA, Alembic head, and container health.
- [ ] Complete Admin, POS, Orders, KDS, receipt, and non-variant smoke checks.
- [ ] Keep rollback Git SHA and backend image tag until post-deploy validation is complete.
