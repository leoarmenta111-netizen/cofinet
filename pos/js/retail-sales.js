window.CofiRetailSales = (() => {
    function number(
        value,
        field
    ) {
        const result =
            Number(value);

        if (
            !Number.isFinite(result)
        ) {
            throw new Error(
                `${field} must be numeric`
            );
        }

        return result;
    }


    function requireUuid(
        value,
        field
    ) {
        const normalized =
            String(
                value || ""
            ).trim();

        if (!normalized) {
            throw new Error(
                `${field} is required`
            );
        }

        return normalized;
    }


    function cartLines(cart) {
        if (
            !window.CofiRetailCart
            || typeof (
                window
                    .CofiRetailCart
                    .checkoutLines
            ) !== "function"
        ) {
            throw new Error(
                "Retail cart is unavailable"
            );
        }

        const lines =
            window.CofiRetailCart
                .checkoutLines(cart);

        if (
            !Array.isArray(lines)
            || lines.length === 0
        ) {
            throw new Error(
                "Sale requires at least one line"
            );
        }

        return lines;
    }


    function buildHeldPayload(
        cart,
        label
    ) {
        const lines =
            cartLines(cart)
                .map(
                    line => ({
                        item_id:
                            line.item_id,

                        presentation_id:
                            line
                                .presentation_id,

                        quantity:
                            line.quantity,
                    })
                );

        const normalizedLabel =
            String(
                label || ""
            ).trim();

        return {
            label:
                normalizedLabel
                || "Venta en espera",

            lines,
        };
    }


    function buildCheckoutPayload({
        cart,
        saleUuid,
        paymentUuid,
        heldSaleUuid = null,
        paymentMethod,
        amountTendered = null,
        externalReference = null,
    }) {
        const method =
            String(
                paymentMethod || ""
            )
                .trim()
                .toUpperCase();

        if (
            method !== "CASH"
            && method !== "CARD"
        ) {
            throw new Error(
                "Unsupported payment method"
            );
        }

        const payload = {
            sale_uuid:
                requireUuid(
                    saleUuid,
                    "sale UUID"
                ),

            held_sale_uuid:
                heldSaleUuid
                    ? String(
                        heldSaleUuid
                    ).trim()
                    : null,

            lines:
                cartLines(cart),

            sale_discount_amount:
                0,

            payment_uuid:
                requireUuid(
                    paymentUuid,
                    "payment UUID"
                ),

            payment_method:
                method,

            amount_tendered:
                null,

            external_reference:
                null,
        };

        if (method === "CASH") {
            const tendered =
                number(
                    amountTendered,
                    "cash tendered"
                );

            if (tendered < 0) {
                throw new Error(
                    "Cash tendered must be nonnegative"
                );
            }

            payload.amount_tendered =
                tendered;
        }

        if (method === "CARD") {
            const reference =
                String(
                    externalReference
                    || ""
                ).trim();

            if (!reference) {
                throw new Error(
                    "Card reference is required"
                );
            }

            payload.external_reference =
                reference;
        }

        return payload;
    }


    function serverTotal(sale) {
        if (!sale) {
            throw new Error(
                "Sale response is required"
            );
        }

        const total =
            number(
                sale.total,
                "server total"
            );

        if (total < 0) {
            throw new Error(
                "Server total is invalid"
            );
        }

        return total;
    }


    function paymentSummary(sale) {
        const total =
            serverTotal(sale);

        const payments =
            Array.isArray(
                sale.payments
            )
                ? sale.payments
                : [];

        if (!payments.length) {
            throw new Error(
                "Sale payment is missing"
            );
        }

        const payment =
            payments[0];

        const method =
            String(
                payment.method || ""
            )
                .trim()
                .toUpperCase();

        return {
            method,

            total,

            amount:
                number(
                    payment.amount,
                    "payment amount"
                ),

            amountTendered:
                payment
                    .amount_tendered
                    == null
                    ? null
                    : number(
                        payment
                            .amount_tendered,
                        "amount tendered"
                    ),

            changeDue:
                payment.change_due
                    == null
                    ? null
                    : number(
                        payment
                            .change_due,
                        "change due"
                    ),

            externalReference:
                payment
                    .external_reference
                    == null
                    ? null
                    : String(
                        payment
                            .external_reference
                    ),
        };
    }


    return {
        buildHeldPayload,
        buildCheckoutPayload,
        serverTotal,
        paymentSummary,
    };
})();
