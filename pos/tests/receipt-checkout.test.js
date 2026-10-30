const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");


global.window = {};

delete require.cache[
    require.resolve("../js/receipt-core.js")
];

require("../js/receipt-core.js");

const receiptCore =
    window.CofiPosReceipt;

const appSource =
    fs.readFileSync(
        path.join(
            __dirname,
            "../js/app.js"
        ),
        "utf8"
    );


function extractFunction(
    source,
    name
) {
    const marker =
        `function ${name}`;

    const start =
        source.indexOf(marker);

    assert.ok(
        start >= 0,
        `${name} must exist`
    );

    const paramsStart =
        source.indexOf(
            "(",
            start
        );

    assert.ok(
        paramsStart >= 0,
        `${name} parameters must exist`
    );

    let parenDepth = 0;
    let paramsEnd = -1;

    for (
        let index = paramsStart;
        index < source.length;
        index += 1
    ) {
        const char =
            source[index];

        if (char === "(") {
            parenDepth += 1;
        }

        if (char === ")") {
            parenDepth -= 1;

            if (parenDepth === 0) {
                paramsEnd = index;
                break;
            }
        }
    }

    assert.ok(
        paramsEnd >= 0,
        `${name} parameter list must close`
    );

    const bodyStart =
        source.indexOf(
            "{",
            paramsEnd
        );

    assert.ok(
        bodyStart >= 0,
        `${name} body must exist`
    );

    let depth = 0;

    for (
        let index = bodyStart;
        index < source.length;
        index += 1
    ) {
        const char =
            source[index];

        if (char === "{") {
            depth += 1;
        }

        if (char === "}") {
            depth -= 1;

            if (depth === 0) {
                return source.slice(
                    start,
                    index + 1
                );
            }
        }
    }

    throw new Error(
        `${name} closing brace not found`
    );
}


function loadCalculator() {
    const functionSource =
        extractFunction(
            appSource,
            "calculateCheckoutTotals"
        );

    return vm.runInNewContext(
        `(${functionSource})`,
        {
            window: {
                CofiPosReceipt:
                    receiptCore,
            },
        }
    );
}


function settings(
    taxMode,
    taxRate
) {
    return {
        tax_mode:
            taxMode,
        tax_rate:
            taxRate,
    };
}


