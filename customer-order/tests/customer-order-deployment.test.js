const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const ROOT = path.resolve(__dirname, "..", "..");

function read(relative) {
    return fs.readFileSync(
        path.join(ROOT, relative),
        "utf8"
    );
}

test(
    "production plumbing exposes customer-order",
    () => {
        const compose = read("docker-compose.yml");
        const http = read("nginx/default.conf");
        const https = read("nginx/pos-ssl.conf");

        assert.match(
            compose,
            /\.\/customer-order:\/usr\/share\/nginx\/customer-order:ro/
        );

        for (const config of [http, https]) {
            assert.match(
                config,
                /location = \/customer-order/
            );

            assert.match(
                config,
                /location \/customer-order\//
            );

            assert.match(
                config,
                /\/customer-order\/index\.html/
            );
        }
    }
);
