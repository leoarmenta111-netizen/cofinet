(function () {
    "use strict";

    const CROCKFORD =
        "0123456789ABCDEFGHJKMNPQRSTVWXYZ";

    function normalizePrefix(value) {
        const prefix = String(value || "")
            .trim()
            .toUpperCase();

        if (!/^[A-Z0-9]{2,8}$/.test(prefix)) {
            throw new Error(
                "branchPrefix must be 2-8 ASCII alphanumeric characters"
            );
        }

        return prefix;
    }

    function validateTimeZone(timeZone) {
        if (
            typeof timeZone !== "string" ||
            timeZone.trim() === ""
        ) {
            throw new Error("timeZone is required");
        }

        try {
            new Intl.DateTimeFormat(
                "en-US",
                {
                    timeZone,
                }
            ).format(new Date());
        } catch (error) {
            throw new Error("Invalid timeZone");
        }

        return timeZone;
    }

    function formatLocalDate(soldAt, timeZone) {
        if (
            !(soldAt instanceof Date) ||
            Number.isNaN(soldAt.getTime())
        ) {
            throw new Error("soldAt must be a valid Date");
        }

        const formatter = new Intl.DateTimeFormat(
            "en-US",
            {
                timeZone,
                year: "2-digit",
                month: "2-digit",
                day: "2-digit",
            }
        );

        const parts = formatter.formatToParts(soldAt);

        const values = {};

        for (const part of parts) {
            if (
                part.type === "year" ||
                part.type === "month" ||
                part.type === "day"
            ) {
                values[part.type] = part.value;
            }
        }

        return (
            values.year +
            values.month +
            values.day
        );
    }

    function generateSuffix() {
        if (
            !globalThis.crypto ||
            typeof globalThis.crypto.getRandomValues !==
                "function"
        ) {
            throw new Error(
                "Cryptographic randomness is unavailable"
            );
        }

        const bytes = new Uint8Array(5);

        globalThis.crypto.getRandomValues(bytes);

        let value = 0n;

        for (const byte of bytes) {
            value =
                (value << 8n) |
                BigInt(byte);
        }

        let suffix = "";

        for (let shift = 35; shift >= 0; shift -= 5) {
            const index = Number(
                (value >> BigInt(shift)) & 31n
            );

            suffix += CROCKFORD[index];
        }

        return suffix;
    }

    function generate({
        branchPrefix,
        soldAt,
        timeZone,
    }) {
        const prefix =
            normalizePrefix(branchPrefix);

        const zone =
            validateTimeZone(timeZone);

        const localDate =
            formatLocalDate(soldAt, zone);

        const suffix =
            generateSuffix();

        return `${prefix}-${localDate}-${suffix}`;
    }

    window.CofiPosFolio = {
        generate,
    };
})();
