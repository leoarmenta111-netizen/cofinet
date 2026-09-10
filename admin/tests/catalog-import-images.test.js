const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function read(path) {
    return fs.readFileSync(path, "utf8");
}

test(
    "catalogo expone carga masiva",
    () => {
        const html = read(
            "admin/catalog.html"
        );

        [
            'id="bulk-products"',
            "/admin/pos/catalog/products/bulk/preview",
            "/admin/pos/catalog/products/bulk/import",
            "new FormData()",
        ].forEach(value => {
            assert.ok(
                html.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "catalogo expone editor de imagen",
    () => {
        const html = read(
            "admin/catalog.html"
        );

        [
            'id="product-image-section"',
            'id="product-image-file"',
            'id="product-image-dropzone"',
            'id="product-image-preview"',
            'id="select-product-image"',
            'id="remove-product-image"',
        ].forEach(value => {
            assert.ok(
                html.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "adminRequest permite FormData multipart",
    () => {
        const js = read(
            "admin/admin.js"
        );

        assert.ok(
            js.includes(
                "!(options.body instanceof FormData)"
            )
        );

        assert.ok(
            js.includes(
                '"Content-Type"'
            )
        );
    }
);

test(
    "scripts inline de catalog.html tienen sintaxis valida",
    () => {
        const html = read(
            "admin/catalog.html"
        );

        const pattern =
            /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;

        const scripts = [
            ...html.matchAll(pattern)
        ];

        assert.ok(
            scripts.length > 0,
            "No se encontraron scripts inline"
        );

        for (const match of scripts) {
            new Function(match[1]);
        }
    }
);
