const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const ordersJs = fs.readFileSync(
    "pos/js/orders.js",
    "utf8"
);

const css = fs.readFileSync(
    "pos/css/pos.css",
    "utf8"
);


test(
    "detalle de orden usa estados reales de preparacion",
    () => {
        assert.match(
            ordersJs,
            /order\.stations/,
            "El detalle no usa order.stations"
        );

        assert.match(
            ordersJs,
            /station\.station/,
            "No identifica Cocina o Barra"
        );

        assert.match(
            ordersJs,
            /station\.status/,
            "No muestra estado individual de estación"
        );
    }
);


test(
    "detalle traduce nombres de estaciones",
    () => {
        assert.match(
            ordersJs,
            /KITCHEN[\s\S]{0,100}Cocina/,
            "Falta etiqueta Cocina"
        );

        assert.match(
            ordersJs,
            /BAR[\s\S]{0,100}Barra/,
            "Falta etiqueta Barra"
        );
    }
);


test(
    "detalle traduce estados de preparacion",
    () => {
        assert.match(
            ordersJs,
            /NEW[\s\S]{0,100}Nueva/,
            "Falta estado Nueva"
        );

        assert.match(
            ordersJs,
            /PREPARING[\s\S]{0,100}Preparando/,
            "Falta estado Preparando"
        );

        assert.match(
            ordersJs,
            /READY[\s\S]{0,100}Lista/,
            "Falta estado Lista"
        );
    }
);


test(
    "detalle tiene bloque visual de preparacion",
    () => {
        assert.match(
            ordersJs,
            /order-preparation/,
            "Falta markup de preparación"
        );

        assert.match(
            css,
            /\.order-preparation/,
            "Faltan estilos de preparación"
        );

        assert.match(
            css,
            /\.order-preparation-station/,
            "Faltan estilos por estación"
        );
    }
);


test(
    "productos NONE no generan estacion visual",
    () => {
        assert.doesNotMatch(
            ordersJs,
            /NONE[\s\S]{0,80}(Cocina|Barra)/,
            "NONE no debe mostrarse como estación"
        );
    }
);
