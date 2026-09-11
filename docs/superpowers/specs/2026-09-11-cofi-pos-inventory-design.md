# COFI POS Inventory Phase 1 — Design

Date: 2026-09-11
Branch: feature/cofi-pos-inventory
Status: Approved design

## 1. Purpose

Add a simple, reliable inventory system to COFI POS without turning the
product into a complex warehouse or restaurant ERP.

Phase 1 tracks finished products by branch.

The architecture must also leave a clean path for a future hybrid inventory
model where prepared products can consume ingredients and recipes.

## 2. Goals

Phase 1 must support:

- Inventory tracking per product and per branch.
- Inventory tracking only for products where it is explicitly enabled.
- Current stock.
- Low-stock threshold.
- Initial stock.
- Stock receipts / inventory entries.
- Waste.
- Physical-count adjustments.
- Automatic inventory deduction when an order becomes paid.
- Automatic inventory restoration when an applied sale is reversed through
  cancellation/refund.
- Protection against duplicate deductions and duplicate reversals.
- Low-stock status in Admin.
- Out-of-stock blocking in POS.
- A dedicated Inventory page in Admin.
- Full inventory movement history.
- Offline-compatible behavior.
- Independent balances between branches.
- A future migration path to ingredient/recipe inventory.

## 3. Non-goals for Phase 1

The following are intentionally deferred:

- Ingredient inventory.
- Recipes.
- Recipe costing.
- Modifier ingredient consumption.
- Transfers between branches.
- Purchase orders.
- Suppliers.
- Automatic purchasing.
- WhatsApp notifications.
- Email notifications.
- Advanced warehouse management.
- Lot tracking.
- Expiration dates.

These can be added later without replacing the Phase 1 ledger.

## 4. Core Architecture

Inventory uses three logical entities:

1. Inventory Item
2. Inventory Balance
3. Inventory Movement

A finished catalog product maps to one inventory item.

Balances are branch-specific.

Every inventory change creates an immutable movement.

The current balance is stored separately so the POS can read availability
quickly without summing the complete movement history for every request.

Conceptually:

    PosProduct
        |
        v
    PosInventoryItem
        |
        +---- PosInventoryBalance [Branch A]
        |
        +---- PosInventoryBalance [Branch B]
        |
        +---- PosInventoryMovement history

Phase 1 exposes only finished products to users.

The generic inventory-item boundary exists so Phase 2 can later introduce
ingredients without replacing the balance or movement systems.

## 5. Data Model

### 5.1 PosInventoryItem

Represents something that can have stock.

Phase 1 creates one inventory item for each tracked finished product.

Proposed fields:

- id
- product_id
- name
- unit_code
- is_active
- created_at
- updated_at

Rules:

- product_id references pos_products.
- A product can have at most one Phase 1 inventory item.
- unit_code defaults to EA.
- Phase 1 UI treats quantities as pieces/whole units.
- The database uses a decimal-capable quantity type so Phase 2 can later
  support grams, milliliters and fractional portions.

### 5.2 PosInventoryBalance

Stores the current stock state for one inventory item at one branch.

Proposed fields:

- id
- branch_id
- inventory_item_id
- quantity_on_hand
- low_stock_threshold
- is_tracked
- updated_at

Constraints:

- Unique branch_id + inventory_item_id.
- quantity_on_hand uses a decimal-capable numeric type.
- low_stock_threshold cannot be negative.

Tracking is branch-specific.

This allows the same product to be inventory-controlled in one branch and not
controlled in another if necessary.

### 5.3 PosInventoryMovement

Immutable audit record for every stock change.

Proposed fields:

- id
- branch_id
- inventory_item_id
- movement_type
- quantity_delta
- balance_after
- order_id nullable
- order_item_id nullable
- idempotency_key nullable
- note nullable
- created_by_admin_id nullable
- created_at

Proposed movement types:

- INITIAL
- RECEIPT
- SALE
- SALE_REVERSAL
- WASTE
- ADJUSTMENT

Movement rows are never edited or deleted as part of normal operation.

Corrections are performed by creating compensating movements.

## 6. Inventory Status

Inventory status is derived from the branch balance.

