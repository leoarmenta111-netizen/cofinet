const test = require("node:test");
const assert = require("node:assert/strict");

global.window = {};

const requests = [];

global.fetch = async (url, options = {}) => {
    requests.push({
        url,
        options,
    });

    return {
        ok: true,
        status: 200,
        async json() {
            return {
                count: 0,
                orders: [],
            };
        },
    };
};

require("../js/api.js");

const api = window.CofiPosAPI;


test(
    "listOrders consulta la sucursal y rango solicitado",
    async () => {
        requests.length = 0;

        await api.listOrders(
            "nuevo-vallarta",
            {
                fromAt:
                    "2026-08-29T00:00:00.000Z",
                toAt:
                    "2026-08-30T00:00:00.000Z",
                limit: 200,
            }
        );

        assert.equal(
            requests.length,
            1
        );

        const request =
            requests[0];

        const url =
            new URL(
                request.url,
                "https://cofinet.test"
            );

        assert.equal(
            url.pathname,
            "/api/pos/orders"
        );

        assert.equal(
            url.searchParams.get(
                "branch_code"
            ),
            "nuevo-vallarta"
        );

        assert.equal(
            url.searchParams.get(
                "limit"
            ),
            "200"
        );

        assert.equal(
            url.searchParams.get(
                "from_at"
            ),
            "2026-08-29T00:00:00.000Z"
        );

        assert.equal(
            url.searchParams.get(
                "to_at"
            ),
            "2026-08-30T00:00:00.000Z"
        );
    }
);


test(
    "getOrder consulta una orden dentro de su sucursal",
    async () => {
        requests.length = 0;

        await api.getOrder(
            "order-123",
            "bucerias"
        );

        assert.equal(
            requests.length,
            1
        );

        assert.equal(
            requests[0].url,
            "/api/pos/orders/order-123?branch_code=bucerias"
        );
    }
);


test(
    "updateOrderStatus envia PATCH con sucursal y estado",
    async () => {
        requests.length = 0;

        await api.updateOrderStatus(
            "order-456",
            "ixtapa",
            "PREPARING"
        );

        assert.equal(
            requests.length,
            1
        );

        const request =
            requests[0];

        assert.equal(
            request.url,
            "/api/pos/orders/order-456/status"
        );

        assert.equal(
            request.options.method,
            "PATCH"
        );

        assert.deepEqual(
            JSON.parse(
                request.options.body
            ),
            {
                branch_code: "ixtapa",
                status: "PREPARING",
            }
        );
    }
);
