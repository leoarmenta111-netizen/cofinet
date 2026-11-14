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
    "Papeleria tiene UI de presentaciones",
    () => {
        const html =
            read(
                "admin/retail.html"
            );

        [
            'id="retail-presentations-dialog"',
            'id="retail-presentation-dialog"',
            'id="retail-presentation-form"',
            'id="retail-presentation-name"',
            'id="retail-presentation-barcode"',
            'id="retail-presentation-factor"',
            'id="retail-presentation-price"',
            'id="retail-presentation-default"',
            'id="retail-presentation-active"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria soporta precio mayoreo",
    () => {
        const html =
            read(
                "admin/retail.html"
            );

        const js =
            read(
                "admin/retail-pricing.js"
            );

        [
            'id="retail-presentation-bulk-price"',
            'id="retail-presentation-bulk-min"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker)
            );
        });

        [
            "bulk_price",
            "bulk_min_quantity",
            "deben capturarse juntos",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker)
            );
        });
    }
);


test(
    "Papeleria crea y edita presentaciones",
    () => {
        const js =
            read(
                "admin/retail-pricing.js"
            );

        [
            "/presentations",
            "presentations/",
            'method: "POST"',
            'method: "PATCH"',
            "conversion_factor",
            "sale_price",
            "is_default",
            "is_active",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria tiene UI de tarifas de servicio",
    () => {
        const html =
            read(
                "admin/retail.html"
            );

        [
            'id="retail-tiers-dialog"',
            'id="retail-tier-dialog"',
            'id="retail-tier-form"',
            'id="retail-tier-min"',
            'id="retail-tier-max"',
            'id="retail-tier-price"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria permite CRUD de tarifas",
    () => {
        const js =
            read(
                "admin/retail-pricing.js"
            );

        [
            "/service-price-tiers",
            "service-price-tiers/",
            'method: "POST"',
            'method: "PATCH"',
            'method:\n                        "DELETE"',
            "min_quantity",
            "max_quantity",
            "unit_price",
            "confirmAdminAction",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Catalogo abre precios segun tipo",
    () => {
        const js =
            read(
                "admin/retail-admin.js"
            );

        [
            "CofiRetailPricingUI",
            "openProduct",
            "openService",
            '"Tarifas"',
            '"Presentaciones"',
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Pagina carga controlador de precios",
    () => {
        const html =
            read(
                "admin/retail.html"
            );

        assert.ok(
            html.includes(
                "retail-pricing.js"
            )
        );
    }
);
