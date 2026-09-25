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
    "customer order tiene shell independiente del POS de empleados",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /CofiCenter/i
        );

        assert.match(
            html,
            /id=["']customer-order-app["']/
        );

        assert.doesNotMatch(
            html,
            /Órdenes del día/i
        );

        assert.doesNotMatch(
            html,
            /CRM de mostrador/i
        );

        assert.doesNotMatch(
            html,
            /Terminal activa/i
        );

        assert.doesNotMatch(
            html,
            /Efectivo/i
        );
    }
);


test(
    "flujo visual contiene inicio menu personalizacion carrito y revision",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /id=["']start-screen["']/
        );

        assert.match(
            html,
            /Iniciar pedido/i
        );

        assert.match(
            html,
            /id=["']menu-screen["']/
        );

        assert.match(
            html,
            /id=["']category-tabs["']/
        );

        assert.match(
            html,
            /id=["']product-grid["']/
        );

        assert.match(
            html,
            /id=["']modifier-dialog["']/
        );

        assert.match(
            html,
            /id=["']customer-cart-bar["']/
        );

        assert.match(
            html,
            /id=["']review-sheet["']/
        );
    }
);


test(
    "carrito inferior muestra cantidad total y accion revisar",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /id=["']cart-count["']/
        );

        assert.match(
            html,
            /id=["']cart-total["']/
        );

        assert.match(
            html,
            /id=["']review-order-button["']/
        );

        assert.match(
            html,
            /Revisar pedido/i
        );
    }
);


test(
    "shell carga API cart y app dedicados al cliente",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /js\/api\.js/
        );

        assert.match(
            html,
            /js\/cart\.js/
        );

        assert.match(
            html,
            /js\/app\.js/
        );
    }
);


test(
    "diseño usa identidad CofiCenter y controles tactiles",
    () => {
        const css = read(
            "customer-order/css/customer-order.css"
        );

        assert.match(
            css,
            /--cofi-green\s*:/
        );

        assert.match(
            css,
            /--cofi-cream\s*:/
        );

        assert.match(
            css,
            /\.customer-primary-button[\s\S]*?min-height:\s*(?:48|5[0-9])px/
        );

        assert.match(
            css,
            /\.customer-cart-bar[\s\S]*?position:\s*fixed/
        );

        assert.match(
            css,
            /border-radius:/
        );
    }
);


test(
    "diseño contempla kiosk tablet tactil y movil",
    () => {
        const css = read(
            "customer-order/css/customer-order.css"
        );

        assert.match(
            css,
            /pointer:\s*coarse/
        );

        assert.match(
            css,
            /max-width:\s*1024px/
        );

        assert.match(
            css,
            /max-width:\s*720px/
        );

        assert.match(
            css,
            /repeat\(\s*2\s*,\s*minmax\(\s*0\s*,\s*1fr\s*\)\s*\)/
        );

        assert.match(
            css,
            /100dvh/
        );
    }
);
