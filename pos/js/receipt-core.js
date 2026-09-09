(function () {
    "use strict";

    const TAX_MODES = new Set([
        "NONE",
        "INCLUDED",
        "ADDED",
    ]);

    function requireNonnegativeCents(
        value,
        name
    ) {
        if (
            !Number.isInteger(value) ||
            value < 0
        ) {
            throw new Error(
                `${name} must be a non-negative integer`
            );
        }

        return value;
    }

    function parseRate(value) {
        const text = String(value).trim();

        const match = text.match(
            /^(\d+)(?:\.(\d+))?$/
        );

        if (!match) {
            throw new Error(
                "taxRate must be a non-negative decimal fraction"
            );
        }

        const whole = match[1];
        const fraction = match[2] || "";

        const denominator =
            10n ** BigInt(fraction.length);

        const numerator = BigInt(
            whole + fraction
        );

        return {
            numerator,
            denominator,
            text,
        };
    }

    function roundFraction(
        numerator,
        denominator
    ) {
        if (denominator <= 0n) {
            throw new Error(
                "Invalid rounding denominator"
            );
        }

        return Number(
            (
                (numerator * 2n) +
                denominator
            ) /
            (denominator * 2n)
        );
    }

    function calculateTax(input) {
        const merchandiseCents =
            requireNonnegativeCents(
                input.merchandiseCents,
                "merchandiseCents"
            );

        const discountCents =
            requireNonnegativeCents(
                input.discountCents ?? 0,
                "discountCents"
            );

        const tipCents =
            requireNonnegativeCents(
                input.tipCents,
                "tipCents"
            );

        const taxMode =
            String(input.taxMode || "")
                .toUpperCase();

        if (!TAX_MODES.has(taxMode)) {
            throw new Error(
                "Unsupported tax mode"
            );
        }

        const rate =
            parseRate(input.taxRate);

        if (
            discountCents >
            merchandiseCents
        ) {
            throw new Error(
                "discountCents cannot exceed merchandiseCents"
            );
        }

        const netMerchandiseCents =
            merchandiseCents -
            discountCents;

        let taxCents = 0;

        if (taxMode === "INCLUDED") {
            taxCents = roundFraction(
                BigInt(netMerchandiseCents) *
                    rate.numerator,
                rate.denominator +
                    rate.numerator
            );
        }

        if (taxMode === "ADDED") {
            taxCents = roundFraction(
                BigInt(netMerchandiseCents) *
                    rate.numerator,
                rate.denominator
            );
        }

        const totalCents =
            netMerchandiseCents +
            (
                taxMode === "ADDED"
                    ? taxCents
                    : 0
            ) +
            tipCents;

        return {
            taxCents,
            totalCents,
        };
    }

    function centsToMoney(
        value,
        name = "money"
    ) {
        requireNonnegativeCents(
            value,
            name
        );

        const pesos =
            Math.floor(value / 100);

        const cents =
            String(value % 100)
                .padStart(2, "0");

        return `${pesos}.${cents}`;
    }

    function moneyToCents(
        value,
        name
    ) {
        if (
            typeof value !== "string" ||
            !/^\d+\.\d{2}$/.test(value)
        ) {
            throw new Error(
                `${name} must be a non-negative two-decimal money string`
            );
        }

        const [whole, fraction] =
            value.split(".");

        const cents =
            (
                Number(whole) * 100
            ) +
            Number(fraction);

        if (!Number.isSafeInteger(cents)) {
            throw new Error(
                `${name} is outside the safe money range`
            );
        }

        return cents;
    }

    function detachedClone(value) {
        if (value === null) {
            return null;
        }

        return JSON.parse(
            JSON.stringify(value)
        );
    }

    function buildCustomer(customer) {
        if (customer === null || customer === undefined) {
            return null;
        }

        return {
            name: String(
                customer.name || ""
            ),
        };
    }

    function buildModifiers(modifiers) {
        if (!Array.isArray(modifiers)) {
            return [];
        }

        return modifiers
            .filter(
                (modifier) =>
                    modifier.customer_visible === true
            )
            .map(
                (modifier) => ({
                    name: String(
                        modifier.name || ""
                    ),
                    price_delta:
                        centsToMoney(
                            modifier.price_delta_cents ?? 0,
                            "modifier.price_delta_cents"
                        ),
                })
            );
    }

    function buildItems(items) {
        if (!Array.isArray(items)) {
            throw new Error(
                "items must be an array"
            );
        }

        return items.map(
            (item) => ({
                product_id:
                    item.product_id,
                name:
                    String(item.name || ""),
                quantity:
                    item.quantity,
                unit_price:
                    centsToMoney(
                        item.unit_price_cents,
                        "item.unit_price_cents"
                    ),
                line_total:
                    centsToMoney(
                        item.line_total_cents,
                        "item.line_total_cents"
                    ),
                modifiers:
                    buildModifiers(
                        item.modifiers
                    ),
            })
        );
    }

    function buildSnapshot(input) {
        if (
            !input ||
            typeof input !== "object"
        ) {
            throw new Error(
                "snapshot input is required"
            );
        }

        const totals =
            input.totals || {};

        const payment =
            input.payment || {};

        const snapshot = {
            schema_version: 1,
            order_uuid:
                input.order_uuid,
            folio:
                input.folio,
            sold_at:
                input.sold_at,
            currency:
                input.currency,
            business:
                detachedClone(
                    input.business
                ),
            branch:
                detachedClone(
                    input.branch
                ),
            terminal:
                detachedClone(
                    input.terminal
                ),
            customer:
                buildCustomer(
                    input.customer
                ),
            items:
                buildItems(
                    input.items
                ),
            totals: {
                subtotal:
                    centsToMoney(
                        totals.subtotal_cents,
                        "totals.subtotal_cents"
                    ),
                discount:
                    centsToMoney(
                        totals.discount_cents ?? 0,
                        "totals.discount_cents"
                    ),
                tax_mode:
                    String(
                        totals.tax_mode || ""
                    ).toUpperCase(),
                tax_rate:
                    String(
                        totals.tax_rate
                    ),
                tax:
                    centsToMoney(
                        totals.tax_cents,
                        "totals.tax_cents"
                    ),
                tip:
                    centsToMoney(
                        totals.tip_cents,
                        "totals.tip_cents"
                    ),
                total:
                    centsToMoney(
                        totals.total_cents,
                        "totals.total_cents"
                    ),
            },
            payment: {
                method:
                    payment.method,
                amount:
                    centsToMoney(
                        payment.amount_cents,
                        "payment.amount_cents"
                    ),
                amount_tendered:
                    payment.method === "CASH"
                        ? centsToMoney(
                            payment.amount_tendered_cents,
                            "payment.amount_tendered_cents"
                        )
                        : null,
                change_due:
                    payment.method === "CASH"
                        ? centsToMoney(
                            payment.change_due_cents,
                            "payment.change_due_cents"
                        )
                        : null,
            },
        };

        validateSnapshot(snapshot);

        return snapshot;
    }

    function requireText(
        value,
        name
    ) {
        if (
            typeof value !== "string" ||
            value.trim() === ""
        ) {
            throw new Error(
                `${name} is required`
            );
        }
    }

    function validateCustomer(customer) {
        if (customer === null) {
            return;
        }

        if (
            !customer ||
            typeof customer !== "object" ||
            Array.isArray(customer)
        ) {
            throw new Error(
                "customer must be null or an object"
            );
        }

        const keys =
            Object.keys(customer);

        if (
            keys.length !== 1 ||
            keys[0] !== "name"
        ) {
            throw new Error(
                "customer may contain only name"
            );
        }

        requireText(
            customer.name,
            "customer.name"
        );
    }

    function validateItem(
        item,
        index
    ) {
        if (
            !item ||
            typeof item !== "object"
        ) {
            throw new Error(
                `items[${index}] is invalid`
            );
        }

        if (
            !Number.isInteger(
                item.quantity
            ) ||
            item.quantity <= 0
        ) {
            throw new Error(
                "item quantity must be positive"
            );
        }

        requireText(
            item.name,
            "item.name"
        );

        const unitPriceCents =
            moneyToCents(
                item.unit_price,
                "item.unit_price"
            );

        const lineTotalCents =
            moneyToCents(
                item.line_total,
                "item.line_total"
            );

        if (
            unitPriceCents *
                item.quantity !==
            lineTotalCents
        ) {
            throw new Error(
                "Inconsistent item line total"
            );
        }

        if (!Array.isArray(item.modifiers)) {
            throw new Error(
                "item.modifiers must be an array"
            );
        }

        for (
            const modifier
            of item.modifiers
        ) {
            requireText(
                modifier.name,
                "modifier.name"
            );

            moneyToCents(
                modifier.price_delta,
                "modifier.price_delta"
            );
        }

        return lineTotalCents;
    }

    function validateSnapshot(snapshot) {
        if (
            !snapshot ||
            typeof snapshot !== "object"
        ) {
            throw new Error(
                "snapshot is required"
            );
        }

        if (
            snapshot.schema_version !== 1
        ) {
            throw new Error(
                "Unsupported receipt schema version"
            );
        }

        requireText(
            snapshot.order_uuid,
            "order_uuid"
        );

        requireText(
            snapshot.folio,
            "folio"
        );

        requireText(
            snapshot.sold_at,
            "sold_at"
        );

        requireText(
            snapshot.currency,
            "currency"
        );

        if (!snapshot.business) {
            throw new Error(
                "business is required"
            );
        }

        if (!snapshot.branch) {
            throw new Error(
                "branch is required"
            );
        }

        if (!snapshot.terminal) {
            throw new Error(
                "terminal is required"
            );
        }

        validateCustomer(
            snapshot.customer
        );

        if (!Array.isArray(snapshot.items)) {
            throw new Error(
                "items must be an array"
            );
        }

        let itemSubtotalCents = 0;

        for (
            let index = 0;
            index < snapshot.items.length;
            index += 1
        ) {
            itemSubtotalCents +=
                validateItem(
                    snapshot.items[index],
                    index
                );
        }

        const totals =
            snapshot.totals;

        if (
            !totals ||
            typeof totals !== "object"
        ) {
            throw new Error(
                "totals are required"
            );
        }

        if (
            !TAX_MODES.has(
                totals.tax_mode
            )
        ) {
            throw new Error(
                "Unsupported tax mode"
            );
        }

        const subtotalCents =
            moneyToCents(
                totals.subtotal,
                "totals.subtotal"
            );

        const discountCents =
            moneyToCents(
                totals.discount,
                "totals.discount"
            );

        const taxCents =
            moneyToCents(
                totals.tax,
                "totals.tax"
            );

        const tipCents =
            moneyToCents(
                totals.tip,
                "totals.tip"
            );

        const totalCents =
            moneyToCents(
                totals.total,
                "totals.total"
            );

        parseRate(
            totals.tax_rate
        );

        if (
            subtotalCents !==
            itemSubtotalCents
        ) {
            throw new Error(
                "Inconsistent receipt subtotal"
            );
        }

        const calculated =
            calculateTax({
                merchandiseCents:
                    subtotalCents,
                discountCents,
                taxMode:
                    totals.tax_mode,
                taxRate:
                    totals.tax_rate,
                tipCents,
            });

        if (
            calculated.taxCents !==
            taxCents
        ) {
            throw new Error(
                "Inconsistent receipt tax"
            );
        }

        if (
            calculated.totalCents !==
            totalCents
        ) {
            throw new Error(
                "Inconsistent receipt total"
            );
        }

        const payment =
            snapshot.payment;

        if (
            !payment ||
            typeof payment !== "object"
        ) {
            throw new Error(
                "payment is required"
            );
        }

        requireText(
            payment.method,
            "payment.method"
        );

        const paymentAmountCents =
            moneyToCents(
                payment.amount,
                "payment.amount"
            );

        if (
            paymentAmountCents !==
            totalCents
        ) {
            throw new Error(
                "Payment amount does not match receipt total"
            );
        }

        if (
            payment.method === "CASH"
        ) {
            const tenderedCents =
                moneyToCents(
                    payment.amount_tendered,
                    "payment.amount_tendered"
                );

            const changeCents =
                moneyToCents(
                    payment.change_due,
                    "payment.change_due"
                );

            if (
                tenderedCents <
                paymentAmountCents
            ) {
                throw new Error(
                    "Cash tendered is insufficient"
                );
            }

            if (
                tenderedCents -
                    paymentAmountCents !==
                changeCents
            ) {
                throw new Error(
                    "Inconsistent cash change"
                );
            }
        }

        return true;
    }

    window.CofiPosReceipt = {
        calculateTax,
        buildSnapshot,
        validateSnapshot,
    };
})();
