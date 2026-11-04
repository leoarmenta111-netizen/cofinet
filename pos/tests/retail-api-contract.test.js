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

function loadRetailApi() {
    const filename =
        path.join(
            ROOT,
            "pos/js/retail-api.js"
        );

    assert.equal(
        fs.existsSync(filename),
        true,
        "pos/js/retail-api.js must exist"
    );

    const calls = [];

    const context = {
        window: {
            CofiPosAPI: {
                request:
                    async (...args) => {
                        calls.push(args);

                        return {
                            ok: true,
                        };
                    },
            },
        },
        console,
    };

    vm.createContext(context);

    vm.runInContext(
        fs.readFileSync(
            filename,
            "utf8"
        ),
        context,
        {
            filename:
                "pos/js/retail-api.js",
        }
    );

    assert.ok(
        context.window.CofiRetailAPI,
        "window.CofiRetailAPI must be exported"
    );

    return {
        api:
            context.window.CofiRetailAPI,
        calls,
    };
}

test(
    "retail API exposes the Papeleria workflows required by the cashier shell",
    () => {
        const { api } =
            loadRetailApi();

        const methods = [
            "loadCatalog",
            "listHeldSales",
            "holdSale",
            "updateHeldSale",
            "checkout",
            "receipt",
            "returnItems",
            "cancelSale",
        ];

        for (const method of methods) {
            assert.equal(
                typeof api[method],
                "function",
                `${method} must be a function`
            );
        }
    }
);

test(
    "retail API is permanently scoped to PAPELERIA",
    () => {
        const { api } =
            loadRetailApi();

        assert.equal(
            api.moduleCode,
            "PAPELERIA"
        );
    }
);
