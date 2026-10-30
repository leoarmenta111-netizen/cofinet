const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const MODULE_PATH = path.resolve(
    __dirname,
    "../js/staff-session.js"
);

function loadFactory() {
    assert.equal(
        fs.existsSync(MODULE_PATH),
        true,
        "staff-session.js todavía no existe"
    );

    delete require.cache[MODULE_PATH];

    const feature = require(MODULE_PATH);

    assert.equal(
        typeof feature.createStaffSession,
        "function"
    );

    return feature.createStaffSession;
}

function fakeTimers() {
    let sequence = 0;
    const entries = [];

    return {
        entries,

        setTimeout(fn, ms) {
            sequence += 1;

            const entry = {
                id: sequence,
                fn,
                ms,
                cleared: false,
            };

            entries.push(entry);

            return entry.id;
        },

        clearTimeout(id) {
            const entry =
                entries.find(item => item.id === id);

            if (entry) {
                entry.cleared = true;
            }
        },
    };
}

function fixture() {
    const timers = fakeTimers();

    const createStaffSession =
        loadFactory();

    const session =
        createStaffSession({
            branchCode: "ixtapa",
            terminalId: "POS-IXTAPA-01",

            isOnline: () => true,

            getActiveShift: async () => ({
                shift_uuid: "shift-001",
                status: "OPEN",
            }),

            api: {
                async unlockStaff() {
                    return {
                        staff_id: 7,
                        display_name: "Ana",
                        role: "CASHIER",
                        branch_code: "ixtapa",
                        terminal_id: "POS-IXTAPA-01",
                        access_token: "temporary-token",
                    };
                },
            },

            db: {
                async putStaffVerifier() {},
                async getStaffVerifier() {
                    return null;
                },
            },

            timers,
        });

    return {
        session,
        timers,
    };
}

test(
    "manual lock preserves the current cart",
    async () => {
        const { session } = fixture();

        const cart = [
            {
                product_id: 10,
                quantity: 2,
            },
        ];

        await session.unlock(
            7,
            "2468"
        );

        session.lock();

        assert.deepEqual(
            cart,
            [
                {
                    product_id: 10,
                    quantity: 2,
                },
            ]
        );

        assert.equal(
            session.current(),
            null
        );
    }
);

test(
    "inactivity locks after exactly 5 minutes",
    async () => {
        const {
            session,
            timers,
        } = fixture();

        await session.unlock(
            7,
            "2468"
        );

        const activeTimer =
            timers.entries.at(-1);

        assert.equal(
            activeTimer.ms,
            5 * 60 * 1000
        );

        assert.notEqual(
            session.current(),
            null
        );

        activeTimer.fn();

        assert.equal(
            session.current(),
            null
        );
    }
);

test(
    "POS activity resets the inactivity timer",
    async () => {
        const {
            session,
            timers,
        } = fixture();

        await session.unlock(
            7,
            "2468"
        );

        const firstTimer =
            timers.entries.at(-1);

        session.resetActivityTimer();

        const secondTimer =
            timers.entries.at(-1);

        assert.equal(
            firstTimer.cleared,
            true
        );

        assert.notEqual(
            firstTimer.id,
            secondTimer.id
        );

        assert.equal(
            secondTimer.ms,
            5 * 60 * 1000
        );
    }
);
