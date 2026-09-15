const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const cssPath = path.join(
    process.cwd(),
    "pos/css/pos.css"
);

const css = fs.readFileSync(
    cssPath,
    "utf8"
);

test(
    "Android tablet disables expensive modal backdrop blur",
    () => {
        const marker =
            "COFI POS — ANDROID TABLET PWA V1";

        const markerIndex =
            css.indexOf(marker);

        assert.notEqual(
            markerIndex,
            -1,
            "tablet PWA CSS marker must exist"
        );

        const tabletCss =
            css.slice(markerIndex);

        assert.match(
            tabletCss,
            /\.modal-backdrop\s*\{[\s\S]*?backdrop-filter:\s*none\s*!important\s*;/,
            "tablet CSS must disable modal backdrop blur"
        );
    }
);
