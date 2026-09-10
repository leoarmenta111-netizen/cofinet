# POS Receipts and Station Printing — Design

Date: 2026-09-08
Status: Approved design
Scope: Customer receipts, immutable sale snapshots, offline receipts,
tax configuration, Kitchen/Bar print jobs, and future Print Bridge.

## 1. Objective

Build a reliable receipt and printing subsystem for the CofiCenter POS.

It must:

- work online and offline;
- generate customer sale receipts;
- support historical reprints;
- support separate Kitchen and Bar production tickets;
- preserve the exact commercial sale as charged;
- support configurable taxes;
- support configuration by business and branch;
- avoid dependency on a specific printer brand;
- never allow printer failure to block payment;
- support a multi-business SaaS architecture.

This is a normal proof-of-sale receipt.

It is NOT:

- CFDI;
- SAT integration;
- a fiscal invoice;
- a government tax-document system.

## 2. Core Architecture

Keep three concepts separate.

### Order

The commercial and operational sale.

It continues to participate in:

- payment;
- Orders;
- Kitchen/Bar routing;
- KDS;
- operational statuses.

### Receipt Snapshot

An immutable representation of exactly what was sold and charged.

It is the source for:

- customer receipt preview;
- customer printing;
- historical reprinting.

### Print Job

A request to print a specific document.

It is independent from payment and order state.

It will support:

- customer tickets;
- Kitchen tickets;
- Bar tickets;
- original prints;
- intentional reprints;
- retries;
- print audit.

## 3. Immutable Paid Sales

Once a sale is paid, its commercial values must never be edited in place.

The sale freezes:

- public folio;
- original sale date/time;
- branch;
- terminal;
- customer display name, when selected;
- product names;
- quantities;
- modifiers;
- actual charged unit prices;
- line totals;
- subtotal;
- discount when applicable;
- tax mode;
- tax rate;
- tax amount;
- tip;
- final total;
- payment method;
- cash tendered;
- change due;
- receipt header/footer configuration.

Changing the catalog later must never alter an old receipt.

Changing business settings later must never alter an old receipt.

Future refunds, returns, or cancellations must be separate movements that
reference the original paid sale.

## 4. Offline-Safe Public Folio

New sales will no longer depend on a server database ID for their public folio.

The POS generates the final public folio locally before payment finalization.

Example:

    NV-260908-7K3M9Q2F

Recommended structure:

- branch prefix;
- branch-local date;
- high-entropy human-readable random suffix.

Requirements:

- works offline;
- exists before server synchronization;
- shared by sale, order, customer ticket, Kitchen and Bar;
- never changes after creation;
- unique database constraint on server.

`order_uuid` remains the technical idempotency identifier.

The numeric PostgreSQL order ID remains internal.

Legacy folios such as `NUE-000040` remain valid forever and are not rewritten.

## 5. Branch Time

The receipt and folio date use the configured branch timezone.

The POS must cache branch timezone/configuration for offline operation.

`created_at_client` remains the canonical original sale instant sent to
the backend.

## 6. Receipt Snapshot

Create a versioned receipt snapshot.

Minimum semantic data:

- `schema_version`
- `order_uuid`
- `folio`
- `sold_at`
- `currency`

Business snapshot:

- commercial name;
- logo reference;
- phone;
- web/social text;
- footer message.

Branch snapshot:

- branch code;
- display name;
- address;
- phone;
- timezone.

Terminal snapshot:

- terminal ID;
- cashier identity when available in the future.

Customer snapshot:

- customer name only, when selected.

Item snapshot:

- product ID;
- product name;
- quantity;
- actual unit price;
- line total;
- customer-visible modifiers and their charged deltas.

Totals snapshot:

- subtotal;
- discount;
- tax mode;
- tax rate;
- tax amount;
- tip;
- final total.

Payment snapshot:

- payment method;
- amount;
- cash tendered when applicable;
- change due when applicable.

Internal Kitchen/Bar notes do not belong in the customer receipt snapshot
presentation.

## 7. Historical Integrity

Historical tickets must render from the frozen receipt snapshot.

They must NEVER be reconstructed from:

- current product names;
- current prices;
- current modifier configuration;
- current tax settings;
- current logo;
- current address;
- current receipt footer.

The renderer displays historical data.

It does not recalculate commercial business rules.

## 8. Business and Branch Configuration

Receipt configuration follows inheritance:

    Business defaults
          ↓
    Branch overrides

If a branch defines a value, the branch value wins.

Otherwise, the business default is used.

### Business Settings

Configure:

