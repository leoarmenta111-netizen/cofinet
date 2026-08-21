window.CofiPosDB = (() => {
    const DB_NAME = "cofi_pos_local";
    const DB_VERSION = 2;

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
        countPending,
        getPendingEvents,
        getOrCreateTerminalId,
    };
})();
