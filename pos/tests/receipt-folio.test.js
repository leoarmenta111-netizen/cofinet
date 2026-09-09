const test = require("node:test");
const assert = require("node:assert/strict");

global.window = {};

require("../js/folio.js");

const { generate } = window.CofiPosFolio;

const soldAt = new Date("2026-09-08T18:30:00.000Z");
const timeZone = "America/Bahia_Banderas";

function generateFolio(overrides = {}) {
    return generate({
        branchPrefix: "NV",
        soldAt,
        timeZone,
        ...overrides,
    });
}

test("folio usa formato PREFIX-YYMMDD-XXXXXXXX", () => {
    const folio = generateFolio();

    assert.match(
        folio,
        /^NV-\d{6}-[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{8}$/
    );
});

test("folio normaliza prefix a mayusculas", () => {
    const folio = generateFolio({
        branchPrefix: "nv",
    });

    assert.match(folio, /^NV-/);
});

test("folio usa fecha local de la sucursal", () => {
    const folio = generateFolio({
        soldAt: new Date("2026-09-09T04:30:00.000Z"),
    });

    assert.match(folio, /^NV-260908-/);
});

test("suffix tiene exactamente 8 caracteres Crockford Base32", () => {
    const suffix = generateFolio().split("-")[2];

    assert.equal(suffix.length, 8);
    assert.match(
        suffix,
        /^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{8}$/
    );
    assert.doesNotMatch(suffix, /[ILOU]/);
});

test("dos folios del mismo momento son distintos", () => {
    const first = generateFolio();
    const second = generateFolio();

    assert.notEqual(first, second);
});

test("folio nuevo no incorpora database order id", () => {
    const folio = generateFolio({
        orderId: 987654321,
    });

    assert.equal(
        folio.includes("987654321"),
        false
    );
});

test("folio usa cinco bytes criptograficos y todos afectan el suffix", () => {
    const originalCrypto = Object.getOwnPropertyDescriptor(
        globalThis,
        "crypto"
    );
    const originalRandom = Math.random;

    function withBytes(bytes) {
        let requestedLength = null;

        Object.defineProperty(
            globalThis,
            "crypto",
            {
                configurable: true,
                writable: true,
                value: {
                    getRandomValues(view) {
                        requestedLength = view.length;
                        view.set(bytes);
                        return view;
                    },
                },
            }
        );

        Math.random = () => {
            throw new Error("Math.random must not be used");
        };

        const folio = generateFolio();

        assert.equal(requestedLength, 5);

        return folio;
    }

    try {
        const first = withBytes([0, 0, 0, 0, 0]);
        const second = withBytes([0, 0, 0, 0, 1]);

        assert.notEqual(first, second);
    } finally {
        Math.random = originalRandom;

        if (originalCrypto) {
            Object.defineProperty(
                globalThis,
                "crypto",
                originalCrypto
            );
        } else {
            delete globalThis.crypto;
        }
    }
});

test("folio rechaza prefix o timezone invalidos", () => {
    assert.throws(() => {
        generateFolio({
            branchPrefix: "N-",
        });
    });

    assert.throws(() => {
        generateFolio({
            timeZone: "Mars/Olympus",
        });
    });
});
