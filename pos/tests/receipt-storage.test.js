const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


const dbSource = fs.readFileSync(
    path.join(__dirname, "../js/db.js"),
    "utf8"
);


test(
    "IndexedDB v3 declares receipts storage",
    () => {
        assert.match(
            dbSource,
            /const DB_VERSION = 3;/
        );

        assert.match(
            dbSource,
            /createObjectStore\(\s*"receipts"[\s\S]*?keyPath:\s*"order_uuid"/
        );
    }
);


test(
    "receipt database accessors are exposed",
    () => {
        global.window = {};

        delete require.cache[
            require.resolve("../js/db.js")
        ];

        require("../js/db.js");

        assert.equal(
            typeof window.CofiPosDB.getReceipt,
            "function"
        );

        assert.equal(
            typeof window.CofiPosDB.getLocalOrder,
            "function"
        );
    }
);


function clone(value) {
    return JSON.parse(
        JSON.stringify(value)
    );
}


function makeAtomicIndexedDb(
    {
        failStore = null,
    } = {}
) {
    const committed = {
        local_orders: new Map(),
        receipts: new Map(),
        sync_queue: new Map(),
    };

    const transactions = [];

    const db = {
        transaction(storeNames, mode) {
            const names = Array.isArray(
                storeNames
            )
                ? [...storeNames]
                : [storeNames];

            transactions.push({
                storeNames: names,
                mode,
            });

            const staged = [];
            let aborted = false;
            let requestCount = 0;

            const tx = {
                error: null,
                oncomplete: null,
                onerror: null,
                onabort: null,

                objectStore(name) {
                    assert.ok(
                        names.includes(name),
                        `unexpected store ${name}`
                    );

                    return {
                        put(value) {
                            requestCount += 1;

                            const request = {
                                result: undefined,
                                error: null,
                                onsuccess: null,
                                onerror: null,
                            };

                            queueMicrotask(() => {
                                if (aborted) {
                                    return;
                                }

                                if (
                                    name === failStore
                                ) {
                                    request.error =
                                        new Error(
                                            `forced ${name} failure`
                                        );

                                    tx.error =
                                        request.error;

                                    if (
                                        request.onerror
                                    ) {
                                        request.onerror({
                                            target:
                                                request,
                                        });
                                    }

                                    /*
                                     * IndexedDB request errors
                                     * abort the transaction unless
                                     * explicitly prevented.
                                     */
                                    if (!aborted) {
                                        tx.abort();
                                    }

                                    return;
                                }

                                staged.push({
                                    name,
                                    value:
                                        clone(value),
                                });

                                if (
                                    request.onsuccess
                                ) {
                                    request.onsuccess({
                                        target:
                                            request,
                                    });
                                }

                                if (
                                    requestCount === 3 &&
                                    staged.length === 3
                                ) {
                                    queueMicrotask(
                                        () => {
                                            if (
                                                aborted
                                            ) {
                                                return;
                                            }

                                            for (
                                                const entry
                                                of staged
                                            ) {
                                                const key =
                                                    entry.name ===
                                                    "sync_queue"
                                                        ? entry
                                                            .value
                                                            .event_uuid
                                                        : entry
                                                            .value
                                                            .order_uuid;

                                                committed[
                                                    entry.name
                                                ].set(
                                                    key,
                                                    entry.value
                                                );
                                            }

                                            if (
                                                tx.oncomplete
                                            ) {
                                                tx.oncomplete({
                                                    target:
                                                        tx,
                                                });
                                            }
                                        }
                                    );
                                }
                            });

                            return request;
                        },
                    };
                },

                abort() {
                    if (aborted) {
                        return;
                    }

                    aborted = true;
                    staged.length = 0;

                    queueMicrotask(() => {
                        if (tx.onabort) {
                            tx.onabort({
                                target: tx,
                            });
                        }
                    });
                },
            };

            return tx;
        },
    };

    const indexedDB = {
        open() {
            const request = {
                result: db,
                error: null,
                onsuccess: null,
                onerror: null,
                onupgradeneeded: null,
            };

            queueMicrotask(() => {
                if (request.onsuccess) {
                    request.onsuccess({
                        target: request,
                    });
                }
            });

            return request;
        },
    };

    return {
        indexedDB,
        committed,
        transactions,
    };
}


function loadDbWithIndexedDb(
    fakeIndexedDb
) {
    global.window = {};
    global.indexedDB =
        fakeIndexedDb;

    delete require.cache[
        require.resolve("../js/db.js")
    ];

    require("../js/db.js");

    return window.CofiPosDB;
}


function paidSaleRecord() {
    const orderUuid =
        "a72f19c3-1111-2222-3333-666666666666";

    const folio =
        "NV-260909-ATOMIC01";

    const receiptSnapshot = {
        schema_version: 1,
        order_uuid: orderUuid,
        folio,
        totals: {
            total_cents: 8500,
        },
    };

    const localOrder = {
        order_uuid: orderUuid,
        folio,
        receipt_snapshot:
            receiptSnapshot,
        sync_status:
            "PENDING_SYNC",
        created_at:
            "2026-09-09T20:00:00.000Z",
    };

    const syncEvent = {
        event_uuid: orderUuid,
        event_type:
            "ORDER_CREATED",
        sync_status:
            "PENDING_SYNC",
        attempts: 0,
        created_at:
            "2026-09-09T20:00:00.000Z",

        payload: {
            order_uuid:
                orderUuid,
            folio,
            receipt_snapshot:
                receiptSnapshot,
        },
    };

    return {
        order_uuid:
            orderUuid,

        local_order:
            localOrder,

        receipt_snapshot:
            receiptSnapshot,

        sync_event:
            syncEvent,
    };
}


test(
    "finalizePaidSale atomically stores order receipt and sync event",
    async () => {
        const fake =
            makeAtomicIndexedDb();

        const db =
            loadDbWithIndexedDb(
                fake.indexedDB
            );

        const record =
            paidSaleRecord();

        await db.finalizePaidSale(
            record
        );

        assert.equal(
            fake.transactions.length,
            1
        );

        assert.equal(
            fake.transactions[0].mode,
            "readwrite"
        );

        assert.deepEqual(
            [
                ...fake.transactions[0]
                    .storeNames,
            ].sort(),
            [
                "local_orders",
                "receipts",
                "sync_queue",
            ].sort()
        );

        assert.deepEqual(
            fake.committed
                .local_orders
                .get(record.order_uuid),
            record.local_order
        );

        assert.deepEqual(
            fake.committed
                .receipts
                .get(record.order_uuid),
            record.receipt_snapshot
        );

        assert.deepEqual(
            fake.committed
                .sync_queue
                .get(record.order_uuid),
            record.sync_event
        );
    }
);


test(
    "finalizePaidSale leaves no partial writes when transaction fails",
    async () => {
        const fake =
            makeAtomicIndexedDb({
                failStore:
                    "receipts",
            });

        const db =
            loadDbWithIndexedDb(
                fake.indexedDB
            );

        const record =
            paidSaleRecord();

        await assert.rejects(
            db.finalizePaidSale(
                record
            )
        );

        assert.equal(
            fake.committed
                .local_orders.size,
            0
        );

        assert.equal(
            fake.committed
                .receipts.size,
            0
        );

        assert.equal(
            fake.committed
                .sync_queue.size,
            0
        );
    }
);


function makeUpgradeIndexedDb() {
    const records = {
        meta: new Map([
            [
                "terminal_id",
                "NV-POS-LEGACY",
            ],
        ]),

        catalogs: new Map([
            [
                "nuevo-vallarta",
                {
                    branch_code:
                        "nuevo-vallarta",
                    marker:
                        "legacy-catalog",
                },
            ],
        ]),

        local_orders: new Map([
            [
                "legacy-order",
                {
                    order_uuid:
                        "legacy-order",
                    sync_status:
                        "PENDING_SYNC",
                },
            ],
        ]),

        sync_queue: new Map([
            [
                "legacy-event",
                {
                    event_uuid:
                        "legacy-event",
                    sync_status:
                        "PENDING_SYNC",
                },
            ],
        ]),
    };

    const keyPaths = {
        meta: null,
        catalogs:
            "branch_code",
        local_orders:
            "order_uuid",
        sync_queue:
            "event_uuid",
    };

    const createCalls = [];

    const objectStoreNames = {
        contains(name) {
            return Object.prototype
                .hasOwnProperty.call(
                    records,
                    name
                );
        },
    };

    const db = {
        objectStoreNames,

        createObjectStore(
            name,
            options = {}
        ) {
            if (
                Object.prototype
                    .hasOwnProperty.call(
                        records,
                        name
                    )
            ) {
                throw new Error(
                    `store ${name} already exists`
                );
            }

            records[name] =
                new Map();

            keyPaths[name] =
                options.keyPath ??
                null;

            createCalls.push({
                name,
                keyPath:
                    options.keyPath ??
                    null,
            });

            return {
                createIndex() {},
            };
        },

        transaction(
            storeName,
            mode
        ) {
            assert.equal(
                mode,
                "readonly"
            );

            return {
                objectStore(name) {
                    assert.equal(
                        name,
                        storeName
                    );

                    return {
                        get(key) {
                            const request = {
                                result:
                                    undefined,
                                error:
                                    null,
                                onsuccess:
                                    null,
                                onerror:
                                    null,
                            };

                            queueMicrotask(
                                () => {
                                    request.result =
                                        records[
                                            name
                                        ].get(
                                            key
                                        );

                                    if (
                                        request
                                            .onsuccess
                                    ) {
                                        request
                                            .onsuccess({
                                                target:
                                                    request,
                                            });
                                    }
                                }
                            );

                            return request;
                        },
                    };
                },
            };
        },
    };

    const indexedDB = {
        open(
            databaseName,
            version
        ) {
            assert.equal(
                databaseName,
                "cofi_pos_local"
            );

            assert.equal(
                version,
                3
            );

            const request = {
                result: db,
                error: null,
                onsuccess: null,
                onerror: null,
                onupgradeneeded:
                    null,
            };

            queueMicrotask(
                () => {
                    if (
                        request
                            .onupgradeneeded
                    ) {
                        request
                            .onupgradeneeded({
                                oldVersion: 2,
                                newVersion:
                                    3,
                                target:
                                    request,
                            });
                    }

                    if (
                        request.onsuccess
                    ) {
                        request
                            .onsuccess({
                                target:
                                    request,
                            });
                    }
                }
            );

            return request;
        },
    };

    return {
        indexedDB,
        records,
        keyPaths,
        createCalls,
    };
}


test(
    "upgrade from v2 preserves existing records and adds receipts",
    async () => {
        const fake =
            makeUpgradeIndexedDb();

        const originalMeta =
            fake.records.meta.get(
                "terminal_id"
            );

        const originalCatalog =
            clone(
                fake.records.catalogs.get(
                    "nuevo-vallarta"
                )
            );

        const originalOrder =
            clone(
                fake.records.local_orders.get(
                    "legacy-order"
                )
            );

        const originalEvent =
            clone(
                fake.records.sync_queue.get(
                    "legacy-event"
                )
            );

        const api =
            loadDbWithIndexedDb(
                fake.indexedDB
            );

        await api.open();

        assert.deepEqual(
            fake.createCalls,
            [
                {
                    name:
                        "receipts",
                    keyPath:
                        "order_uuid",
                },
            ]
        );

        assert.equal(
            fake.keyPaths.receipts,
            "order_uuid"
        );

        assert.equal(
            fake.records.meta.get(
                "terminal_id"
            ),
            originalMeta
        );

        assert.deepEqual(
            fake.records.catalogs.get(
                "nuevo-vallarta"
            ),
            originalCatalog
        );

        assert.deepEqual(
            fake.records.local_orders.get(
                "legacy-order"
            ),
            originalOrder
        );

        assert.deepEqual(
            fake.records.sync_queue.get(
                "legacy-event"
            ),
            originalEvent
        );
    }
);


test(
    "getReceipt returns the exact stored receipt snapshot",
    async () => {
        const fake =
            makeUpgradeIndexedDb();

        const api =
            loadDbWithIndexedDb(
                fake.indexedDB
            );

        await api.open();

        const orderUuid =
            "receipt-lookup-order";

        const snapshot = {
            order_uuid:
                orderUuid,
            schema_version: 1,
            folio:
                "NV-260909-LOOKUP01",
        };

        fake.records.receipts.set(
            orderUuid,
            clone(snapshot)
        );

        const stored =
            await api.getReceipt(
                orderUuid
            );

        assert.deepEqual(
            stored,
            snapshot
        );
    }
);


test(
    "getReceipt returns null when receipt does not exist",
    async () => {
        const fake =
            makeUpgradeIndexedDb();

        const api =
            loadDbWithIndexedDb(
                fake.indexedDB
            );

        await api.open();

        const missing =
            await api.getReceipt(
                "missing-order"
            );

        assert.equal(
            missing,
            null
        );
    }
);
