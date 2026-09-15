const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "../..");

function filePath(relativePath) {
    return path.join(ROOT, relativePath);
}

function exists(relativePath) {
    return fs.existsSync(filePath(relativePath));
}

function read(relativePath) {
    const target = filePath(relativePath);

    if (!fs.existsSync(target)) {
        return "";
    }

    return fs.readFileSync(target, "utf8");
}

test(
    "existe un motor compartido de alertas de sonido",
    () => {
        assert.equal(
            exists("pos/js/sound-alerts.js"),
            true,
            "debe existir pos/js/sound-alerts.js"
        );

        const source =
            read("pos/js/sound-alerts.js");

        assert.match(
            source,
            /CofiSoundAlerts/
        );

        assert.match(
            source,
            /playNewOrder/
        );

        assert.match(
            source,
            /playOrderReady/
        );

        assert.match(
            source,
            /AudioContext|webkitAudioContext/
        );

        assert.match(
            source,
            /pointerdown|touchstart/
        );
    }
);

test(
    "KDS alerta una sola vez por orden nueva y nunca por READY",
    () => {
        const station =
            read("pos/js/station.js");

        assert.match(
            station,
            /playNewOrder/
        );

        assert.match(
            station,
            /alertedNewOrderIds/
        );

        assert.match(
            station,
            /alertsInitialized/
        );

        assert.match(
            station,
            /station_status\s*===\s*["']NEW["']/
        );

        assert.doesNotMatch(
            station,
            /playOrderReady/,
            "KDS no debe reproducir alerta de orden lista"
        );
    }
);

test(
    "Cocina y Barra cargan sonido y refrescan cache",
    () => {
        const kitchen =
            read("pos/kitchen/index.html");

        const bar =
            read("pos/bar/index.html");

        const kitchenSw =
            read("pos/kitchen/sw.js");

        const barSw =
            read("pos/bar/sw.js");

        assert.match(
            kitchen,
            /sound-alerts\.js\?v=1/
        );

        assert.match(
            bar,
            /sound-alerts\.js\?v=1/
        );

        assert.match(
            kitchen,
            /station\.js\?v=3/
        );

        assert.match(
            bar,
            /station\.js\?v=3/
        );

        assert.match(
            kitchenSw,
            /cofi-kds-kitchen-shell-v3/
        );

        assert.match(
            barSw,
            /cofi-kds-bar-shell-v3/
        );

        assert.match(
            kitchenSw,
            /sound-alerts\.js\?v=1/
        );

        assert.match(
            barSw,
            /sound-alerts\.js\?v=1/
        );

        assert.match(
            kitchenSw,
            /station\.js\?v=3/
        );

        assert.match(
            barSw,
            /station\.js\?v=3/
        );
    }
);

test(
    "POS monitorea READY globalmente aunque Orders no este abierta",
    () => {
        const index =
            read("pos/index.html");

        const orders =
            read("pos/js/orders.js");

        assert.match(
            index,
            /sound-alerts\.js\?v=1/,
            "POS debe cargar el motor globalmente"
        );

        assert.match(
            index,
            /orders\.js\?v=15/,
            "orders.js debe refrescarse"
        );

        assert.match(
            orders,
            /playOrderReady/,
            "orders.js debe disparar alerta READY"
        );

        assert.match(
            orders,
            /readyAlertStatuses/,
            "debe conservar estados anteriores"
        );

        assert.match(
            orders,
            /readyAlertsInitialized/,
            "primera consulta debe ser baseline silencioso"
        );

        assert.match(
            orders,
            /status\s*===\s*["']READY["']/,
            "solo READY dispara la alerta"
        );

        assert.match(
            orders,
            /setInterval/,
            "monitor debe ejecutarse aun fuera de Orders"
        );
    }
);

test(
    "POS actualiza cache para alertas globales",
    () => {
        const sw =
            read("pos/sw.js");

        assert.match(
            sw,
            /cofi-pos-shell-v23/
        );

        assert.match(
            sw,
            /\.\/js\/sound-alerts\.js/
        );

        assert.match(
            sw,
            /\.\/js\/orders\.js/
        );
    }
);
