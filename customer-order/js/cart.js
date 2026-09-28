(function (root, factory) {
    const api = factory();

    if (
        typeof module !== "undefined" &&
        module.exports
    ) {
        module.exports = api;
    }

    if (root) {
        root.CofiCustomerCart = api;
    }
})(
    typeof window !== "undefined"
        ? window
        : globalThis,
    function () {
        function numeric(value) {
            const parsed = Number(value);

            return Number.isFinite(parsed)
                ? parsed
                : 0;
        }


        function optionMap(product) {
            const map = new Map();

            (product?.modifiers || [])
                .forEach(group => {
                    (group.options || [])
                        .forEach(option => {
                            map.set(
                                Number(option.id),
                                {
                                    ...option,
                                    group_id:
                                        group.id,
                                    group_name:
                                        group.name,
                                }
                            );
                        });
                });

            return map;
        }


        function validateModifiers(
            product,
            selectedOptionIds
        ) {
            const selected =
                (selectedOptionIds || [])
                    .map(Number);

            const allowed =
                optionMap(product);

            for (const optionId of selected) {
                if (!allowed.has(optionId)) {
                    return {
                        valid: false,
                        message:
                            "Opción no disponible.",
                    };
                }
            }

            for (
                const group
                of product?.modifiers || []
            ) {
                const groupIds =
                    new Set(
                        (group.options || [])
                            .map(
                                option =>
                                    Number(option.id)
                            )
                    );

                const count =
                    selected.filter(
                        optionId =>
                            groupIds.has(optionId)
                    ).length;

                const min =
                    Number(
                        group.min_select ??
                        (group.required ? 1 : 0)
                    );

                const max =
                    Number(
                        group.max_select ?? 1
                    );

                if (count < min) {
                    return {
                        valid: false,
                        message:
                            `Selecciona ${group.name} para continuar.`,
                    };
                }

                if (count > max) {
                    return {
                        valid: false,
                        message:
                            `Selecciona máximo ${max} en ${group.name}.`,
                    };
                }
            }

            return {
                valid: true,
                message: null,
            };
        }


        function normalizeNote(notes) {
            if (notes === null || notes === undefined) {
                return null;
            }

            const value = String(notes).trim();

            if (!value) {
                return null;
            }

            if (value.length > 150) {
                throw new Error(
                    "La nota no puede exceder 150 caracteres."
                );
            }

            return value;
        }


        function makeLine({
            product,
            selectedOptionIds = [],
            quantity = 1,
            lineUuid,
            notes = null,
        }) {
            const validation =
                validateModifiers(
                    product,
                    selectedOptionIds
                );

            if (!validation.valid) {
                throw new Error(
                    validation.message
                );
            }

            const options =
                optionMap(product);

            const modifiers =
                selectedOptionIds.map(
                    rawId => {
                        const optionId =
                            Number(rawId);

                        const option =
                            options.get(optionId);

                        return {
                            option_id:
                                optionId,
                            group_id:
                                option.group_id,
                            group_name:
                                option.group_name,
                            option_name:
                                option.name,
                            price_delta:
                                numeric(
                                    option.price_delta
                                ),
                        };
                    }
                );

            const basePrice =
                numeric(product.price);

            const modifierTotal =
                modifiers.reduce(
                    (sum, item) =>
                        sum +
                        numeric(
                            item.price_delta
                        ),
                    0
                );

            const safeQuantity =
                Math.max(
                    1,
                    Math.min(
                        99,
                        Number(quantity) || 1
                    )
                );

            const unitPrice =
                basePrice +
                modifierTotal;

            return {
                line_uuid:
                    lineUuid,
                product_id:
                    product.id,
                product_name:
                    product.name,
                image_url:
                    product.image_url || null,
                quantity:
                    safeQuantity,
                base_price:
                    basePrice,
                modifiers,
                unit_price:
                    unitPrice,
                line_total:
                    unitPrice *
                    safeQuantity,
                notes:
                    normalizeNote(notes),
            };
        }


        function cartCount(lines) {
            return (lines || [])
                .reduce(
                    (sum, item) =>
                        sum +
                        Number(
                            item.quantity || 0
                        ),
                    0
                );
        }


        function cartTotal(lines) {
            return (lines || [])
                .reduce(
                    (sum, item) =>
                        sum +
                        numeric(
                            item.line_total
                        ),
                    0
                );
        }


        function toSelfOrderItems(lines) {
            return (lines || [])
                .map(item => ({
                    product_id:
                        item.product_id,
                    quantity:
                        item.quantity,
                    modifier_option_ids:
                        (item.modifiers || [])
                            .map(
                                modifier =>
                                    modifier.option_id
                            ),
                    notes:
                        item.notes || null,
                }));
        }


        return {
            validateModifiers,
            makeLine,
            cartCount,
            cartTotal,
            toSelfOrderItems,
        };
    }
);
