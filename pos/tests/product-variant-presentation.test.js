const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const station = fs.readFileSync(
    "pos/js/station.js",
    "utf8"
);

const orders = fs.readFileSync(
    "pos/js/orders.js",
    "utf8"
);

const localOrders = fs.readFileSync(
    "pos/js/orders-local.js",
    "utf8"
);

const adminSales = fs.readFileSync(
    "admin/sales.html",
    "utf8"
);

test("KDS muestra nombre de variante junto al producto", () => {
    assert.match(station, /item\.variant_name/);
    assert.match(station, /·/);
});

test("pantalla de órdenes muestra nombre de variante", () => {
    assert.match(orders, /item\.variant_name/);
    assert.match(orders, /·/);
});

test("órdenes locales preservan product_variant_id", () => {
    assert.match(
        localOrders,
        /product_variant_id/
    );
});

test("órdenes locales preservan variant_name", () => {
    assert.match(
        localOrders,
        /variant_name/
    );
});

test("Admin Ventas muestra la variante seleccionada", () => {
    assert.match(
        adminSales,
        /item\.variant_name/
    );

    assert.match(
        adminSales,
        /·/
    );
});
