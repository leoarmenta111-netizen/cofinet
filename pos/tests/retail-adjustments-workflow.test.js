const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const adjustmentPath =
    "pos/js/retail-adjustments.js";


function loadModule() {
    assert.equal(
        fs.existsSync(adjustmentPath),
        true,
        "retail-adjustments.js must exist"
    );

    const source =
        fs.readFileSync(
            adjustmentPath,
            "utf8"
        );

    const context = {
        window: {},
    };

    vm.createContext(context);

    vm.runInContext(
        source,
        context
    );

    return (
        context
            .window
            .CofiRetailAdjustments
    );
}


test(
    "retail adjustments module exists",
    () => {
        assert.equal(
            fs.existsSync(
                adjustmentPath
            ),
            true
        );
    }
);


test(
    "return payload matches backend contract",
    () => {
        const api =
            loadModule();

        const payload =
            api.buildReturnPayload({
                returnUuid:
                    "return-uuid-1",

                reason:
                    "Producto equivocado",

                refundMethod:
                    "CASH",

                externalReference:
                    null,

                managerStaffId:
                    51,

                managerPin:
                    "2468",

                lines: [
                    {
                        sale_line_id:
                            1001,
                        quantity:
                            "2.0000",
                    },
                ],
            });

        assert.deepEqual(
            JSON.parse(
                JSON.stringify(
                    payload
                )
            ),
            {
                return_uuid:
                    "return-uuid-1",

                reason:
                    "Producto equivocado",

                refund_method:
                    "CASH",

                external_reference:
                    null,

                authorizing_manager_staff_id:
                    51,

                manager_pin:
                    "2468",

                lines: [
                    {
                        sale_line_id:
                            1001,

                        quantity:
                            "2.0000",
                    },
                ],
            }
        );
    }
);


test(
    "return payload never sends client refund prices",
    () => {
        const api =
            loadModule();

        const payload =
            api.buildReturnPayload({
                returnUuid:
                    "return-uuid-2",

                reason:
                    "Devolución",

                refundMethod:
                    "CASH",

                managerStaffId:
                    51,

                managerPin:
                    "2468",

                lines: [
                    {
                        sale_line_id:
                            1001,

                        quantity:
                            "1",
                    },
                ],
            });

        const line =
            payload.lines[0];

        assert.equal(
            Object.hasOwn(
                line,
                "unit_amount"
            ),
            false
        );

        assert.equal(
            Object.hasOwn(
                line,
                "line_total"
            ),
            false
        );

        assert.equal(
            Object.hasOwn(
                line,
                "unit_price"
            ),
            false
        );
    }
);


test(
    "card return preserves external reference",
    () => {
        const api =
            loadModule();

        const payload =
            api.buildReturnPayload({
                returnUuid:
                    "return-uuid-3",

                reason:
                    "Refund card",

                refundMethod:
                    "CARD",

                externalReference:
                    "REF-9988",

                managerStaffId:
                    77,

                managerPin:
                    "1234",

                lines: [
                    {
                        sale_line_id:
                            12,

                        quantity:
                            "1",
                    },
                ],
            });

        assert.equal(
            payload.refund_method,
            "CARD"
        );

        assert.equal(
            payload.external_reference,
            "REF-9988"
        );
    }
);


test(
    "return requires manager authorization",
    () => {
        const api =
            loadModule();

        assert.throws(
            () =>
                api.buildReturnPayload({
                    returnUuid:
                        "return-uuid-4",

                    reason:
                        "Refund",

                    refundMethod:
                        "CASH",

                    managerStaffId:
                        null,

                    managerPin:
                        "",

                    lines: [
                        {
                            sale_line_id:
                                1,

                            quantity:
                                "1",
                        },
                    ],
                })
        );
    }
);


test(
    "return requires at least one positive line",
    () => {
        const api =
            loadModule();

        assert.throws(
            () =>
                api.buildReturnPayload({
                    returnUuid:
                        "return-uuid-5",

                    reason:
                        "Refund",

                    refundMethod:
                        "CASH",

                    managerStaffId:
                        10,

                    managerPin:
                        "9999",

                    lines: [],
                })
        );

        assert.throws(
            () =>
                api.buildReturnPayload({
                    returnUuid:
                        "return-uuid-6",

                    reason:
                        "Refund",

                    refundMethod:
                        "CASH",

                    managerStaffId:
                        10,

                    managerPin:
                        "9999",

                    lines: [
                        {
                            sale_line_id:
                                1,

                            quantity:
                                "0",
                        },
                    ],
                })
        );
    }
);


test(
    "refund method only accepts CASH or CARD",
    () => {
        const api =
            loadModule();

        assert.throws(
            () =>
                api.buildReturnPayload({
                    returnUuid:
                        "return-uuid-7",

                    reason:
                        "Refund",

                    refundMethod:
                        "TRANSFER",

                    managerStaffId:
                        10,

                    managerPin:
                        "9999",

                    lines: [
                        {
                            sale_line_id:
                                1,

                            quantity:
                                "1",
                        },
                    ],
                })
        );
    }
);


test(
    "cancellation payload builder exists",
    () => {
        const api =
            loadModule();

        assert.equal(
            typeof (
                api
                    .buildCancellationPayload
            ),
            "function"
        );
    }
);