- commercial name;
- logo;
- phone;
- website or social text;
- receipt footer message;
- currency;
- default receipt width;
- tax mode;
- tax rate;
- customer automatic-print preference.

### Branch Overrides

A branch may override:

- branch display name;
- address;
- phone;
- receipt header;
- receipt footer;
- tax mode;
- tax rate;
- timezone;
- receipt folio prefix;
- printer mappings in later phases.

The effective configuration is resolved at sale time.

That resolved configuration is copied into the immutable receipt snapshot.

A later settings change must not modify a historical receipt.

## 9. Tax Modes

V1 supports one effective tax configuration per business/branch.

V1 does not implement product-specific tax classes.

Supported modes:

### NONE

No tax is calculated.

The receipt does not need to show a tax row.

### INCLUDED

Displayed product prices already include tax.

The sale total does not increase because of tax.

For gross amount `G` and tax rate `R`:

    tax = G - (G / (1 + R))

Example:

    Gross price: $116.00
    Tax rate: 16%

    Tax included: $16.00

The customer still pays:

    $116.00

### ADDED

Tax is added after the commercial subtotal.

For taxable subtotal `S` and tax rate `R`:

    tax = S * R

    total = S + tax + tip

Example:

    Subtotal: $100.00
    Tax 16%:  $16.00
    Total:    $116.00

V1 applies tax to product subtotal after commercial discounts when those
discounts exist.

Tip is not part of the tax base in V1.

All money calculations must use deterministic decimal rounding consistently
in frontend and backend.

This receipt is still a normal proof-of-sale document.

It is not a fiscal invoice.

## 10. Customer Privacy

When no customer is selected:

- omit the customer section.

When a customer is selected:

- print the customer name only.

Do not print by default:

- phone;
- email;
- customer UUID;
- CRM history;
- loyalty identifiers;
- private notes.

## 11. Customer Receipt — 80 mm

Initial paper format:

    80 mm thermal receipt

The receipt displays:

- configured logo;
- business commercial name;
- branch name;
- branch address when configured;
- phone when configured;
- website/social text when configured;
- public sale folio;
- original date and time;
- terminal;
- cashier when cashier identity exists;
- customer name when selected;
- products;
- quantities;
- customer-visible modifiers;
- unit/line prices;
- subtotal;
- discount when applicable;
- tax information according to configuration;
- tip;
- final total;
- payment method;
- cash received and change for cash sales;
- configured thank-you/footer message.

The customer ticket must not display:

- Kitchen notes;
- Bar notes;
- internal preparation notes;
- complete external card-terminal references;
- private customer data;
- fiscal/CFDI wording.

## 12. Receipt User Flow

After a successful sale, the success experience becomes:

    Venta registrada

    [ Ver ticket ]
    [ Imprimir ticket ]
    [ Nueva venta ]

Customer ticket printing is manual by default.

Automatic customer printing may later be enabled by business/branch
configuration.

Without a Print Bridge, browser/device security may still require a system
print confirmation.

The sale must never depend on successful printing.

## 13. Historical Reprinting

From:

    Órdenes
       → Ver detalle
       → Ticket

provide:

- View receipt
- Reprint receipt

The reprinted receipt must use the original immutable receipt snapshot.

It must never use current catalog prices or current business settings.

## 14. Customer Receipt Renderer

Create one reusable receipt renderer.

Input:

- immutable receipt snapshot.

Initial outputs:

- on-screen receipt preview;
- browser print view.

The renderer must not:

- query the current catalog;
- query current product prices;
- recalculate tax business rules;
- replace historical business settings.

It only renders the frozen snapshot.

## 15. Print CSS

Initial printing uses browser printing with dedicated print styles.

Requirements:

- `@media print`;
- 80 mm layout;
- thermal-printer-safe typography;
- black-and-white friendly;
- no POS navigation;
- no modal backgrounds;
- no unnecessary visual decoration;
- no clipped totals;
- no horizontal scrolling;
- clean page margins.

Design the renderer so 58 mm support can be added later without changing
stored historical data.

## 16. Offline Receipt Flow

A paid sale must be able to produce its receipt while offline.

Flow:

1. POS prepares the final local sale.
2. POS generates final public folio.
3. POS creates immutable receipt snapshot.
4. POS persists the sale locally.
5. Receipt can immediately be viewed.
6. Receipt can immediately be printed.
7. Sync queue sends the same sale later.
8. Server stores the same order UUID, folio and commercial values.

The POS may show:

    Pendiente de sincronizar

inside the application.

That status must NOT be printed on the customer's receipt.

