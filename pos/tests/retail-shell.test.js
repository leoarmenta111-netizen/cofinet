const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(
    __dirname,
    "..",
    ".."
);

function read(relativePath) {
    return fs.readFileSync(
        path.join(ROOT, relativePath),
        "utf8"
    );
}

test(
    "papeleria has an isolated operational shell",
    () => {
        const filename =
            path.join(
                ROOT,
                "pos/papeleria/index.html"
            );

        assert.equal(
            fs.existsSync(filename),
            true,
            "pos/papeleria/index.html must exist"
        );

        const html = read(
            "pos/papeleria/index.html"
        );

        assert.match(
            html,
            /COFI\s+Papeler[ií]a/i
        );

        assert.match(
            html,
            /PAPELERIA/
        );
    }
);

test(
    "papeleria reuses shared staff and cash infrastructure but has its own retail modules",
    () => {
        const html = read(
            "pos/papeleria/index.html"
        );

        assert.match(
            html,
            /\.\.\/js\/api\.js/
        );

        assert.match(
            html,
            /\.\.\/js\/staff-session\.js/
        );

        assert.match(
            html,
            /\.\.\/js\/cash-shift\.js/
        );

        assert.match(
            html,
            /\.\.\/js\/retail-api\.js/
        );

        assert.match(
            html,
            /\.\.\/js\/retail-cart\.js/
        );

        assert.match(
            html,
            /\.\.\/js\/retail-app\.js/
        );
    }
);

test(
    "papeleria shell exposes cashier retail workflow regions",
    () => {
        const html = read(
            "pos/papeleria/index.html"
        );

        const requiredIds = [
            "retail-search",
            "retail-product-grid",
            "retail-cart",
            "retail-cart-lines",
            "retail-cart-total",
            "retail-hold-sale",
            "retail-held-sales",
            "retail-pay-cash",
            "retail-pay-card",
            "retail-manager-modal",
        ];

        for (const id of requiredIds) {
            assert.match(
                html,
                new RegExp(
                    `id=["']${id}["']`
                ),
                `missing #${id}`
            );
        }
    }
);

test(
    "papeleria shell is separate from cafe index",
    () => {
        const cafe = read(
            "pos/index.html"
        );

        const papeleria = read(
            "pos/papeleria/index.html"
        );

        assert.notEqual(
            papeleria,
            cafe,
            "Papeleria must not be a copy of the Cafe shell"
        );
    }
);
