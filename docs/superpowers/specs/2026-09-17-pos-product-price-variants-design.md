# Cofi POS — Product Price Variants

Date: 2026-09-17
Status: Approved design
Branch: `feature/cofi-product-variants`

## 1. Purpose

Add reusable price variants to Cofi POS for products such as coffee,
lattes, cappuccinos, frappes, teas, and similar items.

Example:

Latte
- Chico 12 oz — $55
- Mediano 16 oz — $65
- Grande 20 oz — $75

The same reusable size definitions may be shared by many products, while
each product keeps its own price for every variant.

Variant prices and availability may also vary by branch.

## 2. Approved product decisions

The following decisions are approved:

- reusable variant groups,
- reusable variants,
- product-specific variant prices,
- branch-specific price overrides,
- branch-specific availability,
- products may use only a subset of variants,
- one variant group per product in v1,
- POS product cards show `Desde $X`,
- variant selection is mandatory,
- modifiers are selected after the variant,
- no inventory by variant in v1,
- products without variants keep current behavior.

## 3. Terminology

### Variant Group

Reusable collection of variants.

Example:

`Tamaños Café`

### Variant

Reusable option inside a group.

Examples:

- Chico 12 oz
- Mediano 16 oz
- Grande 20 oz

A Variant does not contain the final selling price.

### Product Variant

Relationship between a product and a Variant.

It determines:

- whether that product uses the variant,
- the default price for that product/variant,
- display order.

Example:

`Latte + Grande 20 oz = $75`

### Branch Product Variant

Branch-specific configuration of a Product Variant.

It may define:

- available / unavailable,
- branch-specific price override.

If there is no branch price override, the Product Variant default price
is used.

## 4. Data model

The existing product and modifier systems remain intact.

Variants are modeled separately from normal modifiers.

### 4.1 PosVariantGroup

Suggested fields:

- `id`
- `name`
- `is_active`
- `sort_order`

Example:

- name: Tamaños Café

### 4.2 PosVariant

Suggested fields:

- `id`
- `variant_group_id`
- `name`
- `is_active`
- `sort_order`

Examples:

- Chico 12 oz
- Mediano 16 oz
- Grande 20 oz

### 4.3 PosProductVariant

Relationship between a product and a reusable Variant.

Suggested fields:

- `id`
- `product_id`
- `variant_id`
- `price`
- `is_active`
- `sort_order`

Rules:

- unique `(product_id, variant_id)`
- price must be nonnegative
- a product may use only variants from one Variant Group in v1

Examples:

- Latte + Chico 12 oz = $55
- Latte + Mediano 16 oz = $65
- Latte + Grande 20 oz = $75
- Mocha + Grande 20 oz = $85

This allows the same reusable size to have a different price for every
product.

### 4.4 PosBranchProductVariant

Branch-specific configuration for a Product Variant.

Suggested fields:

- `id`
- `branch_id`
- `product_variant_id`
- `is_available`
- `price_override`

Rules:

- unique `(branch_id, product_variant_id)`
- `price_override = NULL` means use the Product Variant default price
- `is_available = false` means the variant cannot be sold in that branch
- price override must be nonnegative when present

Example:

Latte Grande 20 oz

- default price: $75
- Centro: no override -> $75
- Marina: override -> $82
- Aeropuerto: unavailable

## 5. Price resolution

For products with variants, the backend resolves the selling price.

Resolution order:

1. Find the selected Product Variant.
2. Verify it belongs to the selected product.
3. Verify Product Variant is active.
4. Verify Variant is active.
5. Verify Variant Group is active.
6. Look for Branch Product Variant configuration.
7. If branch configuration marks it unavailable, reject the sale.
8. If branch `price_override` is not NULL, use it.
9. Otherwise use Product Variant default price.

The frontend may display prices but must not be authoritative for sale
pricing.

For products without variants, existing product and branch price logic
remains unchanged.

## 6. Why variants are separate from modifiers

Existing modifiers represent additions or selections such as:

- leche de almendra,
- extra shot,
- vainilla,
- toppings.

Those are price deltas added after the product base price.

A size variant is different because:

- it determines the base selling price,
- it is mandatory for products that use variants,
- its price changes by product,
- its price may change by branch,
- its availability may change by branch,
- it must be validated as part of the product selection itself.

Therefore sizes must not be implemented as ordinary modifier price
deltas.


## 7. POS catalog response

The customer-facing POS catalog response must include resolved variant
information for every product that uses variants.

Conceptual product response:

