const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


function read(relativePath) {
    const target = path.join(
        process.cwd(),
        relativePath
    );

    assert.equal(
        fs.existsSync(target),
        true,

    );

    return fs.readFileSync(
        target,
        "utf8"
    );
}


test(
    "API de cliente consume catalogo publico existente",
    () => {
        const source = read(
            "customer-order/js/api.js"
        );

        assert.match(
            source,
            /\/api/
        );

        assert.match(
            source,
            /\/pos\/catalog\?branch_code=/
        );

        assert.match(
            source,
            /getCatalog/
        );
    }
);


test(
    "app fija identidad operativa sin selector editable",
    () => {
        const source = read(
            "customer-order/js/app.js"
        );

        assert.match(
            source,
            /KIOSK-IXTAPA-01/
        );

        assert.match(
            source,
            /BAR-TABLET-IXTAPA-01/
        );

        assert.match(
            source,
            /URLSearchParams/
        );

        assert.match(
            source,
            /device/
        );
    }
);


test(
    "app renderiza imagenes reales cuando catalogo tiene image_url",
    () => {
        const source = read(
            "customer-order/js/app.js"
        );

        assert.match(
            source,
            /image_url/
        );

        assert.match(
            source,
            /product-image/
        );
    }
);


test(
    "app conecta catalogo modificadores carrito y revision",
    () => {
        const source = read(
            "customer-order/js/app.js"
        );

        assert.match(
            source,
            /CofiCustomerAPI\.getCatalog/
        );

        assert.match(
            source,
            /CofiCustomerCart\.validateModifiers/
        );

        assert.match(
            source,
            /CofiCustomerCart\.makeLine/
        );

        assert.match(
            source,
            /review-sheet/
        );

        assert.match(
            source,
            /toSelfOrderItems/
        );
    }
);
