const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");


function readRequired(path) {
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
    "Cocina y Barra tienen pantallas independientes",
    () => {
        const kitchen = readRequired(
            "pos/kitchen/index.html"
        );

        const bar = readRequired(
            "pos/bar/index.html"
        );

        assert.match(
            kitchen,
            /data-station="KITCHEN"/
        );

        assert.match(
            bar,
            /data-station="BAR"/
        );

        for (const html of [
            kitchen,
            bar,
        ]) {
            assert.match(
                html,
                /\.\.\/js\/api\.js/
            );

            assert.match(
                html,
                /\.\.\/js\/station\.js/
            );

            assert.match(
                html,
                /\.\.\/css\/station\.css/
            );
        }
    }
);


test(
    "pantallas comparten controlador de estacion",
    () => {
        const source = readRequired(
            "pos/js/station.js"
        );

        assert.match(
            source,
            /dataset\.station/
        );

        assert.match(
            source,
            /listStationOrders/
        );

        assert.match(
            source,
            /updateStationStatus/
        );
    }
);


test(
    "pantallas refrescan automaticamente cada 5 segundos",
    () => {
        const source = readRequired(
            "pos/js/station.js"
        );

        assert.match(
            source,
            /setInterval/
        );

        assert.match(
            source,
            /5000/
        );
    }
);


test(
    "cliente API soporta feed y avance por estacion",
    () => {
        const source = readRequired(
            "pos/js/api.js"
        );

        assert.match(
            source,
            /function\s+listStationOrders/
        );

        assert.match(
            source,
            /\/orders\/stations\//
        );

        assert.match(
            source,
            /function\s+updateStationStatus/
        );

        assert.match(
            source,
            /\/stations\//
        );
    }
);


test(
    "KDS muestra informacion operacional necesaria",
    () => {
        const source = readRequired(
            "pos/js/station.js"
        );

        [
            "NEW",
            "PREPARING",
            "READY",
            "notes",
            "modifiers",
            "quantity",
            "product_name",
        ].forEach(value => {
            assert.ok(
                source.includes(value),
                `Falta ${value} en station.js`
            );
        });
    }
);


test(
    "KDS no depende del modo offline del POS",
    () => {
        const source = readRequired(
            "pos/js/station.js"
        );

        assert.doesNotMatch(
            source,
            /CofiPosDB/
        );

        assert.doesNotMatch(
            source,
            /local_orders/
        );

        assert.doesNotMatch(
            source,
            /indexedDB/
        );
    }
);


test(
    "KDS tiene stylesheet propio",
    () => {
        const source = readRequired(
            "pos/css/station.css"
        );

        assert.match(
            source,
            /COFICENTER KDS/
        );

        assert.match(
            source,
            /\.station-board/
        );

        assert.match(
            source,
            /\.station-order-card/
        );
    }
);
