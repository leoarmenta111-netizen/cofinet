# CofiCenter POS — Ixtapa v1 Completion Design

**Date:** 2026-10-14
**Status:** Approved design
**Initial production branch:** Ixtapa
**Initial physical registers:** 1
**Architecture:** Existing POS extended through separate integrated subsystems

---

## 1. Purpose

Complete the existing CofiCenter POS so it can become the official production POS for the Ixtapa branch.

The goal is not to rewrite the POS. Existing catalog, orders, customer management, receipts, Kitchen/Bar routing, PWA support, offline queue, and self-order capabilities remain in place.

The work adds the missing operational and financial controls required for real daily use:

- employee authentication and roles
- cash shifts
- blind cash counts
- cash movements
- payment lifecycle
- mixed payments
- tips
- discounts
- cancellations
- refunds
- finished-product inventory
- audit trail
- reporting
- production-grade offline behavior

Clip integration will be added only after this foundation is stable.

---

## 2. Scope

### Included in Ixtapa v1

- Ixtapa only
- one physical POS/cash drawer
- multiple employees sharing that register
- employee PIN authentication
- Cashier / Manager / Administrator roles
- multiple cash shifts per day
- one open cash shift at a time
- blind cash closing
- denomination-based opening and closing counts
- cash inflows/outflows
- cash payments
- external card payments
- mixed Cash + Card payments
- tips
- predefined and manager-authorized manual discounts
- cancellations
- full and partial refunds
- Kitchen/Bar cancellation visibility
- finished-product inventory
- stock receipts
- waste
- physical-count adjustments
- low-stock warnings
- out-of-stock manager override
- offline cash sales
- automatic synchronization
- reporting
- audit events
- receipt printing/reprinting

### Explicitly out of scope

- Clip integration
- CFDI / invoicing
- ingredient inventory
- recipes
- gram/ml consumption
- purchasing / purchase orders
- inventory valuation/accounting
- Bucerías production rollout
- Nuevo Vallarta production rollout

Those are later phases.

---

## 3. Existing POS Foundation

The current POS already contains:

- product catalog and modifiers
- branch-aware catalog
- POS orders
- POS customers
- receipts and receipt snapshots
- Kitchen and Bar station routing
- order states
- PWA functionality
- IndexedDB/local persistence
- offline synchronization queue
- unique order UUIDs
- unique payment UUID foundation
- administrative sales reporting
- Kiosk/self-order integration

The current order API is branch-aware and includes terminal identifiers.

The current offline synchronization flow resends orders using their original order UUID, giving the server an idempotency base for reconnection.

---

## 4. Architectural Direction

Use separate subsystems integrated with the existing POS.

Do not rebuild the POS.

Proposed domains:

- `pos_staff`
- `pos_cash`
- `pos_payments`
- `pos_refunds`
- `pos_inventory`
- `pos_audit`

`PosOrder` remains the commercial sale/order entity.

Financial, cash, authorization, refund, and inventory responsibilities should not all be added directly into `PosOrderService`.

---

# 5. Staff and Authorization

## 5.1 Roles

### CASHIER

May:

- unlock POS with personal PIN
- create sales
- use predefined promotions
- view orders
- print/reprint receipts
- perform blind closing count
- cancel unpaid orders with reason
- view product availability

May not:

- open/close cash drawer without Manager authorization
- approve cash movements
- approve manual discounts
- approve refunds
- override out-of-stock products
- change inventory configuration

### MANAGER

May perform all Cashier actions plus:

- authorize cash opening
- authorize final cash close
- authorize cash movements
- authorize manual/special discounts
- authorize refunds
- authorize card reversals
- register inventory receipts
- register waste
- perform physical inventory count
- authorize out-of-stock override

### ADMINISTRATOR

Uses username + password rather than an operational PIN.

May:

- access reports
- manage employees
- manage permissions
- manage catalog/configuration
- enable/disable inventory tracking
- change low-stock thresholds
- perform Manager actions
- inspect audit history

---

## 5.2 Employee PINs

Cashiers and Managers have individual PINs.

Requirements:

- PIN must never be stored in plaintext
- server stores a secure password/PIN hash
- each sale records the employee
- sensitive approvals record both requesting employee and authorizing Manager
- inactive employees cannot authenticate

---

## 5.3 POS Locking