test(
    "checkout totals use receipt-core as the tax calculator",
    () => {
        const functionSource =
            extractFunction(
                appSource,
                "calculateCheckoutTotals"
            );

        assert.match(
            functionSource,
            /CofiPosReceipt\s*\.\s*calculateTax\s*\(/
        );
    }
);


test(
    "NONE keeps tax at zero",
    () => {
        const calculate =
            loadCalculator();

        const result =
            calculate({
                merchandiseCents:
                    10000,
                discountCents:
                    0,
                tipCents:
                    0,
                receiptSettings:
                    settings(
                        "NONE",
                        0
                    ),
            });

        assert.deepEqual(
            JSON.parse(
                JSON.stringify(
                    result
                )
            ),
            {
                subtotalCents:
                    10000,
                discountCents:
                    0,
                taxMode:
                    "NONE",
                taxRate:
                    0,
                taxCents:
                    0,
                tipCents:
                    0,
                totalCents:
                    10000,
            }
        );
    }
);


test(
    "INCLUDED exposes tax without adding it again",
    () => {
        const calculate =
            loadCalculator();

        const result =
            calculate({
                merchandiseCents:
                    10000,
                discountCents:
                    0,
                tipCents:
                    0,
                receiptSettings:
                    settings(
                        "INCLUDED",
                        0.16
                    ),
            });

        assert.equal(
            result.taxCents,
            1379
        );

        assert.equal(
            result.totalCents,
            10000
        );
    }
);


test(
    "ADDED increases amount due by calculated tax",
    () => {
        const calculate =
            loadCalculator();

        const result =
            calculate({
                merchandiseCents:
                    10000,
                discountCents:
                    0,
                tipCents:
                    0,
                receiptSettings:
                    settings(
                        "ADDED",
                        0.16
                    ),
            });

        assert.equal(
            result.taxCents,
            1600
        );

        assert.equal(
            result.totalCents,
            11600
        );
    }
);


test(
    "tip is applied after tax",
    () => {
        const calculate =
            loadCalculator();

        const result =
            calculate({
                merchandiseCents:
                    10000,
                discountCents:
                    0,
                tipCents:
                    1500,
                receiptSettings:
                    settings(
                        "ADDED",
                        0.16
                    ),
            });

        assert.equal(
            result.taxCents,
            1600
        );

        assert.equal(
            result.tipCents,
            1500
        );

        assert.equal(
            result.totalCents,
            13100
        );
    }
);


test(
    "discount is applied consistently with receipt-core arithmetic",
    () => {
        const calculate =
            loadCalculator();

        const result =
            calculate({
                merchandiseCents:
                    10000,
                discountCents:
                    2000,
                tipCents:
                    0,
                receiptSettings:
                    settings(
                        "ADDED",
                        0.16
                    ),
            });

        assert.equal(
            result.subtotalCents,
            10000
        );

        assert.equal(
            result.discountCents,
            2000
        );

        assert.equal(
            result.taxCents,
            1280
        );

        assert.equal(
            result.totalCents,
            9280
        );
    }
);


test(
    "payment modal freezes checkout totals in cents",
    () => {
        const source =
            extractFunction(
                appSource,
                "openPayment"
            );

        assert.match(
            source,
            /state\.paymentCheckoutTotals\s*=/
        );

        assert.match(
            source,
            /calculateCheckoutTotals\s*\(/
        );

        assert.match(
            source,
            /CofiPosReceipt\s*\.\s*moneyToCents\s*\(/
        );

        assert.match(
            source,
            /state\.paymentCheckoutTotals[\s\S]*?totalCents/
        );
    }
);


test(
    "payment amount due displays frozen checkout total",
    () => {
        const source =
            extractFunction(
                appSource,
                "openPayment"
            );

        assert.match(
            source,
            /payment-total/
        );

        assert.match(
            source,
            /confirm-payment-total/
        );

        const cartTotalCalls =
            (
                source.match(
                    /cartTotal\s*\(\s*\)/g
                ) || []
            ).length;

        assert.equal(
            cartTotalCalls,
            1,
            "openPayment may read merchandise total once, not recalculate amount due"
        );

        assert.match(
            source,
            /paymentCheckoutTotals[\s\S]*?totalCents/
        );
    }
);


test(
    "cash change uses the same frozen payment total cents",
    () => {
        const source =
            extractFunction(
                appSource,
                "updateChange"
            );

        assert.match(
            source,
            /CofiPosReceipt\s*\.\s*moneyToCents\s*\(/
        );

        assert.match(
            source,
            /state\.paymentCheckoutTotals/
        );

        assert.match(
            source,
            /totalCents/
        );

        assert.doesNotMatch(
            source,
            /cartTotal\s*\(/
        );
    }
);


function confirmPaymentSource() {
    return extractFunction(
        appSource,
        "confirmPayment"
    );
}


function matchCount(
    source,
    pattern
) {
    return (
        source.match(pattern) ||
        []
    ).length;
}


test(
    "paid sale generates exactly one local public folio",
    () => {
        const source =
            confirmPaymentSource();

        assert.equal(
            matchCount(
                source,
                /CofiPosFolio\s*\.\s*generate\s*\(/g
            ),
            1,
            "folio must be generated exactly once during finalization"
        );

        assert.doesNotMatch(
            source,
            /LOCAL-\$\{/
        );

        assert.doesNotMatch(
            source,
            /response\s*\.\s*folio/
        );
    }
);


test(
    "paid sale builds and validates exactly one receipt snapshot",
    () => {
        const source =
            confirmPaymentSource();

        assert.equal(
            matchCount(
                source,
                /CofiPosReceipt\s*\.\s*buildSnapshot\s*\(/g
            ),
            1,
            "snapshot must be built exactly once"
        );

        assert.equal(
            matchCount(
                source,
                /CofiPosReceipt\s*\.\s*validateSnapshot\s*\(/g
            ),
            1,
            "frozen snapshot must be validated before persistence"
        );

        assert.match(
            source,
            /receipt_snapshot/
        );

        assert.match(
            source,
            /\bfolio\b/
        );
    }
);


test(
    "local finalization completes before remote synchronization and success UI",
    () => {
        const source =
            confirmPaymentSource();

        const finalizeIndex =
            source.indexOf(
                ".finalizePaidSale("
            );

        const syncIndex =
            source.indexOf(
                ".syncPending("
            );

        const successIndex =
            source.indexOf(
                "showSaleSuccess("
            );

        assert.ok(
            finalizeIndex >= 0,
            "confirmPayment must call finalizePaidSale"
        );

        assert.ok(
            syncIndex > finalizeIndex,
            "remote synchronization must happen after local finalization"
        );

        assert.ok(
            successIndex > finalizeIndex,
            "success UI must happen after local finalization"
        );
    }
);


test(
    "confirmPayment never sends the sale directly before local persistence",
    () => {
        const source =
            confirmPaymentSource();

        assert.doesNotMatch(
            source,
            /CofiPosAPI[\s\S]*?createOrder\s*\(/
        );

        assert.match(
            source,
            /CofiPosDB[\s\S]*?finalizePaidSale\s*\(/
        );
    }
);


test(
    "success state exposes the locally frozen folio and receipt",
    () => {
        const source =
            confirmPaymentSource();

        const successCall =
            source.slice(
                source.indexOf(
                    "showSaleSuccess("
                )
            );

        assert.match(
            successCall,
            /\bfolio\b/
        );

        assert.match(
            successCall,
            /receipt/
        );

        assert.doesNotMatch(
            successCall,
            /response\s*\.\s*folio/
        );

        assert.doesNotMatch(
            successCall,
            /LOCAL-/
        );
    }
);



test("receipt modules load before app boot", () => {
    const html = fs.readFileSync(
        path.join(
            __dirname,
            "..",
            "index.html"
        ),
        "utf8"
    );

    const folioIndex =
        html.indexOf(
            "./js/folio.js"
        );

    const receiptCoreIndex =
        html.indexOf(
            "./js/receipt-core.js"
        );

    const appIndex =
        html.indexOf(
            "./js/app.js"
        );

    assert.ok(
        folioIndex >= 0,
        "index.html must load folio.js"
    );

    assert.ok(
        receiptCoreIndex >= 0,
        "index.html must load receipt-core.js"
    );

    assert.ok(
        appIndex >= 0,
        "index.html must load app.js"
    );

    assert.ok(
        folioIndex < appIndex,
        "folio.js must load before app.js"
    );

    assert.ok(
        receiptCoreIndex < appIndex,
        "receipt-core.js must load before app.js"
    );
});


test("service worker precaches receipt modules with bumped shell version", () => {
    const sw = fs.readFileSync(
        path.join(
            __dirname,
            "..",
            "sw.js"
        ),
        "utf8"
    );

    assert.match(
        sw,
        /const SHELL_CACHE = "cofi-pos-shell-v25";/,
        "receipt wiring must use current shell cache v23"
    );

    assert.match(
        sw,
        /["']\.\/js\/folio\.js["']/,
        "service worker must precache folio.js"
    );

    assert.match(
        sw,
        /["']\.\/js\/receipt-core\.js["']/,
        "service worker must precache receipt-core.js"
    );
});
