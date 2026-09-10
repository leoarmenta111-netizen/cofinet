const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const css = fs.readFileSync(
    path.join(
        __dirname,
        "..",
        "css",
        "pos.css"
    ),
    "utf8"
);

const marker =
    "COFICENTER PRODUCT CARD RESPONSIVE FIT V2";

function responsiveCss() {
    const index = css.indexOf(marker);

    assert.notEqual(
        index,
        -1,
        "falta el bloque responsive final de tarjetas"
    );

    return css.slice(index);
}

test(
    "tarjetas no se estiran verticalmente en tablet y movil",
    () => {
        const source = responsiveCss();

        assert.match(
            source,
            /grid-auto-rows:\s*max-content/
        );

        assert.match(
            source,
            /align-items:\s*start/
        );

        assert.match(
            source,
            /align-self:\s*start/
        );

        assert.match(
            source,
            /\.product-content[\s\S]*?min-height:\s*0/
        );
    }
);

test(
    "movil usa dos columnas fluidas",
    () => {
        const source = responsiveCss();

        assert.match(
            source,
            /@media\s*\(max-width:\s*620px\)/
        );

        assert.match(
            source,
            /repeat\(\s*2\s*,\s*minmax\(\s*0\s*,\s*1fr\s*\)\s*\)/
        );

        assert.match(
            source,
            /aspect-ratio:\s*4\s*\/\s*3/
        );
    }
);

test(
    "nombre y descripcion tienen limites compactos",
    () => {
        const source = responsiveCss();

        assert.match(
            source,
            /-webkit-line-clamp:\s*2/
        );

        assert.match(
            source,
            /-webkit-line-clamp:\s*1/
        );
    }
);

test(
    "telefonos pequenos tienen ajuste dedicado",
    () => {
        const source = responsiveCss();

        assert.match(
            source,
            /@media\s*\(max-width:\s*380px\)/
        );
    }
);
