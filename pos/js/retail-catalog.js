window.CofiRetailCatalog = (() => {
    function text(value) {
        return String(
            value ?? ""
        )
            .trim()
            .toLocaleLowerCase();
    }


    function number(value) {
        const parsed =
            Number(value);

        return Number.isFinite(parsed)
            ? parsed
            : null;
    }


    function activeItems(catalog) {
        if (!Array.isArray(catalog)) {
            return [];
        }

        return catalog.filter(
            item =>
                item
                && item.is_active
                !== false
        );
    }


    function activePresentations(item) {
        if (
            !item
            || !Array.isArray(
                item.presentations
            )
        ) {
            return [];
        }

        return item.presentations.filter(
            presentation =>
                presentation
                && presentation
                    .is_active
                    !== false
        );
    }


    function search(
        catalog,
        query
    ) {
        const needle =
            text(query);

        const items =
            activeItems(catalog);

        if (!needle) {
            return items;
        }

        return items.filter(
            item => {
                const fields = [
                    item.name,
                    item.sku,
                    item.category,
                    item.description,
                ];

                return fields.some(
                    value =>
                        text(value)
                            .includes(
                                needle
                            )
                );
            }
        );
    }


    function findBarcode(
        catalog,
        rawBarcode
    ) {
        const barcode =
            String(
                rawBarcode ?? ""
            ).trim();

        if (!barcode) {
            return null;
        }

        for (
            const item
            of activeItems(catalog)
        ) {
            for (
                const presentation
                of activePresentations(
                    item
                )
            ) {
                if (
                    String(
                        presentation
                            .barcode
                        ?? ""
                    ).trim()
                    === barcode
                ) {
                    return {
                        item,
                        presentation,
                    };
                }
            }
        }

        return null;
    }


    function selectionFor(item) {
        if (!item) {
            return {
                action:
                    "UNAVAILABLE",
                presentation:
                    null,
                presentations: [],
            };
        }

        if (
            text(item.item_type)
            === "service"
        ) {
            return {
                action: "ADD",
                presentation: null,
                presentations: [],
            };
        }

        const presentations =
            activePresentations(item);

        if (
            presentations.length
            === 0
        ) {
            return {
                action:
                    "UNAVAILABLE",
                presentation:
                    null,
                presentations: [],
            };
        }

        if (
            presentations.length
            === 1
        ) {
            return {
                action: "ADD",
                presentation:
                    presentations[0],
                presentations,
            };
        }

        return {
            action:
                "CHOOSE_PRESENTATION",
            presentation: null,
            presentations,
        };
    }


    function productPrice(
        presentation,
        quantity
    ) {
        if (!presentation) {
            return null;
        }

        const normal =
            number(
                presentation.sale_price
            );

        if (normal === null) {
            return null;
        }

        const bulk =
            number(
                presentation.bulk_price
            );

        const threshold =
            number(
                presentation
                    .bulk_min_quantity
            );

        if (
            bulk !== null
            && threshold !== null
            && quantity >= threshold
        ) {
            return bulk;
        }

        return normal;
    }


    function servicePrice(
        item,
        quantity
    ) {
        if (
            !item
            || !Array.isArray(
                item.service_price_tiers
            )
        ) {
            return null;
        }

        const matches =
            item.service_price_tiers
                .filter(
                    tier => {
                        const minimum =
                            number(
                                tier
                                    .min_quantity
                            );

                        const maximum =
                            tier
                                .max_quantity
                                === null
                                || tier
                                    .max_quantity
                                    === undefined
                                ? null
                                : number(
                                    tier
                                        .max_quantity
                                );

                        return (
                            minimum
                            !== null
                            && quantity
                            >= minimum
                            && (
                                maximum
                                === null
                                || quantity
                                <= maximum
                            )
                        );
                    }
                )
                .sort(
                    (a, b) =>
                        Number(
                            b.min_quantity
                        )
                        - Number(
                            a.min_quantity
                        )
                );

        if (
            matches.length === 0
        ) {
            return null;
        }

        return number(
            matches[0].unit_price
        );
    }


    function estimateUnitPrice(
        item,
        presentation,
        rawQuantity
    ) {
        const quantity =
            number(rawQuantity);

        if (
            quantity === null
            || quantity <= 0
        ) {
            return null;
        }

        if (
            text(item?.item_type)
            === "service"
        ) {
            return servicePrice(
                item,
                quantity
            );
        }

        return productPrice(
            presentation,
            quantity
        );
    }


    return {
        search,
        findBarcode,
        selectionFor,
        estimateUnitPrice,
        activePresentations,
    };
})();
