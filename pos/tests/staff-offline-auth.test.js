const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { webcrypto } = require("node:crypto");

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

function createFixture() {
    const records = new Map();

    let online = true;

    let activeShift = {
        shift_uuid: "shift-existing",
        status: "OPEN",
    };

    let apiCalls = 0;
    let lastPersisted = null;
    let rejectNextAuth = false;

    const db = {
        async putStaffVerifier(record) {
            lastPersisted =
                structuredClone(record);

            records.set(
                `${record.terminal_id}:${record.staff_id}`,
                structuredClone(record)
            );
        },

        async deleteStaffVerifier(
            terminalId,
            staffId
        ) {
            records.delete(
                `${terminalId}:${staffId}`
            );
        },

        async getStaffVerifier(
            terminalId,
            staffId
        ) {
            return records.get(
                `${terminalId}:${staffId}`
            ) || null;
        },
    };

    const api = {
        async unlockStaff(
            staffId,
            pin
        ) {
            apiCalls += 1;

            assert.equal(
                pin,
                "2468"
            );

            if (rejectNextAuth) {
                rejectNextAuth = false;

                const error =
                    new Error(
                        "Staff authorization rejected"
                    );

                error.status = 401;
                error.isHttpError = true;

                throw error;
            }

            return {
                staff_id: staffId,
                display_name: "Ana",
                role: "CASHIER",
                branch_code: "ixtapa",
                terminal_id: "POS-IXTAPA-01",
                access_token:
                    "temporary-online-access-token",
            };
        },
    };

    const createStaffSession =
        loadFactory();

    const session =
        createStaffSession({
            branchCode: "ixtapa",
            terminalId: "POS-IXTAPA-01",

            api,
            db,

            crypto: webcrypto,

            isOnline() {
                return online;
            },

            async getActiveShift() {
                return activeShift;
            },

            timers: {
                setTimeout() {
                    return 1;
                },
                clearTimeout() {},
            },
        });

    return {
        session,
        records,

        setOnline(value) {
            online = value;
        },

        setActiveShift(value) {
            activeShift = value;
        },

        apiCallCount() {
            return apiCalls;
        },

        rejectNextOnlineAuth() {
            rejectNextAuth = true;
        },

        lastPersisted() {
            return lastPersisted;
        },
    };
}

test(
    "previously authorized staff can unlock offline",
    async () => {
        const fixture =
            createFixture();

        await fixture.session.unlock(
            7,
            "2468"
        );

        assert.equal(
            fixture.apiCallCount(),
            1
        );

        fixture.session.lock();
        fixture.setOnline(false);

        assert.equal(
            await fixture.session
                .canUnlockOffline(
                    7,
                    "2468"
                ),
            true
        );

        const offlineSession =
            await fixture.session.unlock(
                7,
                "2468"
            );

        assert.equal(
            offlineSession.staff_id,
            7
        );

        assert.equal(
            offlineSession.offline,
            true
        );

        assert.equal(
            fixture.apiCallCount(),
            1,
            "offline unlock must not call server authorization"
        );
    }
);

test(
    "unseen staff cannot unlock offline",
    async () => {
        const fixture =
            createFixture();

        fixture.setOnline(false);

        assert.equal(
            await fixture.session
                .canUnlockOffline(
                    99,
                    "2468"
                ),
            false
        );
    }
);

test(
    "plaintext PIN and reusable server secret are not persisted",
    async () => {
        const fixture =
            createFixture();

        await fixture.session.unlock(
            7,
            "2468"
        );

        const persisted =
            fixture.lastPersisted();

        assert.ok(persisted);

        const serialized =
            JSON.stringify(persisted);

        assert.equal(
            serialized.includes("2468"),
            false
        );

        assert.equal(
            serialized.includes(
                "temporary-online-access-token"
            ),
            false
        );

        assert.equal(
            /pin_hash/i.test(serialized),
            false
        );

        assert.equal(
            /access_token/i.test(serialized),
            false
        );
    }
);

test(
    "offline unlock is rejected without a previously-open shift",
    async () => {
        const fixture =
            createFixture();

        await fixture.session.unlock(
            7,
            "2468"
        );

        fixture.session.lock();

        fixture.setActiveShift(null);
        fixture.setOnline(false);

        assert.equal(
            await fixture.session
                .canUnlockOffline(
                    7,
                    "2468"
                ),
            false
        );

        await assert.rejects(
            fixture.session.unlock(
                7,
                "2468"
            )
        );
    }
);

test(
    "server rejection invalidates previously cached offline verifier",
    async () => {
        const fixture =
            createFixture();

        await fixture.session.unlock(
            7,
            "2468"
        );

        fixture.session.lock();

        fixture.setOnline(true);

        fixture.rejectNextOnlineAuth?.();

        await assert.rejects(
            fixture.session.unlock(
                7,
                "2468"
            )
        );

        fixture.setOnline(false);

        assert.equal(
            await fixture.session
                .canUnlockOffline(
                    7,
                    "2468"
                ),
            false
        );
    }
);
