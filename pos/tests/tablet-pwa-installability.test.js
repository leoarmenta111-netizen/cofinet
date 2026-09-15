const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const manifests = [
    "manifest.webmanifest",
    "manifest-nuevo-vallarta.webmanifest",
    "manifest-bucerias.webmanifest",
    "manifest-ixtapa.webmanifest",
];

function loadManifest(name) {
    return JSON.parse(
        fs.readFileSync(
            path.join("pos", name),
            "utf8"
        )
    );
}

test(
    "todos los manifests abren Cofi POS en fullscreen",
    () => {
        for (const file of manifests) {
            const manifest = loadManifest(file);

            assert.equal(
                manifest.display,
                "fullscreen",
                `${file} debe usar fullscreen`
            );
        }
    }
);

test(
    "todos los manifests permiten portrait y landscape",
    () => {
        for (const file of manifests) {
            const manifest = loadManifest(file);

            assert.equal(
                manifest.orientation,
                "any",
                `${file} debe permitir cualquier orientación`
            );
        }
    }
);

test(
    "todos los manifests incluyen iconos PWA 192 y 512",
    () => {
        for (const file of manifests) {
            const manifest = loadManifest(file);

            assert.ok(
                Array.isArray(manifest.icons),
                `${file} no declara icons`
            );

            const sizes = new Set(
                manifest.icons.map(icon => icon.sizes)
            );

            assert.ok(
                sizes.has("192x192"),
                `${file} no tiene icono 192x192`
            );

            assert.ok(
                sizes.has("512x512"),
                `${file} no tiene icono 512x512`
            );
        }
    }
);

test(
    "manifest incluye un icono maskable",
    () => {
        for (const file of manifests) {
            const manifest = loadManifest(file);

            assert.ok(
                manifest.icons.some(icon =>
                    String(icon.purpose || "")
                        .split(/\s+/)
                        .includes("maskable")
                ),
                `${file} no tiene icono maskable`
            );
        }
    }
);

test(
    "archivos de iconos PWA existen",
    () => {
        [
            "pos/assets/pwa/icon-192.png",
            "pos/assets/pwa/icon-512.png",
            "pos/assets/pwa/icon-maskable-512.png",
        ].forEach(file => {
            assert.ok(
                fs.existsSync(file),
                `Falta ${file}`
            );
        });
    }
);
