const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(
    __dirname,
    ".."
);

const api = fs.readFileSync(
    path.join(
        root,
        "js",
        "api.js"
    ),
    "utf8"
);

const app = fs.readFileSync(
    path.join(
        root,
        "js",
        "app.js"
    ),
    "utf8"
);


test(
    "API expone reconciliacion de pago Point",
    () => {
        assert.match(
            api,
            /function reconcilePayment/
        );

        assert.match(
            api,
            /payment-status/
        );
    }
);


test(
    "kiosk hace polling mientras Point procesa",
    () => {
        assert.match(
            app,
            /function pollPointPayment/
        );

        assert.match(
            app,
            /reconcilePayment/
        );

        assert.match(
            app,
            /PAYMENT_PROCESSING/
        );
    }
);


test(
    "kiosk espera reconciliacion cuando Point sigue procesando",
    () => {
        assert.match(
            app,
            /order\.status\s*===\s*"PAYMENT_PROCESSING"[\s\S]*?pollPointPayment/
        );

        assert.match(
            app,
            /await\s+pollPointPayment\(\)/
        );
    }
);


test(
    "kiosk recuperado reanuda verificacion Point",
    () => {
        assert.match(
            app,
            /recoverCheckoutSession/
        );

        assert.match(
            app,
            /pollPointPayment/
        );
    }
);
