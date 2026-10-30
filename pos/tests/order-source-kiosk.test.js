const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const js = fs.readFileSync("pos/js/orders.js", "utf8");
const css = fs.readFileSync("pos/css/pos.css", "utf8");
const html = fs.readFileSync("pos/index.html", "utf8");

test("ordenes identifica pedidos de kiosk sin separarlos del listado POS", () => {
    assert.match(js, /function\s+orderSource\s*\(/);
    assert.match(js, /terminal\.startsWith\("KIOSK-"\)/);
    assert.match(js, /KIOSK:\s*"Kiosk"/);
    assert.match(js, /sourceLabel\(source\)/);
    assert.match(js, /Autoservicio/);
});

test("origen kiosk se muestra en lista y detalle de orden", () => {
    assert.match(js, /order-source-badge/);
    assert.match(js, /order-detail-source/);
    assert.match(css, /ORDER SOURCE BADGES/);
    assert.match(css, /\.order-source-badge\.source-kiosk/);
    assert.match(css, /\.order-detail-source\.source-kiosk/);
});

test("cache bust de orders carga la version con origen de kiosk", () => {
    assert.match(html, /\.\/js\/orders\.js\?v=17/);
});
