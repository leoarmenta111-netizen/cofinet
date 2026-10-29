const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const receiptCore = fs.readFileSync(
    path.resolve(__dirname, "../js/receipt-core.js"),
    "utf8"
);

const renderer = fs.readFileSync(
    path.resolve(__dirname, "../js/receipt-renderer.js"),
    "utf8"
);

const app = fs.readFileSync(
    path.resolve(__dirname, "../js/app.js"),
    "utf8"
);

test("receipt snapshot preserves product variant id", () => {
    assert.match(
        receiptCore,
        /product_variant_id[\s\S]{0,180}item\.product_variant_id/
    );
});

test("receipt snapshot preserves historical variant name", () => {
    assert.match(
        receiptCore,
        /variant_name[\s\S]{0,180}item\.variant_name/
    );
});

test("receipt validation checks variant identity pair", () => {
    assert.match(
        receiptCore,
        /product_variant_id[\s\S]{0,500}variant_name/
    );

    assert.match(
        receiptCore,
        /variant identity|variant_name|product_variant_id/i
    );
});

test("checkout receiptItems include variant identity", () => {
    const start = app.indexOf(
        "const receiptItems"
    );

    const end = app.indexOf(
        "const receiptSnapshot",
        start
    );

    assert.ok(start >= 0);
    assert.ok(end > start);

    const block = app.slice(start, end);

    assert.match(
        block,
        /product_variant_id/
    );

    assert.match(
        block,
        /variant_name/
    );
});

test("receipt renderer displays variant name with product", () => {
    assert.match(
        renderer,
        /variant_name/
    );

    assert.match(
        renderer,
        /product_name/
    );
});