```json
{
  "id": 123,
  "name": "Latte",
  "has_variants": true,
  "display_price": 55.00,
  "variants": [
    {
      "product_variant_id": 1001,
      "variant_id": 1,
      "name": "Chico 12 oz",
      "price": 55.00
    },
    {
      "product_variant_id": 1002,
      "variant_id": 2,
      "name": "Mediano 16 oz",
      "price": 65.00
    },
    {
      "product_variant_id": 1003,
      "variant_id": 3,
      "name": "Grande 20 oz",
      "price": 75.00
    }
  ]
}
```

Catalog rules:

- only active Variant Groups are considered,
- only active Variants are considered,
- only active Product Variants are considered,
- branch-unavailable Product Variants are excluded,
- branch-specific price overrides are resolved by the backend,
- frontend receives the final price for the current branch,
- `display_price` is the lowest currently available variant price,
- products without variants retain current catalog behavior.

The frontend must not calculate branch override rules itself.

## 8. Product-card behavior

### Product without variants

No behavior change.

Example:

`Taco Pastor — $25`

Selecting it follows the current flow.

### Product with variants

The card displays:

`Latte`

`Desde $55`

The "Desde" value must come from the lowest available resolved variant
price for the current branch.

A variant product cannot be added directly to the cart from the product
card.

Selecting the product opens configuration.

## 9. Variant selection flow

When the cashier taps a product with variants:

1. Open the existing product configuration flow.
2. Require exactly one available Product Variant.
3. Show each available variant name and resolved branch price.
4. Do not allow adding to cart until a variant is selected.
5. After variant selection, show existing modifier groups.
6. Existing modifier validation remains unchanged.
7. Calculate:
   - selected variant price,
   - plus modifier price deltas,
   - multiplied by quantity.

Example:

Latte

Select size:

- Chico 12 oz — $55
- Mediano 16 oz — $65
- Grande 20 oz — $75

Then modifiers:

- Leche de almendra +$12
- Extra shot +$15

Selected configuration:

- Grande 20 oz: $75
- Leche de almendra: +$12
- Extra shot: +$15

Unit total:

$102

## 10. Product configuration UI

The existing modifier modal should be extended rather than creating a
completely separate purchase flow.

For a variant product, the modal should present:

1. product name,
2. variant selection,
3. selected variant/base price,
4. modifier groups,
5. quantity,
6. calculated total,
7. add-to-cart action.

For a non-variant product with modifiers, the current modifier flow
remains visually and functionally unchanged.

For a product with variants but no modifiers, selecting a variant is
still mandatory before adding it.

## 11. Cart representation

Cart items must preserve the selected Product Variant explicitly.

Conceptual cart item:

```json
{
  "product_id": 123,
  "product_name": "Latte",
  "product_variant_id": 1003,
  "variant_name": "Grande 20 oz",
  "base_price": 75.00,
  "modifiers": [
    {
      "modifier_option_id": 10,
      "option_name": "Leche de almendra",
      "price_delta": 12.00
    }
  ],
  "unit_price": 87.00,
  "quantity": 1
}
```

For products without variants:

- `product_variant_id` is null or absent as allowed by the existing
  client model,
- `variant_name` is null or absent,
- existing behavior remains unchanged.

The cart UI should display:

`Latte · Grande 20 oz`

and then existing modifier lines below it.

## 12. Checkout request

The order creation request must identify the selected Product Variant.

Conceptual request item:

```json
{
  "product_id": 123,
  "product_variant_id": 1003,
  "quantity": 1,
  "modifier_option_ids": [10]
}
```

The frontend does not send a trusted sale price.

The backend recalculates the authoritative selling price using the
current product, variant, branch, availability, override, and modifier
rules.

## 13. Server-side order validation

For every order item, the backend must validate:

1. Product exists.
2. Product is active.
3. Product is available in the current branch.
4. Whether the product requires a Product Variant.
5. If variants are required, `product_variant_id` is present.
6. Product Variant belongs to the selected product.
7. Product Variant is active.
8. Variant is active.
9. Variant Group is active.
10. Product Variant is available in the current branch.
11. Branch price override is valid when present.
12. Existing modifier selections remain valid.

The server calculates:

`resolved variant price + modifier price deltas`

For products without variants, the current pricing path remains unchanged.

Client-provided prices must never override backend price resolution.

## 14. Historical order snapshots

Historical orders must not depend on future catalog changes.

When a variant product is sold, the order item must preserve:

- product identity,
- product name snapshot,
- selected Product Variant identity,
- variant name snapshot,
- resolved historical unit price,
- modifier names,
- modifier price deltas.

