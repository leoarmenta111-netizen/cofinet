const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const css = fs.readFileSync(
    "pos/css/pos.css",
    "utf8"
);

const marker =
    "COFI POS — ANDROID TABLET PWA V1";

function tabletCss() {
    const index = css.indexOf(marker);

    assert.notEqual(
        index,
        -1,
        "falta el bloque final dedicado a tablet Android"
    );

    return css.slice(index);
}

test(
    "tablet Android tiene breakpoint landscape dedicado",
    () => {
        const source = tabletCss();

        assert.match(
            source,
            /pointer:\s*coarse/
        );

        assert.match(
            source,
            /orientation:\s*landscape/
        );

        assert.match(
            source,
            /max-width:\s*1366px/
        );
    }
);

test(
    "landscape conserva catalogo y orden lado a lado",
    () => {
        const source = tabletCss();

        assert.match(
            source,
            /\.workspace[\s\S]*?grid-template-columns:/
        );

        assert.match(
            source,
            /minmax\(\s*0\s*,\s*1\.\d+fr\s*\)/
        );

        assert.match(
            source,
            /minmax\(\s*3\d\dpx/
        );
    }
);

test(
    "tablet usa viewport dinamico y evita overflow global",
    () => {
        const source = tabletCss();

        assert.match(
            source,
            /100dvh/
        );

        assert.match(
            source,
            /overflow:\s*hidden/
        );
    }
);

test(
    "portrait permanece contemplado en tablet tactil",
    () => {
        const source = tabletCss();

        assert.match(
            source,
            /orientation:\s*portrait/
        );
    }
);
