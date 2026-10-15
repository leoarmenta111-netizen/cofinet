const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const MODULE_PATH = path.resolve(
    __dirname,
    "../js/cash-shift.js"
);

const HTML_PATH = path.resolve(
    __dirname,
    "../index.html"
);

function loadFactory() {
    assert.equal(
        fs.existsSync(MODULE_PATH),
        true,
        "cash-shift.js todavía no existe"
    );

    delete require.cache[MODULE_PATH];

    const feature = require(MODULE_PATH);

    assert.equal(
        typeof feature.createCashShift,
        "function"
    );

    return feature.createCashShift;
}

function fixture() {
    const calls = {
        open: 0,
        close: 0,
    };

    const api = {
        async getCurrentCashShift() {
            return {
                shift_uuid: "shift-001",
                status: "OPEN",
                opening_total: "1000.00",
            };
        },

        async openCashShift(payload) {
            calls.open += 1;

            return {
                shift_uuid: "shift-001",
                status: "OPEN",
                opening_total: "1000.00",
                payload,
            };
        },

        async submitCashClosingCount() {
            return {
                shift_uuid: "shift-001",
                status: "CLOSING",
                counted_cash: "700.00",
                expected_cash: "800.00",
                difference: "-100.00",
            };
        },

        async finalizeCashShift() {
            calls.close += 1;

            return {
                shift_uuid: "shift-001",
                status: "CLOSED",
            };
        },

        async recordCashMovement(payload) {
            return payload;
        },
    };

    const staffSession = {
        current() {
            return {
                staff_id: 7,
                role: "CASHIER",
                access_token: "token",
            };
        },
    };

    const createCashShift =
        loadFactory();

    const shift =
        createCashShift({
            api,
            staffSession,
            isOnline: () => true,
        });

    return {
        shift,
        calls,
    };
}

test(
    "opening UI has no default or editable manual cash amount",
    () => {
        const html =
            fs.readFileSync(
                HTML_PATH,
                "utf8"
            );

        assert.match(
            html,
            /id="cash-shift-opening"/
        );

        [
            100,
            200,
            500,
            1000,
            2000,
            5000,
            10000,
            20000,
            50000,
            100000,
        ].forEach(value => {
            assert.match(
                html,
                new RegExp(
                    `data-denomination-cents="${value}"`
                )
            );
        });

        assert.doesNotMatch(
            html,
            /id="opening-manual-total"/
        );

        assert.doesNotMatch(
            html,
            /data-default-opening-amount/
        );
    }
);

test(
    "denomination quantities calculate the displayed total",
    () => {
        const { shift } = fixture();

        const total =
            shift.calculateDenominationTotal([
                {
                    denomination_cents: 50000,
                    quantity: 2,
                },
                {
                    denomination_cents: 20000,
                    quantity: 1,
                },
                {
                    denomination_cents: 1000,
                    quantity: 3,
                },
            ]);

        assert.equal(
            total,
            1230
        );
    }
);

test(
    "Manager authorization is required to open shift",
    async () => {
        const {
            shift,
            calls,
        } = fixture();

        await assert.rejects(
            shift.open(
                [
                    {
                        denomination_cents: 50000,
                        quantity: 2,
                    },
                ],
                null
            )
        );

        assert.equal(
            calls.open,
            0
        );
    }
);

test(
    "expected cash remains hidden before closing-count submission",
    async () => {
        const { shift } = fixture();

        const current =
            await shift.loadCurrent();

        assert.equal(
            Object.hasOwn(
                current,
                "expected_cash"
            ),
            false
        );

        assert.equal(
            Object.hasOwn(
                current,
                "difference"
            ),
            false
        );
    }
);

test(
    "reconciliation appears only after closing count submission",
    async () => {
        const source =
            fs.readFileSync(
                MODULE_PATH,
                "utf8"
            );

        const html =
            fs.readFileSync(
                HTML_PATH,
                "utf8"
            );

        assert.match(
            html,
            /id="cash-reconciliation"[^>]*hidden/
        );

        assert.match(
            source,
            /submitClosingCount/
        );

        assert.match(
            source,
            /showReconciliation/
        );

        const { shift } = fixture();

        await shift.loadCurrent();

        assert.equal(
            shift.reconciliation(),
            null
        );

        const reconciliation =
            await shift.submitClosingCount([
                {
                    denomination_cents: 50000,
                    quantity: 1,
                },
                {
                    denomination_cents: 20000,
                    quantity: 1,
                },
            ]);

        assert.equal(
            reconciliation.expected_cash,
            "800.00"
        );

        assert.equal(
            shift.reconciliation()
                .difference,
            "-100.00"
        );
    }
);

test(
    "difference note is required when reconciliation has variance",
    async () => {
        const {
            shift,
            calls,
        } = fixture();

        await shift.loadCurrent();

        await shift.submitClosingCount([
            {
                denomination_cents: 50000,
                quantity: 1,
            },
            {
                denomination_cents: 20000,
                quantity: 1,
            },
        ]);

        await assert.rejects(
            shift.finalizeClose(
                {
                    staffId: 2,
                    pin: "9999",
                },
                ""
            )
        );

        assert.equal(
            calls.close,
            0
        );
    }
);