## 17. Atomic Local Finalization

When payment is finalized locally, the POS should persist together, within
one IndexedDB transaction where practical:

- order UUID;
- final public folio;
- order payload;
- receipt snapshot;
- payment snapshot;
- synchronization queue entry;
- future print jobs when applicable.

If internet disappears immediately after payment, the local sale and receipt
must still remain available.

## 18. Server Synchronization Rules

The backend must not reprice a completed offline sale using the current
catalog.

The server validates:

- valid quantities;
- valid decimal money values;
- line arithmetic;
- modifier arithmetic;
- subtotal arithmetic;
- tax arithmetic;
- tip arithmetic;
- final total;
- cash received/change;
- order UUID idempotency;
- folio uniqueness.

If catalog prices changed between offline payment and later synchronization:

- do not silently modify the paid sale;
- preserve the historical charged values;
- optionally record an audit discrepancy.

The server must validate the received paid snapshot without replacing it
with current commercial pricing.

## 19. Receipt Failure Rules

If receipt preview fails:

- sale remains paid;
- sale remains stored.

If customer printing fails:

- sale remains paid;
- operator may print again.

If synchronization fails:

- local sale remains available;
- local receipt remains available;
- retry preserves order UUID and public folio.

Printing must never roll back payment.

## 20. Kitchen and Bar Production Tickets

Kitchen and Bar tickets are operational documents.

They are NOT customer receipts.

They use separate renderers but share the same:

- order UUID;
- public folio;
- original sale time;
- immutable order-item snapshots.

### Kitchen Ticket

Include only items whose preparation station snapshot is:

    KITCHEN

Display:

- COCINA;
- public folio in large text;
- order time;
- customer name when useful;
- quantity;
- product name;
- all preparation modifiers;
- internal item notes.

Do not display:

- prices;
- subtotal;
- taxes;
- tip;
- payment method;
- customer phone/email.

### Bar Ticket

Include only items whose preparation station snapshot is:

    BAR

Display the same operational structure as Kitchen.

Kitchen and Bar must never be combined into one production ticket.

## 21. Preparation Station Snapshot

Production-ticket routing must use the preparation station stored on the
order item at sale time.

Do not use the current product catalog to determine where a historical item
belongs.

Example:

If a product was KITCHEN yesterday and changes to BAR tomorrow, yesterday's
ticket must still remain KITCHEN.

## 22. Station Output Modes

Each branch can configure Kitchen and Bar independently.

Supported modes:

- KDS
- PRINT
- KDS_AND_PRINT
- OFF

Examples:

    Kitchen → KDS_AND_PRINT
    Bar     → KDS

or:

    Kitchen → PRINT
    Bar     → PRINT

or:

    Kitchen → KDS
    Bar     → KDS

A business that does not need printers can continue using only KDS.

## 23. Automatic Production Printing

When a station is configured as:

- PRINT; or
- KDS_AND_PRINT;

its ORIGINAL production ticket is intended to print automatically after the
sale is successfully registered.

Production printing must never block payment.

If printing fails:

- sale remains paid;
- order remains valid;
- KDS remains independent;
- print job remains pending or failed;
- operator can retry or reprint.

## 24. Print Job Model

Create a dedicated Print Job concept.

Recommended logical fields:

- print job UUID;
- order UUID;
- public folio;
- branch;
- station;
- document type;
- print type;
- reprint sequence;
- target printer identifier;
- status;
- attempt count;
- last error;
- creation time;
- last attempt time;
- printed time.

Document types initially include:

- CUSTOMER_RECEIPT
- KITCHEN_TICKET
- BAR_TICKET

Print type:

- ORIGINAL
- REPRINT

Recommended statuses:

- PENDING
- SENDING
- PRINTED
- FAILED
- CANCELLED

A Print Job is infrastructure.

It must never mutate the commercial sale.

## 25. Print Idempotency

Original automatic Kitchen and Bar jobs must be deduplicated.

Recommended logical identity:

    order_uuid + station + ORIGINAL

Example:

    123e4567...:KITCHEN:ORIGINAL

Synchronization retries must not create multiple original Kitchen tickets.

Synchronization retries must not create multiple original Bar tickets.

An intentional reprint creates a separate job.

Example:

    123e4567...:KITCHEN:REPRINT:1

Reprinted production tickets must visibly show:

    REIMPRESIÓN

near the top.

## 26. Print Audit

Record enough information to diagnose printing problems.

Include:

- order UUID;
- folio;
- station;
- document type;
- original/reprint;
- printer;
- request time;
- attempt count;
- success/failure;
- error message;
- printed time.

