window.CofiPosAPI = (() => {
    async function request(
        path,
        {
            timeout = 8000,
            accessToken = null,
            ...options
        } = {}
    ) {
        const controller = new AbortController();

        const timer = setTimeout(
            () => controller.abort(),
            timeout
        );

        try {
            const response = await fetch(
                `/api${path}`,
                {
                    ...options,
                    headers: {
                        Accept: "application/json",
                        ...(accessToken
                            ? {
                                Authorization:
                                    `Bearer ${accessToken}`,
                            }
                            : {}),
                        ...(options.body
                            ? { "Content-Type": "application/json" }
                            : {}),
                        ...(options.headers || {}),
                    },
                    signal: controller.signal,
                }
            );

            let payload = null;

            try {
                payload = await response.json();
            } catch {
                // Response without JSON.
            }

            if (!response.ok) {
                const detail =
                    Array.isArray(payload?.detail)
                        ? payload.detail
                            .map(item => item.msg)
                            .join("; ")
                        : (
                            payload?.detail ||
                            `HTTP ${response.status}`
                        );

                const error =
                    new Error(detail);

                error.status =
                    response.status;

                error.isHttpError =
                    true;

                error.payload =
                    payload;

                throw error;
            }

            return payload;

        } finally {
            clearTimeout(timer);
        }
    }

    function getCatalog(branchCode) {
        return request(
            `/pos/catalog?branch_code=${
                encodeURIComponent(branchCode)
            }`
        );
    }

    function getReceiptSettings(branchCode) {
        return request(
            `/pos/receipts/settings?branch_code=${
                encodeURIComponent(
                    branchCode
                )
            }`
        );
    }


    function createOrder(payload) {
        return request(
            "/pos/orders",
            {
                method: "POST",
                body: JSON.stringify(payload),
                timeout: 12000,
            }
        );
    }

    function listOrders(
        branchCode,
        {
            fromAt = null,
            toAt = null,
            limit = 100,
        } = {}
    ) {
        const params = new URLSearchParams({
            branch_code: branchCode,
            limit: String(limit),
        });

        if (fromAt) {
            params.set("from_at", fromAt);
        }

        if (toAt) {
            params.set("to_at", toAt);
        }

        return request(
            `/pos/orders?${params.toString()}`
        );
    }

    function getOrder(
        orderUuid,
        branchCode
    ) {
        return request(
            `/pos/orders/${
                encodeURIComponent(orderUuid)
            }?branch_code=${
                encodeURIComponent(branchCode)
            }`
        );
    }

    function updateOrderStatus(
        orderUuid,
        branchCode,
        status
    ) {
        return request(
            `/pos/orders/${
                encodeURIComponent(orderUuid)
            }/status`,
            {
                method: "PATCH",
                body: JSON.stringify({
                    branch_code: branchCode,
                    status,
                }),
            }
        );
    }

    function listStationOrders(

        station,

        branchCode

    ) {

        return request(

            `/pos/orders/stations/${

                encodeURIComponent(station)

            }?branch_code=${

                encodeURIComponent(branchCode)

            }`

        );

    }



    function updateStationStatus(

        orderUuid,

        station,

        branchCode,

        status

    ) {

        return request(

            `/pos/orders/${

                encodeURIComponent(orderUuid)

            }/stations/${

                encodeURIComponent(station)

            }`,

            {

                method: "PATCH",

                body: JSON.stringify({

                    branch_code: branchCode,

                    status,

                }),

            }

        );

    }



    function searchCustomers(
        query = ""
    ) {
        const params =
            new URLSearchParams();

        params.set(
            "q",
            String(query || "").trim()
        );

        return request(
            `/pos/customers?${params.toString()}`
        );
    }


    function createCustomer(payload) {
        return request(
            "/pos/customers",
            {
                method: "POST",
                body: JSON.stringify(payload),
            }
        );
    }


    function getCustomer(customerUuid) {
        return request(
            `/pos/customers/${
                encodeURIComponent(
                    customerUuid
                )
            }`
        );
    }



    function unlockStaff(
        staffId,
        pin,
        {
            branchCode,
            terminalId,
        }
    ) {
        return request(
            "/pos/staff/unlock",
            {
                method: "POST",
                body: JSON.stringify({
                    staff_id:
                        Number(staffId),
                    pin:
                        String(pin),
                    branch_code:
                        branchCode,
                    terminal_id:
                        terminalId,
                }),
            }
        );
    }


    function getStaffSession(
        accessToken
    ) {
        return request(
            "/pos/staff/session",
            {
                accessToken,
            }
        );
    }


    function getCurrentCashShift({
        accessToken,
    }) {
        return request(
            "/pos/cash/shifts/current",
            {
                accessToken,
            }
        );
    }


    function openCashShift(
        payload,
        {
            accessToken,
        }
    ) {
        return request(
            "/pos/cash/shifts/open",
            {
                method: "POST",
                body:
                    JSON.stringify(
                        payload
                    ),
                accessToken,
            }
        );
    }


    function recordCashMovement(
        shiftUuid,
        payload,
        {
            accessToken,
        }
    ) {
        return request(
            `/pos/cash/shifts/${
                encodeURIComponent(
                    shiftUuid
                )
            }/movements`,
            {
                method: "POST",
                body:
                    JSON.stringify(
                        payload
                    ),
                accessToken,
            }
        );
    }


    function submitCashClosingCount(
        shiftUuid,
        payload,
        {
            accessToken,
        }
    ) {
        return request(
            `/pos/cash/shifts/${
                encodeURIComponent(
                    shiftUuid
                )
            }/closing-count`,
            {
                method: "POST",
                body:
                    JSON.stringify(
                        payload
                    ),
                accessToken,
            }
        );
    }


    function finalizeCashShift(
        shiftUuid,
        payload,
        {
            accessToken,
        }
    ) {
        return request(
            `/pos/cash/shifts/${
                encodeURIComponent(
                    shiftUuid
                )
            }/close`,
            {
                method: "POST",
                body:
                    JSON.stringify(
                        payload
                    ),
                accessToken,
            }
        );
    }


    function checkHealth() {
        return request(
            "/health",
            {
                timeout: 3000,
            }
        );
    }

    return {
        request,
        getCatalog,
        getReceiptSettings,
        createOrder,
        listOrders,
        getOrder,
        updateOrderStatus,
        listStationOrders,
        updateStationStatus,
        searchCustomers,
        createCustomer,
        getCustomer,
        unlockStaff,
        getStaffSession,
        getCurrentCashShift,
        openCashShift,
        recordCashMovement,
        submitCashClosingCount,
        finalizeCashShift,
        checkHealth,
    };
})();
