window.CofiRetailApp = (() => {
    const MODULE_CODE =
        "PAPELERIA";

    const state = {
        moduleCode:
            MODULE_CODE,

        cart:
            window.CofiRetailCart
                ? window.CofiRetailCart
                    .create()
                : { lines: [] },

        catalog: null,
        heldSales: [],
        selectedHeldSale: null,

        paymentMethod:
            "CASH",

        busy: false,
    };


    function currentState() {
        return state;
    }


    function renderTotal() {
        const target =
            document.getElementById(
                "retail-cart-total"
            );

        if (
            !target
            || !window.CofiRetailCart
        ) {
            return;
        }

        const amount =
            window.CofiRetailCart
                .total(
                    state.cart
                );

        target.textContent =
            amount.toLocaleString(
                "es-MX",
                {
                    style:
                        "currency",
                    currency:
                        "MXN",
                }
            );
    }


    function init() {
        const root =
            document.getElementById(
                "retail-pos"
            );

        if (!root) {
            return;
        }

        root.dataset.module =
            MODULE_CODE;

        renderTotal();
    }


    if (
        typeof document
        !== "undefined"
    ) {
        if (
            document.readyState
            === "loading"
        ) {
            document.addEventListener(
                "DOMContentLoaded",
                init,
                {
                    once: true,
                }
            );
        } else {
            init();
        }
    }


    return {
        moduleCode:
            MODULE_CODE,

        currentState,
        renderTotal,
        init,
    };
})();