This lets support distinguish between:

- sale problem;
- KDS problem;
- printer offline;
- Print Bridge unavailable;
- intentional reprint.

## 27. Browser Printing

Phase 1 customer receipts use browser printing.

This provides broad compatibility with:

- desktop;
- tablet;
- mobile;
- different thermal printer brands.

Browser printing is appropriate for:

- customer ticket preview;
- customer manual printing;
- development verification of station tickets.

Browser printing alone must NOT be presented as reliable silent automatic
Kitchen/Bar printing.

## 28. Print Bridge

Silent and reliable automatic thermal printing will use a future local
Print Bridge.

The Print Bridge is a small service running on the business LAN.

Responsibilities:

- receive authorized Print Jobs;
- connect to configured thermal printers;
- send printer-compatible output;
- maintain local retry queue;
- report printer/bridge health;
- report print success/failure;
- support station-to-printer assignment.

Future printer transports may include:

- network;
- USB;
- ESC/POS-compatible devices;
- vendor-supported local transports.

The receipt subsystem must not hard-code one specific printer vendor.

## 29. Print Bridge Security

The future Print Bridge must not expose an open unauthenticated LAN endpoint.

Its separate design must define:

- branch-scoped authorization;
- device pairing;
- credentials/tokens;
- job validation;
- replay protection;
- local-network threat model.

The exact bridge protocol will be specified before Phase 3 implementation.

## 30. Offline Station Printing

Target behavior for the Print Bridge phase:

If internet is unavailable but the POS can still reach the Print Bridge on
the local network:

1. Sale completes locally.
2. Order and receipt snapshot persist locally.
3. Kitchen/Bar Print Jobs are created locally.
4. Print Bridge receives station jobs.
5. Kitchen/Bar continue printing.
6. Server synchronization happens later.

The receipt/order model must support this architecture from Phase 1.

## 31. Production Reprinting

From Order Detail, authorized operators should eventually be able to request:

- Reprint customer receipt
- Reprint Kitchen
- Reprint Bar

Only relevant actions should appear.

Example:

If an order contains no BAR items:

    Reprint Bar

must not be shown.

Production reprints must display:

    REIMPRESIÓN

Customer receipt reprints may use normal receipt formatting without an
operational REIMPRESIÓN banner unless business requirements later demand it.

## 32. Printer Failure Rules

A printer problem must never:

- cancel a paid sale;
- delete an order;
- change order totals;
- change payment status;
- change KDS status;
- generate a second commercial sale.

Failure affects only Print Job state.

## 33. Legacy Orders

Existing orders keep their historical server-generated folios.

Example:

    NUE-000040

Do not rewrite old folios.

Legacy orders may not contain a modern receipt snapshot.

For legacy receipt viewing:

- use only information actually stored;
- do not invent historical tax data;
- do not invent historical business settings;
- do not invent customer information.

If insufficient information exists, the UI must clearly treat it as a
legacy receipt representation.

## 34. Phase 1 — Customer Receipt Foundation

Implement first:

- offline-safe public folio;
- final folio generated before synchronization;
- immutable receipt snapshot;
- local IndexedDB persistence;
- exact paid-price preservation;
- no repricing during delayed synchronization;
- business receipt settings;
- branch receipt overrides;
- timezone configuration;
- tax modes NONE / INCLUDED / ADDED;
- customer privacy rules;
- 80 mm receipt renderer;
- receipt preview;
- Print Receipt after payment;
- View/Reprint from Orders;
- browser print stylesheet;
- backend snapshot persistence;
- backend receipt retrieval;
- required migrations;
- full regression coverage.

Do NOT implement Print Bridge in Phase 1.

## 35. Phase 2 — Kitchen and Bar Print Jobs

Implement after Phase 1 is stable:

- Kitchen renderer;
- Bar renderer;
- station output configuration;
- Print Job persistence;
- original-job deduplication;
- reprint sequence;
- REIMPRESIÓN marker;
- print status;
- print audit;
- Order Detail station reprint actions.

Manual/browser printing may be used to verify rendering.

Do not claim true silent automatic station printing yet.

## 36. Phase 3 — Print Bridge

Before implementation, create a separate approved design for Print Bridge.

Phase 3 will address:

- local service architecture;
- supported operating systems;
- printer discovery;
- printer configuration;
- ESC/POS output;
- persistent local queue;
- retries;
- branch authorization;
- device pairing;
- health reporting;
- offline LAN behavior;
- station-to-printer mapping;
- automatic Kitchen/Bar printing.

