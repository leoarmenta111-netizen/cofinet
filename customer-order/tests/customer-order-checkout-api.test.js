const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


function source() {
    const target = path.join(
        process.cwd(),
        "customer-order/js/api.js"
    );

    return fs.readFileSync(
        target,
        "utf8"
    );
}


test(
    "API puede crear self order",
    () => {
        const text = source();

        assert.match(
            text,
            /function createSelfOrder/
        );

        assert.match(
            text,
            /\/self-orders/
        );

        assert.match(
            text,
            /method:\s*"POST"/
        );
    }
);


test(
    "API puede recuperar self order por device code",
    () => {
        const text = source();

        assert.match(
            text,
            /function getSelfOrder/
        );

        assert.match(
            text,
            /device_code/
        );
    }
);


test(
    "API expone payment attempts",
    () => {
        const text = source();

        assert.match(
            text,
            /function createPaymentAttempt/
        );

        assert.match(
            text,
            /payment-attempts/
        );
    }
);


test(
    "API puede cancelar self order",
    () => {
        const text = source();

        assert.match(
            text,
            /function cancelSelfOrder/
        );

        assert.match(
            text,
            /\/cancel/
        );
    }
);
