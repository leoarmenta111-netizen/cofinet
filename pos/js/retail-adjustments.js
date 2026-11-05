(function () {
    "use strict";

    function requiredText(
        value,
        field
    ) {
        const normalized =
            String(value ?? "").trim();

        if (!normalized) {
            throw new Error(
                `${field} is required`
            );
        }

        return normalized;
    }


    function managerId(value) {
        const normalized =
            Number(value);

        if (
            !Number.isInteger(normalized)
            || normalized <= 0
        ) {
            throw new Error(
                "Manager staff ID is required"
            );
        }

        return normalized;
    }


    function refundMethod(value) {
        const normalized =
            String(value ?? "")
                .trim()
                .toUpperCase();

        if (
            normalized !== "CASH"
            && normalized !== "CARD"
        ) {
            throw new Error(
                "Refund method must be CASH or CARD"
            );
        }

        return normalized;
    }


    function referenceFor(
        method,
        value
    ) {
        if (method === "CASH") {
            return null;
        }

        return requiredText(
            value,
            "Card refund reference"
        );
    }


    function returnLines(lines) {
        if (
            !Array.isArray(lines)
            || lines.length === 0
        ) {
            throw new Error(
                "At least one return line is required"
            );
        }

        return lines.map(
            line => {
                const saleLineId =
                    Number(
                        line?.sale_line_id
                    );

                const quantity =
                    Number(
                        line?.quantity
                    );

                if (
                    !Number.isInteger(
                        saleLineId
                    )
                    || saleLineId <= 0
                ) {
                    throw new Error(
                        "Invalid sale line"
                    );
                }

                if (
                    !Number.isFinite(
                        quantity
                    )
                    || quantity <= 0
                ) {
                    throw new Error(
                        "Return quantity must be positive"
                    );
                }

                return {
                    sale_line_id:
                        saleLineId,

                    quantity:
                        String(
                            line.quantity
                        ),
                };
            }
        );
    }


    function buildReturnPayload({
        returnUuid,
        reason,
        refundMethod:
            requestedRefundMethod,
        externalReference = null,
        managerStaffId,
        managerPin,
        lines,
    }) {
        const method =
            refundMethod(
                requestedRefundMethod
            );

        return {
            return_uuid:
                requiredText(
                    returnUuid,
                    "Return UUID"
                ),

            reason:
                requiredText(
                    reason,
                    "Return reason"
                ),

            refund_method:
                method,

            external_reference:
                referenceFor(
                    method,
                    externalReference
                ),

            authorizing_manager_staff_id:
                managerId(
                    managerStaffId
                ),

            manager_pin:
                requiredText(
                    managerPin,
                    "Manager PIN"
                ),

            lines:
                returnLines(lines),
        };
    }


    function buildCancellationPayload({
        cancellationUuid,
        reason,
        refundMethod:
            requestedRefundMethod,
        externalReference = null,
        managerStaffId,
        managerPin,
    }) {
        const method =
            refundMethod(
                requestedRefundMethod
            );

        return {
            cancellation_uuid:
                requiredText(
                    cancellationUuid,
                    "Cancellation UUID"
                ),

            reason:
                requiredText(
                    reason,
                    "Cancellation reason"
                ),

            refund_method:
                method,

            external_reference:
                referenceFor(
                    method,
                    externalReference
                ),

            authorizing_manager_staff_id:
                managerId(
                    managerStaffId
                ),

            manager_pin:
                requiredText(
                    managerPin,
                    "Manager PIN"
                ),
        };
    }


    function originalPaymentMethod(sale) {
        const payment =
            Array.isArray(
                sale?.payments
            )
                ? sale.payments[0]
                : null;

        const method =
            String(
                payment?.method ?? ""
            )
                .trim()
                .toUpperCase();

        return (
            method === "CARD"
                ? "CARD"
                : "CASH"
        );
    }


    window.CofiRetailAdjustments = {
        buildReturnPayload,
        buildCancellationPayload,
        originalPaymentMethod,
    };
})();
