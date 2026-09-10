const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");

const html = fs.readFileSync(
    path.join(ROOT, "index.html"),
    "utf8"
);

const css = fs.readFileSync(
    path.join(ROOT, "css", "pos.css"),
    "utf8"
);

test("modal de cobro usa diseño profesional CofiCenter", () => {
    assert.match(
        html,
        /class="modal-card payment-card payment-card-professional"/
    );

    assert.match(
        html,
        /class="payment-total-professional"/
    );

    assert.match(
        html,
        /class="payment-section-label"/
    );

    assert.match(
        html,
        /class="payment-confirmation-note"/
    );

    assert.match(
        css,
        /PROFESSIONAL PAYMENT MODAL/
    );

    assert.match(
        css,
        /\.payment-card-professional\s*\{/
    );

    assert.match(
        css,
        /\.payment-total-professional\s*\{/
    );
});
