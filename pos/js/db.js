window.CofiPosDB = (() => {
    const DB_NAME = "cofi_pos_local";
    const DB_VERSION = 3;

    let dbPromise = null;

    function open() {
        if (dbPromise) return dbPromise;

        dbPromise = new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onupgradeneeded = () => {
                const db = request.result;

                if (!db.objectStoreNames.contains("meta")) {
                    db.createObjectStore("meta");
                }

                if (!db.objectStoreNames.contains("catalogs")) {
                    db.createObjectStore("catalogs", {
                        keyPath: "branch_code",
                    });
                }

                if (!db.objectStoreNames.contains("local_orders")) {
                    const store = db.createObjectStore(
                        "local_orders",
                        { keyPath: "order_uuid" }
                    );

                    store.createIndex(
                        "sync_status",
                        "sync_status",
                        { unique: false }
                    );

                    store.createIndex(
                        "created_at",
                        "created_at",
                        { unique: false }
                    );
                }

                if (!db.objectStoreNames.contains("sync_queue")) {
                    const store = db.createObjectStore(
                        "sync_queue",
                        { keyPath: "event_uuid" }
                    );

                    store.createIndex(
                        "sync_status",
                        "sync_status",
                        { unique: false }
                    );

                    store.createIndex(
                        "created_at",
                        "created_at",
                        { unique: false }
                    );
                }

                if (!db.objectStoreNames.contains("receipts")) {
                    db.createObjectStore(
                        "receipts",
                        { keyPath: "order_uuid" }
                    );
                }
            };

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });

        return dbPromise;
    }

    async function get(storeName, key) {
        const db = await open();

        return new Promise((resolve, reject) => {
            const tx = db.transaction(storeName, "readonly");
            const request = tx.objectStore(storeName).get(key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function put(storeName, value, key) {
        const db = await open();

        return new Promise((resolve, reject) => {
            const tx = db.transaction(storeName, "readwrite");
            const store = tx.objectStore(storeName);

            const request =
                key === undefined
                    ? store.put(value)
                    : store.put(value, key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function getAll(storeName) {
        const db = await open();

        return new Promise((resolve, reject) => {
            const tx = db.transaction(storeName, "readonly");
            const request = tx.objectStore(storeName).getAll();

            request.onsuccess = () => resolve(request.result || []);
            request.onerror = () => reject(request.error);
        });
    }

    function normalizeReceiptBranchCode(
        value
    ) {
        return String(value || "")
            .trim()
            .toLowerCase();
    }


    function receiptSettingsKey(
        branchCode
    ) {
        const normalized =
            normalizeReceiptBranchCode(
                branchCode
            );

        if (!normalized) {
            throw new Error(
                "Receipt settings require branch code"
            );
        }

        return (
            "receipt_settings:" +
            normalized
        );
    }


    function isValidReceiptSettings(
        branchCode,
        settings
    ) {
        if (
            !settings ||
            typeof settings !== "object" ||
            Array.isArray(settings)
        ) {
            return false;
        }

        const normalizedBranch =
            normalizeReceiptBranchCode(
                branchCode
            );

        const settingsBranch =
            normalizeReceiptBranchCode(
                settings.branch_code
            );

        if (
            !normalizedBranch ||
            settingsBranch !==
                normalizedBranch
        ) {
            return false;
        }

        if (
            typeof settings.business_name
                !== "string" ||
            !settings.business_name.trim()
        ) {
            return false;
        }

        if (
            typeof settings.branch_name
                !== "string" ||
            !settings.branch_name.trim()
        ) {
            return false;
        }

        if (
            ![
                "NONE",
                "INCLUDED",
                "ADDED",
            ].includes(
                settings.tax_mode
            )
        ) {
            return false;
        }

        const taxRate =
            Number(settings.tax_rate);

        if (
            !Number.isFinite(taxRate) ||
            taxRate < 0
        ) {
            return false;
        }

        if (
            settings.tax_mode === "NONE" &&
            taxRate !== 0
        ) {
            return false;
        }

        if (
            Number(
                settings.receipt_width_mm
            ) !== 80
        ) {
            return false;
        }

        if (
            typeof settings.timezone
                !== "string" ||
            !settings.timezone.trim()
        ) {
            return false;
        }

        const prefix =
            String(
                settings.folio_prefix ||
                ""
            )
                .trim()
                .toUpperCase();

        if (
            !/^[A-Z0-9]{2,8}$/.test(
                prefix
            )
        ) {
            return false;
        }

        if (
            typeof settings.currency
                !== "string" ||
            !/^[A-Z]{3}$/.test(
                settings.currency
                    .trim()
                    .toUpperCase()
            )
        ) {
            return false;
        }

        if (
            typeof settings.auto_print_customer
                !== "boolean"
        ) {
            return false;
        }

        return true;
    }


    async function setReceiptSettings(
        branchCode,
        settings
    ) {
        const key =
            receiptSettingsKey(
                branchCode
            );

        if (
            !isValidReceiptSettings(
                branchCode,
                settings
            )
        ) {
            throw new Error(
                "Invalid receipt settings"
            );
        }

        const db = await open();

        return new Promise(
            (resolve, reject) => {
                const tx =
                    db.transaction(
                        "meta",
                        "readwrite"
                    );

                const request =
                    tx.objectStore("meta")
                        .put(
                            settings,
                            key
                        );

                request.onsuccess = () =>
                    resolve(settings);

                request.onerror = () =>
                    reject(
                        request.error
                    );
            }
        );
    }


    async function getReceiptSettings(
        branchCode
    ) {
        const settings =
            await get(
                "meta",
                receiptSettingsKey(
                    branchCode
                )
            );

        if (
            settings == null
        ) {
            return null;
        }

        if (
            !isValidReceiptSettings(
                branchCode,
                settings
            )
        ) {
            return null;
        }

        return settings;
    }


    async function getReceipt(orderUuid) {
        const receipt = await get(
            "receipts",
            orderUuid
        );

        return receipt ?? null;
    }


    async function getLocalOrder(orderUuid) {
        return get(
            "local_orders",
            orderUuid
        );
    }


    async function finalizePaidSale(record) {
        const db = await open();

        return new Promise((resolve, reject) => {
            const tx = db.transaction(
                [
                    "local_orders",
                    "receipts",
                    "sync_queue",
                ],
                "readwrite"
            );

            let settled = false;

            function rejectOnce(error) {
                if (settled) {
                    return;
                }

                settled = true;

                reject(
                    error ||
                    tx.error ||
                    new Error(
                        "Failed to finalize paid sale"
                    )
                );
            }

            tx.oncomplete = () => {
                if (settled) {
                    return;
                }

                settled = true;
                resolve(record);
            };

            tx.onerror = () => {
                rejectOnce(
                    tx.error ||
                    new Error(
                        "Paid sale transaction failed"
                    )
                );
            };

            tx.onabort = () => {
                rejectOnce(
                    tx.error ||
                    new Error(
                        "Paid sale transaction aborted"
                    )
                );
            };

            const requests = [
                tx
                    .objectStore("local_orders")
                    .put(record.local_order),

                tx
                    .objectStore("receipts")
                    .put(record.receipt_snapshot),

                tx
                    .objectStore("sync_queue")
                    .put(record.sync_event),
            ];

            for (const request of requests) {
                request.onerror = () => {
                    const error =
                        request.error ||
                        tx.error ||
                        new Error(
                            "Paid sale write failed"
                        );

                    try {
                        tx.abort();
                    } catch {
                        // Transaction may already be aborting.
                    }

                    rejectOnce(error);
                };
            }
        });
    }


    async function countPending() {
        const db = await open();

        return new Promise((resolve, reject) => {
            const tx = db.transaction("sync_queue", "readonly");

            const request = tx
                .objectStore("sync_queue")
                .index("sync_status")
                .count(IDBKeyRange.only("PENDING_SYNC"));

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async function getPendingEvents() {
        const rows = await getAll("sync_queue");

        return rows
            .filter(row => row.sync_status === "PENDING_SYNC")
            .sort((a, b) =>
                String(a.created_at).localeCompare(
                    String(b.created_at)
                )
            );
    }

    async function getOrCreateTerminalId(branchCode) {
        const key = `terminal_id:${branchCode}`;

        const existing = await get(
            "meta",
            key
        );

        if (
            typeof existing === "string" &&
            existing.trim()
        ) {
            return existing;
        }

        const legacy = await get(
            "meta",
            "terminal_id"
        );

        if (
            typeof legacy === "string" &&
            legacy.trim()
        ) {
            await put(
                "meta",
                legacy,
                key
            );

            return legacy;
        }

        const prefix = (
            branchCode
                .replace(/[^a-z0-9]/gi, "")
                .slice(0, 3) || "POS"
        ).toUpperCase();

        const suffix = window.CofiUUID
            .v4()
            .replace(/-/g, "")
            .slice(0, 6)
            .toUpperCase();

        const terminalId =
            `${prefix}-POS-${suffix}`;

        await put(
            "meta",
            terminalId,
            key
        );

        return terminalId;
    }

    return {
        open,
        get,
        put,
        getAll,
        setReceiptSettings,
        getReceiptSettings,
        getReceipt,
        getLocalOrder,
        finalizePaidSale,
        countPending,
        getPendingEvents,
        getOrCreateTerminalId,
    };
})();
