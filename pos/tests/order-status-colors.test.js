const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

const js = fs.readFileSync(
    path.join(ROOT, "js", "orders.js"),
    "utf8"
);

const css = fs.readFileSync(
    path.join(ROOT, "css", "pos.css"),
    "utf8"
);

test("filas de orden usan acento segun estado", () => {
    assert.match(
        js,
        /status-accent-/
    );

    assert.match(
        css,
        /ORDER STATUS ROW COLORS/
    );

    assert.match(
        css,
        /\.status-accent-new/
    );

    assert.match(
        css,
        /\.status-accent-preparing/
    );

    assert.match(
        css,
        /\.status-accent-ready/
    );

    assert.match(
        css,
        /\.status-accent-delivered/
    );
});

test("filtros activos usan color de su estado", () => {
    assert.match(
        css,
        /data-order-filter="NEW"/
    );

    assert.match(
        css,
        /data-order-filter="PREPARING"/
    );

    assert.match(
        css,
        /data-order-filter="READY"/
    );

    assert.match(
        css,
        /data-order-filter="DELIVERED"/
    );
});
