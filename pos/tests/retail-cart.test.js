const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(
    __dirname,
    "..",
    ".."
);

function loadCartModule() {
    const filename =
        path.join(
            ROOT,
            "pos/js/retail-cart.js"
        );

    assert.equal(
        fs.existsSync(filename),
        true,
        "pos/js/retail-cart.js must exist"
    );

    const source =
        fs.readFileSync(
            filename,
            "utf8"
        );

    const context = {
        window: {},
        console,
    };

    vm.createContext(context);

    vm.runInContext(
        source,
        context,
        {
            filename:
                "pos/js/retail-cart.js",
        }
    );

    assert.ok(
        context.window.CofiRetailCart,
        "window.CofiRetailCart must be exported"
    );

    return context.window.CofiRetailCart;
}

test(
    "retail cart starts empty",
    () => {
        const Cart =
            loadCartModule();

        const cart =
            Cart.create();

        assert.deepEqual(
            JSON.parse(
                JSON.stringify(cart.lines)
            ),
            []
        );

        assert.equal(
            Cart.total(cart),
            0
        );
    }
);

test(
    "adding same presentation merges quantity",
    () => {
        const Cart =
            loadCartModule();

        const cart =
            Cart.create();

        const product = {
            item_id: 10,
            presentation_id: 20,
            name: "Pluma azul",
            presentation_name: "Pieza",
            unit_price: 12.5,
            item_type: "PRODUCT",
        };

        Cart.add(
            cart,
            product,
            1
        );

        Cart.add(
            cart,
            product,
            2
        );

        assert.equal(
            cart.lines.length,
            1
        );

        assert.equal(
            cart.lines[0].quantity,
            3
        );

        assert.equal(
            Cart.total(cart),
            37.5
        );
    }
);

test(
    "different presentations remain separate cart lines",
    () => {
        const Cart =
            loadCartModule();

        const cart =
            Cart.create();

        Cart.add(
            cart,
            {
                item_id: 30,
                presentation_id: 31,
                name: "Papel",
                presentation_name: "Hoja",
                unit_price: 1,
                item_type: "PRODUCT",
            },
            1
        );

        Cart.add(
            cart,
            {
                item_id: 30,
                presentation_id: 32,
                name: "Papel",
                presentation_name: "Paquete",
                unit_price: 80,
                item_type: "PRODUCT",
            },
            1
        );

        assert.equal(
            cart.lines.length,
            2
        );
    }
);

test(
    "services can be added without inventory assumptions",
    () => {
        const Cart =
            loadCartModule();

        const cart =
            Cart.create();

        Cart.add(
            cart,
            {
                item_id: 100,
                presentation_id: null,
                name: "Copia B/N",
                presentation_name: null,
                unit_price: 2,
                item_type: "SERVICE",
            },
            5
        );

        assert.equal(
            cart.lines.length,
            1
        );

        assert.equal(
            cart.lines[0].quantity,
            5
        );

        assert.equal(
            Cart.total(cart),
            10
        );
    }
);

test(
    "quantity updates and removal recalculate total",
    () => {
        const Cart =
            loadCartModule();

        const cart =
            Cart.create();

        Cart.add(
            cart,
            {
                item_id: 50,
                presentation_id: 51,
                name: "Cuaderno",
                presentation_name: "Pieza",
                unit_price: 35,
                item_type: "PRODUCT",
            },
            2
        );

        const lineId =
            cart.lines[0].line_id;

        Cart.setQuantity(
            cart,
            lineId,
            3
        );

        assert.equal(
            Cart.total(cart),
            105
        );

        Cart.remove(
            cart,
            lineId
        );

        assert.equal(
            cart.lines.length,
            0
        );

        assert.equal(
            Cart.total(cart),
            0
        );
    }
);

test(
    "checkout lines contain identifiers and quantities but never client prices",
    () => {
        const Cart =
            loadCartModule();

        const cart =
            Cart.create();

        Cart.add(
            cart,
            {
                item_id: 71,
                presentation_id: 72,
                name: "Marcador",
                presentation_name: "Pieza",
                unit_price: 22,
                item_type: "PRODUCT",
            },
            2
        );

        const payload =
            Cart.checkoutLines(cart);

        assert.equal(
            payload.length,
            1
        );

        assert.deepEqual(
            Object.keys(payload[0]).sort(),
            [
                "discount_amount",
                "item_id",
                "presentation_id",
                "quantity",
            ]
        );

        assert.equal(
            "unit_price" in payload[0],
            false
        );

        assert.equal(
            "line_total" in payload[0],
            false
        );
    }
);
