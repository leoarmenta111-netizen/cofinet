const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


function read(relativePath) {
    return fs.readFileSync(
        path.join(
            process.cwd(),
            relativePath
        ),
        "utf8"
    );
}


test(
    "HTML contiene flujo de pago tarjeta y sus estados",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /id="payment-sheet"/
        );

        assert.match(
            html,
            /id="pay-card-button"/
        );

        assert.match(
            html,
            /Pagar con tarjeta/i
        );

        assert.match(
            html,
            /id="payment-processing"/
        );

        assert.match(
            html,
            /id="payment-declined"/
        );

        assert.match(
            html,
            /id="payment-unknown"/
        );

        assert.match(
            html,
            /id="payment-success"/
        );
    }
);


test(
    "success muestra folio y recoge en barra",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /id="success-folio"/
        );

        assert.match(
            html,
            /Recoge en barra/i
        );
    }
);


test(
    "HTML contiene advertencia de inactividad",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.match(
            html,
            /id="idle-warning"/
        );

        assert.match(
            html,
            /id="idle-countdown"/
        );

        assert.match(
            html,
            /Seguir ordenando/i
        );
    }
);


test(
    "checkout sigue siendo exclusivamente tarjeta",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        assert.doesNotMatch(
            html,
            /Pagar en caja/i
        );

        assert.doesNotMatch(
            html,
            /Efectivo/i
        );
    }
);


test(
    "app crea staging antes de iniciar pago",
    () => {
        const app = read(
            "customer-order/js/app.js"
        );

        assert.match(
            app,
            /CofiCustomerAPI\s*\.\s*createSelfOrder/
        );

        assert.match(
            app,
            /CofiCustomerCart\s*\.\s*toSelfOrderItems/
        );

        assert.match(
            app,
            /self_order_uuid/
        );
    }
);


test(
    "app persiste y recupera self order",
    () => {
        const app = read(
            "customer-order/js/app.js"
        );

        assert.match(
            app,
            /localStorage/
        );

        assert.match(
            app,
            /CofiCustomerAPI\s*\.\s*getSelfOrder/
        );

        assert.match(
            app,
            /payment_attempt_uuid/
        );
    }
);


test(
    "app procesa payment attempt y contempla tres resultados",
    () => {
        const app = read(
            "customer-order/js/app.js"
        );

        assert.match(
            app,
            /CofiCustomerAPI\s*\.\s*createPaymentAttempt/
        );

        assert.match(
            app,
            /PAYMENT_DECLINED/
        );

        assert.match(
            app,
            /PAYMENT_UNKNOWN/
        );

        const checkout = read(
            "customer-order/js/checkout.js"
        );

        assert.match(
            checkout,
            /SUBMITTED/
        );

        assert.match(
            checkout,
            /SUCCESS/
        );
    }
);


test(
    "app implementa warning y reset por inactividad",
    () => {
        const app = read(
            "customer-order/js/app.js"
        );

        assert.match(
            app,
            /setTimeout/
        );

        assert.match(
            app,
            /idle-warning/
        );

        assert.match(
            app,
            /canIdleReset/
        );

        assert.match(
            app,
            /pointerdown/
        );

        assert.match(
            app,
            /keydown/
        );
    }
);


test(
    "customer shell carga checkout antes de app",
    () => {
        const html = read(
            "customer-order/index.html"
        );

        const checkoutIndex =
            html.indexOf(
                "js/checkout.js"
            );

        const appIndex =
            html.indexOf(
                "js/app.js"
            );

        assert.notEqual(
            checkoutIndex,
            -1
        );

        assert.notEqual(
            appIndex,
            -1
        );

        assert.equal(
            checkoutIndex < appIndex,
            true
        );
    }
);
