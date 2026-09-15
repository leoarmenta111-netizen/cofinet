const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    assert.ok(
        fs.existsSync(path),
        `Falta archivo requerido: ${path}`
    );

    return fs.readFileSync(
        path,
        "utf8"
    );
}

test(
    "KDS permite READY a DELIVERED con boton Entregado",
    () => {
        const source = read(
            "pos/js/station.js"
        );

        assert.match(
            source,
            /READY:\s*"DELIVERED"/
        );

        assert.match(
            source,
            /READY:\s*"Entregado"/
        );
    }
);

test(
    "KDS no crea columna visible para DELIVERED",
    () => {
        const kitchen = read(
            "pos/kitchen/index.html"
        );

        const bar = read(
            "pos/bar/index.html"
        );

        for (const html of [
            kitchen,
            bar,
        ]) {
            assert.doesNotMatch(
                html,
                /data-column="DELIVERED"/
            );
        }
    }
);

test(
    "Ordenes POS muestran DELIVERED de estacion como Entregada",
    () => {
        const source = read(
            "pos/js/orders.js"
        );

        const start = source.indexOf(
            "function preparationStatusLabel"
        );

        const end = source.indexOf(
            "function renderPreparationProgress",
            start
        );

        assert.ok(start >= 0);
        assert.ok(end > start);

        const block = source.slice(
            start,
            end
        );

        assert.match(
            block,
            /DELIVERED:\s*"Entregada"/
        );
    }
);

test(
    "KDS versiona station.js despues del cambio de entregado",
    () => {
        const kitchen = read(
            "pos/kitchen/index.html"
        );

        const bar = read(
            "pos/bar/index.html"
        );

        const kitchenSw = read(
            "pos/kitchen/sw.js"
        );

        const barSw = read(
            "pos/bar/sw.js"
        );

        assert.match(
            kitchen,
            /station\.js\?v=2/
        );

        assert.match(
            bar,
            /station\.js\?v=2/
        );

        assert.match(
            kitchenSw,
            /cofi-kds-kitchen-shell-v2/
        );

        assert.match(
            barSw,
            /cofi-kds-bar-shell-v2/
        );

        assert.match(
            kitchenSw,
            /station\.js\?v=2/
        );

        assert.match(
            barSw,
            /station\.js\?v=2/
        );
    }
);