Rules:

    quantity < 0
        REVIEW

    quantity == 0
        OUT_OF_STOCK

    0 < quantity <= low_stock_threshold
        LOW_STOCK

    quantity > low_stock_threshold
        AVAILABLE

REVIEW is primarily expected after an offline oversell or a physical inventory
discrepancy.

Low stock does not block sales.

Out of stock blocks new sales.

## 7. Enabling Inventory Tracking

Inventory tracking is optional.

A product without inventory tracking behaves exactly as it does today.

For each branch, the administrator can enable:

    Controlar inventario

When tracking is enabled for the first time, the administrator provides:

- Initial stock.
- Low-stock threshold.

The initial quantity creates an INITIAL movement.

After initialization, stock is never changed by directly overwriting the
balance.

All subsequent changes go through inventory movements.

The product editor should remain simple.

Inventory operations belong to the dedicated Inventory page.

## 8. Admin Inventory Page

Inventory is a separate Admin section.

The page must use the existing Admin shell/navigation.

Top-level branch selector:

    Sucursal: [ Nuevo Vallarta v ]

Summary metrics:

- Tracked products.
- Low stock.
- Out of stock.
- Needs review.

Main inventory table:

    PRODUCTO        STOCK     MÍNIMO     ESTADO

    Coca-Cola       24        6          Disponible
    Agua             5        5          Stock bajo
    Galletas          0        4          Agotado

Supported filters:

- Search.
- Branch.
- Status.
- Tracked products.

Opening a product displays inventory details and movement history.

Supported manual actions:

- Entrada.
- Merma.
- Ajuste de conteo.

### Entrada

User enters the quantity received.

Backend creates a positive RECEIPT movement.

### Merma

User enters the quantity lost/damaged.

Backend creates a negative WASTE movement.

A reason/note is required.

### Ajuste de conteo

Admin enters the real physical quantity counted.

Example:

    System quantity: 12
    Physical count:   9

Backend calculates:

    quantity_delta = -3

and creates an ADJUSTMENT movement.

The user should not have to calculate the delta manually.

A reason/note is required.

## 9. Permissions

Inventory mutations are administrative actions.

Cashier/POS users cannot:

- Increase stock.
- Decrease stock manually.
- Change low-stock thresholds.
- Disable tracking.
- Correct negative balances.

Inventory mutation endpoints must reuse the existing Admin authorization
model.

The POS receives only the inventory information needed to determine whether a
product can be sold.

## 10. POS Catalog Contract

The POS catalog should expose inventory state for each branch product.

Conceptually, a tracked product can expose:

    inventory:
        tracked
        quantity_available
        low_stock
        out_of_stock
        needs_review

The exact API representation can follow the existing catalog schema style.

Persisted catalog availability and inventory availability must remain separate.

A product manually disabled in the catalog is different from a product that is
temporarily out of stock.

The POS computes sellability from both conditions.

Conceptually:

    can_sell =
        catalog_is_available
        AND
        (
            inventory_not_tracked
            OR quantity_available > 0
        )

## 11. POS User Experience

For untracked products:

- Behavior does not change.

For tracked products with stock:

- Product can be sold normally.

For low-stock products:

- Product remains sellable.
- A subtle low-stock state may be displayed.

For stock = 0:

- Product displays Agotado.
- Product cannot be added to a new sale.

Cashiers cannot override an out-of-stock block.

An administrator must correct the inventory if the count is wrong.

## 12. When Inventory Is Deducted

Inventory is not reserved when:

- Product is viewed.
- Product is added to the cart.
- A sale has not yet crossed its payment boundary.

Inventory is applied when a sale is confirmed as PAID.

### Online sale boundary

When the POS has network connectivity, checkout is server-first.

The POS freezes one immutable sale identity before sending:

- order_uuid
- payment_uuid
- folio
- created_at_client
- receipt_snapshot

It then sends that exact payload to the normal online order endpoint.

The backend:

1. Resolves the branch and products.
2. Locks relevant tracked inventory balances.
3. Validates sufficient stock.
4. Persists order and payment.
5. Creates SALE movements.
6. Updates inventory balances.
7. Commits the complete transaction.

If tracked stock is insufficient, the transaction is rejected and the sale is
not confirmed. The cashier keeps the cart and corrects the unavailable item.

