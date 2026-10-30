const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const ROOT = path.resolve(__dirname, "..");

test("customer kiosk es una PWA instalable", () => {
    const html = fs.readFileSync(
        path.join(ROOT, "index.html"),
        "utf8"
    );

    const manifest = JSON.parse(
        fs.readFileSync(
            path.join(
                ROOT,
                "manifest-ixtapa.webmanifest"
            ),
            "utf8"
        )
    );

    const sw = fs.readFileSync(
        path.join(ROOT, "sw.js"),
        "utf8"
    );

    assert.match(
        html,
        /manifest-ixtapa\.webmanifest/
    );

    assert.match(
        html,
        /js\/pwa\.js/
    );

    assert.equal(
        manifest.display,
        "fullscreen"
    );

    assert.equal(
        manifest.scope,
        "./"
    );

    assert.match(
        manifest.start_url,
        /branch=ixtapa/
    );

    assert.match(
        manifest.start_url,
        /device=KIOSK-IXTAPA-01/
    );

    assert.ok(
        manifest.icons.some(
            icon => icon.sizes === "192x192"
        )
    );

    assert.ok(
        manifest.icons.some(
            icon => icon.sizes === "512x512"
        )
    );

    assert.match(
        sw,
        /addEventListener\("fetch"/
    );
});
