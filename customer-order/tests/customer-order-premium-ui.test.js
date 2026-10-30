const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function read(relativePath) {
    return fs.readFileSync(
        path.join(process.cwd(), relativePath),
        "utf8"
    );
}

const html = read(
    "customer-order/index.html"
);

const css = read(
    "customer-order/css/customer-order.css"
);

const app = read(
    "customer-order/js/app.js"
);


test(
    "premium shell usa hero visual oficial",
    () => {
        assert.match(
            html,
            /assets\/coficenter-hero-combo\.png/
        );

        assert.equal(
            fs.existsSync(
                path.join(
                    process.cwd(),
                    "customer-order/assets/coficenter-hero-combo.png"
                )
            ),
            true
        );

        assert.match(
            html,
            /class="start-art-image"/
        );
    }
);


test(
    "premium shell no conserva artefactos de bash",
    () => {
        assert.doesNotMatch(
            html,
            /-bash\.00/
        );

        assert.match(
            html,
            /\$0\.00/
        );
    }
);


test(
    "premium css define nueva capa visual",
    () => {
        assert.match(
            css,
            /COFICENTER CUSTOMER ORDER PREMIUM V1/
        );

        assert.match(
            css,
            /\.start-art-frame/
        );

        assert.match(
            css,
            /\.product-badge/
        );

        assert.match(
            css,
            /\.product-card:hover/
        );

        assert.match(
            css,
            /\.cart-review-button/
        );
    }
);


test(
    "tarjetas premium distinguen nombre precio y personalizacion",
    () => {
        assert.match(
            app,
            /product-name/
        );

        assert.match(
            app,
            /product-price/
        );

        assert.match(
            app,
            /Personalizable/
        );

        assert.match(
            app,
            /product-badge/
        );
    }
);


test(
    "premium mantiene hidden como estado autoritativo",
    () => {
        assert.match(
            css,
            /\[hidden\]\s*\{[\s\S]*?display:\s*none\s*!important/
        );
    }
);
