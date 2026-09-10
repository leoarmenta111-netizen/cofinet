const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const app = fs.readFileSync(
    path.resolve(__dirname, "../js/app.js"),
    "utf8"
);

test("pago rapido reutiliza el flujo existente de cobro", () => {
    assert.match(app, /function openQuickPayment\s*\(/);
    assert.match(app, /openPayment\(\)/);
    assert.match(app, /setPaymentMethod\(method\)/);
    assert.match(app, /data-quick-payment/);
    assert.match(app, /payment-more/);
});

test("estado de accesos rapidos sigue al carrito", () => {
    assert.match(app, /function syncPaymentShortcuts\s*\(/);
    assert.match(app, /syncPaymentShortcuts\(\)/);
});
