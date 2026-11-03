# COFI Papelería — Functional Design

Date: 2026-11-03

## Intent

Create **COFI Papelería** as a retail/POS module inside the existing COFI platform. It should reproduce the practical day-to-day workflows users expect from a desktop retail POS such as eleventa, while keeping COFI's own visual design, code, branding, architecture, permissions, and deployment model.

This is not a code or UI copy of eleventa. eleventa is used only as a functional/workflow reference.

## Product Position

COFI remains the parent platform.

- **COFI Cafetería** continues operating independently.
- **COFI Papelería** is a separate operational module.
- Both share the same backend infrastructure, authentication foundation, database server, deployment, backups, and global administration.
- Operational data, staff access, registers, inventory, and reports are separated by module/business context.
- The global administrator can access both Cafetería and Papelería.
- Papelería employees are exclusive to Papelería.

## Selected Architecture

### Approach A — Modular subsystem inside COFI

Selected by the owner.

Papelería will be implemented as a first-class COFI module rather than as a second standalone application or separate database.

Shared:
- authentication foundation;
- global administrator;
- branch/business identity;
- backend/API conventions;
- audit infrastructure;
- deployment;
- backups;
- receipt infrastructure where reusable.

Separated:
- POS workspace;
- Papelería employees/permissions;
- register shifts and cash;
- product catalog visibility;
- inventory;
- services;
- sales;
- Papelería reports;
- operational settings.

## Functional Reference

The target is the **speed and coverage of a retail POS like eleventa**, with a different COFI-native design.

Core reference workflows to reproduce:
- rapid sale screen;
- barcode scanner input;
- product search;
- multiple concurrent/in-progress sales;
- products by unit/package;
- retail/wholesale or quantity-based pricing;
- products that use inventory and items/services that do not;
- inventory entries, adjustments, low-stock view, movement history and Kardex;
- day sales history;
- returns/cancellations;
- cash register shifts, cash movements and closing;
- user permissions;
- ticket printing;
- price verification;
- keyboard/scanner-friendly operation;
- support for common POS peripherals where technically available.

## Explicit Scope Decisions

### Payments

Supported:
- CASH;
- CARD.

Not included:
- customer credit;
- customer balances;
- payment plans.

Card processing may initially remain external/manual and can later use the Mercado Pago Point integration already being evaluated for COFI.

### Employees and permissions

- Papelería employees cannot enter Cafetería.
- Cafetería employees cannot enter Papelería.
- The global administrator can access both.
- Sensitive actions use an **administrator PIN overlay** without logging the cashier out.

Administrator authorization is required for:
- discounts;
- manual price overrides;
- cancellations;
- returns/exchanges;
- manual inventory entries;
- manual inventory removals;
- inventory corrections/adjustments.

Every authorization stores:
- acting employee;
- authorizing administrator;
- timestamp;
- sale/product affected;
- old/new values when applicable;
- reason.

### Products

A product supports:
- internal SKU;
- name/description;
- barcode;
- category/department;
- cost;
- sale price;
- optional wholesale/alternate price;
- active/inactive state;
- inventory-enabled flag;
- minimum stock;
- optional maximum stock;
- multiple sale presentations.

Search supports:
- barcode scan;
- SKU;
- product name;
- category;
- presentation.

A valid barcode scan should add the matching presentation directly to the current sale when unambiguous.

### Presentations / package-unit conversion

Inventory uses a base unit.

Examples:
- pen: 1 piece base unit; box = 12 pieces;
- paper: 1 sheet base unit; pack = 500 sheets; case = 5,000 sheets.

Each presentation may have:
- its own barcode;
- conversion factor;
- sale price;
- alternate/wholesale price.

Selling a presentation decrements inventory by its base-unit conversion.

### Services

Papelería also sells non-stock services such as:
- black-and-white copies;
- color copies;
- printing;
- scanning;
- binding;
- laminating;
- other configurable services.

Computer rental is explicitly excluded.

Services support quantity-tier pricing.

Example:
- 1–20 copies: price A each;
- 21–100: price B each;
- 101+: price C each.

The POS recalculates the applicable unit price automatically when quantity changes.

Future enhancement, not required for V1:
- link service consumption to internal consumables such as paper or toner.

### Inventory

Employees:
- may view stock;
- may sell stock-controlled items.

Administrators:
- may add stock;
- remove stock;
- correct stock;
- enter adjustment reasons.

Every stock change creates an immutable movement.

Movement types:
- opening/import;
- sale;
- return;
- manual entry;
- manual removal;
- adjustment;
- cancellation reversal.

Inventory views:
- current stock;
- low stock;
- movement report;
- per-product Kardex;
- inventory valuation using product cost.

### Purchases and suppliers

Explicitly excluded from the first Papelería version.

Stock replenishment is entered manually by an administrator.

The data model should avoid blocking a future purchases/suppliers module.

### POS sale workspace

The Papelería POS should prioritize speed over restaurant-style product browsing.

