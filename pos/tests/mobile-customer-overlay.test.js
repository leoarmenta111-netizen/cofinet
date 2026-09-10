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
    "Clientes incluye cierre dedicado para overlay movil",
    () => {
        assert.match(
            html,
            /id="mobile-customer-close"/
        );
    }
);


test(
    "app define overlay movil de clientes",
    () => {
        assert.match(
            js,
            /MOBILE CUSTOMER OVERLAY V1/
        );

        assert.match(
            js,
            /function openMobileCustomerOverlay/
        );

        assert.match(
            js,
            /function closeMobileCustomerOverlay/
        );
    }
);


test(
    "Buscar cambiar usa flujo especial desde la orden movil",
    () => {
        assert.match(
            js,
            /function openCustomersFromSale/
        );

        assert.match(
            js,
            /mobile-order-open/
        );

        assert.match(
            js,
            /matchMedia/
        );

        assert.match(
            js,
            /\$\("#open-customers-from-sale"\)[\s\S]*?openCustomersFromSale/
        );
    }
);


test(
    "seleccionar cliente cierra overlay y regresa a la orden",
    () => {
        assert.match(
            js,
            /function selectCustomer[\s\S]*?closeMobileCustomerOverlay/
        );

        assert.match(
            js,
            /mobile-customer-overlay-open/
        );
    }
);


test(
    "boton cerrar clientes cierra solamente el overlay",
    () => {
        assert.match(
            js,
            /\$\("#mobile-customer-close"\)[\s\S]*?closeMobileCustomerOverlay/
        );
    }
);


test(
    "CSS muestra Clientes por encima del drawer en telefonos",
    () => {
        const marker =
            "COFICENTER MOBILE CUSTOMER OVERLAY V1";

        const start = css.indexOf(marker);

        assert.notEqual(
            start,
            -1,
            "falta bloque CSS mobile customer overlay"
        );

        const source = css.slice(start);

        assert.match(
            source,
            /@media\s*\(max-width:\s*620px\)/
        );

        assert.match(
            source,
            /\.workspace\.mobile-customer-overlay-open[\s\S]*?#customers-view/
        );

        assert.match(
            source,
            /position:\s*fixed/
        );

        assert.match(
            source,
            /z-index:\s*(?:1[3-9]\d|[2-9]\d{2,})/
        );

        assert.match(
            source,
            /\.mobile-customer-close/
        );
    }
);
