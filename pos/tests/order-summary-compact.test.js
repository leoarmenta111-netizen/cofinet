const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync("pos/css/pos.css", "utf8");

test("lista de productos conserva todo el espacio disponible", () => {
    assert.match(
        css,
        /ORDER SUMMARY COMPACT REDESIGN[\s\S]*?\.cart-items\s*\{[\s\S]*?flex\s*:\s*1\s*!important/
    );
});

test("resumen de cobro es compacto", () => {
    assert.match(
        css,
        /ORDER SUMMARY COMPACT REDESIGN[\s\S]*?\.order-summary\s*\{[\s\S]*?padding\s*:\s*8px 16px 8px\s*!important/
    );
});

test("total usa tamaño más compacto", () => {
    assert.match(
        css,
        /ORDER SUMMARY COMPACT REDESIGN[\s\S]*?\.order-total strong\s*\{[\s\S]*?font-size\s*:\s*22px\s*!important/
    );
});

test("boton cobrar usa altura compacta", () => {
    assert.match(
        css,
        /ORDER SUMMARY COMPACT REDESIGN[\s\S]*?\.checkout-button\s*\{[\s\S]*?min-height\s*:\s*44px\s*!important/
    );
});
