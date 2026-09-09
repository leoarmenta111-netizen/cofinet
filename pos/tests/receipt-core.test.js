const test = require("node:test");
const assert = require("node:assert/strict");

global.window = {};

require("../js/receipt-core.js");

const {
    calculateTax,
    buildSnapshot,
    validateSnapshot,
} = window.CofiPosReceipt;

function baseSnapshotInput() {
    return {
        order_uuid: "order-uuid-001",
        folio: "NV-260908-7K3M9Q2F",
        sold_at: "2026-09-08T18:30:00.000Z",
        currency: "MXN",
        business: {
            name: "CofiCenter",
            phone: "3221234567",
            footer_message: "Gracias por su compra",
        },
        branch: {
            code: "nuevo-vallarta",
            name: "CofiCenter Nuevo Vallarta",
            address: "Nuevo Vallarta, Nayarit",
        },
        terminal: {
            id: "tablet-1",
            name: "Caja 1",
        },
        customer: {
            name: "Ana Perez",
            phone: "3220000000",
            email: "ana@example.com",
        },
        items: [
            {
                product_id: 101,
                name: "Orden de tacos",
                quantity: 2,
                unit_price_cents: 4000,
                line_total_cents: 8000,
                modifiers: [
                    {
                        name: "Queso extra",
                        price_delta_cents: 500,
                        customer_visible: true,
                    },
                    {
                        name: "Nota cocina",
                        price_delta_cents: 0,
                        customer_visible: false,
                    },
                ],
                preparation_notes: "SIN CEBOLLA",
            },
        ],
        totals: {
            subtotal_cents: 8000,
            discount_cents: 0,
            tax_mode: "ADDED",
            tax_rate: "0.1600",
            tax_cents: 1280,
            tip_cents: 500,
            total_cents: 9780,
        },
        payment: {
            method: "CASH",
            amount_cents: 9780,
            amount_tendered_cents: 10000,
            change_due_cents: 220,
        },
    };
}

function clone(value) {
    return JSON.parse(JSON.stringify(value));
}


test("NONE no agrega impuesto y suma propina despues", () => {
    assert.deepEqual(
        calculateTax({
            merchandiseCents: 10000,
            taxMode: "NONE",
            taxRate: "0.1600",
            tipCents: 500,
        }),
        {
            taxCents: 0,
            totalCents: 10500,
        }
    );
});

test("INCLUDED extrae impuesto sin volverlo a sumar", () => {
    assert.deepEqual(
        calculateTax({
            merchandiseCents: 11600,
            taxMode: "INCLUDED",
            taxRate: "0.1600",
            tipCents: 500,
        }),
        {
            taxCents: 1600,
            totalCents: 12100,
        }
    );
});

test("ADDED agrega impuesto al merchandise post-discount", () => {
    assert.deepEqual(
        calculateTax({
            merchandiseCents: 10000,
            discountCents: 1000,
            taxMode: "ADDED",
            taxRate: "0.1600",
            tipCents: 500,
        }),
        {
            taxCents: 1440,
            totalCents: 10940,
        }
    );
});

test("propina queda fuera de la base gravable", () => {
    const withoutTip = calculateTax({
        merchandiseCents: 10000,
        taxMode: "ADDED",
        taxRate: "0.1600",
        tipCents: 0,
    });

    const withTip = calculateTax({
        merchandiseCents: 10000,
        taxMode: "ADDED",
        taxRate: "0.1600",
        tipCents: 5000,
    });

    assert.equal(
        withoutTip.taxCents,
        withTip.taxCents
    );
});

test("discount defaults a cero", () => {
    assert.deepEqual(
        calculateTax({
            merchandiseCents: 10000,
            taxMode: "ADDED",
            taxRate: "0.1600",
            tipCents: 0,
        }),
        {
            taxCents: 1600,
            totalCents: 11600,
        }
    );
});

test("impuesto redondea deterministicamente a centavos", () => {
    assert.deepEqual(
        calculateTax({
            merchandiseCents: 101,
            taxMode: "ADDED",
            taxRate: "0.0750",
            tipCents: 0,
        }),
        {
            taxCents: 8,
            totalCents: 109,
        }
    );
});

test("calculateTax rechaza entradas invalidas", () => {
    assert.throws(() => calculateTax({
        merchandiseCents: 100,
        taxMode: "INVALID",
        taxRate: "0.16",
        tipCents: 0,
    }));

    assert.throws(() => calculateTax({
        merchandiseCents: -1,
        taxMode: "NONE",
        taxRate: "0",
        tipCents: 0,
    }));

    assert.throws(() => calculateTax({
        merchandiseCents: 100,
        taxMode: "NONE",
        taxRate: "0",
        tipCents: -1,
    }));

    assert.throws(() => calculateTax({
        merchandiseCents: 100,
        discountCents: -1,
        taxMode: "NONE",
        taxRate: "0",
        tipCents: 0,
    }));

    assert.throws(() => calculateTax({
        merchandiseCents: 100,
        discountCents: 101,
        taxMode: "NONE",
        taxRate: "0",
        tipCents: 0,
    }));

    assert.throws(() => calculateTax({
        merchandiseCents: 100,
        taxMode: "ADDED",
        taxRate: "-0.01",
        tipCents: 0,
    }));
});

