(function (root, factory) {
    const api = factory();

    if (
        typeof module === "object" &&
        module.exports
    ) {
        module.exports = api;
    }

    if (root) {
        root.CofiPosOrdersLocal = api;
    }
})(
    typeof window !== "undefined"
        ? window
        : globalThis,

    function () {

        function number(value) {
            const parsed =
                Number(value || 0);

            return Number.isFinite(parsed)
                ? parsed
                : 0;
        }


        function catalogProducts(catalog) {

            const products =
                new Map();

            for (
                const category
                of catalog?.categories || []
            ) {
                for (
                    const product
                    of category.products || []
                ) {
                    products.set(
                        Number(product.id),
                        product
                    );
                }
            }

            return products;
        }


        function modifierOptions(product) {

            const options =
                new Map();

            for (
                const group
                of product?.modifiers || []
            ) {
                for (
                    const option
                    of group.options || []
                ) {
                    options.set(
                        Number(option.id),
                        {
                            ...option,
                            group_name:
                                group.name,
                        }
                    );
                }
            }

            return options;
        }


        function buildLocalOrder(
            localOrder,
            catalog
        ) {

            const payload =
                localOrder?.payload || {};

            const products =
                catalogProducts(
                    catalog
                );


            const items =
                (payload.items || [])
                    .map(item => {

                        const product =
                            products.get(
                                Number(
                                    item.product_id
                                )
                            );

                        const options =
                            modifierOptions(
                                product
                            );

                        const selected =
                            (
                                item
                                    .modifier_option_ids
                                || []
                            )
                                .map(id =>
                                    options.get(
                                        Number(id)
                                    )
                                )
                                .filter(Boolean);


                        const quantity =
                            Math.max(
                                1,
                                number(
                                    item.quantity
                                )
                            );


                        const productPrice =
                            number(
                                product?.price
                            );


                        const modifiersTotal =
                            selected.reduce(
                                (
                                    total,
                                    option
                                ) =>
                                    total +
                                    number(
                                        option
                                            .price_delta
                                    ),
                                0
                            );


                        const unitTotal =
                            productPrice +
                            modifiersTotal;


                        return {
                            product_id:
                                item.product_id,

                            product_name:
                                product?.name ||
                                `Producto #${
                                    item.product_id
                                }`,

                            quantity,

                            unit_price:
                                unitTotal,

                            line_total:
                                unitTotal *
                                quantity,

                            modifiers:
                                selected.map(
                                    option => ({
                                        option_id:
                                            option.id,

                                        option_name:
                                            option.name,

                                        group_name:
                                            option
                                                .group_name,

                                        price_delta:
                                            number(
                                                option
                                                    .price_delta
                                            ),
                                    })
                                ),

                            notes:
                                item.notes ||
                                null,
                        };
                    });


            const calculatedTotal =
                items.reduce(
                    (
                        total,
                        item
                    ) =>
                        total +
                        number(
                            item.line_total
                        ),
                    0
                );


            const total =
                localOrder
                    ?.local_total !==
                    undefined
                    ? number(
                        localOrder
                            .local_total
                    )
                    : calculatedTotal;


            const uuid =
                payload.order_uuid ||
                localOrder.order_uuid;


            return {
                order_uuid:
                    uuid,

                folio:
                    `LOCAL-${
                        String(uuid || "")
                            .replace(
                                /-/g,
                                ""
                            )
                            .slice(0, 8)
                            .toUpperCase()
                    }`,

                branch_code:
                    payload.branch_code ||
                    null,

                terminal_id:
                    payload.terminal_id ||
                    null,

                created_at_client:
                    payload
                        .created_at_client ||
                    localOrder.created_at,

                created_at:
                    localOrder.created_at,

                status:
                    "NEW",

                payment_status:
                    "PAID",

                total,

                items,

                payment:
                    payload.payment ||
                    null,

                notes:
                    payload.notes ||
                    null,

                is_local:
                    true,

                sync_status:
                    localOrder
                        .sync_status ||
                    "PENDING_SYNC",
            };
        }


        function pendingLocalOrders(
            rows
        ) {
            return (
                rows || []
            ).filter(
                row =>
                    row.sync_status ===
                    "PENDING_SYNC"
            );
        }


        function timestamp(order) {

            const value =
                order
                    ?.created_at_client ||
                order?.created_at;

            if (!value) {
                return 0;
            }

            const parsed =
                new Date(value)
                    .getTime();

            return Number.isFinite(
                parsed
            )
                ? parsed
                : 0;
        }


        function mergeOrders(
            cloudOrders,
            localOrders
        ) {

            const merged =
                new Map();


            for (
                const order
                of localOrders || []
            ) {
                if (
                    order?.order_uuid
                ) {
                    merged.set(
                        order.order_uuid,
                        order
                    );
                }
            }


            // Cloud siempre gana si el UUID
            // ya fue sincronizado.
            for (
                const order
                of cloudOrders || []
            ) {
                if (
                    order?.order_uuid
                ) {
                    merged.set(
                        order.order_uuid,
                        order
                    );
                }
            }


            return [
                ...merged.values()
            ].sort(
                (a, b) =>
                    timestamp(b) -
                    timestamp(a)
            );
        }


        return {
            buildLocalOrder,
            pendingLocalOrders,
            mergeOrders,
        };
    }
);
