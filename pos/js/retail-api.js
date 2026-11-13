window.CofiRetailAPI = (() => {
    const MODULE_CODE =
        "PAPELERIA";

    let accessToken = null;


    function setAccessToken(value) {
        accessToken =
            value
                ? String(value)
                : null;
    }


    function getAccessToken() {
        return accessToken;
    }


    function request(
        path,
        options = {}
    ) {
        const api =
            window.CofiPosAPI;

        if (
            !api
            || typeof api.request
                !== "function"
        ) {
            throw new Error(
                "CofiPosAPI is unavailable"
            );
        }

        return api.request(
            path,
            {
                ...options,
                accessToken,
            }
        );
    }


    function jsonRequest(
        path,
        method,
        payload
    ) {
        return request(
            path,
            {
                method,
                body:
                    JSON.stringify(
                        payload
                    ),
            }
        );
    }


    /*
     * Initial retail adapter.
     *
     * Route contracts will be validated
     * against the current FastAPI OpenAPI
     * before Task 6 checkout wiring.
     */

    function loadCatalog() {
        return request(
            "/retail/catalog"
        );
    }


    function listHeldSales() {
        return request(
            "/retail/sales/held"
        );
    }


    function holdSale(payload) {
        return jsonRequest(
            "/retail/sales/held",
            "POST",
            payload
        );
    }


    function updateHeldSale(
        saleUuid,
        payload
    ) {
        return jsonRequest(
            `/retail/sales/held/${encodeURIComponent(saleUuid)}`,
            "PUT",
            payload
        );
    }


    function checkout(payload) {
        return jsonRequest(
            "/retail/sales/checkout",
            "POST",
            payload
        );
    }


    function receipt(
        saleUuid
    ) {
        return request(
            `/retail/sales/${
                encodeURIComponent(
                    saleUuid
                )
            }/receipt`
        );
    }


    function returnItems(
        saleUuid,
        payload
    ) {
        return jsonRequest(
            `/retail/sales/${
                encodeURIComponent(
                    saleUuid
                )
            }/returns`,
            "POST",
            payload
        );
    }


    function cancelSale(
        saleUuid,
        payload
    ) {
        return jsonRequest(
            `/retail/sales/${
                encodeURIComponent(
                    saleUuid
                )
            }/cancel`,
            "POST",
            payload
        );
    }


    return {
        moduleCode:
            MODULE_CODE,

        setAccessToken,
        getAccessToken,

        loadCatalog,
        listHeldSales,
        holdSale,
        updateHeldSale,
        checkout,
        receipt,
        returnItems,
        cancelSale,
    };
})();
