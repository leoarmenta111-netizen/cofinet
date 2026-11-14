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
    "Admin agrega Papeleria a navegacion",
    () => {
        const js = read(
            "admin/admin.js"
        );

        assert.ok(
            js.includes(
                '["retail", "retail.html", "Papelería"]'
            )
        );
    }
);


test(
    "Admin tiene workspace de Papeleria",
    () => {
        assert.ok(
            fs.existsSync(
                "admin/retail.html"
            )
        );

        const html = read(
            "admin/retail.html"
        );

        [
            'data-page="retail"',
            'id="retail-branch"',
            'id="retail-search"',
            'id="retail-catalog-rows"',
            'id="retail-new-item"',
            'id="retail-item-dialog"',
            'id="retail-inventory-dialog"',
            "retail-admin.js",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria admin consume catalogo e inventario retail",
    () => {
        const js = read(
            "admin/retail-admin.js"
        );

        [
            "/admin/retail/catalog",
            "/admin/retail/inventory",
            "/admin/retail/catalog/items",
            "branch_code=",
            "Promise.all",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria admin permite crear y editar articulos",
    () => {
        const html = read(
            "admin/retail.html"
        );

        const js = read(
            "admin/retail-admin.js"
        );

        [
            'id="retail-item-type"',
            'id="retail-item-name"',
            'id="retail-item-sku"',
            'id="retail-item-category"',
            'id="retail-item-unit"',
            'id="retail-item-cost"',
            'id="retail-item-tracked"',
            'id="retail-item-low-stock"',
            'id="retail-item-max-stock"',
            'id="retail-item-active"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });

        [
            'method: "POST"',
            'method: "PATCH"',
            "inventory_tracked",
            "low_stock_threshold",
            "max_stock",
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
    "Papeleria admin permite movimientos de inventario",
    () => {
        const html = read(
            "admin/retail.html"
        );

        const js = read(
            "admin/retail-admin.js"
        );

        [
            'value="entry"',
            'value="removal"',
            'value="adjust"',
            'id="retail-inventory-quantity"',
            'id="retail-inventory-note"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });

        [
            "physical_quantity",
            "idempotency_key",
            "branch_code",
            "/admin/retail/inventory/",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria admin restringe acceso a super admin",
    () => {
        const js = read(
            "admin/retail-admin.js"
        );

        assert.ok(
            js.includes(
                "allowedRoles"
            )
        );

        assert.ok(
            js.includes(
                "SUPER_ADMIN"
            )
        );
    }
);
