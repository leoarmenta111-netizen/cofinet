const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(
    path.join(
        __dirname,
        "..",
        "catalog.html"
    ),
    "utf8"
);

test(
    "modifier option editor exposes image controls",
    () => {
        assert.match(
            html,
            /id="option-image-file"/
        );

        assert.match(
            html,
            /id="option-image-preview"/
        );

        assert.match(
            html,
            /id="select-option-image"/
        );

        assert.match(
            html,
            /id="remove-option-image"/
        );
    }
);

test(
    "modifier option uses multipart image upload",
    () => {
        assert.match(
            html,
            /new FormData\(\)/
        );

        assert.match(
            html,
            /formData\.append\(\s*"image"/
        );

        assert.match(
            html,
            /modifier-options\/\$\{optionId\}\/image/
        );
    }
);

test(
    "modifier option image supports delete",
    () => {
        assert.match(
            html,
            /deleteModifierOptionImage/
        );

        assert.match(
            html,
            /method:\s*"DELETE"/
        );
    }
);

test(
    "modifier option renders image with monogram fallback",
    () => {
        assert.match(
            html,
            /option\.image_url/
        );

        assert.match(
            html,
            /modifier-option-thumbnail/
        );
    }
);
