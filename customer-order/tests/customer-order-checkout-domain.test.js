const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


function loadCheckout() {
    const target = path.join(
        process.cwd(),
        "customer-order/js/checkout.js"
    );

    assert.equal(
        fs.existsSync(target),
        true,
        "falta customer-order/js/checkout.js"
    );

    delete require.cache[
        require.resolve(target)
    ];

    return require(target);
}


test(
    "mapea estados backend a estados visibles de checkout",
    () => {
        const checkout = loadCheckout();

        assert.equal(
            checkout.viewForStatus(
                "AWAITING_PAYMENT"
            ),
            "PAYMENT"
        );

        assert.equal(
            checkout.viewForStatus(
                "PAYMENT_PROCESSING"
            ),
            "PROCESSING"
        );

        assert.equal(
            checkout.viewForStatus(
                "PAYMENT_DECLINED"
            ),
            "DECLINED"
        );

        assert.equal(
            checkout.viewForStatus(
                "PAYMENT_UNKNOWN"
            ),
            "UNKNOWN"
        );

        assert.equal(
            checkout.viewForStatus(
                "SUBMITTED"
            ),
            "SUCCESS"
        );
    }
);


test(
    "solo permite iniciar pago desde awaiting o declined",
    () => {
        const checkout = loadCheckout();

        assert.equal(
            checkout.canStartPayment(
                "AWAITING_PAYMENT"
            ),
            true
        );

        assert.equal(
            checkout.canStartPayment(
                "PAYMENT_DECLINED"
            ),
            true
        );

        assert.equal(
            checkout.canStartPayment(
                "PAYMENT_PROCESSING"
            ),
            false
        );

        assert.equal(
            checkout.canStartPayment(
                "PAYMENT_UNKNOWN"
            ),
            false
        );

        assert.equal(
            checkout.canStartPayment(
                "SUBMITTED"
            ),
            false
        );
    }
);


test(
    "inactividad nunca resetea durante processing o unknown",
    () => {
        const checkout = loadCheckout();

        assert.equal(
            checkout.canIdleReset(
                "PAYMENT_PROCESSING"
            ),
            false
        );

        assert.equal(
            checkout.canIdleReset(
                "PAYMENT_UNKNOWN"
            ),
            false
        );

        assert.equal(
            checkout.canIdleReset(
                "AWAITING_PAYMENT"
            ),
            true
        );

        assert.equal(
            checkout.canIdleReset(
                "PAYMENT_DECLINED"
            ),
            true
        );
    }
);


test(
    "reutiliza payment attempt uuid existente",
    () => {
        const checkout = loadCheckout();

        let calls = 0;

        const existing =
            checkout.ensureAttemptUuid(
                "attempt-existing",
                () => {
                    calls += 1;
                    return "attempt-new";
                }
            );

        assert.equal(
            existing,
            "attempt-existing"
        );

        assert.equal(
            calls,
            0
        );
    }
);


test(
    "genera payment attempt una sola vez cuando no existe",
    () => {
        const checkout = loadCheckout();

        let calls = 0;

        const generated =
            checkout.ensureAttemptUuid(
                null,
                () => {
                    calls += 1;
                    return "attempt-new";
                }
            );

        assert.equal(
            generated,
            "attempt-new"
        );

        assert.equal(
            calls,
            1
        );
    }
);


test(
    "sesion recuperable conserva pedido dispositivo y attempt",
    () => {
        const checkout = loadCheckout();

        const session =
            checkout.buildSession({
                selfOrderUuid:
                    "order-1",
                branchCode:
                    "ixtapa",
                deviceCode:
                    "KIOSK-IXTAPA-01",
                paymentAttemptUuid:
                    "attempt-1",
            });

        assert.deepEqual(
            session,
            {
                self_order_uuid:
                    "order-1",
                branch_code:
                    "ixtapa",
                device_code:
                    "KIOSK-IXTAPA-01",
                payment_attempt_uuid:
                    "attempt-1",
            }
        );
    }
);
