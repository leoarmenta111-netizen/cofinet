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
                modifier =>
                    modifier.customer_visible === true
            )
            .map(modifier => {
                const priceDeltaCents =
                    modifier.price_delta_cents ?? 0;

                requireNonnegativeCents(
                    priceDeltaCents,
                    "modifier.price_delta_cents"
                );

                return {
                    modifier_group_id:
                        modifier.modifier_group_id ??
                        modifier.group_id ??
                        null,

                    modifier_option_id:
                        modifier.modifier_option_id ??
                        modifier.option_id ??
                        null,

                    group_name:
                        modifier.group_name == null
                            ? null
                            : String(
                                modifier.group_name
                            ),

                    option_name:
                        String(
                            modifier.option_name ??
                            modifier.name ??
                            ""
                        ),

                    price_delta_cents:
                        priceDeltaCents,
                };
            });
    }

    function buildItems(items) {
        if (!Array.isArray(items)) {
            throw new Error(
                "items must be an array"
            );
        }

        return items.map(
            item => ({
                product_id:
                    item.product_id,

                product_name:
                    String(
                        item.product_name ??
                        item.name ??
                        ""
                    ),

                quantity:
                    item.quantity,

                unit_price_cents:
                    item.unit_price_cents,

                line_total_cents:
                    item.line_total_cents,

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

        const business =
            input.business || {};

        const branch =
            input.branch || {};

        const terminal =
            input.terminal || {};

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

            business: {
                business_name:
                    String(
                        business.business_name ??
                        business.name ??
                        ""
                    ),

                logo_ref:
                    business.logo_ref ??
                    null,

                phone:
                    business.phone ??
                    null,

                web_social:
                    business.web_social ??
                    null,

                footer_message:
                    business.footer_message ??
                    null,
            },

            branch: {
                branch_code:
                    String(
                        branch.branch_code ??
                        branch.code ??
                        ""
                    ),

                branch_name:
                    String(
                        branch.branch_name ??
                        branch.name ??
                        ""
                    ),

                address:
                    branch.address ??
                    null,

                phone:
                    branch.phone ??
                    null,
            },

            terminal: {
                terminal_id:
                    String(
                        terminal.terminal_id ??
                        terminal.id ??
                        ""
                    ),
            },

            customer:
                buildCustomer(
                    input.customer
                ),

            items:
                buildItems(
                    input.items
                ),

            totals: {
                subtotal_cents:
                    totals.subtotal_cents,

                discount_cents:
                    totals.discount_cents ?? 0,

                tax_mode:
                    String(
                        totals.tax_mode || ""
                    ).toUpperCase(),

                tax_rate:
                    String(
                        totals.tax_rate
                    ),

                tax_cents:
                    totals.tax_cents,

                tip_cents:
                    totals.tip_cents,

                total_cents:
                    totals.total_cents,
            },

            payment: {
                method:
                    String(
                        payment.method || ""
                    ).toUpperCase(),

                amount_cents:
                    payment.amount_cents,

                amount_tendered_cents:
                    payment.amount_tendered_cents ??
                    null,

                change_due_cents:
                    payment.change_due_cents ??
                    null,
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
                item.product_id
            )
        ) {
            throw new Error(
                "item product_id must be an integer"
            );
        }

        requireText(
            item.product_name,
            "item.product_name"
        );

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

        requireNonnegativeCents(
            item.unit_price_cents,
            "item.unit_price_cents"
        );

        requireNonnegativeCents(
            item.line_total_cents,
            "item.line_total_cents"
        );

        if (
            item.line_total_cents !==
            item.unit_price_cents *
                item.quantity
        ) {
            throw new Error(
                "Inconsistent receipt line total"
            );
        }

        if (
            !Array.isArray(
                item.modifiers
            )
        ) {
            throw new Error(
                "item modifiers must be an array"
            );
        }

        for (
            const modifier
            of item.modifiers
        ) {
            if (
                !modifier ||
                typeof modifier !== "object"
            ) {
                throw new Error(
                    "Invalid receipt modifier"
                );
            }

            if (
                modifier.modifier_group_id !== null &&
                modifier.modifier_group_id !== undefined &&
                !Number.isInteger(
                    modifier.modifier_group_id
                )
            ) {
                throw new Error(
                    "Invalid modifier_group_id"
                );
            }

            if (
                modifier.modifier_option_id !== null &&
                modifier.modifier_option_id !== undefined &&
                !Number.isInteger(
                    modifier.modifier_option_id
                )
            ) {
                throw new Error(
                    "Invalid modifier_option_id"
                );
            }

            requireText(
                modifier.option_name,
                "modifier.option_name"
            );

            requireNonnegativeCents(
                modifier.price_delta_cents,
                "modifier.price_delta_cents"
            );
        }

        return item.line_total_cents;
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

        if (
            !snapshot.business ||
            typeof snapshot.business !== "object"
        ) {
            throw new Error(
                "business is required"
            );
        }

        requireText(
            snapshot.business.business_name,
            "business.business_name"
        );

        if (
            !snapshot.branch ||
            typeof snapshot.branch !== "object"
        ) {
            throw new Error(
                "branch is required"
            );
        }

        requireText(
            snapshot.branch.branch_code,
            "branch.branch_code"
        );

        requireText(
            snapshot.branch.branch_name,
            "branch.branch_name"
        );

        if (
            !snapshot.terminal ||
            typeof snapshot.terminal !== "object"
        ) {
            throw new Error(
                "terminal is required"
            );
        }

        requireText(
            snapshot.terminal.terminal_id,
            "terminal.terminal_id"
        );

        validateCustomer(
            snapshot.customer
        );

        if (
            !Array.isArray(
                snapshot.items
            ) ||
            snapshot.items.length === 0
        ) {
            throw new Error(
                "items must be a non-empty array"
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

        requireNonnegativeCents(
            totals.subtotal_cents,
            "totals.subtotal_cents"
        );

        requireNonnegativeCents(
            totals.discount_cents,
            "totals.discount_cents"
        );

        requireNonnegativeCents(
            totals.tax_cents,
            "totals.tax_cents"
        );

        requireNonnegativeCents(
            totals.tip_cents,
            "totals.tip_cents"
        );

        requireNonnegativeCents(
            totals.total_cents,
            "totals.total_cents"
        );

        parseRate(
            totals.tax_rate
        );

        if (
            totals.subtotal_cents !==
            itemSubtotalCents
        ) {
            throw new Error(
                "Inconsistent receipt subtotal"
            );
        }

        const calculated =
            calculateTax({
                merchandiseCents:
                    totals.subtotal_cents,

                discountCents:
                    totals.discount_cents,

                taxMode:
                    totals.tax_mode,

                taxRate:
                    totals.tax_rate,

                tipCents:
                    totals.tip_cents,
            });

        if (
            calculated.taxCents !==
            totals.tax_cents
        ) {
            throw new Error(
                "Inconsistent receipt tax"
            );
        }

        if (
            calculated.totalCents !==
            totals.total_cents
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

        if (
            ![
                "CASH",
                "CARD_EXTERNAL",
            ].includes(
                payment.method
            )
        ) {
            throw new Error(
                "Unsupported payment method"
            );
        }

        requireNonnegativeCents(
            payment.amount_cents,
            "payment.amount_cents"
        );

        if (
            payment.amount_cents !==
            totals.total_cents
        ) {
            throw new Error(
                "Inconsistent receipt payment amount"
            );
        }

        if (
            payment.method === "CASH"
        ) {
            requireNonnegativeCents(
                payment.amount_tendered_cents,
                "payment.amount_tendered_cents"
            );

            requireNonnegativeCents(
                payment.change_due_cents,
                "payment.change_due_cents"
            );

            if (
                payment.amount_tendered_cents <
                payment.amount_cents
            ) {
                throw new Error(
                    "Insufficient receipt cash"
                );
            }

            if (
                payment.change_due_cents !==
                payment.amount_tendered_cents -
                    payment.amount_cents
            ) {
                throw new Error(
                    "Inconsistent receipt change"
                );
            }
        }

        return true;
    }

    window.CofiPosReceipt = {
        calculateTax,
        centsToMoney,
        moneyToCents,
        buildSnapshot,
        validateSnapshot,
    };
})();
