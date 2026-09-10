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

const js = fs.readFileSync(
    path.join(ROOT, "js", "orders.js"),
    "utf8"
);

test("ordenes usa workspace profesional", () => {
    assert.match(html, /class="orders-toolbar"/);
    assert.match(html, /id="order-search"/);
    assert.match(html, /class="orders-table-wrap"/);
    assert.match(html, /class="orders-table-head"/);

    assert.match(css, /COFICENTER PROFESSIONAL ORDERS/);
    assert.match(css, /\.order-table-row\s*\{/);

    assert.match(js, /query:\s*""/);
    assert.match(js, /order-table-row/);
    assert.match(js, /order-search/);
});
