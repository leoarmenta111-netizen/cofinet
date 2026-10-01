const fs = require("node:fs");
const test = require("node:test");
const assert = require("node:assert/strict");

const app = fs.readFileSync(
    "customer-order/js/app.js",
    "utf8"
);

test(
    "producto solo se selecciona desde boton mas",
    () => {
        assert.match(
            app,
            /document\.createElement\(\s*"article"\s*\)/
        );

        assert.match(
            app,
            /add\.addEventListener\(\s*"click"/
        );

        assert.match(
            app,
            /selectProduct\(product\)/
        );

        assert.doesNotMatch(
            app,
            /card\.addEventListener\(\s*"click"/
        );
    }
);
