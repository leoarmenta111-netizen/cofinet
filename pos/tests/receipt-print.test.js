const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT =
    path.resolve(__dirname, "..");

const cssPath =
    path.join(
        ROOT,
        "css",
        "receipt.css"
    );

const htmlPath =
    path.join(
        ROOT,
        "index.html"
    );

const swPath =
    path.join(
        ROOT,
        "sw.js"
    );

function read(file) {
    return fs.readFileSync(
        file,
        "utf8"
    );
}

test(
    "dedicated 80mm receipt stylesheet exists",
    () => {
        assert.equal(
            fs.existsSync(cssPath),
            true,
            "receipt.css must exist"
        );
    }
);

test(
    "receipt print stylesheet defines 80mm thermal output",
    () => {
        assert.equal(
            fs.existsSync(cssPath),
            true,
            "receipt.css must exist"
        );

        const css =
            read(cssPath);

        assert.match(
            css,
            /@page\s*\{[\s\S]*?margin\s*:\s*0\s*;/i
        );

        assert.match(
            css,
            /width\s*:\s*80mm\s*;/i
        );

        assert.match(
            css,
            /@media\s+print/i
        );
    }
);

test(
    "POS loads receipt stylesheet and renderer before app",
    () => {
        const html =
            read(htmlPath);

        assert.match(
            html,
            /css\/receipt\.css/
        );

        const rendererIndex =
            html.indexOf(
                "js/receipt-renderer.js"
            );

        const appIndex =
            html.indexOf(
                "js/app.js"
            );

        assert.ok(
            rendererIndex >= 0,
            "receipt renderer script must be loaded"
        );

        assert.ok(
            rendererIndex < appIndex,
            "receipt renderer must load before app.js"
        );
    }
);

test(
    "POS contains receipt preview modal and post-sale actions",
    () => {
        const html =
            read(htmlPath);

        assert.match(
            html,
            /id=["']receipt-modal["']/
        );

        assert.match(
            html,
            /id=["']receipt-document["']/
        );

        assert.match(
            html,
            />\s*Ver ticket\s*</i
        );

        assert.match(
            html,
            />\s*Imprimir ticket\s*</i
        );

        assert.match(
            html,
            />\s*Nueva venta\s*</i
        );
    }
);

test(
    "service worker precaches receipt assets with new shell version",
    () => {
        const sw =
            read(swPath);

        assert.match(
            sw,
            /\.\/css\/receipt\.css/
        );

        assert.match(
            sw,
            /\.\/js\/receipt-renderer\.js/
        );

        assert.doesNotMatch(
            sw,
            /cofi-pos-shell-v16/
        );
    }
);
