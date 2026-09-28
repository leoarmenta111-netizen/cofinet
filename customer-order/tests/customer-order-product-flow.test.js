const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function read(relativePath) {
    return fs.readFileSync(
        path.join(process.cwd(), relativePath),
        "utf8"
    );
}

const html = read("customer-order/index.html");
const css = read("customer-order/css/customer-order.css");
const app = read("customer-order/js/app.js");


test(
    "configurador kiosk usa una vista vertical dedicada con producto y CTA persistente",
    () => {
        assert.match(html, /product-configurator-modal/);
        assert.match(html, /id="modifier-product-image"/);
        assert.match(html, /id="modifier-description"/);
        assert.match(html, /id="modifier-groups"/);
        assert.match(html, /id="modifier-required-hint"/);
        assert.match(html, /id="modifier-add-label"/);
        assert.match(css, /COFICENTER KIOSK PRODUCT CONFIGURATOR V2/);
        assert.match(css, /height:\s*100dvh/);
        assert.match(css, /\.product-configurator-footer[\s\S]*?position:\s*sticky/);
    }
);


test(
    "opciones se renderizan como tarjetas tactiles visuales y seleccionadas",
    () => {
        assert.match(app, /modifier-option-grid/);
        assert.match(app, /modifier-option-visual/);
        assert.match(app, /modifier-option-check/);
        assert.match(css, /\.modifier-option-grid/);
        assert.match(css, /\.modifier-option:has\(input:checked\)/);
        assert.match(css, /@media \(pointer:\s*coarse\)/);
    }
);


test(
    "flujo es generico y usa orden de modifier groups del catalogo",
    () => {
        assert.match(app, /\(product\.modifiers \|\| \[\]\)/);
        assert.match(app, /modifierGroupHint/);
        assert.match(app, /validateModifiers/);
        assert.doesNotMatch(
            app,
            /Cappuccino|Baguette|Almendra|Pechuga de pavo/
        );
    }
);


test(
    "required groups bloquean agregar hasta estar completos",
    () => {
        assert.match(app, /updateModifierCompletion/);
        assert.match(app, /addButton\.disabled/);
        assert.match(app, /modifier-group--incomplete/);
        assert.match(html, /Completa las opciones obligatorias/);
    }
);


test(
    "precio dinamico y orden actual permanecen visibles en configurador",
    () => {
        assert.match(app, /modifierEstimate/);
        assert.match(html, /id="modifier-total"/);
        assert.match(html, /id="modifier-cart-count"/);
        assert.match(html, /id="modifier-cart-total"/);
        assert.match(app, /updateModifierOrderSummary/);
    }
);


test(
    "cliente puede guardar nota y editar producto configurable desde su orden",
    () => {
        assert.match(html, /id="modifier-notes"/);
        assert.match(html, /maxlength="150"/);
        assert.match(app, /openProductCustomizer/);
        assert.match(app, /modifierEditingLineUuid/);
        assert.match(app, /Guardar cambios/);
        assert.match(app, /review-edit/);
    }
);