The POS supports:

- manual quick lock
- automatic lock after 5 minutes of inactivity

Locking:

- does not close the cash shift
- does not delete the current cart
- does not cancel the sale

The next employee enters their personal PIN.

---

## 5.4 Offline Unlock

If the register was already operating before connectivity was lost:

- previously authorized employees may unlock offline
- only employees already known to that device are eligible
- PIN plaintext is never cached
- use a secure local verifier
- new employees/credentials require online validation

---

# 6. Cash Shifts

## 6.1 Register Model

Ixtapa v1 has:

- one branch
- one physical register
- one cash drawer
- only one OPEN shift at a time

Multiple shifts may occur on the same calendar day.

---

## 6.2 Shift States

Recommended states:

- `OPEN`
- `CLOSING`
- `CLOSED`

A shift cannot be deleted after financial activity exists.

Closed shifts are immutable.

---

## 6.3 Cash Opening

Opening requires online connectivity.

Flow:

1. employee requests new shift
2. opening cash is counted by denomination
3. system calculates opening total
4. Manager enters PIN
5. shift becomes OPEN

There is no default opening amount.

A person determines the amount each time.

---

## 6.4 Denominations

Opening and closing use:

- $1
- $2
- $5
- $10
- $20
- $50
- $100
- $200
- $500
- $1,000 MXN

Store quantity for each denomination.

The total is calculated by the system rather than manually entered.

---

## 6.5 Cash Movements

Supported directions:

- INFLOW
- OUTFLOW

Supported categories:

- Cambio
- Gasto
- Retiro a caja fuerte
- Depósito
- Corrección
- Otro

Every movement stores:

- shift
- direction
- category
- amount
- note
- requesting employee
- authorizing Manager
- timestamp

Manager authorization is mandatory.

Movements modify expected cash.

---

# 7. Blind Cash Closing

Closing requires online connectivity.

Flow:

1. Cashier selects Close Shift.
2. POS does not reveal expected cash.
3. Cashier counts physical cash by denomination.
4. Count is submitted.
5. System then reveals reconciliation.
6. If a difference exists, explanation is mandatory.
7. Manager authorizes with PIN.
8. Shift becomes CLOSED.

Reconciliation displays:

- opening cash
- cash sales
- cash tips
- cash inflows
- cash outflows
- cash refunds
- expected cash
- counted cash
- difference

Closed shifts cannot be edited.

Corrections after closure require a new auditable event.

---

# 8. Payment Architecture

## 8.1 Principle

An order and a payment are different domain concepts.

The current POS assumes one payment object during order creation.

Ixtapa v1 must support one or more payment records related to one order.

---

## 8.2 Payment Methods

Initial methods:

- `CASH`
- `CARD_EXTERNAL`

Future:

- `CLIP`

Clip must fit into this model without redesigning orders.

---

## 8.3 Payment States

Recommended lifecycle:

- `PENDING`
- `APPROVED`
- `DECLINED`
- `CANCELLED`
- `REFUNDED`

Each payment includes:

- `payment_uuid`
- order
- shift
- employee
- method
- amount
- status
- external reference
- amount tendered when applicable
- change due when applicable
- created timestamp

Payment UUID must remain unique/idempotent.

---

# 9. Cash Payment

Flow:

1. calculate final amount
2. enter amount tendered
3. validate tendered >= cash portion
4. calculate change
5. approve payment
6. register financial effect against active shift

Example:

Total: 185
Tendered: 200
Change: 15

Cash drawer financial increase is 185.

---

# 10. External Card Payment

Until Clip is integrated:

1. cashier selects Card
2. payment is performed on external terminal
3. cashier confirms approval/rejection
4. optional terminal authorization/reference may be stored
5. only an approved card payment contributes toward paid balance

Selecting “Card” alone must never mark the order as paid.

---

# 11. Mixed Payments

Ixtapa v1 supports exactly two payment parts:

- Card
- Cash

No multiple-card split in v1.

Example:

Order total: 400
Card: 250
Cash: 150

Card is processed first.

If the customer gives 200 cash:

- cash portion remains 150
- change = 50

The order becomes PAID only when approved payments exactly cover the final amount.

---

## 11.1 Card Decline

If card is declined:

- order remains open
- cart/order is preserved
- cashier may retry
- cashier may change payment method

---

