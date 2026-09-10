const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync("pos/css/pos.css", "utf8");

test("rediseño no fuerza visible el estado de orden vacía", () => {
    const marker = "POS ORDER PANEL PROFESSIONAL REDESIGN";
    const start = css.indexOf(marker);

    assert.notEqual(
        start,
        -1,
        "No se encontró el bloque del rediseño"
    );

    const redesign = css.slice(start);

    assert.doesNotMatch(
        redesign,
        /\.empty-order\s*,[\s\S]{0,350}display\s*:\s*flex\s*!important/
    );
});

test("se conserva el estado vacío original del POS", () => {
    assert.match(
        css,
        /\.empty-order\s*\{[^}]*display\s*:\s*grid/s
    );
});
