const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const rendererPath = path.join(
    ROOT,
    "js",
    "receipt-renderer.js"
);

function loadRenderer() {
    assert.equal(
        fs.existsSync(rendererPath),
        true,
        "receipt-renderer.js must exist"
    );

    const source =
        fs.readFileSync(
            rendererPath,
            "utf8"
        );

    const documentStub = {
        querySelector() {
            return null;
        },
        getElementById() {
            return null;
        },
        body: {
            classList: {
                add() {},
                remove() {},
            },
        },
    };

    const context = {
        window: {
            print() {},
        },
        document: documentStub,
        console,
        Intl,
        Date,
    };

    vm.createContext(context);
    vm.runInContext(
        source,
        context,
        {
            filename:
                "receipt-renderer.js",
        }
    );

    return context.window
        .CofiPosReceiptRenderer;
}

test(
    "receipt renderer exposes render/open/close/print",
    () => {
        const renderer =
            loadRenderer();

        assert.ok(renderer);

        for (
            const method of [
                "render",
                "open",
                "close",
                "print",
            ]
        ) {
            assert.equal(
                typeof renderer[method],
                "function",
                `${method} must be a function`
            );
        }
    }
);

test(
    "renderer source does not fetch or rebuild receipt data",
    () => {
        assert.equal(
            fs.existsSync(rendererPath),
            true,
            "receipt-renderer.js must exist"
        );

        const source =
            fs.readFileSync(
                rendererPath,
                "utf8"
            );

        assert.doesNotMatch(
            source,
            /\bfetch\s*\(/,
            "renderer must not fetch network data"
        );

        assert.doesNotMatch(
            source,
            /\.buildSnapshot\s*\(/,
            "renderer must not rebuild snapshots"
        );

        assert.doesNotMatch(
            source,
            /syncPending\s*\(/,
            "renderer must not trigger synchronization"
        );
    }
);

test(
    "renderer includes escaping for receipt text",
    () => {
        assert.equal(
            fs.existsSync(rendererPath),
            true,
            "receipt-renderer.js must exist"
        );

        const source =
            fs.readFileSync(
                rendererPath,
                "utf8"
            );

        assert.match(
            source,
            /escape/i,
            "renderer must escape configurable text"
        );
    }
);


function customerReceiptSnapshot({
    quantity = 1,
} = {}) {
    return {
        schema_version: 1,
        order_uuid:
            "11111111-1111-4111-8111-111111111111",

        folio:
            "CF-260910-ABCDEFGH",

        sold_at:
            "2026-09-10T20:00:00.000Z",

        currency:
            "MXN",

        business: {
            business_name:
                "CofiCenter",
        },

        branch: {
            branch_code:
                "nuevo-vallarta",

            branch_name:
                "Nuevo Vallarta",

            timezone:
                "America/Bahia_Banderas",
        },

        terminal: {
            terminal_id:
                "test-terminal",
        },

        customer: null,

        items: [
            {
                product_id: 1,

                product_name:
                    "Chilaquiles",

                quantity,

                /*
                 * Final unit price:
                 * base 115 + Huevo 20 = 135.
                 */
                unit_price_cents:
                    13500,

                line_total_cents:
                    13500 * quantity,

                modifiers: [
                    {
                        modifier_group_id:
                            1,

                        modifier_option_id:
                            1,

                        group_name:
                            "Salsa",

                        option_name:
                            "Salsa roja",

                        price_delta_cents:
                            0,
                    },

                    {
                        modifier_group_id:
                            2,

                        modifier_option_id:
                            2,

                        group_name:
                            "Extras",

                        option_name:
                            "Huevo",

                        price_delta_cents:
                            2000,
                    },
                ],
            },
        ],

        totals: {
            subtotal_cents:
                13500 * quantity,

            discount_cents:
                0,

            tax_mode:
                "NONE",

            tax_rate:
                "0",

            tax_cents:
                0,

            tip_cents:
                0,

            total_cents:
                13500 * quantity,
        },

        payment: {
            method:
                "CASH",

            amount_cents:
                13500 * quantity,

            amount_tendered_cents:
                13500 * quantity,

            change_due_cents:
                0,
        },
    };
}


test(
    "customer receipt hides zero-price preparation modifiers",
    () => {
        const renderer =
            loadRenderer();

        const html =
            renderer.render(
                customerReceiptSnapshot()
            );

        assert.doesNotMatch(
            html,
            /Salsa roja/,
            "zero-price preparation choices must stay off the customer receipt"
        );

        assert.match(
            html,
            /Huevo/,
            "paid complements must remain visible on the customer receipt"
        );
    }
);


test(
    "customer receipt splits final price into base product plus paid complements",
    () => {
        const renderer =
            loadRenderer();

        const html =
            renderer.render(
                customerReceiptSnapshot({
                    quantity: 2,
                })
            )
            .replace(
                /\s+/g,
                " "
            );

        assert.match(
            html,
            /receipt-item-main[^>]*>.*?2 ×.*?Chilaquiles.*?\$230\.00/,
            "two Chilaquiles must show base 115 x 2 = 230 on the product line"
        );

        assert.match(
            html,
            /receipt-modifier.*?Huevo.*?\$40\.00/,
            "paid complement must show 20 x 2 = 40 separately"
        );
    }
);
