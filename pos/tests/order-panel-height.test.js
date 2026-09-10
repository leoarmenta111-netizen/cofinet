const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync("pos/css/pos.css", "utf8");

test("orden no usa altura basada en viewport que desborda workspace", () => {
    const marker = "ORDER SUMMARY COMPACT REDESIGN";
    const start = css.indexOf(marker);

    assert.notEqual(start, -1);

    const section = css.slice(start);

    assert.doesNotMatch(
        section,
        /height\s*:\s*calc\(100dvh\s*-\s*118px\)/
    );
});

test("orden respeta la altura disponible de su contenedor", () => {
    const marker = "ORDER SUMMARY COMPACT REDESIGN";
    const start = css.indexOf(marker);

    assert.notEqual(start, -1);

    const section = css.slice(start);

    assert.match(
        section,
        /\.order-panel\s*\{[\s\S]*?height\s*:\s*100%\s*!important[\s\S]*?max-height\s*:\s*100%\s*!important/
    );
});
