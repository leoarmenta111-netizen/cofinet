window.CofiRetailCart = (() => {
    let nextLineId = 1;

    function money(value) {
        const number =
            Number(value || 0);

        if (!Number.isFinite(number)) {
            throw new Error(
                "Invalid retail money value"
            );
        }

        return (
            Math.round(
                (number + Number.EPSILON)
                * 100
            )
            / 100
        );
    }


    function quantity(value) {
        const number =
            Number(value);

        if (
            !Number.isFinite(number)
            || number <= 0
        ) {
            throw new Error(
                "Retail quantity must be greater than zero"
            );
        }

        return number;
    }


    function create() {
        return {
            lines: [],
        };
    }


    function sameSaleUnit(
        line,
        item
    ) {
        return (
            Number(line.item_id)
                === Number(item.item_id)
            &&
            (
                line.presentation_id
                ?? null
            )
                === (
                    item.presentation_id
                    ?? null
                )
        );
    }


    function add(
        cart,
        item,
        requestedQuantity = 1
    ) {
        const amount =
            quantity(
                requestedQuantity
            );

        const existing =
            cart.lines.find(
                line =>
                    sameSaleUnit(
                        line,
                        item
                    )
            );

        if (existing) {
            existing.quantity =
                quantity(
                    existing.quantity
                    + amount
                );

            return existing;
        }

        const line = {
            line_id:
                `retail-line-${nextLineId++}`,

            item_id:
                Number(item.item_id),

            presentation_id:
                item.presentation_id
                ?? null,

            name:
                String(
                    item.name || ""
                ),

            presentation_name:
                item.presentation_name
                ?? null,

            item_type:
                String(
                    item.item_type
                    || "PRODUCT"
                ).toUpperCase(),

            unit_price:
                money(
                    item.unit_price
                ),

            quantity:
                amount,

            discount_amount:
                0,
        };

        cart.lines.push(line);

        return line;
    }


    function findLine(
        cart,
        lineId
    ) {
        return cart.lines.find(
            line =>
                line.line_id
                === lineId
        );
    }


    function setQuantity(
        cart,
        lineId,
        requestedQuantity
    ) {
        const line =
            findLine(
                cart,
                lineId
            );

        if (!line) {
            throw new Error(
                "Retail cart line not found"
            );
        }

        const amount =
            Number(
                requestedQuantity
            );

        if (
            !Number.isFinite(amount)
        ) {
            throw new Error(
                "Invalid retail quantity"
            );
        }

        if (amount <= 0) {
            remove(
                cart,
                lineId
            );

            return null;
        }

        line.quantity =
            quantity(amount);

        return line;
    }


    function remove(
        cart,
        lineId
    ) {
        const index =
            cart.lines.findIndex(
                line =>
                    line.line_id
                    === lineId
            );

        if (index < 0) {
            return false;
        }

        cart.lines.splice(
            index,
            1
        );

        return true;
    }


    function lineTotal(line) {
        return money(
            (
                money(line.unit_price)
                * Number(line.quantity)
            )
            - money(
                line.discount_amount
            )
        );
    }


    function total(cart) {
        return money(
            cart.lines.reduce(
                (sum, line) =>
                    sum
                    + lineTotal(line),
                0
            )
        );
    }


    function clear(cart) {
        cart.lines.splice(
            0,
            cart.lines.length
        );
    }


    function checkoutLines(cart) {
        return cart.lines.map(
            line => ({
                item_id:
                    line.item_id,

                presentation_id:
                    line.presentation_id,

                quantity:
                    line.quantity,

                discount_amount:
                    money(
                        line.discount_amount
                    ),
            })
        );
    }


    return {
        create,
        add,
        setQuantity,
        remove,
        clear,
        total,
        lineTotal,
        checkoutLines,
    };
})();
