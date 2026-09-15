const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    assert.ok(
        fs.existsSync(path),
        `Falta archivo requerido: ${path}`
    );

    return fs.readFileSync(path, "utf8");
}

function json(path) {
    return JSON.parse(read(path));
}

const stations = [
    {
        dir: "kitchen",
        name: "Cofi KDS Cocina",
        id: "/pos/kitchen/",
        visibleName: "Cocina",
        cache: "cofi-kds-kitchen-shell-v2",
    },
    {
        dir: "bar",
        name: "Cofi KDS Barra",
        id: "/pos/bar/",
        visibleName: "Barra",
        cache: "cofi-kds-bar-shell-v2",
    },
];

const branches = [
    "nuevo-vallarta",
    "bucerias",
    "ixtapa",
];

test(
    "Cocina y Barra son PWAs fullscreen independientes en landscape",
    () => {
        for (const station of stations) {
            const manifest = json(
                `pos/${station.dir}/manifest.webmanifest`
            );

            assert.equal(
                manifest.name,
                station.name
            );

            assert.equal(
                manifest.id,
                station.id
            );

            assert.equal(
                manifest.scope,
                "./"
            );

            assert.equal(
                manifest.display,
                "fullscreen"
            );

            assert.equal(
                manifest.orientation,
                "landscape"
            );

            assert.ok(
                Array.isArray(manifest.icons)
                && manifest.icons.length >= 3
            );
        }

        assert.notEqual(
            json(
                "pos/kitchen/manifest.webmanifest"
            ).id,
            json(
                "pos/bar/manifest.webmanifest"
            ).id
        );
    }
);

test(
    "manifests por sucursal conservan la sucursal al abrir la app",
    () => {
        for (const station of stations) {
            for (const branch of branches) {
                const manifest = json(
                    `pos/${station.dir}/manifest-${branch}.webmanifest`
                );

                assert.equal(
                    manifest.id,
                    station.id
                );

                assert.equal(
                    manifest.start_url,
                    `./?branch=${branch}`
                );

                assert.equal(
                    manifest.display,
                    "fullscreen"
                );

                assert.equal(
                    manifest.orientation,
                    "landscape"
                );
            }
        }
    }
);

test(
    "cada pantalla selecciona manifest por sucursal y registra su propio service worker",
    () => {
        for (const station of stations) {
            const html = read(
                `pos/${station.dir}/index.html`
            );

            assert.ok(
                html.includes(
                    'id="cofi-kds-manifest"'
                )
            );

            for (const branch of branches) {
                assert.ok(
                    html.includes(
                        `manifest-${branch}.webmanifest`
                    ),
                    `Falta manifest de ${branch} en ${station.dir}`
                );
            }

            assert.ok(
                html.includes(
                    'serviceWorker'
                ),
                `Falta serviceWorker en ${station.dir}`
            );

            assert.ok(
                html.includes(
                    '.register("./sw.js"'
                ),
                `Falta registro de sw.js en ${station.dir}`
            );

            assert.ok(
                html.includes(
                    "station.css?v=2"
                ),
                `Falta station.css?v=2 en ${station.dir}`
            );
        }
    }
);

test(
    "Cocina y Barra muestran el nombre correcto de estación",
    () => {
        for (const station of stations) {
            const html = read(
                `pos/${station.dir}/index.html`
            );

            assert.ok(
                html.includes(
                    station.visibleName
                ),
                `Falta nombre ${station.visibleName}`
            );
        }
    }
);

test(
    "cada KDS usa cache propio y no intercepta tráfico operativo",
    () => {
        for (const station of stations) {
            const sw = read(
                `pos/${station.dir}/sw.js`
            );

            assert.ok(
                sw.includes(
                    station.cache
                )
            );

            assert.ok(
                sw.includes(
                    "isStationNavigation"
                )
            );

            assert.ok(
                sw.includes(
                    "isStaticAsset"
                )
            );

            assert.ok(
                sw.includes(
                    "!isStationNavigation"
                )
                && sw.includes(
                    "!isStaticAsset"
                )
            );

            assert.ok(
                !sw.includes(
                    '"/api/'
                ),
                `No debe cachear API en ${station.dir}`
            );
        }

        assert.notEqual(
            read("pos/kitchen/sw.js"),
            read("pos/bar/sw.js")
        );
    }
);

test(
    "KDS usa viewport dinámico para fullscreen en tablet",
    () => {
        const css = read(
            "pos/css/station.css"
        );

        assert.ok(
            css.includes(
                "min-height: 100dvh"
            )
        );

        assert.ok(
            css.includes(
                "overscroll-behavior: none"
            )
        );
    }
);
