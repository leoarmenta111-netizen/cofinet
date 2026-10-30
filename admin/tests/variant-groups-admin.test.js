const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const html = fs.readFileSync(
    path.resolve(__dirname, "../catalog.html"),
    "utf8"
);

test("admin includes reusable price variant group panel", () => {
    assert.match(
        html,
        /id="variant-groups"/
    );

    assert.match(
        html,
        /id="new-variant-group"/
    );

    assert.match(
        html,
        />Variantes de precio</
    );
});

test("admin includes variant group dialog", () => {
    assert.match(
        html,
        /id="variant-group-dialog"/
    );

    assert.match(
        html,
        /id="variant-group-form"/
    );

    assert.match(
        html,
        /id="variant-group-name"/
    );
});

test("admin includes variant option dialog", () => {
    assert.match(
        html,
        /id="variant-option-dialog"/
    );

    assert.match(
        html,
        /id="variant-option-form"/
    );

    assert.match(
        html,
        /id="variant-option-name"/
    );
});

test("admin renders reusable variant groups", () => {
    assert.match(
        html,
        /function renderVariantGroups\(\)/
    );

    assert.match(
        html,
        /catalog\.variant_groups/
    );

    assert.match(
        html,
        /renderVariantGroups\(\)/
    );
});

test("admin creates and updates variant groups", () => {
    assert.match(
        html,
        /function openVariantGroup\(group = null\)/
    );

    assert.match(
        html,
        /\/admin\/pos\/catalog\/variant-groups/
    );

    assert.match(
        html,
        /method:\s*id\s*\?\s*"PATCH"\s*:\s*"POST"/
    );
});

test("admin creates and updates variants inside group", () => {
    assert.match(
        html,
        /function openVariantOption\(/
    );

    assert.match(
        html,
        /\/variant-groups\/\$\{groupId\}\/variants/
    );

    assert.match(
        html,
        /\/variants\/\$\{variantId\}/
    );
});

test("variant group editor exposes active and sort order", () => {
    assert.match(
        html,
        /id="variant-group-order"/
    );

    assert.match(
        html,
        /id="variant-group-active"/
    );

    assert.match(
        html,
        /sort_order:/
    );

    assert.match(
        html,
        /is_active:/
    );
});

test("variant option editor exposes active and sort order", () => {
    assert.match(
        html,
        /id="variant-option-order"/
    );

    assert.match(
        html,
        /id="variant-option-active"/
    );
});
