const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    return fs.readFileSync(path, "utf8");
}

test(
    "HTML conecta workspace, navegación y modal de órdenes",
    () => {
        const html = read("pos/index.html");

        [
            'id="sale-view"',
            'id="orders-view"',
            'id="orders-list"',
            'id="nav-sale"',
            'id="nav-orders"',
            'id="order-detail-modal"',
            'id="order-status-action"',
            './js/orders-local.js?v=1',
            './js/orders.js?v=15',
        ].forEach(value => {
            assert.ok(
                html.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "CSS contiene presentación propia de órdenes",
    () => {
        const css = read("pos/css/pos.css");

        [
            ".workspace.orders-mode",
            ".orders-view",
            ".orders-list",
            ".order-list-card",
            ".order-status-badge",
            ".order-detail-card",
        ].forEach(value => {
            assert.ok(
                css.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "service worker cachea módulos de órdenes",
    () => {
        const sw = read("pos/sw.js");

        assert.ok(
            sw.includes("SHELL_CACHE")
        );

        assert.ok(
            sw.includes(
                '"./js/orders-local.js"'
            )
        );

        assert.ok(
            sw.includes(
                '"./js/orders.js"'
            )
        );
    }
);
