(() => {
    async function request(
        path,
        {
            timeout = 8000,
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
                        ...(options.body
                            ? {
                                "Content-Type":
                                    "application/json",
                            }
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

                const error = new Error(detail);
                error.status = response.status;
                error.payload = payload;

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


    window.CofiCustomerAPI = {
        request,
        getCatalog,
    };
})();
