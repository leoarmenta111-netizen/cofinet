const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    return fs.readFileSync(path, "utf8");
}

test(
    "POS usa logo oficial",
    () => {
        const html = read("pos/index.html");

        assert.ok(
            html.includes(
                "./assets/coficenter-logo.png"
            )
        );

        assert.ok(
            html.includes(
                "coficenter-pos-logo"
            )
        );
    }
);

test(
    "POS selecciona manifest por sucursal",
    () => {
        const html = read("pos/index.html");

        [
            "manifest-nuevo-vallarta.webmanifest",
            "manifest-bucerias.webmanifest",
            "manifest-ixtapa.webmanifest",
        ].forEach(value => {
            assert.ok(
                html.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "manifests de las tres sucursales son JSON validos",
    () => {
        const files = [
            "pos/manifest-nuevo-vallarta.webmanifest",
            "pos/manifest-bucerias.webmanifest",
            "pos/manifest-ixtapa.webmanifest",
        ];

        for (const file of files) {
            const manifest =
                JSON.parse(read(file));

            assert.ok(manifest.name);
            assert.ok(manifest.short_name);
            assert.ok(manifest.start_url);
            assert.ok(manifest.display);
        }
    }
);

test(
    "POS incluye responsive y soporte de imágenes",
    () => {
        const css = read("pos/css/pos.css");

        [
            "COFI POS — RESPONSIVE SYSTEM V1",
            ".coficenter-pos-logo",
            ".product-image",
            ".product-visual",
        ].forEach(value => {
            assert.ok(
                css.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "service worker incluye shell, imágenes y manifests",
    () => {
        const sw = read("pos/sw.js");

        [
            "SHELL_CACHE",
            "IMAGE_CACHE",
            "./js/orders-local.js",
            "./js/orders.js",
            "./assets/coficenter-logo.png",
            "./manifest-nuevo-vallarta.webmanifest",
            "./manifest-bucerias.webmanifest",
            "./manifest-ixtapa.webmanifest",
        ].forEach(value => {
            assert.ok(
                sw.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "app conserva fallback local de sucursal",
    () => {
        const app = read("pos/js/app.js");

        assert.ok(
            app.includes(
                'localStorage.getItem'
            )
        );

        assert.ok(
            app.includes(
                '"cofi_pos_branch"'
            )
        );
    }
);
