const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


test(
    "POS API exposes branch receipt settings endpoint",
    () => {
        global.window = {};

        delete require.cache[
            require.resolve("../js/api.js")
        ];

        require("../js/api.js");

        assert.equal(
            typeof window.CofiPosAPI
                .getReceiptSettings,
            "function"
        );

        const source =
            fs.readFileSync(
                path.join(
                    __dirname,
                    "../js/api.js"
                ),
                "utf8"
            );

        assert.match(
            source,
            /\/pos\/receipts\/settings/
        );
    }
);


test(
    "DB exposes branch scoped receipt settings cache helpers",
    () => {
        global.window = {};

        delete require.cache[
            require.resolve("../js/db.js")
        ];

        require("../js/db.js");

        assert.equal(
            typeof window.CofiPosDB
                .setReceiptSettings,
            "function"
        );

        assert.equal(
            typeof window.CofiPosDB
                .getReceiptSettings,
            "function"
        );
    }
);


function cloneJson(value) {
    return JSON.parse(
        JSON.stringify(value)
    );
}


function makeMetaIndexedDb() {
    const meta = new Map();

    const db = {
        transaction(
            storeName,
            mode
        ) {
            assert.equal(
                storeName,
                "meta"
            );

            const tx = {
                error: null,
            };

            return {
                ...tx,

                objectStore(name) {
                    assert.equal(
                        name,
                        "meta"
                    );

                    return {
                        get(key) {
                            const request = {
                                result: undefined,
                                error: null,
                                onsuccess: null,
                                onerror: null,
                            };

                            queueMicrotask(
                                () => {
                                    request.result =
                                        meta.has(key)
                                            ? cloneJson(
                                                meta.get(key)
                                            )
                                            : undefined;

                                    request.onsuccess?.({
                                        target:
                                            request,
                                    });
                                }
                            );

                            return request;
                        },

                        put(
                            value,
                            key
                        ) {
                            const request = {
                                result: key,
                                error: null,
                                onsuccess: null,
                                onerror: null,
                            };

                            queueMicrotask(
                                () => {
                                    meta.set(
                                        key,
                                        cloneJson(
                                            value
                                        )
                                    );

                                    request.onsuccess?.({
                                        target:
                                            request,
                                    });
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
        open() {
            const request = {
                result: db,
                error: null,
                onsuccess: null,
                onerror: null,
                onupgradeneeded: null,
            };

            queueMicrotask(
                () => {
                    request.onsuccess?.({
                        target:
                            request,
                    });
                }
            );

            return request;
        },
    };

    return {
        indexedDB,
        meta,
    };
}


function loadReceiptDb(
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


function validSettings(
    branchCode =
        "nuevo-vallarta"
) {
    return {
        business_name:
            "CofiCenter",

        logo_ref: null,

        branch_code:
            branchCode,

        branch_name:
            "CofiCenter Nuevo Vallarta",

        address: null,
        phone: null,
        web_social: null,
        footer_message:
            "Gracias por tu compra",

        currency:
            "MXN",

        tax_mode:
            "NONE",

        tax_rate:
            0,

        receipt_width_mm:
            80,

        timezone:
            "America/Bahia_Banderas",

        folio_prefix:
            "NV",

        auto_print:
            false,
    };
}


test(
    "receipt settings cache is normalized and branch scoped",
    async () => {
        const fake =
            makeMetaIndexedDb();

        const db =
            loadReceiptDb(
                fake.indexedDB
            );

        const settings =
            validSettings();

        await db.setReceiptSettings(
            "  NUEVO-VALLARTA  ",
            settings
        );

        const sameBranch =
            await db.getReceiptSettings(
                "nuevo-vallarta"
            );

        const otherBranch =
            await db.getReceiptSettings(
                "bucerias"
            );

        assert.deepEqual(
            sameBranch,
            settings
        );

        assert.equal(
            otherBranch,
            null
        );

        assert.ok(
            fake.meta.has(
                "receipt_settings:nuevo-vallarta"
            )
        );

        assert.equal(
            fake.meta.has(
                "receipt_settings:bucerias"
            ),
            false
        );
    }
);


test(
    "invalid receipt settings do not replace last valid cache",
    async () => {
        const fake =
            makeMetaIndexedDb();

        const db =
            loadReceiptDb(
                fake.indexedDB
            );

        const valid =
            validSettings();

        await db.setReceiptSettings(
            "nuevo-vallarta",
            valid
        );

        const invalid = {
            ...valid,
            tax_mode:
                "BROKEN",
        };

        await assert.rejects(
            db.setReceiptSettings(
                "nuevo-vallarta",
                invalid
            )
        );

        const stored =
            await db.getReceiptSettings(
                "nuevo-vallarta"
            );

        assert.deepEqual(
            stored,
            valid
        );
    }
);


test(
    "malformed cached receipt settings are rejected",
    async () => {
        const fake =
            makeMetaIndexedDb();

        fake.meta.set(
            "receipt_settings:nuevo-vallarta",
            {
                branch_code:
                    "nuevo-vallarta",

                tax_mode:
                    "BROKEN",
            }
        );

        const db =
            loadReceiptDb(
                fake.indexedDB
            );

        const stored =
            await db.getReceiptSettings(
                "nuevo-vallarta"
            );

        assert.equal(
            stored,
            null
        );
    }
);


test(
    "active branch loads cached receipt settings before online refresh",
    () => {
        const source =
            fs.readFileSync(
                path.join(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        assert.match(
            source,
            /receiptSettings:\s*null/
        );

        assert.match(
            source,
            /async function loadReceiptSettingsForBranch\s*\(/
        );

        assert.match(
            source,
            /CofiPosDB[\s\S]*?getReceiptSettings\s*\(/
        );

        assert.match(
            source,
            /CofiPosAPI[\s\S]*?getReceiptSettings\s*\(/
        );

        assert.match(
            source,
            /CofiPosDB[\s\S]*?setReceiptSettings\s*\(/
        );
    }
);


test(
    "terminal branch initialization invokes receipt settings lifecycle",
    () => {
        const source =
            fs.readFileSync(
                path.join(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        assert.match(
            source,
            /await\s+loadReceiptSettingsForBranch\s*\(\s*state\.branchCode\s*\)/
        );
    }
);


test(
    "receipt settings lifecycle preserves cached settings when refresh fails",
    () => {
        const source =
            fs.readFileSync(
                path.join(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        assert.match(
            source,
            /const cachedReceiptSettings\s*=\s*await/
        );

        assert.match(
            source,
            /state\.receiptSettings\s*=\s*cachedReceiptSettings/
        );

        assert.match(
            source,
            /catch\s*\([^)]*\)\s*\{[\s\S]*?cachedReceiptSettings/
        );
    }
);


test(
    "offline checkout without cached receipt settings cannot finalize payment",
    () => {
        const source =
            fs.readFileSync(
                path.join(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        const start =
            source.indexOf(
                "async function confirmPayment()"
            );

        const end =
            source.indexOf(
                "function showPaymentError",
                start
            );

        assert.ok(
            start >= 0,
            "confirmPayment must exist"
        );

        assert.ok(
            end > start,
            "confirmPayment boundary must exist"
        );

        const confirmPaymentSource =
            source.slice(
                start,
                end
            );

        const settingsGuard =
            confirmPaymentSource.search(
                /if\s*\(\s*!state\.receiptSettings\s*\)/
            );

        const paymentBusy =
            confirmPaymentSource.indexOf(
                "state.paymentBusy = true"
            );

        assert.ok(
            settingsGuard >= 0,
            "confirmPayment must guard missing receipt settings"
        );

        assert.ok(
            paymentBusy >= 0,
            "payment busy boundary must exist"
        );

        assert.ok(
            settingsGuard < paymentBusy,
            "receipt settings guard must run before payment finalization starts"
        );

        const guardArea =
            confirmPaymentSource.slice(
                settingsGuard,
                paymentBusy
            );

        assert.match(
            guardArea,
            /showPaymentError\s*\(/
        );

        assert.match(
            guardArea,
            /conexi[oó]n|con[eé]ct/i
        );
    }
);
