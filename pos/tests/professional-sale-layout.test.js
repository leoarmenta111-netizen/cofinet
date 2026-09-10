const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

const html = fs.readFileSync(
    path.join(ROOT, "index.html"),
    "utf8"
);

const css = fs.readFileSync(
    path.join(ROOT, "css", "pos.css"),
    "utf8"
);

test("sale view uses professional CofiCenter layout", () => {
    assert.match(
        html,
        /data-ui="coficenter-pos-professional"/,
        "Professional POS marker is missing"
    );

    assert.match(
        html,
        /class="catalog-title"/,
        "Professional menu heading is missing"
    );

    assert.match(
        html,
        /class="catalog-actions"/,
        "Catalog actions toolbar is missing"
    );

    assert.match(
        html,
        /class="scan-action"/,
        "Scan action is missing"
    );

    assert.match(
        html,
        /class="filter-action"/,
        "Filter action is missing"
    );

    assert.match(
        css,
        /COFICENTER POS PROFESSIONAL/,
        "Professional POS stylesheet section is missing"
    );

    assert.match(
        css,
        /\.sale-view\s*\{/,
        "Sale view styling is missing"
    );

    assert.match(
        css,
        /\.catalog-actions\s*\{/,
        "Professional toolbar styling is missing"
    );
});
