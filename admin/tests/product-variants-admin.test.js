const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const html = fs.readFileSync(
    path.resolve(__dirname, "../catalog.html"),
    "utf8"
);

test("product editor includes price variants section", () => {
    assert.match(
        html,
        /id="product-variants-section"/
    );

    assert.match(
        html,
        /id="product-variant-group"/
    );

    assert.match(
        html,
        /id="product-variants"/
    );

    assert.match(
        html,
        />Variantes de precio</
    );
});

test("admin renders product variant editor", () => {
    assert.match(
        html,
        /function renderProductVariants\(product\)/
    );

    assert.match(
        html,
        /catalog\.variant_groups/
    );

    assert.match(
        html,
        /product\.variant_group_id/
    );
});

test("admin assigns and removes product variant group", () => {
    assert.match(
        html,
        /\/variant-group\/\$\{groupId\}/
    );

    assert.match(
        html,
        /\/variant-group`/
    );

    assert.match(
        html,
        /method:\s*"DELETE"/
    );
});

test("admin saves per-product variant price and active state", () => {
    assert.match(
        html,
        /function saveProductVariants\(productId\)/
    );

    assert.match(
        html,
        /\/variants\/\$\{variantId\}/
    );

    assert.match(
        html,
        /price:/
    );

    assert.match(
        html,
        /is_active:/
    );
});

test("openProduct renders variant settings", () => {
    assert.match(
        html,
        /renderProductVariants\(\s*product\s*\)/
    );
});

test("product submit saves variants after base product update", () => {
    assert.match(
        html,
        /await saveProductVariants\(\s*id\s*\)/
    );
});
