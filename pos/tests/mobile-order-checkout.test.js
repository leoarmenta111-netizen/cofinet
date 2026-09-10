const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");

const html = fs.readFileSync(
    path.join(root, "index.html"),
    "utf8"
);

const js = fs.readFileSync(
    path.join(root, "js", "app.js"),
    "utf8"
);

const css = fs.readFileSync(
    path.join(root, "css", "pos.css"),
    "utf8"
);


test(
    "venta movil incluye barra fija de orden y cobro",
    () => {
        assert.match(
            html,
            /id="mobile-order-bar"/
        );

        assert.match(
            html,
            /id="mobile-order-view"/
        );

        assert.match(
            html,
            /id="mobile-order-checkout"/
        );

        assert.match(
            html,
            /id="mobile-order-count"/
        );

        assert.match(
            html,
            /id="mobile-order-total"/
        );
    }
);


test(
    "panel de orden tiene cierre dedicado para movil",
    () => {
        assert.match(
            html,
            /id="mobile-order-close"/
        );
    }
);


test(
    "renderCart sincroniza barra movil con carrito",
    () => {
        assert.match(
            js,
            /MOBILE ORDER ACTIONS V1/
        );

        assert.match(
            js,
            /mobile-order-count/
        );

        assert.match(
            js,
            /mobile-order-total/
        );

        assert.match(
            js,
            /mobile-order-checkout/
        );
    }
);


test(
    "cobrar movil reutiliza openPayment",
    () => {
        assert.match(
            js,
            /\$\("#mobile-order-checkout"\)[\s\S]*?openPayment/
        );
    }
);


test(
    "ver orden abre el order panel como bottom sheet",
    () => {
        assert.match(
            js,
            /function openMobileOrderDrawer/
        );

        assert.match(
            js,
            /function closeMobileOrderDrawer/
        );

        assert.match(
            js,
            /\$\("#mobile-order-view"\)[\s\S]*?openMobileOrderDrawer/
        );

        assert.match(
            js,
            /\$\("#mobile-order-close"\)[\s\S]*?closeMobileOrderDrawer/
        );
    }
);


test(
    "CSS movil mantiene cobrar visible encima de navegacion",
    () => {
        const marker =
            "COFICENTER MOBILE ORDER CHECKOUT V1";

        const start = css.indexOf(marker);

        assert.notEqual(
            start,
            -1,
            "falta bloque CSS de checkout movil"
        );

        const source = css.slice(start);

        assert.match(
            source,
            /@media\s*\(max-width:\s*620px\)/
        );

        assert.match(
            source,
            /\.mobile-order-bar[\s\S]*?position:\s*fixed/
        );

        assert.match(
            source,
            /\.workspace\.mobile-order-open[\s\S]*?\.order-panel/
        );

        assert.match(
            source,
            /\.order-panel[\s\S]*?position:\s*fixed/
        );
    }
);
