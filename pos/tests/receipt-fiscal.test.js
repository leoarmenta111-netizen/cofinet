const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT =
    path.resolve(__dirname, "..");

const configPath =
    path.join(
        ROOT,
        "js",
        "receipt-fiscal-config.js"
    );

const rendererPath =
    path.join(
        ROOT,
        "js",
        "receipt-renderer.js"
    );

const corePath =
    path.join(
        ROOT,
        "js",
        "receipt-core.js"
    );

const indexPath =
    path.join(
        ROOT,
        "index.html"
    );

const swPath =
    path.join(
        ROOT,
        "sw.js"
    );

const qrPath =
    path.join(
        ROOT,
        "assets",
        "facturacion-qr.png"
    );


test(
    "Ixtapa fiscal configuration is exact",
    () => {
        const context = {
            window: {},
        };

        vm.createContext(context);

        vm.runInContext(
            fs.readFileSync(
                configPath,
                "utf8"
            ),
            context
        );

        const fiscal =
            context.window
                .CofiPosFiscalConfig
                .getForBranch("ixtapa");

        assert.equal(
            fiscal.rfc,
            "HETA0203028E0"
        );

        assert.equal(
            fiscal.fiscal_address,
            "CARR A LAS PALMAS 1179 E, LAS JUNTAS, JALISCO"
        );

        assert.equal(
            fiscal.billing_url,
            "https://forms.gle/V6UpN26P8wkSfYtT9"
        );

        assert.equal(
            fiscal.billing_qr_ref,
            "./assets/facturacion-qr.png"
        );
    }
);


test(
    "unknown branch has no fiscal override",
    () => {
        const context = {
            window: {},
        };

        vm.createContext(context);

        vm.runInContext(
            fs.readFileSync(
                configPath,
                "utf8"
            ),
            context
        );

        assert.equal(
            context.window
                .CofiPosFiscalConfig
                .getForBranch("unknown"),
            null
        );
    }
);


test(
    "billing QR is stored locally",
    () => {
        assert.equal(
            fs.existsSync(qrPath),
            true
        );

        const header =
            fs.readFileSync(qrPath)
                .subarray(0, 8)
                .toString("hex");

        assert.equal(
            header,
            "89504e470d0a1a0a"
        );
    }
);


test(
    "receipt core freezes fiscal context",
    () => {
        const source =
            fs.readFileSync(
                corePath,
                "utf8"
            );

        assert.match(
            source,
            /fiscal_address/
        );

        assert.match(
            source,
            /billing_qr_ref/
        );

        assert.match(
            source,
            /validateFiscal/
        );
    }
);


test(
    "renderer prints fiscal and billing section",
    () => {
        const source =
            fs.readFileSync(
                rendererPath,
                "utf8"
            );

        assert.match(
            source,
            /DATOS FISCALES/
        );

        assert.match(
            source,
            /receipt-billing-qr/
        );

        assert.match(
            source,
            /billing_qr_ref/
        );
    }
);


test(
    "POS shell exposes fiscal configuration and app scripts",
    () => {
        const html =
            fs.readFileSync(
                path.join(
                    __dirname,
                    "..",
                    "index.html"
                ),
                "utf8"
            );

        assert.match(
            html,
            /\.\/js\/receipt-fiscal-config\.js(?:\?v=\d+)?/
        );

        assert.match(
            html,
            /\.\/js\/app\.js(?:\?v=\d+)?/
        );
    }
);

test(
    "service worker precaches fiscal assets",
    () => {
        const source =
            fs.readFileSync(
                swPath,
                "utf8"
            );

        assert.match(
            source,
            /const SHELL_CACHE = "cofi-pos-shell-v\d+";/
        );

        assert.match(
            source,
            /receipt-fiscal-config\.js/
        );

        assert.match(
            source,
            /facturacion-qr\.png/
        );
    }
);


test(
    "Ixtapa receipt uses local Coficenter logo",
    () => {
        const context = {
            window: {},
        };

        vm.createContext(context);

        vm.runInContext(
            fs.readFileSync(
                configPath,
                "utf8"
            ),
            context
        );

        const fiscal =
            context.window
                .CofiPosFiscalConfig
                .getForBranch("ixtapa");

        assert.equal(
            fiscal.logo_ref,
            "./assets/coficenter-ticket-logo.png"
        );

        const logoPath =
            path.join(
                ROOT,
                "assets",
                "coficenter-ticket-logo.png"
            );

        assert.equal(
            fs.existsSync(logoPath),
            true
        );

        const sw =
            fs.readFileSync(
                swPath,
                "utf8"
            );

        assert.match(
            sw,
            /coficenter-ticket-logo\.png/
        );
    }
);
