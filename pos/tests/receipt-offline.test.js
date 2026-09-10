const test = require("node:test");
const assert = require("node:assert/strict");

const {
    buildLocalOrder,
} = require("../js/orders-local.js");


test(
    "pending frozen sale keeps original receipt values",
    () => {
        const orderUuid =
            "a72f19c3-1111-2222-3333-555555555555";

        const folio =
            "NV-260909-7K3M9Q2F";

        const receiptSnapshot = {
            schema_version: 1,
            order_uuid: orderUuid,
            folio,

            items: [
                {
                    product_id: 10,
                    product_name:
                        "Latte vendido",
                    quantity: 2,
                    unit_price_cents: 8500,
                    line_total_cents: 17000,

                    modifiers: [
                        {
                            modifier_option_id: 51,
                            group_name: "Leche",
                            option_name: "Avena",
                            price_delta_cents: 1000,
                        },
                    ],
                },
            ],

            totals: {
                total_cents: 17000,
            },

            payment: {
                method: "CASH",
                amount_cents: 17000,
                amount_tendered_cents: 20000,
                change_due_cents: 3000,
            },
        };

        const local = {
            order_uuid: orderUuid,
            folio,
            receipt_snapshot:
                receiptSnapshot,

            sync_status:
                "PENDING_SYNC",

            created_at:
                "2026-09-09T20:00:00.000Z",

            local_total: 170,

            payload: {
                order_uuid: orderUuid,
                folio,

                branch_code:
                    "nuevo-vallarta",

                terminal_id:
                    "POS-TEST-01",

                receipt_snapshot:
                    receiptSnapshot,

                items: [
                    {
                        product_id: 10,
                        quantity: 2,
                        modifier_option_ids: [
                            51,
                        ],
                    },
                ],

                payment: {
                    method: "CASH",
                    amount_tendered:
                        200,
                },
            },
        };

        /*
         * Deliberately different current catalog.
         * Offline history must not be rebuilt
         * from these newer values.
         */
        const changedCatalog = {
            categories: [
                {
                    products: [
                        {
                            id: 10,
                            name:
                                "Latte RENAMED",

                            price: 999,

                            modifiers: [
                                {
                                    id: 5,
                                    name:
                                        "Leche nueva",

                                    options: [
                                        {
                                            id: 51,
                                            name:
                                                "Avena nueva",

                                            price_delta:
                                                99,
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        };

        const order = buildLocalOrder(
            local,
            changedCatalog
        );

        assert.equal(
            order.order_uuid,
            orderUuid
        );

        assert.equal(
            order.folio,
            folio
        );

        assert.deepEqual(
            order.receipt_snapshot,
            receiptSnapshot
        );

        assert.equal(
            order.total,
            170
        );

        assert.equal(
            order.items[0].product_name,
            "Latte vendido"
        );

        assert.equal(
            order.items[0].unit_price,
            85
        );

        assert.equal(
            order.items[0].line_total,
            170
        );

        assert.equal(
            order.items[0]
                .modifiers[0]
                .option_name,
            "Avena"
        );

        assert.equal(
            order.items[0]
                .modifiers[0]
                .price_delta,
            10
        );
    }
);


test(
    "receipt capable enqueue uses atomic paid sale finalization",
    async () => {
        const finalizeCalls = [];
        const putCalls = [];

        global.window = {
            CofiPosDB: {
                async finalizePaidSale(
                    record
                ) {
                    finalizeCalls.push(
                        record
                    );
                },

                async put(
                    storeName,
                    value
                ) {
                    putCalls.push({
                        storeName,
                        value,
                    });
                },
            },
        };

        delete require.cache[
            require.resolve(
                "../js/sync.js"
            )
        ];

        require("../js/sync.js");

        const orderUuid =
            "a72f19c3-1111-2222-3333-777777777777";

        const folio =
            "NV-260909-SYNC0001";

        const receiptSnapshot = {
            schema_version: 1,
            order_uuid: orderUuid,
            folio,

            items: [
                {
                    product_id: 10,
                    product_name:
                        "Latte vendido",
                    quantity: 1,
                    unit_price_cents:
                        8500,
                    line_total_cents:
                        8500,

                    modifiers: [
                        {
                            modifier_option_id:
                                51,
                            option_name:
                                "Avena",
                            price_delta_cents:
                                1000,
                        },
                    ],
                },
            ],

            totals: {
                subtotal_cents:
                    8500,
                discount_cents:
                    0,
                tax_mode:
                    "NONE",
                tax_rate:
                    "0",
                tax_cents:
                    0,
                tip_cents:
                    0,
                total_cents:
                    8500,
            },

            payment: {
                method:
                    "CASH",
                amount_cents:
                    8500,
                amount_tendered_cents:
                    10000,
                change_due_cents:
                    1500,
            },
        };

        const payload = {
            order_uuid:
                orderUuid,

            branch_code:
                "nuevo-vallarta",

            terminal_id:
                "POS-TEST-01",

            folio,

            items: [
                {
                    product_id:
                        10,
                    quantity:
                        1,
                    modifier_option_ids:
                        [51],
                },
            ],

            payment: {
                method:
                    "CASH",
                amount_tendered:
                    100,
            },

            receipt_snapshot:
                receiptSnapshot,
        };

        await window.CofiPosSync
            .enqueueOrder(
                payload,
                85
            );

        assert.equal(
            finalizeCalls.length,
            1
        );

        assert.equal(
            putCalls.length,
            0
        );

        const record =
            finalizeCalls[0];

        assert.equal(
            record.order_uuid,
            orderUuid
        );

        assert.equal(
            record.local_order
                .order_uuid,
            orderUuid
        );

        assert.equal(
            record.local_order
                .folio,
            folio
        );

        assert.deepEqual(
            record.local_order
                .receipt_snapshot,
            receiptSnapshot
        );

        assert.equal(
            record.sync_event
                .event_uuid,
            orderUuid
        );

        assert.equal(
            record.sync_event
                .payload.folio,
            folio
        );

        assert.deepEqual(
            record.sync_event
                .payload
                .receipt_snapshot,
            receiptSnapshot
        );

        assert.deepEqual(
            record.sync_event
                .payload,
            payload
        );

        assert.deepEqual(
            record.receipt_snapshot,
            receiptSnapshot
        );
    }
);


function frozenSyncFixture() {
    const orderUuid =
        "a72f19c3-1111-2222-3333-888888888888";

    const folio =
        "NV-260909-RETRY001";

    const receiptSnapshot = {
        schema_version: 1,
        order_uuid: orderUuid,
        folio,

        items: [
            {
                product_id: 10,
                product_name:
                    "Latte original",
                quantity: 1,
                unit_price_cents:
                    8500,
                line_total_cents:
                    8500,

                modifiers: [
                    {
                        modifier_option_id:
                            51,
                        group_name:
                            "Leche",
                        option_name:
                            "Avena",
                        price_delta_cents:
                            1000,
                    },
                ],
            },
        ],

        totals: {
            subtotal_cents:
                8500,
            discount_cents:
                0,
            tax_mode:
                "NONE",
            tax_rate:
                "0",
            tax_cents:
                0,
            tip_cents:
                0,
            total_cents:
                8500,
        },

        payment: {
            method:
                "CASH",
            amount_cents:
                8500,
            amount_tendered_cents:
                10000,
            change_due_cents:
                1500,
        },
    };

    const payload = {
        order_uuid:
            orderUuid,

        branch_code:
            "nuevo-vallarta",

        terminal_id:
            "POS-TEST-01",

        folio,

        items: [
            {
                product_id: 10,
                quantity: 1,
                modifier_option_ids:
                    [51],
            },
        ],

        payment: {
            method:
                "CASH",
            amount_tendered:
                100,
        },

        receipt_snapshot:
            receiptSnapshot,
    };

    return {
        orderUuid,
        folio,
        receiptSnapshot,
        payload,
    };
}


function cloneJson(value) {
    return JSON.parse(
        JSON.stringify(value)
    );
}


test(
    "sync retry reuses the exact frozen payload",
    async () => {
        const fixture =
            frozenSyncFixture();

        const originalPayload =
            cloneJson(
                fixture.payload
            );

        let storedEvent = {
            event_uuid:
                fixture.orderUuid,

            event_type:
                "ORDER_CREATED",

            payload:
                cloneJson(
                    fixture.payload
                ),

            sync_status:
                "PENDING_SYNC",

            attempts: 0,
            last_error: null,

            created_at:
                "2026-09-09T20:00:00.000Z",
        };

        const sentPayloads = [];
        let apiAttempts = 0;

        global.window = {
            CofiPosDB: {
                async getPendingEvents() {
                    if (
                        storedEvent.sync_status
                        !== "PENDING_SYNC"
                    ) {
                        return [];
                    }

                    return [
                        cloneJson(
                            storedEvent
                        ),
                    ];
                },

                async put(
                    storeName,
                    value
                ) {
                    if (
                        storeName ===
                        "sync_queue"
                    ) {
                        storedEvent =
                            cloneJson(
                                value
                            );
                    }
                },

                async getOrCreateTerminalId() {
                    throw new Error(
                        "terminal repair must not run"
                    );
                },
            },

            CofiPosAPI: {
                async createOrder(
                    payload
                ) {
                    sentPayloads.push(
                        cloneJson(
                            payload
                        )
                    );

                    apiAttempts += 1;

                    if (
                        apiAttempts === 1
                    ) {
                        throw new Error(
                            "temporary network failure"
                        );
                    }

                    return {
                        order_uuid:
                            fixture.orderUuid,

                        folio:
                            fixture.folio,
                    };
                },
            },

            CofiPosFolio: {
                generate() {
                    throw new Error(
                        "folio must never be regenerated"
                    );
                },
            },

            CofiReceiptCore: {
                buildSnapshot() {
                    throw new Error(
                        "receipt must never be rebuilt"
                    );
                },
            },
        };

        Object.defineProperty(
            globalThis,
            "navigator",
            {
                configurable: true,
                value: {
                    onLine: true,
                },
            }
        );

        delete require.cache[
            require.resolve(
                "../js/sync.js"
            )
        ];

        require("../js/sync.js");

        await window.CofiPosSync
            .syncPending();

        assert.equal(
            storedEvent.sync_status,
            "PENDING_SYNC"
        );

        assert.equal(
            storedEvent.attempts,
            1
        );

        await window.CofiPosSync
            .syncPending();

        assert.equal(
            sentPayloads.length,
            2
        );

        assert.deepEqual(
            sentPayloads[0],
            originalPayload
        );

        assert.deepEqual(
            sentPayloads[1],
            originalPayload
        );

        assert.equal(
            sentPayloads[1].folio,
            fixture.folio
        );

        assert.deepEqual(
            sentPayloads[1]
                .receipt_snapshot,
            fixture.receiptSnapshot
        );

        assert.equal(
            storedEvent.sync_status,
            "SYNCED"
        );
    }
);


test(
    "sync success preserves frozen folio and receipt on local order",
    async () => {
        const fixture =
            frozenSyncFixture();

        const writes = [];

        global.window = {
            CofiPosDB: {
                async getPendingEvents() {
                    return [
                        {
                            event_uuid:
                                fixture.orderUuid,

                            event_type:
                                "ORDER_CREATED",

                            payload:
                                cloneJson(
                                    fixture.payload
                                ),

                            sync_status:
                                "PENDING_SYNC",

                            attempts: 0,
                            last_error: null,

                            created_at:
                                "2026-09-09T20:00:00.000Z",
                        },
                    ];
                },

                async put(
                    storeName,
                    value
                ) {
                    writes.push({
                        storeName,
                        value:
                            cloneJson(
                                value
                            ),
                    });
                },

                async getOrCreateTerminalId() {
                    throw new Error(
                        "terminal repair must not run"
                    );
                },
            },

            CofiPosAPI: {
                async createOrder() {
                    return {
                        order_uuid:
                            fixture.orderUuid,

                        folio:
                            fixture.folio,
                    };
                },
            },
        };

        Object.defineProperty(
            globalThis,
            "navigator",
            {
                configurable: true,
                value: {
                    onLine: true,
                },
            }
        );

        delete require.cache[
            require.resolve(
                "../js/sync.js"
            )
        ];

        require("../js/sync.js");

        await window.CofiPosSync
            .syncPending();

        const localWrite =
            writes.find(
                entry =>
                    entry.storeName ===
                    "local_orders"
            );

        assert.ok(
            localWrite,
            "expected local_orders sync write"
        );

        assert.equal(
            localWrite.value
                .order_uuid,
            fixture.orderUuid
        );

        assert.equal(
            localWrite.value.folio,
            fixture.folio
        );

        assert.deepEqual(
            localWrite.value
                .receipt_snapshot,
            fixture.receiptSnapshot
        );

        assert.deepEqual(
            localWrite.value
                .payload,
            fixture.payload
        );

        assert.equal(
            localWrite.value
                .sync_status,
            "SYNCED"
        );
    }
);
