const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


function loadCart() {
    const target = path.join(
        process.cwd(),
        "customer-order/js/cart.js"
    );

    assert.equal(
        fs.existsSync(target),
        true,
        "falta customer-order/js/cart.js"
    );

    delete require.cache[
        require.resolve(target)
    ];

    return require(target);
}


function productFixture() {
    return {
        id: 7,
        name: "Latte",
        price: "57.00",
        modifiers: [
            {
                id: 10,
                name: "Tamaño",
                required: true,
                min_select: 1,
                max_select: 1,
                options: [
                    {
                        id: 101,
                        name: "Regular",
                        price_delta: "0.00",
                    },
                    {
                        id: 102,
                        name: "Grande",
                        price_delta: "8.00",
                    },
                ],
            },
            {
                id: 20,
                name: "Leche",
                required: false,
                min_select: 0,
                max_select: 1,
                options: [
                    {
                        id: 201,
                        name: "Avena",
                        price_delta: "12.00",
                    },
                ],
            },
        ],
    };
}


test(
    "valida grupos requeridos de modificadores",
    () => {
        const cart = loadCart();
        const product = productFixture();

        const missing =
            cart.validateModifiers(
                product,
                []
            );

        assert.equal(
            missing.valid,
            false
        );

        const valid =
            cart.validateModifiers(
                product,
                [102]
            );

        assert.equal(
            valid.valid,
            true
        );
    }
);


test(
    "rechaza mas opciones que max_select",
    () => {
        const cart = loadCart();
        const product = productFixture();

        const result =
            cart.validateModifiers(
                product,
                [101, 102]
            );

        assert.equal(
            result.valid,
            false
        );
    }
);


test(
    "crea linea congelando nombre precio y modificadores",
    () => {
        const cart = loadCart();
        const product = productFixture();

        const line = cart.makeLine({
            product,
            selectedOptionIds: [
                102,
                201,
            ],
            quantity: 2,
            lineUuid: "line-1",
        });

        assert.equal(
            line.line_uuid,
            "line-1"
        );

        assert.equal(
            line.product_id,
            7
        );

        assert.equal(
            line.product_name,
            "Latte"
        );

        assert.equal(
            line.quantity,
            2
        );

        assert.equal(
            line.unit_price,
            77
        );

        assert.equal(
            line.line_total,
            154
        );

        assert.deepEqual(
            line.modifiers.map(
                item => item.option_id
            ),
            [102, 201]
        );
    }
);


test(
    "totales del carrito cuentan unidades y dinero",
    () => {
        const cart = loadCart();
        const product = productFixture();

        const first = cart.makeLine({
            product,
            selectedOptionIds: [101],
            quantity: 1,
            lineUuid: "line-1",
        });

        const second = cart.makeLine({
            product,
            selectedOptionIds: [
                102,
                201,
            ],
            quantity: 2,
            lineUuid: "line-2",
        });

        assert.equal(
            cart.cartCount([
                first,
                second,
            ]),
            3
        );

        assert.equal(
            cart.cartTotal([
                first,
                second,
            ]),
            211
        );
    }
);


test(
    "payload self-order usa ids y no confia en precios del navegador",
    () => {
        const cart = loadCart();
        const product = productFixture();

        const line = cart.makeLine({
            product,
            selectedOptionIds: [
                102,
                201,
            ],
            quantity: 2,
            lineUuid: "line-1",
        });

        const payload =
            cart.toSelfOrderItems(
                [line]
            );

        assert.deepEqual(
            payload,
            [
                {
                    product_id: 7,
                    quantity: 2,
                    modifier_option_ids: [
                        102,
                        201,
                    ],
                    notes: null,
                },
            ]
        );

        assert.equal(
            Object.hasOwn(
                payload[0],
                "unit_price"
            ),
            false
        );
    }
);
