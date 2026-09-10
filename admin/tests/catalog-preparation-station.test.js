const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const html = fs.readFileSync(
    "admin/catalog.html",
    "utf8"
);

test(
    "editor de producto muestra selector de estacion",
    () => {
        assert.match(
            html,
            /id="product-preparation-station"/,
            "Falta selector de estación"
        );

        assert.match(
            html,
            /value="KITCHEN"[\s\S]{0,120}>[\s\S]*?Cocina/i,
            "Falta opción Cocina"
        );

        assert.match(
            html,
            /value="BAR"[\s\S]{0,120}>[\s\S]*?Barra/i,
            "Falta opción Barra"
        );

        assert.match(
            html,
            /value="NONE"[\s\S]{0,160}>[\s\S]*?Sin preparación/i,
            "Falta opción Sin preparación"
        );
    }
);

test(
    "editor carga la estacion actual del producto",
    () => {
        assert.match(
            html,
            /getElementById\(\s*"product-preparation-station"\s*\)[\s\S]{0,160}\.value\s*=[\s\S]{0,160}preparation_station/,
            "openProduct no carga preparation_station"
        );

        assert.match(
            html,
            /preparation_station[\s\S]{0,100}(?:\|\||\?\?)[\s\S]{0,60}"NONE"/,
            "Producto nuevo debe usar NONE por defecto"
        );
    }
);

test(
    "guardar producto envia preparation_station",
    () => {
        assert.match(
            html,
            /preparation_station\s*:[\s\S]{0,160}getElementById\(\s*"product-preparation-station"\s*\)[\s\S]{0,100}\.value/,
            "El payload no envía preparation_station"
        );
    }
);
