const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");

const path =
    require("node:path");

const test =
    require("node:test");


const html =
    fs.readFileSync(
        path.join(
            process.cwd(),
            "pos/papeleria/index.html"
        ),
        "utf8"
    );

const app =
    fs.readFileSync(
        path.join(
            process.cwd(),
            "pos/js/retail-app.js"
        ),
        "utf8"
    );


test(
    "sales workflow module loads before retail app",
    () => {
        const sales =
            html.indexOf(
                'src="../js/retail-sales.js"'
            );

        const appIndex =
            html.indexOf(
                'src="../js/retail-app.js"'
            );

        assert.notEqual(
            sales,
            -1
        );

        assert.notEqual(
            appIndex,
            -1
        );

        assert.ok(
            sales < appIndex
        );
    }
);


test(
    "payment modal has cash and card workflow fields",
    () => {
        assert.match(
            html,
            /id=["']retail-payment-modal["']/
        );

        assert.match(
            html,
            /id=["']retail-payment-title["']/
        );

        assert.match(
            html,
            /id=["']retail-amount-tendered["']/
        );

        assert.match(
            html,
            /id=["']retail-card-reference["']/
        );

        assert.match(
            html,
            /id=["']retail-payment-confirm["']/
        );

        assert.match(
            html,
            /id=["']retail-payment-cancel["']/
        );
    }
);


test(
    "receipt modal exists",
    () => {
        assert.match(
            html,
            /id=["']retail-receipt-modal["']/
        );

        assert.match(
            html,
            /id=["']retail-receipt-body["']/
        );

        assert.match(
            html,
            /id=["']retail-receipt-close["']/
        );
    }
);


test(
    "app wires held sale API",
    () => {
        assert.match(
            app,
            /\.holdSale\s*\(/
        );

        assert.match(
            app,
            /\.listHeldSales\s*\(/
        );

        assert.match(
            app,
            /\.updateHeldSale\s*\(/
        );
    }
);


test(
    "app wires hold and held sales controls",
    () => {
        assert.match(
            app,
            /retail-hold-sale/
        );

        assert.match(
            app,
            /retail-held-sales/
        );
    }
);


test(
    "app wires cash and card checkout controls",
    () => {
        assert.match(
            app,
            /retail-pay-cash/
        );

        assert.match(
            app,
            /retail-pay-card/
        );

        assert.match(
            app,
            /\.checkout\s*\(/
        );
    }
);


test(
    "app retrieves immutable receipt after checkout",
    () => {
        assert.match(
            app,
            /\.receipt\s*\(/
        );

        assert.match(
            app,
            /retail-receipt-body/
        );
    }
);


test(
    "app explicitly consumes authoritative server total",
    () => {
        assert.match(
            app,
            /CofiRetailSales/
        );

        assert.match(
            app,
            /\.serverTotal\s*\(/
        );
    }
);