test("snapshot congela los datos visibles del recibo", () => {
    const input = baseSnapshotInput();
    const snapshot = buildSnapshot(input);

    assert.equal(snapshot.schema_version, 1);
    assert.equal(snapshot.order_uuid, input.order_uuid);
    assert.equal(snapshot.folio, input.folio);

    assert.deepEqual(
        snapshot.customer,
        {
            name: "Ana Perez",
        }
    );

    assert.equal(snapshot.items.length, 1);
    assert.equal(snapshot.items[0].product_id, 101);
    assert.equal(snapshot.items[0].name, "Orden de tacos");
    assert.equal(snapshot.items[0].quantity, 2);
    assert.equal(snapshot.items[0].unit_price, "40.00");
    assert.equal(snapshot.items[0].line_total, "80.00");

    assert.deepEqual(
        snapshot.items[0].modifiers,
        [
            {
                name: "Queso extra",
                price_delta: "5.00",
            },
        ]
    );

    assert.equal(
        "preparation_notes" in snapshot.items[0],
        false
    );

    assert.deepEqual(
        snapshot.business,
        input.business
    );

    assert.deepEqual(
        snapshot.branch,
        input.branch
    );

    assert.deepEqual(
        snapshot.totals,
        {
            subtotal: "80.00",
            discount: "0.00",
            tax_mode: "ADDED",
            tax_rate: "0.1600",
            tax: "12.80",
            tip: "5.00",
            total: "97.80",
        }
    );

    assert.deepEqual(
        snapshot.payment,
        {
            method: "CASH",
            amount: "97.80",
            amount_tendered: "100.00",
            change_due: "2.20",
        }
    );

    assert.doesNotThrow(() => {
        validateSnapshot(snapshot);
    });
});

test("snapshot queda separado de mutaciones posteriores", () => {
    const input = baseSnapshotInput();
    const snapshot = buildSnapshot(input);

    input.business.name = "CAMBIADO";
    input.branch.name = "CAMBIADO";
    input.customer.name = "CAMBIADO";
    input.items[0].name = "CAMBIADO";
    input.items[0].modifiers[0].name = "CAMBIADO";
    input.totals.total_cents = 1;
    input.payment.method = "CARD_EXTERNAL";

    assert.equal(snapshot.business.name, "CofiCenter");
    assert.equal(
        snapshot.branch.name,
        "CofiCenter Nuevo Vallarta"
    );
    assert.equal(snapshot.customer.name, "Ana Perez");
    assert.equal(
        snapshot.items[0].name,
        "Orden de tacos"
    );
    assert.equal(
        snapshot.items[0].modifiers[0].name,
        "Queso extra"
    );
    assert.equal(snapshot.totals.total, "97.80");
    assert.equal(snapshot.payment.method, "CASH");
});

test("snapshot admite customer null", () => {
    const input = baseSnapshotInput();
    input.customer = null;

    const snapshot = buildSnapshot(input);

    assert.equal(snapshot.customer, null);
});

test("validateSnapshot rechaza snapshots inconsistentes", () => {
    const valid = buildSnapshot(baseSnapshotInput());

    const wrongVersion = clone(valid);
    wrongVersion.schema_version = 2;
    assert.throws(() => validateSnapshot(wrongVersion));

    const missingUuid = clone(valid);
    delete missingUuid.order_uuid;
    assert.throws(() => validateSnapshot(missingUuid));

    const missingFolio = clone(valid);
    delete missingFolio.folio;
    assert.throws(() => validateSnapshot(missingFolio));

    const negativeMoney = clone(valid);
    negativeMoney.totals.tip = "-1.00";
    assert.throws(() => validateSnapshot(negativeMoney));

    const wrongLine = clone(valid);
    wrongLine.items[0].line_total = "79.99";
    assert.throws(() => validateSnapshot(wrongLine));

    const wrongSubtotal = clone(valid);
    wrongSubtotal.totals.subtotal = "79.00";
    assert.throws(() => validateSnapshot(wrongSubtotal));

    const wrongTotal = clone(valid);
    wrongTotal.totals.total = "1.00";
    assert.throws(() => validateSnapshot(wrongTotal));

    const wrongMode = clone(valid);
    wrongMode.totals.tax_mode = "INVALID";
    assert.throws(() => validateSnapshot(wrongMode));

    const leakedCustomer = clone(valid);
    leakedCustomer.customer.phone = "3220000000";
    assert.throws(() => validateSnapshot(leakedCustomer));
});
