const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const http = fs.readFileSync("nginx/default.conf", "utf8");
const https = fs.readFileSync("nginx/pos-ssl.conf", "utf8");
const template = fs.readFileSync("nginx/prod.conf.template", "utf8");

test("production nginx rate limits admin login and POS unlock only", () => {
    assert.match(
        http,
        /map \$uri \$admin_login_limit_key/
    );
    assert.match(
        http,
        /"\/api\/admin\/login" \$binary_remote_addr/
    );
    assert.match(
        http,
        /rate=5r\/m/
    );
    assert.match(
        http,
        /"\/api\/pos\/staff\/unlock" \$binary_remote_addr/
    );
    assert.match(
        http,
        /rate=30r\/m/
    );

    for (const source of [http, https, template]) {
        assert.match(
            source,
            /limit_req zone=admin_login burst=5 nodelay/
        );
        assert.match(
            source,
            /limit_req zone=staff_unlock burst=15 nodelay/
        );
        assert.match(
            source,
            /limit_req_status 429/
        );
    }
});

test("production nginx accepts backend-supported 5 MB image uploads", () => {
    for (const source of [http, https, template]) {
        assert.match(
            source,
            /client_max_body_size 6m/
        );
    }
});

test("HTTPS production nginx emits baseline browser security headers", () => {
    assert.match(
        https,
        /X-Content-Type-Options "nosniff"/
    );
    assert.match(
        https,
        /X-Frame-Options "SAMEORIGIN"/
    );
    assert.match(
        https,
        /Referrer-Policy "strict-origin-when-cross-origin"/
    );
    assert.match(
        https,
        /Strict-Transport-Security "max-age=63072000; includeSubDomains"/
    );
});
