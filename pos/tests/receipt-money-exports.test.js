const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function loadReceiptCore() {
    const source = fs.readFileSync(
        path.resolve(
            __dirname,
            "../js/receipt-core.js"
        ),
        "utf8"
    );

    const context = {
        window: {},
        console,
        structuredClone:
            global.structuredClone,
        Date,
        Intl,
    };

    vm.createContext(context);

    vm.runInContext(
        source,
        context,
        {
            filename:
                "receipt-core.js",
        }
    );

    return context.window
        .CofiPosReceipt;
}

test(
    "receipt core exports money conversion helpers used by checkout",
    () => {
        const receipt =
            loadReceiptCore();

        assert.equal(
            typeof receipt.moneyToCents,
            "function",
            "moneyToCents must be exported"
        );

        assert.equal(
            typeof receipt.centsToMoney,
            "function",
            "centsToMoney must be exported"
        );
    }
);

test(
    "receipt money helpers convert checkout values exactly",
    () => {
        const receipt =
            loadReceiptCore();

        assert.equal(
            receipt.moneyToCents(
                "105.00",
                "amount"
            ),
            10500
        );

        assert.equal(
            receipt.centsToMoney(
                10500,
                "amount"
            ),
            "105.00"
        );
    }
);
