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


test(
    "CLOSING shift reload restores reconciliation and can finalize",
    async () => {
        let closeCalls = 0;

        const api = {
            async getCurrentCashShift() {
                return {
                    shift_uuid: "shift-refresh-001",
                    status: "CLOSING",
                    opening_total: "1000.00",
                    counted_cash: "700.00",
                    expected_cash: "800.00",
                    difference: "-100.00",
                };
            },

            async finalizeCashShift() {
                closeCalls += 1;

                return {
                    shift_uuid: "shift-refresh-001",
                    status: "CLOSED",
                    opening_total: "1000.00",
                };
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

        const current =
            await shift.loadCurrent();

        assert.equal(
            current.status,
            "CLOSING"
        );

        const reconciliation =
            shift.reconciliation();

        assert.ok(
            reconciliation,
            "Reload must restore CLOSING reconciliation"
        );

        assert.equal(
            reconciliation.counted_cash,
            "700.00"
        );

        assert.equal(
            reconciliation.expected_cash,
            "800.00"
        );

        assert.equal(
            reconciliation.difference,
            "-100.00"
        );

        const closed =
            await shift.finalizeClose(
                {
                    staffId: 2,
                    pin: "9999",
                },
                "Diferencia validada"
            );

        assert.equal(
            closeCalls,
            1
        );

        assert.equal(
            closed.status,
            "CLOSED"
        );
    }
);


test(
    "opening cash control restores visible reconciliation for CLOSING shift",
    () => {
        const app =
            fs.readFileSync(
                path.resolve(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        const start =
            app.indexOf(
                "async function openCashControl()"
            );

        assert.notEqual(
            start,
            -1,
            "Falta openCashControl"
        );

        const end =
            app.indexOf(
                "async function handleCashOpening()",
                start
            );

        assert.notEqual(
            end,
            -1,
            "No se pudo aislar openCashControl"
        );

        const source =
            app.slice(
                start,
                end
            );

        assert.match(
            source,
            /state\.cashShift[\s\S]*?\.reconciliation\(\)/
        );

        assert.match(
            source,
            /showCashReconciliation\([\s\S]*?reconciliation/
        );
    }
);


test(
    "closing count marks cached shift CLOSING before server submission",
    () => {
        const app =
            fs.readFileSync(
                path.resolve(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        const start =
            app.indexOf(
                "async function handleClosingCount()"
            );

        assert.notEqual(
            start,
            -1,
            "Falta handleClosingCount"
        );

        const end =
            app.indexOf(
                "async function handleFinalClose()",
                start
            );

        assert.notEqual(
            end,
            -1,
            "No se pudo aislar handleClosingCount"
        );

        const source =
            app.slice(
                start,
                end
            );

        const persistIndex =
            source.indexOf(
                "persistCashShift("
            );

        const submitIndex =
            source.indexOf(
                ".submitClosingCount("
            );

        assert.notEqual(
            persistIndex,
            -1,
            "El cierre debe persistir estado local provisional"
        );

        assert.notEqual(
            submitIndex,
            -1,
            "Falta envío del conteo de cierre"
        );

        assert.match(
            source,
            /status:\s*"CLOSING"/
        );

        assert.ok(
            persistIndex < submitIndex,
            "El cache local debe quedar CLOSING antes de enviar el conteo al servidor"
        );
    }
);


test(
    "cash control keeps movement and closing actions collapsed by default",
    () => {
        const html =
            fs.readFileSync(
                path.resolve(
                    __dirname,
                    "../index.html"
                ),
                "utf8"
            );

        assert.match(
            html,
            /<section id="cash-movement-panel"[\s\S]*?<details class="cash-action-disclosure"[\s\S]*?<summary>[\s\S]*Movimiento de caja[\s\S]*?<\/summary>/
        );

        assert.match(
            html,
            /<section id="cash-shift-closing"[\s\S]*?<details class="cash-action-disclosure"[\s\S]*?<summary>[\s\S]*Cerrar caja[\s\S]*?<\/summary>/
        );

        assert.doesNotMatch(
            html,
            /<details class="cash-action-disclosure"[^>]*\sopen(?:\s|>)/
        );
    }
);



test(
    "cash opening uses a single opening amount instead of denomination inputs",
    () => {
        const html =
            fs.readFileSync(
                path.resolve(
                    __dirname,
                    "../index.html"
                ),
                "utf8"
            );

        assert.match(
            html,
            /id="cash-opening-amount"/
        );

        const openingSection =
            html.match(
                /<section id="cash-shift-opening"[\s\S]*?<\/section>/
            )?.[0] || "";

        assert.doesNotMatch(
            openingSection,
            /data-denomination-cents/
        );

        assert.doesNotMatch(
            openingSection,
            /Total contado/
        );
    }
);

test(
    "operational connectivity trusts confirmed backend health over navigator.onLine",
    () => {
        const source =
            fs.readFileSync(
                path.resolve(
                    __dirname,
                    "../js/app.js"
                ),
                "utf8"
            );

        const match =
            source.match(
                /function operationalOnline\(\)\s*\{([\s\S]*?)\n\s*\}/
            );

        assert.ok(
            match,
            "operationalOnline function must exist"
        );

        assert.match(
            match[1],
            /state\.cloudOnline\s*===\s*true/
        );

        assert.doesNotMatch(
            match[1],
            /navigator\.onLine/
        );
    }
);
