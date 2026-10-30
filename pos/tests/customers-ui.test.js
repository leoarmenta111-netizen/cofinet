const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");


function read(path) {
    return fs.readFileSync(
        path,
        "utf8"
    );
}


test(
    "POS habilita workspace de Clientes",
    () => {
        const html = read(
            "pos/index.html"
        );

        [
            'id="nav-customers"',
            'id="customers-view"',
            'id="customer-search"',
            'id="customer-results"',
            'id="new-customer-button"',
            'id="customer-create-form"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });

        assert.doesNotMatch(
            html,
            /<button(?=[^>]*id="nav-customers")(?=[^>]*\bdisabled\b)[^>]*>/,
            "Clientes sigue deshabilitado"
        );
    }
);


test(
    "POS muestra cliente seleccionado en venta",
    () => {
        const html = read(
            "pos/index.html"
        );

        [
            'id="sale-customer-section"',
            'id="selected-customer-card"',
            'id="selected-customer-name"',
            'id="selected-customer-phone"',
            'id="selected-customer-points"',
            'id="selected-customer-visits"',
            'id="selected-customer-spend"',
            'id="selected-customer-last-purchase"',
            'id="remove-selected-customer"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "API POS expone operaciones de Clientes",
    () => {
        const api = read(
            "pos/js/api.js"
        );

        [
            "function searchCustomers",
            "function createCustomer",
            "function getCustomer",
            '"/pos/customers"',
        ].forEach(marker => {
            assert.ok(
                api.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "venta POS conserva customer_uuid",
    () => {
        const app = read(
            "pos/js/app.js"
        );

        [
            "selectedCustomer",
            "customer_uuid",
            "showCustomers",
            "selectCustomer",
            "clearSelectedCustomer",
            "Clientes requiere conexión",
        ].forEach(marker => {
            assert.ok(
                app.includes(marker),
                `Falta ${marker}`
            );
        });

        assert.match(
            app,
            /customer_uuid\s*:\s*state\.selectedCustomer/
        );
    }
);


test(
    "POS contiene estilos propios para Clientes",
    () => {
        const css = read(
            "pos/css/pos.css"
        );

        [
            ".customers-view",
            ".customers-layout",
            ".customer-card",
            ".selected-customer-card",
            ".customer-metrics",
        ].forEach(marker => {
            assert.ok(
                css.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);