## 11.2 Card Approved but Cash Cannot Be Completed

If the card portion is already approved:

- order remains pending
- remaining balance may be resolved by another allowed method
- if the sale is abandoned, the approved card portion must be reversed/refunded
- reversal requires Manager approval

No orphan partial payments are allowed.

---

# 12. Tips

Options:

- 10%
- 15%
- 20%
- Other
- No tip

Tips are stored separately from product sales.

Example:

Products: 300
Tip: 45
Collected: 345

Tips belong to a general Ixtapa shift pool rather than to the cashier.

Reports distinguish:

- cash tips
- card tips
- total tips

Cash tips remain physically in the cash drawer and are included in expected cash.

---

# 13. Discounts

## Predefined promotions

Cashier may apply approved predefined promotions.

## Manual/special discount

Requires Manager PIN.

Store:

- requesting employee
- authorizing Manager
- percentage or amount
- reason
- timestamp

The backend recalculates financial totals.

Never trust only the browser-calculated total.

---

# 14. Financial Integrity

Server must enforce:

`product total - discounts + tips = final amount`

And:

`sum(APPROVED payments) = final amount`

A sale must not become PAID if those conditions are false.

Prevent:

- duplicated payment UUID
- incomplete sale marked paid
- negative change
- excess card collection
- duplicated offline payment
- reused payment operation

---

# 15. Cancellations

Cancellation means the sale has not been financially completed.

An unpaid order may be cancelled by Cashier without Manager PIN.

Required:

- reason
- employee
- timestamp

If any approved payment already exists, the financial payment must be reversed first.

That case is not a simple cancellation.

---

# 16. Refunds

Refunds may be:

- full
- partial

Partial refund selects specific original items and quantities.

Refunds are allowed up to 7 days after the original sale.

Every refund requires:

- Manager PIN
- mandatory reason
- requesting employee
- authorizing Manager
- original order
- original order items
- quantities
- exact refund amount
- timestamp

Use original sale pricing.

Do not recalculate using today's catalog price.

---

## 16.1 Refund Data Model

Recommended:

### `pos_refunds`

- UUID
- original order
- refund type
- total amount
- state
- reason
- requesting employee
- authorizing Manager
- created/completed timestamps

### `pos_refund_items`

- refund
- original order item
- quantity
- attributed original amount
- inventory disposition

Recommended refund states:

- `PENDING`
- `APPROVED`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

---

## 16.2 Refund Payment Method

Refund goes back through the original payment method.

Cash sale:

- refund from active cash drawer

Card external:

- perform terminal refund first
- record reference/confirmation

Future Clip:

- server requests Clip refund
- mark complete only after provider confirmation

---

## 16.3 Mixed-Payment Refunds

Refund allocation is proportional to original payment allocation.

Example:

Original:

- 100 cash
- 300 card

Partial refund: 80

Refund:

- 20 cash
- 60 card

Do not arbitrarily change the refund method.

---

# 17. Kitchen / Bar Cancellation Behavior

If a refunded/cancelled item is still:

- `NEW`
- `PREPARING`

the station must display:

**CANCELADO — NO PREPARAR**

Do not silently remove the line.

Other valid lines continue through normal preparation.

If an item is already:

- `READY`
- `DELIVERED`

do not pretend preparation was undone.

The refund is recorded and inventory disposition is selected.

---

# 18. Inventory — Ixtapa v1

Inventory v1 tracks finished products only.

No ingredients or recipes.

The existing `feature/cofi-pos-inventory` work will be ported into the current POS architecture rather than blindly merged.

---

## 18.1 Existing Inventory Concepts to Preserve

- inventory item
- branch inventory balance
- quantity on hand
- low-stock threshold
- tracking enabled/disabled
- movement history
- INITIAL
- RECEIPT
- SALE
- SALE_REVERSAL
- WASTE
- ADJUSTMENT
- idempotency key
- row locking
- branch-aware quantities

---

## 18.2 Inventory States

- `UNTRACKED`
- `AVAILABLE`
- `LOW_STOCK`
- `OUT_OF_STOCK`
- `REVIEW`

Rules:

- tracking disabled → UNTRACKED
- quantity < 0 → REVIEW
- quantity = 0 → OUT_OF_STOCK
- quantity <= threshold → LOW_STOCK
- otherwise → AVAILABLE

