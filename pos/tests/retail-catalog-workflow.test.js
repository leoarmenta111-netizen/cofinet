const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");

const path =
    require("node:path");

const test =
    require("node:test");

const vm =
    require("node:vm");


const catalog = [
    {
        id: 10,
        branch_id: 1,
        item_type: "PRODUCT",
        sku: "CUAD-A5",
        name: "Cuaderno Profesional",
        description: "Cuaderno de 100 hojas",
        category: "Cuadernos",
        base_unit_code: "EA",
        cost: "20.00",
        inventory_tracked: true,
        is_active: true,
        presentations: [
            {
                id: 101,
                item_id: 10,
                branch_id: 1,
                name: "Pieza",
                barcode: "750100000001",
                conversion_factor: "1.000",
                sale_price: "45.00",
                bulk_price: "40.00",
                bulk_min_quantity: "6.000",
                is_default: true,
                is_active: true,
            },
            {
                id: 102,
                item_id: 10,
                branch_id: 1,
                name: "Paquete 6",
                barcode: "750100000006",
                conversion_factor: "6.000",
                sale_price: "240.00",
                bulk_price: null,
                bulk_min_quantity: null,
                is_default: false,
                is_active: true,
            },
        ],
        service_price_tiers: [],
    },
    {
        id: 20,
        branch_id: 1,
        item_type: "PRODUCT",
        sku: "PLUMA-AZ",
        name: "Pluma Azul",
        description: null,
        category: "Escritura",
        base_unit_code: "EA",
        cost: "3.00",
        inventory_tracked: true,
        is_active: true,
        presentations: [
            {
                id: 201,
                item_id: 20,
                branch_id: 1,
                name: "Pieza",
                barcode: "750200000001",
                conversion_factor: "1.000",
                sale_price: "8.00",
                bulk_price: null,
                bulk_min_quantity: null,
                is_default: true,
                is_active: true,
            },
        ],
        service_price_tiers: [],
    },
    {
        id: 30,
        branch_id: 1,
        item_type: "SERVICE",
        sku: "COP-BN",
        name: "Copia B/N",
        description: "Copia blanco y negro",
        category: "Copias",
        base_unit_code: "EA",
        cost: "0.00",
        inventory_tracked: false,
        is_active: true,
        presentations: [],
        service_price_tiers: [
            {
                id: 301,
                item_id: 30,
                min_quantity: "1.000",
                max_quantity: "49.000",
                unit_price: "2.00",
            },
            {
                id: 302,
                item_id: 30,
                min_quantity: "50.000",
                max_quantity: null,
                unit_price: "1.50",
            },
        ],
    },
];


function loadCatalogModule() {
    const filename = path.join(
        process.cwd(),
        "pos/js/retail-catalog.js"
    );

    if (!fs.existsSync(filename)) {
        return null;
    }

    const context = {
        window: {},
    };

    vm.createContext(context);

    vm.runInContext(
        fs.readFileSync(
            filename,
            "utf8"
        ),
        context
    );

    return (
        context.window
            .CofiRetailCatalog
        || null
    );
}


test(
    "catalog module exists",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(
            api,
            "CofiRetailCatalog must exist"
        );
    }
);


test(
    "search finds item by name ignoring case",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const result =
            api.search(
                catalog,
                "cuaderno"
            );

        assert.deepEqual(
            Array.from(
                result,
                item => item.id
            ),
            [10]
        );
    }
);


test(
    "search finds item by exact or partial SKU",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const exact =
            api.search(
                catalog,
                "CUAD-A5"
            );

        const partial =
            api.search(
                catalog,
                "pluma"
            );

        assert.deepEqual(
            Array.from(
                exact,
                item => item.id
            ),
            [10]
        );

        assert.deepEqual(
            Array.from(
                partial,
                item => item.id
            ),
            [20]
        );
    }
);


test(
    "barcode lookup returns exact presentation",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const result =
            api.findBarcode(
                catalog,
                "750100000006"
            );

        assert.equal(
            result.item.id,
            10
        );

        assert.equal(
            result.presentation.id,
            102
        );
    }
);


test(
    "barcode lookup trims scanner input but rejects partial barcode",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const exact =
            api.findBarcode(
                catalog,
                " 750200000001\n"
            );

        const partial =
            api.findBarcode(
                catalog,
                "750200"
            );

        assert.equal(
            exact.item.id,
            20
        );

        assert.equal(
            exact.presentation.id,
            201
        );

        assert.equal(
            partial,
            null
        );
    }
);


test(
    "single-presentation product can be added immediately",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const decision =
            api.selectionFor(
                catalog[1]
            );

        assert.equal(
            decision.action,
            "ADD"
        );

        assert.equal(
            decision.presentation.id,
            201
        );
    }
);


test(
    "multi-presentation product requires presentation choice",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const decision =
            api.selectionFor(
                catalog[0]
            );

        assert.equal(
            decision.action,
            "CHOOSE_PRESENTATION"
        );

        assert.deepEqual(
            Array.from(
                decision.presentations,
                presentation =>
                    presentation.id
            ),
            [101, 102]
        );
    }
);


test(
    "service adds without presentation",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const decision =
            api.selectionFor(
                catalog[2]
            );

        assert.equal(
            decision.action,
            "ADD"
        );

        assert.equal(
            decision.presentation,
            null
        );
    }
);


test(
    "product estimated price uses normal price below bulk threshold",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        assert.equal(
            api.estimateUnitPrice(
                catalog[0],
                catalog[0]
                    .presentations[0],
                5
            ),
            45
        );
    }
);


test(
    "product estimated price uses bulk price at threshold",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        assert.equal(
            api.estimateUnitPrice(
                catalog[0],
                catalog[0]
                    .presentations[0],
                6
            ),
            40
        );
    }
);


test(
    "service estimated price resolves matching quantity tier",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        assert.equal(
            api.estimateUnitPrice(
                catalog[2],
                null,
                1
            ),
            2
        );

        assert.equal(
            api.estimateUnitPrice(
                catalog[2],
                null,
                50
            ),
            1.5
        );
    }
);


test(
    "inactive presentations are never offered or barcode matched",
    () => {
        const api =
            loadCatalogModule();

        assert.ok(api);

        const item =
            structuredClone(
                catalog[0]
            );

        item.presentations[1]
            .is_active = false;

        const decision =
            api.selectionFor(item);

        assert.equal(
            decision.action,
            "ADD"
        );

        assert.equal(
            decision.presentation.id,
            101
        );

        assert.equal(
            api.findBarcode(
                [item],
                "750100000006"
            ),
            null
        );
    }
);
