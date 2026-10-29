const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const app = fs.readFileSync(
    path.resolve(__dirname, "../js/app.js"),
    "utf8"
);

const html = fs.readFileSync(
    path.resolve(__dirname, "../index.html"),
    "utf8"
);

test("personalization modal includes required variant section", () => {
    assert.match(
        html,
        /id="variant-section"/
    );

    assert.match(
        html,
        /id="variant-options"/
    );

    assert.match(
        html,
        />Tamaño</
    );

    assert.match(
        html,
        />Obligatorio</
    );
});

test("POS keeps selected product variant in state", () => {
    assert.match(
        app,
        /modifierVariant\s*:\s*null/
    );
});

test("variant product cards display Desde with display_price", () => {
    assert.match(
        app,
        /Desde\s*\$\{money\(product\.display_price\)\}/
    );
});

test("variant product opens personalization even without modifiers", () => {
    assert.match(
        app,
        /productHasVariants\(product\)/
    );

    assert.match(
        app,
        /productHasVariants\(product\)[\s\S]{0,180}product\.modifiers/
    );
});

test("variant options expose id name and resolved price", () => {
    assert.match(
        app,
        /function renderVariantOptions\(product\)/
    );

    assert.match(
        app,
        /product_variant_id/
    );

    assert.match(
        app,
        /variant\.name/
    );

    assert.match(
        app,
        /variant\.price/
    );
});

test("selected variant becomes cart base price", () => {
    assert.match(
        app,
        /function selectedVariant\(\)/
    );

    assert.match(
        app,
        /function configuredBasePrice\(product\)/
    );

    assert.match(
        app,
        /variant[\s\S]{0,120}\.price/
    );
});

test("cart preserves product variant identity", () => {
    assert.match(
        app,
        /product_variant_id\s*:/
    );

    assert.match(
        app,
        /variant_name\s*:/
    );
});

test("checkout sends product_variant_id to backend", () => {
    assert.match(
        app,
        /product_variant_id[\s\S]{0,250}item\.product_variant_id/
    );
});