---

# 19. Inventory Sale Integration

When a completed sale includes tracked products:

- create SALE inventory movements
- decrement quantity exactly once
- associate movement with order and order item

Inventory movement must be idempotent.

Offline retries must not decrement twice.

Financial completion and inventory application must have coherent transactional behavior.

---

# 20. Out of Stock

At quantity `0`:

- product remains visible
- card displays `AGOTADO`
- Cashier cannot add normally

Manager may authorize exceptional sale.

Override records:

- employee
- Manager
- product
- quantity
- quantity before/after
- reason
- timestamp

Negative inventory is allowed only through this explicit Manager override.

Negative quantity yields `REVIEW`.

---

# 21. Low Stock

At or below threshold while quantity is still greater than zero:

- show `BAJO STOCK`
- normal sale remains allowed
- no Manager authorization required

Low stock is a warning, not a sales block.

---

# 22. Inventory Operations

## Manager and Administrator

May:

- receive stock
- register waste
- perform physical counts

## Administrator only

May:

- activate/deactivate inventory tracking
- change low-stock threshold
- structural inventory configuration

---

## 22.1 Receipt

Adds quantity and records:

- quantity
- note
- user
- timestamp

Movement type:

`RECEIPT`

---

## 22.2 Waste

Reduces quantity.

Requires:

- quantity
- reason/note
- user
- timestamp

Movement type:

`WASTE`

---

## 22.3 Physical Count

User enters actual physical quantity.

System calculates delta.

Example:

System: 22
Physical: 19
Movement: -3

Do not silently overwrite balance.

Movement type:

`ADJUSTMENT`

Note is required.

---

# 23. Refund Inventory Disposition

Manager chooses for each returned product:

### RETURN_TO_INVENTORY

Product is saleable again.

Generate positive inventory movement associated with refund.

### WASTE

Product cannot be resold.

Examples:

- prepared beverage
- opened item
- damaged item

Do not increase sellable stock.

Record waste/refund relationship.

Partial refunds affect only refunded quantities.

---

# 24. Inventory UI

Create an Ixtapa inventory management screen.

Columns:

- Product
- Quantity
- Minimum
- Status
- Last Updated

Filters:

- All
- Low Stock
- Out of Stock
- Review

Product detail includes:

- current quantity
- threshold
- movement history
- Receive Stock
- Waste
- Physical Count

POS product cards expose only operational information:

- LOW STOCK
- OUT OF STOCK
- REVIEW

Detailed inventory management belongs in administrative/manager UI.

---

# 25. Offline Operation

## Allowed while offline

Only when a shift was already opened online:

- unlock with previously authorized local employee verifier
- cash-only sales
- receipt generation
- local order persistence
- queueing for synchronization

## Not allowed offline

- opening a shift
- closing a shift
- manual cash movements
- new Manager authorizations
- card payment
- mixed payment
- refund
- employee/permission changes
- inventory configuration

---

# 26. Offline Synchronization

Every local sale remains stored until server confirmation.

States should be visible to staff:

- Online
- Offline — X pending sales
- Synchronizing
- Synchronization Error — Review Required

Synchronization reuses stable UUIDs.

Server idempotency must protect:

- order
- payment
- inventory movement

A retry must never create:

- duplicate sale
- duplicate payment
- duplicate inventory deduction

---

# 27. Audit Log

Create persistent POS audit events.

At minimum:

- `SHIFT_OPENED`
- `SHIFT_CLOSED`
- `CASH_MOVEMENT`
- `MANAGER_OVERRIDE`
- `DISCOUNT_OVERRIDE`
- `ORDER_CANCELLED`
- `REFUND_CREATED`
- `REFUND_COMPLETED`
- `INVENTORY_RECEIPT`
- `INVENTORY_ADJUSTMENT`
- `INVENTORY_WASTE`
- `OUT_OF_STOCK_OVERRIDE`

Each event records:

- event UUID
- branch
- terminal
- actor
- actor role
- authorizer when applicable
- target entity
- timestamp
- structured metadata

Audit history must not depend only on Docker logs.

---

# 28. Reports

Administrator reporting must support Ixtapa filters by:

- date
- shift

Required metrics:

- gross sales
- refunds
- net sales
- cash
- card
- mixed payments
- discounts
- cash tips
- card tips
- total tips
- cancellations
- waste
- cash inflows
- cash outflows
- expected cash
- counted cash
- difference
- sale count
- average ticket

