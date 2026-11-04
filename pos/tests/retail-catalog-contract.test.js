const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");

const path =
    require("node:path");

const test =
    require("node:test");

const vm =
    require("node:vm");


function loadApi() {
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
    };

    vm.createContext(context);

    vm.runInContext(
        fs.readFileSync(
            path.join(
                process.cwd(),
                "pos/js/retail-api.js"
            ),
            "utf8"
        ),
        context
    );

    return {
        api:
            context.window
                .CofiRetailAPI,
        calls,
    };
}


test(
    "retail catalog trusts authenticated server branch",
    async () => {
        const {
            api,
            calls,
        } = loadApi();

        await api.loadCatalog(
            "ignored-client-branch"
        );

        assert.equal(
            calls.length,
            1
        );

        assert.equal(
            calls[0][0],
            "/retail/catalog"
        );

        assert.equal(
            calls[0][0].includes(
                "branch_code"
            ),
            false
        );
    }
);
