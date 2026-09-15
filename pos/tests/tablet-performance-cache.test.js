const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const index = fs.readFileSync("pos/index.html", "utf8");
const sw = fs.readFileSync("pos/sw.js", "utf8");

test("tablet performance release forces fresh CSS cache", () => {
    assert.match(
        index,
        /css\/pos\.css\?v=27/
    );

    assert.match(
        sw,
        /const SHELL_CACHE = "cofi-pos-shell-v22";/
    );

    assert.match(
        sw,
        /"\.\/css\/pos\.css\?v=27"/
    );
});
