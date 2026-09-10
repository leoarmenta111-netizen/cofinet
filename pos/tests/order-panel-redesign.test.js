const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync("pos/css/pos.css", "utf8");

test("orden actual usa layout profesional con carrito flexible", () => {
    assert.match(
        css,
        /POS ORDER PANEL PROFESSIONAL REDESIGN/
    );

    assert.match(
        css,
        /\.order-panel\s*\{[^}]*display\s*:\s*flex/s
    );

    assert.match(
        css,
        /\.order-panel\s*\{[^}]*flex-direction\s*:\s*column/s
    );
});

test("lista de productos ocupa el espacio disponible y tiene scroll", () => {
    assert.match(
        css,
        /\.order-items[\s\S]*?overflow-y\s*:\s*auto/
    );
});

test("cliente seleccionado se muestra compacto", () => {
    assert.match(
        css,
        /#sale-customer-section[\s\S]*?flex-shrink\s*:\s*0/
    );
});

test("zona de cobro permanece visible abajo", () => {
    assert.match(
        css,
        /\.order-footer[\s\S]*?flex-shrink\s*:\s*0/
    );
});