Primary layout:
- always-focused scan/search field;
- sale line table;
- quantity controls;
- line price;
- subtotal/total;
- payment shortcuts;
- product/service quick access;
- current employee and register status.

Supported sale actions:
- scan product;
- search product;
- add service;
- modify quantity;
- remove line before payment;
- suspend/hold sale;
- resume held sale;
- price check;
- cash payment;
- card payment;
- print/reprint receipt.

The design must be visually distinct from eleventa and consistent with COFI.

### Concurrent / held sales

An employee can keep multiple sales in progress.

Each held sale stores:
- identifier;
- optional label/customer note;
- items;
- quantities;
- calculated prices;
- creation time;
- cashier.

Held sales do not affect inventory until payment is finalized.

### Discounts

All discounts require administrator PIN authorization.

Supported:
- line discount;
- whole-sale discount;
- amount or percentage where configured.

The final receipt and audit log preserve the discount.

### Returns, exchanges, cancellations

Administrator authorization is mandatory.

Return:
- references original sale;
- supports returning selected quantities;
- restores inventory when appropriate;
- records money movement according to configured refund method.

Cancellation:
- references original sale;
- reverses eligible inventory effects;
- creates an audit event;
- never deletes the original transaction.

Exchange:
- implemented as controlled return + replacement sale so audit and inventory remain explicit.

### Cash register

Papelería has its own register lifecycle independent of Cafetería.

Functions:
- opening amount;
- active shift;
- cash entries;
- cash withdrawals;
- expected cash;
- closing count;
- difference;
- administrator-controlled close where required;
- historical shifts.

Reports must separate:
- cash sales;
- card sales;
- returns;
- cash movements;
- expected vs counted cash.

### Sales history

Search/filter by:
- ticket/folio;
- date;
- cashier;
- payment method;
- product;
- status.

Actions depend on permissions:
- view;
- reprint;
- administrator-authorized return;
- administrator-authorized cancellation.

### Reports

Initial reports:
- daily sales;
- sales by date range;
- sales by category;
- sales by employee;
- sales by payment method;
- products sold;
- services sold;
- gross margin where cost exists;
- low stock;
- inventory valuation;
- inventory movements;
- Kardex;
- register/cash-shift report;
- discounts and administrator authorizations;
- returns/cancellations.

Global COFI administrator should be able to view Papelería reports without mixing them into Cafetería operational totals unless explicitly requesting a consolidated dashboard.

## Data Model Direction

Use module-aware entities rather than duplicating COFI infrastructure.

Likely new or extended concepts:
- business/module context;
- retail products/presentations or extensions to current POS catalog;
- service pricing tiers;
- inventory balances;
- inventory movements;
- held retail sales;
- retail sales and sale lines;
- retail payments;
- administrator authorization events.

Where existing COFI entities already correctly solve the problem (staff identity, cash shifts, receipts, audit patterns), reuse them with module isolation rather than creating parallel implementations.

## Reuse of Existing Inventory Work

The existing branch `feature/cofi-pos-inventory` contains useful inventory models, APIs, services, migrations and tests.

However, it has diverged substantially from current `main`.

Decision:
- do not merge the old branch wholesale;
- inspect and port the useful domain logic onto current `main`;
- preserve current production behavior;
- adapt inventory to the Papelería module and presentation conversions;
- keep tests or rewrite them against the current architecture.

## Non-Goals for V1

- customer credit;
- customer balances/abonos;
- purchases;
- suppliers;
- computer rental;
- restaurant KDS behavior;
- self-order kiosk for Papelería;
- copying eleventa source code, assets, branding, or visual trade dress.

## Reliability and Safety

- no production deployment during initial development;
- database changes through Alembic;
- idempotent sale/payment identifiers;
- inventory updates and sale finalization in controlled transactions;
- no hard deletion of financial transactions;
- audit every sensitive administrator action;
- tests for stock race conditions, duplicate submissions, returns, conversions and cash reconciliation;
- rollback path before production release.

## Success Criteria

Papelería is ready for operational pilot when an employee can:

1. sign in only to Papelería;
2. open the Papelería cash register;
3. scan/search products rapidly;
4. sell unit/package presentations with correct stock conversion;
5. sell quantity-priced services;
6. hold and resume sales;
7. collect cash or card;
8. print a receipt;
9. see stock decrement correctly;
10. close the register and reconcile cash.

And when an administrator can:

1. access both COFI modules;
2. create/edit products and services;
3. perform stock adjustments;
4. authorize discounts by PIN;
5. authorize returns/cancellations;
6. review audit history;
7. review sales, inventory and cash reports.

## UI Direction

The workflow should feel as fast as a keyboard/scanner-first retail POS, but visually belong to COFI.

Proposed visual language:
- clean modern workspace;
- large total and payment actions;
- dense but readable sale table;
- persistent scan/search input;
- keyboard-first shortcuts;
- optional touch-friendly quick tiles for services;
- clear module identity: **COFI Papelería**;
- responsive for desktop POS and tablet, while desktop/scanner operation is the primary target.

No eleventa visual elements are to be copied.