Only after backend success does the browser persist the completed local copy as
SYNCED.

### Network failure during checkout

If the request cannot reach the server because of an actual network failure or
timeout, the POS preserves the already-frozen order UUID, folio, timestamp and
receipt snapshot.

The same sale is then finalized locally and queued as PENDING_SYNC.

The POS must not generate a second sale identity after a network failure.

### Offline sale boundary

When the device is already offline, checkout remains local-first.

The paid local order, immutable receipt and synchronization event are persisted
atomically in IndexedDB.

The server later receives that already-completed sale through the explicit
offline synchronization path.

Normal online sales must never knowingly reduce tracked stock below zero.

## 13. Sale Movements

Each tracked order item creates an inventory deduction proportional to its
quantity.

Example:

    Order UUID: abc-123
    Coca-Cola quantity: 2

Movement:

    SALE
    quantity_delta = -2

Modifiers do not affect Phase 1 inventory.

Ingredient/modifier consumption is deferred to the hybrid phase.

## 14. Idempotency

Inventory must never be deducted twice because an order is retried or an
offline queue synchronizes more than once.

Automatic movements use deterministic idempotency keys.

Conceptual SALE key:

    sale:{order_uuid}:{order_item_id}:{inventory_item_id}

Conceptual reversal key:

    sale-reversal:{order_uuid}:{order_item_id}:{inventory_item_id}

The database enforces uniqueness for non-null automatic idempotency keys.

Retrying the same operation returns the existing result instead of creating a
second inventory movement.

## 15. Refunds and Cancellations

Phase 1 includes an explicit administrative refund/cancellation operation for
completed POS sales.

This operation is protected by Admin authorization.

For a previously paid sale:

1. Lock the order.
2. Confirm the sale has not already been reversed.
3. Set payment_status to REFUNDED.
4. Set the order operational status to CANCELLED.
5. Create SALE_REVERSAL movements for every original tracked SALE movement.
6. Restore the branch balances.
7. Commit the complete transaction.

A reversal creates:

    SALE_REVERSAL
    quantity_delta = positive original quantity

Only one reversal may be applied for the corresponding SALE movement.

The reversal operation is idempotent. Retrying the same administrative request
must not restore inventory twice.

A cancellation/refund that never had an inventory SALE movement does not
create inventory out of nothing.

Phase 1 does not implement partial refunds. The complete sale is reversed.

## 16. Offline Behavior

Offline sales must remain possible.

The POS uses:

- Last synchronized inventory snapshot.
- Unsynchronized paid sales stored locally.

Effective local availability is conceptually:

    cached_cloud_quantity
    -
    local_unsynchronized_paid_quantity

Example:

    Cached stock: 3
    Offline sale: 2

Local available stock becomes:

    1

After another offline sale of 1:

    0

The same device then blocks additional sales of that product.

## 17. Multiple Offline Devices

Two disconnected devices can have the same stale stock snapshot.

Example:

    Actual stock before disconnect: 1

    Tablet A sees 1 and sells 1.
    Tablet B sees 1 and sells 1.

This cannot be perfectly prevented without network coordination.

When both orders synchronize:

- Both already-completed sales are preserved.
- Both inventory movements are recorded exactly once.
- Balance may become negative.
- Inventory status becomes REVIEW.
- Admin corrects the physical count with an adjustment.

The system must not silently delete or reject a physically completed offline
sale solely to force inventory back to zero.

## 18. Offline Synchronization

Offline replay uses an explicit synchronization endpoint separate from strict
online checkout:

    POST /pos/orders/sync

The payload is the exact immutable paid-sale payload already stored locally.

When an offline paid order reaches the server:

1. Resolve/create the order through the existing order_uuid idempotency rule.
2. Persist its items and payment if the order does not already exist.
3. Apply inventory SALE movements.
4. Reuse deterministic inventory idempotency keys.
5. Update branch balances.
6. Permit a negative result only because the sale was already physically
   completed offline.
7. Return the persisted order response.

Retrying synchronization does not generate an additional order, payment or
inventory deduction.

The normal POST /pos/orders path remains strict and rejects insufficient online
inventory. The /pos/orders/sync path preserves already-completed offline sales.

