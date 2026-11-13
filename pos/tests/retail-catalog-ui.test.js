const assert =
    require("node:assert/strict");

const fs =
    require("node:fs");

const path =
    require("node:path");

const test =
    require("node:test");


const html =
    fs.readFileSync(
        path.join(
            process.cwd(),
            "pos/papeleria/index.html"
        ),
        "utf8"
    );

const app =
    fs.readFileSync(
        path.join(
            process.cwd(),
            "pos/js/retail-app.js"
        ),
        "utf8"
    );


test(
    "papeleria shell loads retail catalog engine before retail app",
    () => {
        const catalogScript =
            html.indexOf(
                '/pos/js/retail-catalog.js'
            );

        const appScript =
            html.indexOf(
                '/pos/js/retail-app.js'
            );

        assert.notEqual(
            catalogScript,
            -1,
            "retail-catalog.js must be loaded"
        );

        assert.notEqual(
            appScript,
            -1,
            "retail-app.js must be loaded"
        );

        assert.ok(
            catalogScript < appScript,
            "catalog engine must load before app"
        );
    }
);


test(
    "papeleria shell provides presentation selector dialog",
    () => {
        assert.match(
            html,
            /id=["']retail-presentation-modal["']/
        );

        assert.match(
            html,
            /id=["']retail-presentation-title["']/
        );

        assert.match(
            html,
            /id=["']retail-presentation-options["']/
        );
    }
);


test(
    "retail app loads server catalog",
    () => {
        assert.match(
            app,
            /CofiRetailAPI/
        );

        assert.match(
            app,
            /\.loadCatalog\s*\(/
        );
    }
);


test(
    "retail app connects search input to catalog filtering",
    () => {
        assert.match(
            app,
            /retail-search/
        );

        assert.match(
            app,
            /CofiRetailCatalog/
        );

        assert.match(
            app,
            /\.search\s*\(/
        );
    }
);


test(
    "retail app supports exact barcode scanner lookup",
    () => {
        assert.match(
            app,
            /\.findBarcode\s*\(/
        );

        assert.match(
            app,
            /keydown|keyup|submit/
        );
    }
);


test(
    "retail app uses presentation decision before adding products",
    () => {
        assert.match(
            app,
            /\.selectionFor\s*\(/
        );

        assert.match(
            app,
            /CHOOSE_PRESENTATION/
        );
    }
);


test(
    "retail app adds selected item to CofiRetailCart",
    () => {
        assert.match(
            app,
            /CofiRetailCart/
        );

        assert.match(
            app,
            /\.add\s*\(/
        );

        assert.match(
            app,
            /presentation_id/
        );
    }
);


test(
    "retail app renders catalog and cart into existing shell",
    () => {
        assert.match(
            app,
            /retail-product-grid/
        );

        assert.match(
            app,
            /retail-cart-lines/
        );

        assert.match(
            app,
            /retail-cart-total/
        );
    }
);
