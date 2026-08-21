window.CofiPosCatalog = (() => {
    async function load(branchCode) {
        try {
            const catalog =
                await window.CofiPosAPI
                    .getCatalog(branchCode);

            const record = {
                branch_code: branchCode,
                catalog,
                cached_at:
                    new Date().toISOString(),
            };

            await window.CofiPosDB.put(
                "catalogs",
                record
            );

            await window.CofiPosDB.put(
                "meta",
                record.cached_at,
                "last_sync"
            );

            return {
                catalog,
                source: "cloud",
                cachedAt: record.cached_at,
            };

        } catch (error) {
            console.warn(
                "Cloud catalog unavailable:",
                error
            );

            const cached =
                await window.CofiPosDB.get(
                    "catalogs",
                    branchCode
                );

            if (!cached) {
                throw new Error(
                    "No hay conexión y esta terminal " +
                    "todavía no tiene un catálogo local."
                );
            }

            return {
                catalog: cached.catalog,
                source: "local",
                cachedAt: cached.cached_at,
            };
        }
    }

    return {
        load,
    };
})();