## 19. Negative Inventory

Normal online sales must not create negative stock.

Negative stock is allowed only as a representation of a real operational
conflict such as offline overselling.

A negative quantity:

- Is not hidden.
- Is not automatically reset to zero.
- Produces REVIEW status.
- Blocks further sales.
- Requires an Admin adjustment.

This preserves auditability.

## 20. Disabling Inventory Tracking

An administrator may disable inventory tracking for a branch product.

When disabled:

- New sales stop creating inventory movements for that branch/product.
- POS no longer blocks sales based on inventory.
- Existing balance remains stored.
- Existing movement history remains available.
- No historical movement is deleted.

Re-enabling tracking resumes from the preserved balance unless an explicit
physical-count adjustment is performed.

## 21. Low Stock

Low stock is informational only in Phase 1.

When:

    quantity_on_hand <= low_stock_threshold
    AND quantity_on_hand > 0

the item is LOW_STOCK.

Phase 1 does not send:

- Email.
- WhatsApp.
- SMS.
- Push notifications.

The warning exists only inside COFI POS/Admin.

## 22. Branch Isolation

Balances are always branch-specific.

A sale at Branch A must never change the balance of Branch B.

Manual inventory actions always require an explicit branch context.

Transfers between branches are not implemented in Phase 1.

## 23. History

The Admin movement history should show:

- Date/time.
- Movement type.
- Quantity change.
- Balance after movement.
- Note/reason when relevant.
- Order folio when relevant.
- Administrative actor when relevant.

Example:

    +24  INITIAL         Stock inicial
     -2  SALE            NV-1052
     -1  WASTE           Producto dañado
     +3  ADJUSTMENT      Conteo físico
     +2  SALE_REVERSAL   NV-1052

## 24. Service Boundary

Inventory business logic belongs in a dedicated backend inventory service.

Order/payment code should call the inventory service instead of implementing
stock calculations directly.

Responsibilities of the inventory service include:

- Resolve inventory items.
- Read balances.
- Create movements.
- Update balances atomically.
- Validate sufficient online stock.
- Apply sales idempotently.
- Apply reversals idempotently.
- Create manual movements.
- Compute status.

This keeps order, catalog and inventory responsibilities isolated.

## 25. Proposed API Surface

Exact route naming may be adjusted to match existing FastAPI conventions.

Conceptual Admin endpoints:

    GET  /admin/pos/inventory
    GET  /admin/pos/inventory/{item_id}
    GET  /admin/pos/inventory/{item_id}/movements

    POST /admin/pos/inventory/{item_id}/receipt
    POST /admin/pos/inventory/{item_id}/waste
    POST /admin/pos/inventory/{item_id}/adjust

    POST /admin/pos/sales/{order_uuid}/refund

POS order endpoints:

    POST /pos/orders
        Strict online paid sale. Reject insufficient tracked inventory.

    POST /pos/orders/sync
        Replay an already-completed offline paid sale. Preserve the sale even
        when stale offline stock causes the resulting balance to become
        negative.

Inventory configuration can be exposed through the existing product/catalog
administration contract or a small inventory-specific configuration endpoint,
whichever best preserves current catalog service boundaries.

Public POS inventory state is delivered through the existing branch catalog
response rather than requiring the cashier to maintain a separate inventory
administration API.

## 26. Database Transaction Rules

A balance mutation and its movement must succeed or fail together.

For each movement:

1. Read/lock the relevant branch balance as appropriate.
2. Validate operation rules.
3. Insert movement.
4. Update quantity_on_hand.
5. Store resulting balance_after.
6. Commit transaction.

Automatic SALE/SALE_REVERSAL operations also enforce idempotency.

The implementation must be safe against two online requests attempting to sell
the same final unit concurrently.

## 27. Audit Rules

The following rules are mandatory:

- Never silently rewrite movement history.
- Never hard-delete normal inventory movements.
- Never alter quantity_on_hand without a corresponding movement.
- Never create duplicate automatic SALE movements.
- Never create duplicate automatic SALE_REVERSAL movements.
- Manual adjustments require an explanation.
- Offline conflicts remain visible instead of being hidden.

