const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync(
    "pos/css/pos.css",
    "utf8"
);

test(
    "cobro movil se muestra por encima de Ver orden",
    () => {
        const marker =
            "COFICENTER MOBILE PAYMENT OVER ORDER V1";

        const start = css.indexOf(marker);

        assert.notEqual(
            start,
            -1,
            "falta bloque CSS mobile payment over order"
        );

        const source = css.slice(start);

        assert.match(
            source,
            /@media\s*\(max-width:\s*620px\)/
        );

        assert.match(
            source,
            /#payment-modal\s*\{[^}]*z-index\s*:\s*(?:1[5-9]\d|[2-9]\d{2,})/s
        );
    }
);

test(
    "modal de pago conserva su flujo existente",
    () => {
        const html = fs.readFileSync(
            "pos/index.html",
            "utf8"
        );

        assert.match(
            html,
            /id="payment-modal"/
        );

        assert.match(
            html,
            /id="payment-close"/
        );

        assert.match(
            html,
            /id="confirm-payment"/
        );
    }
);
