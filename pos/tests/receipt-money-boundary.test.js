const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const appPath = path.resolve(
    __dirname,
    "../js/app.js"
);

function appSource() {
    return fs.readFileSync(
        appPath,
        "utf8"
    );
}

test(
    "checkout canonicalizes cart total before moneyToCents",
    () => {
        const source =
            appSource();

        assert.doesNotMatch(
            source,
            /\.moneyToCents\(\s*cartTotal\(\)\s*\)/,
            "cartTotal number must not be passed directly to moneyToCents"
        );

        assert.match(
            source,
            /\.moneyToCents\(\s*canonicalMoneyString\(\s*cartTotal\(\)/,
            "cart total must be normalized to a two-decimal string"
        );
    }
);

test(
    "cash input is canonicalized before moneyToCents",
    () => {
        const source =
            appSource();

        assert.match(
            source,
            /canonicalMoneyString\([\s\S]*?#cash-received/,
            "cash input must pass through canonicalMoneyString"
        );
    }
);

test(
    "receipt item prices are canonicalized before moneyToCents",
    () => {
        const source =
            appSource();

        assert.match(
            source,
            /\.moneyToCents\(\s*canonicalMoneyString\(\s*item\.unit_price/,
            "item unit price must be normalized"
        );

        assert.match(
            source,
            /\.moneyToCents\(\s*canonicalMoneyString\(\s*modifier\.price_delta/,
            "modifier price delta must be normalized"
        );
    }
);