## 37. Testing Strategy

Implementation uses TDD.

### Backend

Tests must cover:

- public folio validation;
- folio uniqueness;
- order UUID idempotency;
- immutable receipt snapshot;
- receipt retrieval;
- historical price preservation;
- delayed offline synchronization;
- no repricing from current catalog;
- arithmetic validation;
- tax NONE;
- tax INCLUDED;
- tax ADDED;
- deterministic rounding;
- branch settings inheritance;
- branch overrides;
- customer privacy;
- legacy order compatibility.

Phase 2 backend tests additionally cover:

- Print Job creation;
- Print Job deduplication;
- Kitchen isolation;
- Bar isolation;
- intentional reprints;
- failure state;
- print failure not affecting payment.

### Frontend

Tests must cover:

- folio generation before persistence;
- offline-safe folio generation;
- receipt snapshot creation;
- IndexedDB receipt persistence;
- offline receipt access;
- receipt uses snapshot instead of live catalog;
- customer name only;
- preparation notes excluded from customer ticket;
- tax rendering;
- 80 mm print stylesheet;
- receipt preview;
- success-screen receipt actions;
- Orders reprint action;
- responsive mobile receipt preview.

Phase 2 frontend tests additionally cover:

- Kitchen filtering;
- Bar filtering;
- no pricing on production tickets;
- modifiers and notes visible;
- REIMPRESIÓN marker;
- station reprint actions.

### Regression

Always run:

- complete POS Node suite;
- affected backend POS suite;
- customer flow tests;
- payment tests;
- offline sync tests;
- Orders tests;
- Kitchen/Bar KDS tests.

## 38. Migration Safety

Production contains real POS orders.

Migrations must be additive and preserve existing data.

Before production migration:

1. Verify current Alembic revision.
2. Create validated PostgreSQL backup.
3. Test upgrade against development/test environment.
4. Run affected backend tests.
5. Run complete frontend POS suite.
6. Verify migration result.
7. Deploy backend intentionally.
8. Verify live health and receipt routes.

Never:

- recreate the production database;
- delete production PostgreSQL volume;
- rewrite existing order folios;
- destructively rebuild order history.

## 39. Out of Scope

Not included in this initial receipt architecture:

- CFDI;
- SAT integration;
- electronic fiscal invoicing;
- product-specific tax classes;
- complex jurisdiction tax engine;
- refunds engine;
- returns engine;
- discount-engine redesign;
- email receipts;
- SMS receipts;
- 58 mm layout;
- cloud printing;
- automatic printing without Print Bridge;
- printer-driver installation workflow;
- printer purchasing;
- expo station;
- multiple preparation stations per product.

## 40. Success Criteria — Phase 1

Phase 1 is successful when:

1. A sale can complete offline.
2. Final public folio exists before synchronization.
3. Receipt can immediately be viewed offline.
4. Receipt can immediately be printed.
5. Synchronization preserves the exact paid values.
6. Catalog changes do not alter historical receipts.
7. Business-setting changes do not alter historical receipts.
8. Receipt can be reprinted from Orders.
9. Customer privacy rules are respected.
10. All three tax modes behave consistently.
11. Existing payment flows remain functional.
12. Existing customer flows remain functional.
13. Existing Orders flows remain functional.
14. Existing KDS flows remain functional.
15. Full affected regression suites are green.

## 41. Success Criteria — Station Printing

Station printing is successful when:

1. Kitchen and Bar remain isolated.
2. Each station receives only its own items.
3. Production tickets contain modifiers and internal notes.
4. Production tickets contain no prices/payment data.
5. Original jobs are idempotent.
6. Reprints are intentional and visibly marked.
7. Printer failure never affects payment.
8. KDS remains independent from printing.
9. Print audit identifies failures.
10. Future Print Bridge can consume Print Jobs without changing Order or
    Receipt Snapshot architecture.

## 42. Final Architecture Summary

The final architecture is:

    Order
      |
      +---- Immutable Receipt Snapshot
      |         |
      |         +---- Customer Receipt Renderer
      |         |
      |         +---- Historical Reprint
      |
      +---- KITCHEN item snapshots
      |         |
      |         +---- Kitchen Renderer
      |
      +---- BAR item snapshots
                |
                +---- Bar Renderer

    Print Jobs
      |
      +---- Customer
      +---- Kitchen
      +---- Bar
                |
                +---- Future Print Bridge

Commercial sale data is immutable.

Printing is infrastructure.

Printer failure never changes payment.

The POS remains usable online and offline.
