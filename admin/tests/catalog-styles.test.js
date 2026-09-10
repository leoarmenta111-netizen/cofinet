const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

function css() {
    return fs.readFileSync(
        "admin/admin.css",
        "utf8"
    );
}

test(
    "catalogo tiene estilos de imagen",
    () => {
        const source = css();

        [
            "POS PRODUCT IMAGE EDITOR",
            ".product-image-section",
            ".product-image-editor-v2",
            ".product-image-dropzone",
            ".product-image-preview",
            ".product-image-controls",
        ].forEach(value => {
            assert.ok(
                source.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "catalogo tiene estilos de carga masiva",
    () => {
        const source = css();

        [
            "COFI POS — BULK PRODUCT IMPORT V1",
            ".bulk-product-dialog",
            ".bulk-product-dropzone",
            ".bulk-preview-section",
            ".bulk-preview-table",
            ".bulk-row-status",
            ".bulk-product-footer",
        ].forEach(value => {
            assert.ok(
                source.includes(value),
                `Falta ${value}`
            );
        });
    }
);

test(
    "catalogo tiene estilos del editor v2",
    () => {
        const source = css();

        assert.ok(
            source.includes(
                "COFI POS — PRODUCT EDITOR V2"
            )
        );

        assert.ok(
            source.includes(
                "COFI POS — PRODUCT DESCRIPTION V2"
            )
        );
    }
);

test(
    "css mantiene llaves balanceadas",
    () => {
        const source = css();

        const opens =
            (source.match(/\{/g) || []).length;

        const closes =
            (source.match(/\}/g) || []).length;

        assert.equal(
            opens,
            closes,
            "Llaves CSS desbalanceadas"
        );
    }
);
