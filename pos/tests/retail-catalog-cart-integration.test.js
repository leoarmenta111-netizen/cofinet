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


function loadModules() {
    const catalogFile =
        path.join(
            process.cwd(),
            "pos/js/retail-catalog.js"
        );

    const cartFile =
        path.join(
            process.cwd(),
            "pos/js/retail-cart.js"
        );

    if (
        !fs.existsSync(catalogFile)
    ) {
        return null;
    }

    const context = {
        window: {},
    };

    vm.createContext(context);

    vm.runInContext(
        fs.readFileSync(
            cartFile,
            "utf8"
        ),
        context
    );

    vm.runInContext(
        fs.readFileSync(
            catalogFile,
            "utf8"
        ),
        context
    );

    return {
        catalog:
            context.window
                .CofiRetailCatalog,
        cart:
            context.window
                .CofiRetailCart,
    };
}


test(
    "catalog selection produces a cart line while checkout strips client prices",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const item = {
            id: 88,
            item_type: "PRODUCT",
            sku: "TEST-88",
            name: "Producto prueba",
            presentations: [
                {
                    id: 880,
                    name: "Pieza",
                    barcode:
                        "750000000088",
                    sale_price:
                        "25.00",
                    bulk_price:
                        null,
                    bulk_min_quantity:
                        null,
                    is_default: true,
                    is_active: true,
                },
            ],
            service_price_tiers: [],
        };

        const selection =
            modules.catalog
                .selectionFor(item);

        const state =
            modules.cart.create();

        modules.cart.add(
            state,
            {
                item_id: item.id,
                presentation_id:
                    selection
                        .presentation
                        .id,
                quantity: 1,
                unit_price:
                    modules.catalog
                        .estimateUnitPrice(
                            item,
                            selection
                                .presentation,
                            1
                        ),
                name:
                    item.name,
                presentation_name:
                    selection
                        .presentation
                        .name,
                discount_amount: 0,
            }
        );

        const payload =
            modules.cart
                .checkoutLines(
                    state
                );

        assert.equal(
            payload.length,
            1
        );

        assert.deepEqual(
            Object.keys(
                payload[0]
            ).sort(),
            [
                "discount_amount",
                "item_id",
                "presentation_id",
                "quantity",
            ]
        );

        assert.equal(
            "unit_price"
            in payload[0],
            false
        );

        assert.equal(
            "line_total"
            in payload[0],
            false
        );
    }
);
