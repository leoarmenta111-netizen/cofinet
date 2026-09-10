const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync("pos/css/pos.css", "utf8");

test("cliente seleccionado usa diseño compacto", () => {
    assert.match(
        css,
        /FINAL ORDER PANEL STABILIZATION[\s\S]*?#selected-customer-card\s*\{[\s\S]*?padding\s*:\s*8px 10px\s*!important/
    );

    assert.match(
        css,
        /FINAL ORDER PANEL STABILIZATION[\s\S]*?\.customer-avatar\s*\{[\s\S]*?width\s*:\s*32px\s*!important/
    );
});

test("resumen de pago permanece visible con carrito vacío", () => {
    assert.match(
        css,
        /FINAL ORDER PANEL STABILIZATION[\s\S]*?\.order-summary\[hidden\]\s*\{[\s\S]*?display\s*:\s*block\s*!important/
    );
});

test("estado vacío puede reducirse sin empujar el cobro", () => {
    assert.match(
        css,
        /FINAL ORDER PANEL STABILIZATION[\s\S]*?\.empty-order\s*\{[\s\S]*?min-height\s*:\s*0\s*!important/
    );
});