If a variant is later renamed, repriced, disabled, or removed from a branch,
the historical order must continue to show the original sale information.

Example historical line:

`Latte · Grande 20 oz — $75`

Existing `unit_price` remains the authoritative historical final unit price.

## 15. Order storage

Order item storage should gain nullable variant fields compatible with
existing orders.

Suggested additions:

- `product_variant_id`
- `variant_name`

If the current order architecture requires a separate variant or base-price
snapshot for correctness, it may be added during implementation.

Compatibility rules:

- existing order rows remain valid,
- old orders may have NULL variant fields,
- non-variant products create order items with no selected variant,
- no destructive conversion of historical order data.

## 16. KDS behavior

KDS displays the selected variant as part of the product identity.

Example:

`2 × Latte · Grande 20 oz`

Existing modifiers remain below it:

- Leche de almendra
- Extra shot

Variant selection does not create a new KDS status or workflow.

Preparation-station routing remains based on the existing product routing
configuration.

## 17. Order history behavior

POS order history and order detail must display the historical variant
snapshot stored with the order item.

Example:

`Latte · Grande 20 oz`

The display must use the order snapshot rather than the current catalog
variant name.

Orders without variants continue rendering exactly as they do today.

## 18. Receipt behavior

Receipts must display the selected variant as part of the product name.

Example:

`1 x Latte · Grande 20 oz       $75.00`
`    + Leche de almendra        $12.00`
`    + Extra shot               $15.00`

Receipt generation must use historical order or receipt snapshot data.

Changing, disabling, or repricing a current catalog variant must not alter
an old receipt.

Existing receipts without variants remain compatible.

## 19. Offline and cached catalog behavior

The POS currently caches catalog data for local use.

Variant data must be included in the cached catalog so the POS can:

- render `Desde $X`,
- show available size options,
- use already-resolved branch-specific variant prices,
- calculate the expected local display total,
- preserve selected Product Variant identity in the local cart/order model.

For local display, the client uses the already-resolved variant price from
the cached branch catalog.

When the order reaches the backend, server-side validation and price
resolution remain authoritative.

Existing non-variant offline behavior must not regress.

## 20. Admin catalog behavior

The admin catalog must support management of:

- Variant Groups,
- Variants,
- Product Variant assignments,
- Product Variant default prices,
- branch-specific Product Variant availability,
- branch-specific Product Variant price overrides.

### 20.1 Variant Groups

Administrators can:

- create,
- rename,
- activate or deactivate,
- control display order.

Example:

`Tamaños Café`

### 20.2 Variants

Inside a Variant Group, administrators can:

- create,
- rename,
- activate or deactivate,
- control display order.

Examples:

- Chico 12 oz
- Mediano 16 oz
- Grande 20 oz

### 20.3 Product configuration

A product may use zero or one Variant Group in v1.

Administrators choose which variants from that group the product uses and
define the default product-specific price for each enabled option.

Example:

| Variant | Enabled | Default price |
| --- | ---: | ---: |
| Chico 12 oz | Yes | $55 |
| Mediano 16 oz | Yes | $65 |
| Grande 20 oz | Yes | $75 |

Another product may use only part of the same group:

| Variant | Enabled | Default price |
| --- | ---: | ---: |
| Chico 12 oz | No | — |
| Mediano 16 oz | Yes | $72 |
| Grande 20 oz | Yes | $85 |

### 20.4 Branch configuration

For each enabled Product Variant, a branch may configure:

- available or unavailable,
- optional price override.

Example:

| Variant | Available | Branch price |
| --- | ---: | ---: |
| Chico 12 oz | Yes | — |
| Mediano 16 oz | Yes | $68 |
| Grande 20 oz | No | — |

A blank branch price means inherit the Product Variant default price, not
zero.

## 21. Database migration and compatibility

The feature requires new catalog tables for:

- Variant Groups,
- Variants,
- Product Variants,
- Branch Product Variant overrides.

The migration should create concepts equivalent to:

- `pos_variant_groups`
- `pos_variants`
- `pos_product_variants`
- `pos_branch_product_variants`

Order storage receives nullable variant fields required for historical
snapshots.

Migration requirements:

- no destructive transformation of existing product data,
- no automatic conversion of existing modifiers into variants,
- no variant requirement for existing products,
- existing orders remain readable,
- existing receipts remain readable,
- existing products continue selling without configuration changes,
- foreign keys and uniqueness constraints protect catalog integrity.

The migration must be tested against an isolated database before production.

## 22. Security and integrity

The backend is authoritative for:

- product availability,
- Product Variant ownership,
- Variant Group status,
- Variant status,
- branch availability,
- default variant price,
- branch price override,
- modifier validation,
- final calculated order price.

