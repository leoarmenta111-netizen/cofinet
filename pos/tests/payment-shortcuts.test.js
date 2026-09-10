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

test("orden actual muestra metodos rapidos de pago", () => {
    assert.match(html, /class="payment-shortcuts"/);
    assert.match(html, /data-quick-payment="CASH"/);
    assert.match(html, /data-quick-payment="CARD_EXTERNAL"/);
    assert.match(html, />Mixto</);
    assert.match(html, />Más</);

    assert.match(
        css,
        /\.payment-shortcuts\s*\{/
    );
});
