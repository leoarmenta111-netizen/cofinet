const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    return fs.readFileSync(
        path,
        "utf8"
    );
}

test(
    "POS loads the delivered-state Orders code with a new URL version",
    () => {
        const html = read(
            "pos/index.html"
        );

        assert.ok(
            html.includes(
                './js/orders.js?v=17'
            ),
            "orders.js debe usar la version v17"
        );
    }
);

test(
    "POS service worker keeps orders.js as an unversioned shell asset",
    () => {
        const sw = read(
            "pos/sw.js"
        );

        assert.ok(
            sw.includes(
                '"./js/orders.js"'
            )
        );

        assert.match(
            sw,
            /await caches\.match\(request\)/
        );

        assert.match(
            sw,
            /await fetch\(request\)/
        );
    }
);
