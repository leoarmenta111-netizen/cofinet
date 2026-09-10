const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(
    path.resolve(
        __dirname,
        "../js/app.js"
    ),
    "utf8"
);

test(
    "checkout converts frozen ISO soldAt to Date only for folio generation",
    () => {
        assert.match(
            source,
            /const\s+soldAtDate\s*=\s*new Date\(\s*soldAt\s*\)/,
            "checkout must create a Date from the frozen ISO soldAt"
        );

        assert.match(
            source,
            /CofiPosFolio[\s\S]*?\.generate\(\{[\s\S]*?soldAt:\s*soldAtDate/,
            "folio generator must receive the Date instance"
        );
    }
);

test(
    "frozen receipt and payload keep original ISO soldAt",
    () => {
        assert.match(
            source,
            /sold_at:\s*[\r\n\s]*soldAt/,
            "receipt snapshot must keep the original ISO timestamp"
        );

        assert.match(
            source,
            /payload\.created_at_client\s*=\s*[\r\n\s]*soldAt/,
            "order payload must keep the original ISO timestamp"
        );
    }
);