## 28. Existing Data / Migration

Adding inventory must not change behavior for existing products automatically.

After the migration:

- Existing products remain untracked.
- Existing sales remain unchanged.
- No historical inventory movements are fabricated.
- Administrators opt products into inventory explicitly.

This makes deployment backward-compatible.

## 29. Future Hybrid Inventory

Phase 2 can add ingredient items such as:

- Coffee.
- Milk.
- Egg.
- Chicken.
- Tortillas.
- Cups.

Prepared products can then reference recipes.

Example:

    Latte
        18 g Coffee
        250 ml Milk
        1 Cup

The existing Balance and Movement models remain valid.

The future recipe layer decides which inventory items a sale consumes.

Phase 1 finished-product inventory therefore does not need to be discarded.

## 30. Testing Strategy

Implementation follows TDD.

### Model and migration tests

Cover:

- Inventory item constraints.
- Balance uniqueness per branch/item.
- Numeric quantities.
- Movement types.
- Idempotency uniqueness.
- Backward-compatible migration.

### Inventory service tests

Cover:

- Initial stock.
- Receipt.
- Waste.
- Physical-count adjustment.
- Balance-after values.
- Low stock.
- Out of stock.
- Review/negative state.
- Invalid operations.
- Branch isolation.

### Sale integration tests

Cover:

- PENDING does not deduct.
- PAID deducts exactly once.
- Duplicate PAID request does not deduct twice.
- Multiple order quantities deduct correctly.
- Untracked products do not create movements.
- Insufficient online stock blocks payment completion.
- Concurrent attempts at the final unit cannot both succeed online.

### Reversal tests

Cover:

- Refund restores inventory.
- Cancellation reversal restores inventory where applicable.
- Duplicate reversal does not restore twice.
- Reversal without original SALE does not create stock.

### Offline tests

Cover:

- Cached stock.
- Local pending paid sales reduce local availability.
- Local zero stock blocks another sale.
- Offline synchronization applies movement once.
- Synchronization retry is idempotent.
- Two-device oversell can create REVIEW/negative balance without losing sales.

### Admin tests

Cover:

- Inventory page structure.
- Branch selection.
- Summary metrics.
- Search/filter behavior.
- Entry workflow.
- Waste workflow.
- Adjustment workflow.
- Movement history.
- Admin-only mutation access.

### POS UI tests

Cover:

- Untracked products unchanged.
- Available tracked product sellable.
- Low-stock product sellable.
- Out-of-stock product disabled.
- Cashier cannot override zero stock.
- Catalog refresh updates inventory state.

### Regression

Before completion run:

- Existing backend test suite relevant to POS.
- Complete POS Node test suite.
- Admin tests.
- Migration checks.
- Nginx validation if deployment configuration is touched.

Inventory work is not complete unless existing:

- Catalog.
- Cart.
- Orders.
- Payments.
- Customers.
- Loyalty.
- KDS Kitchen/Bar.
- Receipts.
- Offline order behavior.

continue to pass their existing tests.

## 31. Rollout Safety

Deployment order should be:

1. Database migration.
2. Backend models/service/API.
3. Catalog inventory response.
4. Admin Inventory UI.
5. POS inventory-awareness/offline behavior.

Existing products start untracked, so deploying the migration must not
immediately block any current sale.

Inventory can be enabled product-by-product after deployment and verification.

## 32. Success Criteria

Phase 1 is successful when:

- An admin can enable inventory for a product at one branch.
- An initial quantity can be recorded.
- Entries, waste and physical adjustments are auditable.
- A strict online paid sale deducts stock exactly once.
- An online sale with insufficient stock is not confirmed.
- A network failure preserves one frozen sale identity and queues it offline.
- Offline replay through /pos/orders/sync deducts stock exactly once.
- A refund/cancellation reversal restores stock exactly once.
- Low stock is visible.
- Zero stock blocks new POS sales.
- Offline operation remains usable.
- Offline retry cannot double-deduct.
- Offline oversell is visible and recoverable.
- Branch balances remain isolated.
- Existing untracked products behave exactly as before.
- Full existing POS regression tests remain green.
- The architecture can later accept ingredients/recipes without replacing the
  ledger and balance model.
