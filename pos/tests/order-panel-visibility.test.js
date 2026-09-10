const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync("pos/css/pos.css", "utf8");

test("Clientes conserva oculto el panel de Orden actual", () => {
    assert.match(
        css,
        /\.workspace\.customers-mode\s+\.order-panel\s*\{[^}]*display\s*:\s*none/s
    );
});

test("rediseño no fuerza visible Orden actual en todos los módulos", () => {
    const marker = "POS ORDER PANEL PROFESSIONAL REDESIGN";
    const start = css.indexOf(marker);

    assert.notEqual(start, -1);

    const redesign = css.slice(start);

    assert.doesNotMatch(
        redesign,
        /\.order-panel\s*\{[^}]*display\s*:\s*flex\s*!important/s
    );
});
