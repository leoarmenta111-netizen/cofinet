(() => {
    "use strict";

    const catalog =
        window.CofiRetailCatalog;

    if (
        !catalog
        || typeof catalog.estimateUnitPrice
            !== "function"
    ) {
        throw new Error(
            "CofiRetailCatalog.estimateUnitPrice unavailable"
        );
    }


    const originalEstimate =
        catalog.estimateUnitPrice.bind(
            catalog
        );


    function hasValue(value) {
        return (
            value !== null
            && value !== undefined
            && String(value).trim() !== ""
        );
    }


    catalog.estimateUnitPrice =
        function (
            item,
            presentation,
            quantity
        ) {
            const itemType =
                String(
                    item?.item_type || ""
                ).toUpperCase();


            /*
             * PRODUCTOS:
             *
             * Si NO existe configuración de
             * mayoreo, jamás convertir null
             * a Number(null) => 0.
             *
             * Se usa directamente sale_price.
             */
            if (
                itemType === "PRODUCT"
                && presentation
            ) {
                const hasBulkPrice =
                    hasValue(
                        presentation
                            .bulk_price
                    );

                const hasBulkMinimum =
                    hasValue(
                        presentation
                            .bulk_min_quantity
                    );


                if (
                    !hasBulkPrice
                    || !hasBulkMinimum
                ) {
                    const regularPrice =
                        Number(
                            presentation
                                .sale_price
                        );

                    if (
                        Number.isFinite(
                            regularPrice
                        )
                    ) {
                        return regularPrice;
                    }

                    return null;
                }
            }


            /*
             * Cuando sí hay mayoreo o es un
             * servicio, conservar el motor
             * original.
             */
            return originalEstimate(
                item,
                presentation,
                quantity
            );
        };


    console.log(
        "Retail price null-bulk fix active"
    );
})();