The backend must reject:

- a Product Variant belonging to another product,
- an inactive Product Variant,
- an inactive Variant,
- an inactive Variant Group,
- a branch-unavailable Product Variant,
- a missing variant when the product requires one,
- malformed or invalid variant identifiers.

The browser may display calculated prices but is never the trusted source of
the sale price.

## 23. Non-goals for v1

The first version intentionally excludes:

- inventory quantities by variant,
- more than one Variant Group per product,
- time-based variant pricing,
- happy-hour pricing,
- variant-specific modifier rules,
- combo rules based on size,
- automatic recipe consumption by size,
- independent SKU management for every variant,
- branch-specific variant names,
- variant-specific images,
- nested variants.

These may be added later without changing the core Product Variant model.

## 24. Testing strategy

Implementation must follow TDD.

### 24.1 Backend tests

At minimum test:

1. Variant Group creation and update.
2. Variant creation and update.
3. Product Variant assignment.
4. Product may use only selected variants.
5. Default Product Variant price.
6. Branch price override.
7. Branch availability false.
8. Catalog resolves correct branch price.
9. Catalog excludes unavailable variants.
10. Variant is required for variant products.
11. Variant from another product is rejected.
12. Inactive variant is rejected.
13. Unavailable branch variant is rejected.
14. Server ignores manipulated client pricing.
15. Default variant price is used when no override exists.
16. Branch override is used when present.
17. Modifiers are added after variant base price.
18. Non-variant products remain unchanged.
19. Historical snapshot preserves variant name and price.

### 24.2 Frontend tests

At minimum test:

1. Non-variant product keeps existing behavior.
2. Variant product displays `Desde`.
3. `Desde` uses lowest available resolved price.
4. Variant selection is mandatory.
5. Only available variants can be selected.
6. Selected variant changes displayed base price.
7. Modifiers apply after variant selection.
8. Cart stores Product Variant identity.
9. Cart displays variant name.
10. Checkout payload includes `product_variant_id`.
11. KDS displays historical variant name.
12. Orders screen displays historical variant name.
13. Receipt displays historical variant name.
14. Existing POS tests remain green.

### 24.3 Migration tests

Verify:

- new tables exist,
- foreign keys exist,
- unique constraints exist,
- prices cannot be negative,
- nullable historical fields preserve old orders,
- migration head advances correctly.

## 25. TDD implementation order

Implementation should proceed in small RED/GREEN cycles:

1. Database models and migration.
2. Variant Group and Variant admin backend.
3. Product Variant assignment and default prices.
4. Branch availability and price overrides.
5. POS catalog response.
6. Order request schema.
7. Backend validation and price resolution.
8. Historical order snapshot persistence.
9. POS product card `Desde` behavior.
10. Variant-selection UI.
11. Cart representation and checkout payload.
12. Offline/local representation.
13. Orders and KDS rendering.
14. Receipt snapshot and rendering.
15. Full regression verification.

Each production change requires a failing test first.

## 26. Deployment considerations

This feature changes database, backend, and frontend code.

Production deployment must verify:

1. Current production database state is known.
2. Migration passes against an isolated database.
3. Backend suite passes.
4. POS suite passes.
5. Merged main passes fresh verification.
6. Database migration is applied.
7. Backend application is deployed.
8. Static POS assets are deployed.
9. Catalog endpoint returns variants correctly.
10. Existing non-variant product can still be sold.
11. Variant product can be sold.
12. Branch price override works.
13. Branch-unavailable variant cannot be sold.
14. KDS displays selected variant.
15. Receipt displays selected variant.

Rollback planning must distinguish application rollback from database
migration rollback.

No production migration should run until the merged commit passes the full
verification suite.

## 27. Acceptance criteria

The feature is complete when:

1. Admin can create `Tamaños Café`.
2. Admin can create Chico, Mediano, and Grande variants.
3. Latte can use all three variants.
4. Frappé can use only Mediano and Grande.
5. Each product can define a different price for the same size.
6. A branch can override a Product Variant price.
7. A branch can disable a Product Variant.
8. POS card shows the correct branch-specific `Desde` value.
9. Cashier must select a size before adding the product.
10. Existing modifiers work after size selection.
11. Backend independently validates and recalculates the price.
12. Cart displays the selected size.
13. KDS displays the selected size.
14. Order history displays the selected size.
15. Receipt displays the selected size.
16. Historical sales remain correct after catalog changes.
17. Products without variants behave exactly as before.
18. Existing test suites remain green.
