const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    return fs.readFileSync(
        path,
        "utf8"
    );
}

const html = read("pos/index.html");
const app = read("pos/js/app.js");
const api = read("pos/js/api.js");
const db = read("pos/js/db.js");
const sw = read("pos/sw.js");

test(
    "POS starts with operational employee lock screen",
    () => {
        [
            'id="staff-lock-screen"',
            'id="staff-unlock-form"',
            'id="staff-id"',
            'id="staff-pin"',
            'id="staff-unlock-submit"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });

        assert.match(
            html,
            /id="staff-lock-screen"(?![^>]*hidden)/
        );
    }
);

test(
    "topbar shows active employee and explicit Lock action",
    () => {
        [
            'id="operator-name"',
            'id="operator-role"',
            'id="active-shift-status"',
            'id="staff-lock-button"',
            'id="cash-control-button"',
        ].forEach(marker => {
            assert.ok(
                html.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);

test(
    "staff and cash modules load before app",
    () => {
        const staffIndex =
            html.indexOf(
                "./js/staff-session.js"
            );

        const cashIndex =
            html.indexOf(
                "./js/cash-shift.js?v=2"
            );

        const appIndex =
            html.indexOf(
                "./js/app.js"
            );

        assert.ok(staffIndex >= 0);
        assert.ok(cashIndex >= 0);

        assert.ok(
            staffIndex < appIndex
        );

        assert.ok(
            cashIndex < appIndex
        );
    }
);

test(
    "POS API exposes authenticated staff and cash endpoints",
    () => {
        [
            "function unlockStaff",
            "function getStaffSession",
            "function getCurrentCashShift",
            "function openCashShift",
            "function recordCashMovement",
            "function submitCashClosingCount",
            "function finalizeCashShift",
        ].forEach(marker => {
            assert.ok(
                api.includes(marker),
                `Falta ${marker}`
            );
        });

        [
            "/pos/staff/unlock",
            "/pos/staff/session",
            "/pos/cash/shifts/current",
            "/pos/cash/shifts/open",
            "/movements",
            "/closing-count",
            "/close",
        ].forEach(marker => {
            assert.ok(
                api.includes(marker),
                `Falta endpoint ${marker}`
            );
        });

        assert.match(
            api,
            /Authorization[\s\S]*?Bearer/
        );
    }
);

test(
    "offline verifier and active shift cache use existing local meta storage",
    () => {
        assert.match(
            db,
            /const DB_VERSION = 3;/
        );

        [
            "function putStaffVerifier",
            "function getStaffVerifier",
            "function deleteStaffVerifier",
            "function setCachedCashShift",
            "function getCachedCashShift",
            "staff_verifier:",
            "cash_shift:",
        ].forEach(marker => {
            assert.ok(
                db.includes(marker),
                `Falta ${marker}`
            );
        });
    }
);

test(
    "app creates operational session but never restores staff auth from browser storage",
    () => {
        assert.match(
            app,
            /CofiPosStaffSessionModule/
        );

        assert.match(
            app,
            /createStaffSession/
        );

        assert.match(
            app,
            /CofiPosCashShiftModule/
        );

        assert.match(
            app,
            /createCashShift/
        );

        assert.doesNotMatch(
            app,
            /localStorage[\s\S]{0,120}(?:access_token|staff_session|staff_token)/i
        );

        assert.doesNotMatch(
            app,
            /sessionStorage[\s\S]{0,120}(?:access_token|staff_session|staff_token)/i
        );
    }
);

test(
    "normal interaction resets five-minute staff inactivity timer",
    () => {
        assert.match(
            app,
            /resetActivityTimer/
        );

        assert.match(
            app,
            /pointerdown/
        );

        assert.match(
            app,
            /keydown/
        );

        assert.match(
            app,
            /touchstart/
        );

        assert.match(
            app,
            /staff-lock-button[\s\S]*?\.lock\(/
        );
    }
);

test(
    "offline state disables server-required cash operations and service worker caches modules",
    () => {
        assert.match(
            app,
            /syncCashActionAvailability/
        );

        assert.match(
            app,
            /Abrir caja[\s\S]*?requiere conexión|requiere conexión[\s\S]*?Abrir caja/i
        );

        assert.match(
            app,
            /Movimiento de caja[\s\S]*?requiere conexión|requiere conexión[\s\S]*?Movimiento de caja/i
        );

        assert.match(
            app,
            /Cerrar caja[\s\S]*?requiere conexión|requiere conexión[\s\S]*?Cerrar caja/i
        );

        assert.ok(
            sw.includes(
                '"./js/staff-session.js"'
            )
        );

        assert.ok(
            sw.includes(
                '"./js/cash-shift.js?v=2"'
            )
        );
    }
);