Sale detail must expose:

- employee
- order
- products
- discounts
- tips
- payments
- refund history
- approvals
- relevant audit events

---

# 29. Cash Shift Report

Every closed shift produces an immutable report.

Opening:

- employee
- authorizing Manager
- denomination count
- initial cash

Activity:

- cash sales
- cash tips
- inflows
- outflows
- cash refunds

Closing:

- denomination count
- expected cash
- counted cash
- difference
- required difference note
- authorizing Manager

---

# 30. Existing Inventory Branch Integration Strategy

Do not merge `feature/cofi-pos-inventory` directly into the current release.

Port the useful inventory implementation deliberately.

Reason:

The inventory branch predates later POS work including self-order/kiosk and subsequent POS changes.

Preserve:

- database model concepts
- movement service
- row locking
- idempotency
- API behavior where still appropriate
- tests that remain valid

Adapt:

- order completion integration
- refunds
- offline behavior
- new staff/role authorization
- Ixtapa inventory UI
- current schemas and services

---

# 31. Production Safety

Database changes must use Alembic migrations.

Do not manually mutate production schema.

New financial actions require idempotency keys where retry is possible.

Use transactions for operations that must succeed atomically.

Sensitive operations must be server-authorized.

Client-side role checks are UI convenience only, never authorization.

---

# 32. QA Matrix

Ixtapa POS v1 is not complete until the following pass:

1. Open shift with denomination count.
2. Multiple employees use the same open register.
3. Quick lock preserves cart.
4. Automatic lock after 5 minutes.
5. Previously authorized employee unlocks offline.
6. Cash sale.
7. External card approval.
8. External card decline.
9. Mixed Card + Cash.
10. Cash change during mixed payment.
11. Partial card attempt does not create orphan payment.
12. Predefined promotion.
13. Manager-approved manual discount.
14. Cash inflow.
15. Cash outflow.
16. Full refund.
17. Partial refund.
18. Refund within 7-day limit.
19. Refund rejection outside allowed rules.
20. Mixed-payment proportional refund.
21. Kitchen/Bar sees CANCELADO — NO PREPARAR.
22. Returned product goes back to inventory.
23. Returned product becomes waste.
24. Inventory receipt.
25. Inventory waste.
26. Physical-count adjustment.
27. Low-stock warning.
28. Out-of-stock block.
29. Manager out-of-stock override.
30. Negative inventory becomes REVIEW.
31. Internet loss during cash sale.
32. Offline sale persists after reload/restart.
33. Pending sale syncs after reconnection.
34. Repeated sync does not duplicate order.
35. Repeated sync does not duplicate inventory movement.
36. Receipt prints.
37. Historical receipt reprints.
38. Blind closing does not expose expected amount before submission.
39. Difference requires explanation.
40. Manager PIN required for final close.
41. Closed shift cannot be edited.
42. Cash report reconciles correctly.
43. Admin reporting reconciles with orders/payments/refunds.
44. Cashier permissions are enforced server-side.
45. Manager permissions are enforced server-side.
46. Administrator security remains separate from operational PIN login.
47. Kitchen/Bar normal station flow remains functional.
48. Kiosk/self-order regression suite remains green.

---

# 33. Definition of Done

Ixtapa POS v1 is considered production-ready only when all of the following operate end-to-end:

- Staff
- Roles
- Cash shifts
- Blind close
- Cash movements
- Payments
- Mixed payment
- Tips
- Discounts
- Orders
- Kitchen
- Bar
- Receipts
- Cancellations
- Refunds
- Finished-product inventory
- Offline cash sales
- Synchronization
- Reporting
- Audit

All automated tests must pass.

Production migrations must apply cleanly.

Docker/build/health checks must pass.

A manual Ixtapa acceptance test must pass on the actual POS device.

---

# 34. Subsequent Phases

After Ixtapa v1 is stable:

## Payment Integration
- Clip

## Inventory Phase 2
- ingredients
- recipes
- units of measure
- automatic ingredient consumption

## Fiscal
- CFDI / invoicing

## Multi-branch rollout
- Bucerías
- Nuevo Vallarta

The Ixtapa v1 architecture must support these later phases without requiring another POS rewrite.
