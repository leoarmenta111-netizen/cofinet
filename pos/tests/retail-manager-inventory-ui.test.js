const test =
    require("node:test");

const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");


function read(path) {
    return fs.readFileSync(
        path,
        "utf8"
    );
}


test(
    "Papeleria POS expone acceso a inventario",
    () => {
        const html =
            read(
                "pos/papeleria/index.html"
            );

        [
            'id="retail-manager-inventory-open"',
            'id="retail-manager-modal"',
            'id="retail-manager-inventory-rows"',
            "retail-manager-inventory.js",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Papeleria POS tiene formulario de movimiento",
    () => {
        const html =
            read(
                "pos/papeleria/index.html"
            );

        [
            'id="retail-manager-inventory-operation-modal"',
            'id="retail-manager-inventory-operation"',
            'value="entry"',
            'value="removal"',
            'value="adjust"',
            'id="retail-manager-inventory-quantity"',
            'id="retail-manager-inventory-note"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Movimiento exige gerente y PIN",
    () => {
        const html =
            read(
                "pos/papeleria/index.html"
            );

        const js =
            read(
                "pos/js/retail-manager-inventory.js"
            );

        [
            'id="retail-manager-inventory-manager-id"',
            'id="retail-manager-inventory-manager-pin"',
            "Autorización de gerente",
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });

        [
            "authorizing_manager_staff_id",
            "manager_pin",
            "Selecciona un gerente.",
            "Ingresa el PIN del gerente.",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Retail API conecta endpoints manager de A3",
    () => {
        const js =
            read(
                "pos/js/retail-api.js"
            );

        [
            "/retail/manager/staff",
            "/retail/manager/inventory",
            "managerInventoryEntry",
            "managerInventoryRemoval",
            "managerInventoryAdjust",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Manager inventory carga gerentes e inventario juntos",
    () => {
        const js =
            read(
                "pos/js/retail-manager-inventory.js"
            );

        [
            "Promise.all",
            "listRetailManagers",
            "listManagerInventory",
            "state.managers",
            "state.inventory",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Manager inventory soporta las tres operaciones",
    () => {
        const js =
            read(
                "pos/js/retail-manager-inventory.js"
            );

        [
            'operation === "entry"',
            'operation === "removal"',
            "managerInventoryEntry",
            "managerInventoryRemoval",
            "managerInventoryAdjust",
            "physical_quantity",
            "payload.quantity",
        ].forEach(marker => {
            assert.ok(
                js.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);


test(
    "Manager inventory no persiste PIN",
    () => {
        const js =
            read(
                "pos/js/retail-manager-inventory.js"
            );

        assert.ok(
            !/localStorage[\s\S]{0,80}manager[\s\S]{0,80}pin/i
                .test(js)
        );

        assert.ok(
            !/sessionStorage[\s\S]{0,80}manager[\s\S]{0,80}pin/i
                .test(js)
        );

        assert.ok(
            js.includes(
                '"retail-manager-inventory-manager-pin"'
            )
        );

        assert.ok(
            js.includes(
                ".value = \"\";"
            )
        );
    }
);


test(
    "Manager inventory tiene estilos dedicados",
    () => {
        const css =
            read(
                "pos/css/retail-papeleria.css"
            );

        [
            ".retail-manager-inventory-button",
            ".retail-manager-inventory-dialog",
            ".retail-manager-inventory-table",
            ".retail-manager-inventory-toolbar",
        ].forEach(marker => {
            assert.ok(
                css.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);
