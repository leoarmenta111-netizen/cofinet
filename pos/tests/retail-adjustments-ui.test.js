const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const html =
    fs.readFileSync(
        "pos/papeleria/index.html",
        "utf8"
    );

const app =
    fs.readFileSync(
        "pos/js/retail-app.js",
        "utf8"
    );


test(
    "retail adjustments module loads before app",
    () => {
        const adjustments =
            html.indexOf(
                "/pos/js/retail-adjustments.js"
            );

        const retailApp =
            html.indexOf(
                "/pos/js/retail-app.js"
            );

        assert.ok(
            adjustments >= 0,
            "retail-adjustments.js must load"
        );

        assert.ok(
            retailApp > adjustments,
            "adjustments module must load before app"
        );
    }
);


test(
    "receipt exposes return and cancellation actions",
    () => {
        assert.match(
            html,
            /id=["']retail-return-sale["']/
        );

        assert.match(
            html,
            /id=["']retail-cancel-sale["']/
        );
    }
);


test(
    "return modal has line selection and reason",
    () => {
        for (
            const id
            of [
                "retail-return-modal",
                "retail-return-lines",
                "retail-return-reason",
                "retail-return-refund-method",
                "retail-return-external-reference",
                "retail-return-confirm",
                "retail-return-close",
            ]
        ) {
            assert.match(
                html,
                new RegExp(
                    `id=["']${id}["']`
                )
            );
        }
    }
);


test(
    "manager authorization modal remains available",
    () => {
        assert.match(
            html,
            /id=["']retail-manager-modal["']/
        );
    }
);


test(
    "app calls returnItems API",
    () => {
        assert.match(
            app,
            /\.returnItems\s*\(/
        );
    }
);


test(
    "app calls cancelSale API",
    () => {
        assert.match(
            app,
            /\.cancelSale\s*\(/
        );
    }
);


test(
    "app builds return payload through adjustment domain module",
    () => {
        assert.match(
            app,
            /CofiRetailAdjustments/
        );

        assert.match(
            app,
            /\.buildReturnPayload\s*\(/
        );
    }
);


test(
    "app builds cancellation payload through adjustment domain module",
    () => {
        assert.match(
            app,
            /\.buildCancellationPayload\s*\(/
        );
    }
);
