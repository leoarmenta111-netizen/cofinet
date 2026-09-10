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
    "Admin agrega Clientes a navegacion",
    () => {
        const js = read(
            "admin/admin.js"
        );

        assert.ok(
            js.includes(
                '["customers", "customers.html", "Clientes"]'
            ),
            "Falta Clientes en navegación Admin"
        );
    }
);


test(
    "Admin tiene workspace CRM de Clientes",
    () => {
        assert.ok(
            fs.existsSync(
                "admin/customers.html"
            ),
            "Falta admin/customers.html"
        );

        if (
            !fs.existsSync(
                "admin/customers.html"
            )
        ) {
            return;
        }

        const html = read(
            "admin/customers.html"
        );

        [
            'data-page="customers"',
            'id="customer-search"',
            'id="customers-list"',
            'id="customer-profile"',
            'id="customer-edit-form"',
            'id="customer-orders"',
            'id="customer-loyalty-history"',
            'id="loyalty-adjustment-form"',
            "/admin/pos/customers",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Admin CRM muestra metricas de cliente",
    () => {
        if (
            !fs.existsSync(
                "admin/customers.html"
            )
        ) {
            assert.fail(
                "Falta admin/customers.html"
            );
        }

        const html = read(
            "admin/customers.html"
        );

        [
            "Puntos",
            "Visitas",
            "Gasto total",
            "Última compra",
            "Última actividad",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Admin contiene estilos CRM",
    () => {
        const css = read(
            "admin/admin.css"
        );

        [
            ".customers-crm",
            ".customers-list",
            ".customer-profile",
            ".customer-metrics-grid",
        ].forEach(marker => {
            assert.ok(
                css.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);
