const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const css = fs.readFileSync(
    path.join(
        __dirname,
        "../css/pos.css"
    ),
    "utf8"
);

test(
    "panel de nuevo cliente permite scroll vertical",
    () => {
        assert.match(
            css,
            /\.customer-create-panel\s*\{[^}]*max-height\s*:/s
        );

        assert.match(
            css,
            /\.customer-create-panel\s*\{[^}]*overflow-y\s*:\s*auto/s
        );
    }
);

test(
    "boton Guardar y seleccionar permanece visible",
    () => {
        assert.match(
            css,
            /\.customer-save-button\s*\{[^}]*position\s*:\s*sticky/s
        );

        assert.match(
            css,
            /\.customer-save-button\s*\{[^}]*bottom\s*:\s*0/s
        );
    }
);
