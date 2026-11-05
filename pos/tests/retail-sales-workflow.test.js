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
    const salesFile =
        path.join(
            process.cwd(),
            "pos/js/retail-sales.js"
        );

    if (!fs.existsSync(salesFile)) {
        return null;
    }

    const context = {
        window: {},
    };

    vm.createContext(context);

    vm.runInContext(
        fs.readFileSync(
            path.join(
                process.cwd(),
                "pos/js/retail-cart.js"
            ),
            "utf8"
        ),
        context
    );

    vm.runInContext(
        fs.readFileSync(
            salesFile,
            "utf8"
        ),
        context
    );

    return {
        cart:
            context.window
                .CofiRetailCart,

        sales:
            context.window
                .CofiRetailSales,
    };
}


function populatedCart(cartApi) {
    const cart =
        cartApi.create();

    const item = {
        item_id: 10,
        presentation_id: 101,
        quantity: 1,
        unit_price: 45,
        name: "Cuaderno",
        presentation_name: "Pieza",
        discount_amount: 0,
    };

    cartApi.add(
        cart,
        item
    );

    cartApi.add(
        cart,
        item
    );

    return cart;
}


test(
    "retail sales module exists",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        assert.ok(
            modules.sales
        );
    }
);


test(
    "held sale payload contains label and server-pricable lines",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const cart =
            populatedCart(
                modules.cart
            );

        const payload =
            modules.sales
                .buildHeldPayload(
                    cart,
                    "Cliente mostrador"
                );

        assert.equal(
            payload.label,
            "Cliente mostrador"
        );

        assert.equal(
            payload.lines.length,
            1
        );

        assert.equal(
            payload.lines[0]
                .item_id,
            10
        );

        assert.equal(
            payload.lines[0]
                .presentation_id,
            101
        );

        assert.equal(
            payload.lines[0]
                .quantity,
            2
        );

        assert.equal(
            "unit_price"
            in payload.lines[0],
            false
        );

        assert.equal(
            "line_total"
            in payload.lines[0],
            false
        );
    }
);


test(
    "cash checkout payload uses server authoritative line contract",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const cart =
            populatedCart(
                modules.cart
            );

        const payload =
            modules.sales
                .buildCheckoutPayload(
                    {
                        cart,
                        saleUuid:
                            "11111111-1111-4111-8111-111111111111",
                        paymentUuid:
                            "22222222-2222-4222-8222-222222222222",
                        heldSaleUuid:
                            null,
                        paymentMethod:
                            "CASH",
                        amountTendered:
                            100,
                        externalReference:
                            null,
                    }
                );

        assert.equal(
            payload.sale_uuid,
            "11111111-1111-4111-8111-111111111111"
        );

        assert.equal(
            payload.payment_uuid,
            "22222222-2222-4222-8222-222222222222"
        );

        assert.equal(
            payload.payment_method,
            "CASH"
        );

        assert.equal(
            payload.amount_tendered,
            100
        );

        assert.equal(
            payload.external_reference,
            null
        );

        assert.equal(
            payload.sale_discount_amount,
            0
        );

        assert.equal(
            payload.lines.length,
            1
        );

        assert.equal(
            "unit_price"
            in payload.lines[0],
            false
        );

        assert.equal(
            "line_total"
            in payload.lines[0],
            false
        );
    }
);


test(
    "card checkout payload sends reference and no cash tendered",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const cart =
            populatedCart(
                modules.cart
            );

        const payload =
            modules.sales
                .buildCheckoutPayload(
                    {
                        cart,
                        saleUuid:
                            "33333333-3333-4333-8333-333333333333",
                        paymentUuid:
                            "44444444-4444-4444-8444-444444444444",
                        heldSaleUuid:
                            "55555555-5555-4555-8555-555555555555",
                        paymentMethod:
                            "CARD",
                        amountTendered:
                            999,
                        externalReference:
                            "TERM-ABC-123",
                    }
                );

        assert.equal(
            payload.payment_method,
            "CARD"
        );

        assert.equal(
            payload.amount_tendered,
            null
        );

        assert.equal(
            payload.external_reference,
            "TERM-ABC-123"
        );

        assert.equal(
            payload.held_sale_uuid,
            "55555555-5555-4555-8555-555555555555"
        );
    }
);


test(
    "checkout payload rejects unsupported payment method",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const cart =
            populatedCart(
                modules.cart
            );

        assert.throws(
            () =>
                modules.sales
                    .buildCheckoutPayload(
                        {
                            cart,
                            saleUuid:
                                "11111111-1111-4111-8111-111111111111",
                            paymentUuid:
                                "22222222-2222-4222-8222-222222222222",
                            heldSaleUuid:
                                null,
                            paymentMethod:
                                "TRANSFER",
                            amountTendered:
                                100,
                            externalReference:
                                null,
                        }
                    ),
            /payment/i
        );
    }
);


test(
    "server total comes from checkout response not local cart estimate",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const sale = {
            total: "82.50",
        };

        assert.equal(
            modules.sales
                .serverTotal(
                    sale
                ),
            82.5
        );
    }
);


test(
    "cash payment summary uses server change due",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const sale = {
            total: "82.50",
            payments: [
                {
                    method: "CASH",
                    amount: "82.50",
                    amount_tendered:
                        "100.00",
                    change_due:
                        "17.50",
                    external_reference:
                        null,
                },
            ],
        };

        const summary =
            modules.sales
                .paymentSummary(
                    sale
                );

        assert.equal(
            summary.method,
            "CASH"
        );

        assert.equal(
            summary.total,
            82.5
        );

        assert.equal(
            summary.amountTendered,
            100
        );

        assert.equal(
            summary.changeDue,
            17.5
        );
    }
);


test(
    "card payment summary preserves terminal reference",
    () => {
        const modules =
            loadModules();

        assert.ok(modules);

        const sale = {
            total: "125.00",
            payments: [
                {
                    method: "CARD",
                    amount: "125.00",
                    amount_tendered:
                        null,
                    change_due:
                        "0.00",
                    external_reference:
                        "AUTH-8899",
                },
            ],
        };

        const summary =
            modules.sales
                .paymentSummary(
                    sale
                );

        assert.equal(
            summary.method,
            "CARD"
        );

        assert.equal(
            summary.externalReference,
            "AUTH-8899"
        );
    }
);
