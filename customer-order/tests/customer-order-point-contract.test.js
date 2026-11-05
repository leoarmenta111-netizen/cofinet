const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(
    __dirname,
    ".."
);

function source(file) {
    return fs.readFileSync(
        path.join(
            root,
            "js",
            file
        ),
        "utf8"
    );
}

const api = source("api.js");
const checkout = source("checkout.js");
const app = source("app.js");

test(
    "kiosk real no envia simulated_outcome",
    () => {
        assert.doesNotMatch(
            app,
            /simulated_outcome/
        );

        assert.doesNotMatch(
            app,
            /payment_outcome/
        );

        assert.doesNotMatch(
            api,
            /simulated_outcome/
        );
    }
);

test(
    "kiosk conserva PAYMENT_PROCESSING",
    () => {
        assert.match(
            checkout,
            /PAYMENT_PROCESSING/
        );

        assert.match(
            app,
            /PAYMENT_PROCESSING/
        );
    }
);

test(
    "frontend nunca contiene Access Token",
    () => {
        const all =
            `${api}\n${checkout}\n${app}`;

        assert.doesNotMatch(
            all,
            /MERCADOPAGO_ACCESS_TOKEN/
        );
    }
);

test(
    "frontend nunca hardcodea terminal Point",
    () => {
        const all =
            `${api}\n${checkout}\n${app}`;

        assert.doesNotMatch(
            all,
            /NEWLAND_N950__N950NCD500197607/
        );
    }
);
