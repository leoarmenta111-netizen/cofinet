(function (root, factory) {
    const api = factory();

    if (
        typeof module !== "undefined" &&
        module.exports
    ) {
        module.exports = api;
    }

    if (root) {
        root.CofiCustomerCheckout = api;
    }
})(
    typeof window !== "undefined"
        ? window
        : globalThis,
    function () {
        const SESSION_KEY =
            "cofi_customer_self_order_session_v1";


        function viewForStatus(status) {
            switch (status) {
                case "AWAITING_PAYMENT":
                    return "PAYMENT";

                case "PAYMENT_PROCESSING":
                case "PAID":
                    return "PROCESSING";

                case "PAYMENT_DECLINED":
                    return "DECLINED";

                case "PAYMENT_UNKNOWN":
                    return "UNKNOWN";

                case "SUBMITTED":
                    return "SUCCESS";

                case "CANCELLED":
                case "EXPIRED":
                    return "CLOSED";

                default:
                    return "PAYMENT";
            }
        }


        function canStartPayment(status) {
            return (
                status === "AWAITING_PAYMENT" ||
                status === "PAYMENT_DECLINED"
            );
        }


        function canIdleReset(status) {
            return ![
                "PAYMENT_PROCESSING",
                "PAYMENT_UNKNOWN",
                "PAID",
                "SUBMITTED",
            ].includes(status);
        }


        function ensureAttemptUuid(
            existing,
            createUuid
        ) {
            if (existing) {
                return existing;
            }

            return createUuid();
        }


        function buildSession({
            selfOrderUuid,
            branchCode,
            deviceCode,
            paymentAttemptUuid = null,
        }) {
            return {
                self_order_uuid:
                    selfOrderUuid,
                branch_code:
                    branchCode,
                device_code:
                    deviceCode,
                payment_attempt_uuid:
                    paymentAttemptUuid,
            };
        }


        return {
            SESSION_KEY,
            viewForStatus,
            canStartPayment,
            canIdleReset,
            ensureAttemptUuid,
            buildSession,
        };
    }
);
