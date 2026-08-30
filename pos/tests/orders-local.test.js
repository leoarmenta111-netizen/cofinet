const test = require("node:test");
const assert = require("node:assert/strict");

const {
    buildLocalOrder,
    mergeOrders,
    pendingLocalOrders,
} = require("../js/orders-local.js");


const catalog = {
    categories: [
        {
            id: 1,
            name: "Café",
            products: [
                {
                    id: 10,
                    name: "Latte",
                    price: 75,
                    modifiers: [
                        {
                            id: 5,
                            name: "Leche",
                            options: [
                                {
                                    id: 51,
                                    name: "Avena",
                                    price_delta: 10,
                                },
                            ],
                        },
                    ],
                },
                {
                    id: 11,
                    name: "Americano",
                    price: 55,
                    modifiers: [],
                },
            ],
        },
    ],
};


test(
    "convierte una venta offline en una orden visible",
    () => {
        const local = {
            order_uuid:
                "a72f19c3-1111-2222-3333-444444444444",

            local_total: 160,

            sync_status:
                "PENDING_SYNC",

            created_at:
                "2026-08-27T20:00:00.000Z",

            payload: {
                order_uuid:
                    "a72f19c3-1111-2222-3333-444444444444",

                branch_code:
                    "nuevo-vallarta",

                created_at_client:
                    "2026-08-27T20:00:00.000Z",

                items: [
                    {
                        product_id: 10,
                        quantity: 2,
                        modifier_option_ids: [],
                    },
                    {
                        product_id: 11,
                        quantity: 1,
                        modifier_option_ids: [],
                    },
                ],

                payment: {
                    method: "CASH",
                    amount_tendered: 200,
                },
            },
        };


        const order =
            buildLocalOrder(
                local,
                catalog
            );


        assert.equal(
            order.order_uuid,
            local.order_uuid
        );

        assert.equal(
            order.folio,
            "LOCAL-A72F19C3"
        );

        assert.equal(
            order.status,
            "NEW"
        );

        assert.equal(
            order.is_local,
            true
        );

        assert.equal(
            order.sync_status,
            "PENDING_SYNC"
        );

        assert.equal(
            order.total,
            160
        );

        assert.equal(
            order.items[0].product_name,
            "Latte"
        );

        assert.equal(
            order.items[1].product_name,
            "Americano"
        );
    }
);


test(
    "solo devuelve ventas pendientes de sincronizar",
    () => {
        const rows = [
            {
                order_uuid: "pending",
                sync_status:
                    "PENDING_SYNC",
            },
            {
                order_uuid: "synced",
                sync_status:
                    "SYNCED",
            },
        ];

        const result =
            pendingLocalOrders(rows);

        assert.deepEqual(
            result.map(
                row =>
                    row.order_uuid
            ),
            ["pending"]
        );
    }
);


test(
    "si cloud y local tienen el mismo UUID se conserva cloud una sola vez",
    () => {
        const cloud = [
            {
                order_uuid: "same-order",
                folio: "NUE-000123",
                status: "NEW",
            },
        ];

        const local = [
            {
                order_uuid: "same-order",
                folio: "LOCAL-SAME",
                status: "NEW",
                is_local: true,
            },
            {
                order_uuid: "local-only",
                folio: "LOCAL-ONLY",
                status: "NEW",
                is_local: true,
            },
        ];


        const result =
            mergeOrders(
                cloud,
                local
            );


        assert.equal(
            result.length,
            2
        );

        assert.equal(
            result.find(
                row =>
                    row.order_uuid ===
                    "same-order"
            ).folio,
            "NUE-000123"
        );

        assert.equal(
            result.some(
                row =>
                    row.order_uuid ===
                    "local-only"
            ),
            true
        );
    }
);
