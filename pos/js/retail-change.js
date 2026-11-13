window.CofiRetailChange = (() => {
    "use strict";


    function el(id) {
        return document.getElementById(id);
    }


    function money(value) {
        return new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN",
            }
        ).format(
            Number(value || 0)
        );
    }


    function total() {
        const cart =
            window.CofiRetailApp
                ?.state
                ?.cart;

        if (
            !cart
            || !window.CofiRetailCart
        ) {
            return 0;
        }

        return Number(
            window.CofiRetailCart
                .total(cart)
            || 0
        );
    }


    function ensureChangeBox() {
        let box =
            el("retail-cash-change");

        if (box) {
            return box;
        }

        const cashField =
            el("retail-cash-field");

        if (!cashField) {
            return null;
        }

        box =
            document.createElement(
                "div"
            );

        box.id =
            "retail-cash-change";

        box.className =
            "retail-cash-change";

        box.innerHTML = `
            <span
                class="retail-cash-change-label"
            >
                Cambio
            </span>

            <strong
                id="retail-cash-change-value"
            >
                $0.00
            </strong>

            <small
                id="retail-cash-change-status"
            ></small>
        `;

        cashField.appendChild(box);

        return box;
    }


    function update() {
        const box =
            ensureChangeBox();

        const input =
            el(
                "retail-amount-tendered"
            );

        if (
            !box
            || !input
        ) {
            return;
        }

        const totalAmount =
            total();

        const received =
            Number(
                input.value || 0
            );

        const value =
            el(
                "retail-cash-change-value"
            );

        const status =
            el(
                "retail-cash-change-status"
            );

        box.classList.remove(
            "is-short",
            "is-ready"
        );

        if (
            !Number.isFinite(received)
            || received < 0
        ) {
            if (value) {
                value.textContent =
                    money(0);
            }

            if (status) {
                status.textContent = "";
            }

            return;
        }

        const difference =
            received
            - totalAmount;

        if (difference >= 0) {
            box.classList.add(
                "is-ready"
            );

            if (value) {
                value.textContent =
                    money(difference);
            }

            if (status) {
                status.textContent =
                    difference === 0
                        ? "Pago exacto"
                        : "Entregar al cliente";
            }

            return;
        }

        box.classList.add(
            "is-short"
        );

        if (value) {
            value.textContent =
                money(0);
        }

        if (status) {
            status.textContent =
                `Faltan ${money(
                    Math.abs(
                        difference
                    )
                )}`;
        }
    }


    function bind() {
        ensureChangeBox();

        const input =
            el(
                "retail-amount-tendered"
            );

        const cashButton =
            el(
                "retail-pay-cash"
            );

        const cardButton =
            el(
                "retail-pay-card"
            );

        if (input) {
            input.addEventListener(
                "input",
                update
            );

            input.addEventListener(
                "change",
                update
            );
        }

        /*
         * retail-app.js primero abre el modal
         * y coloca el total en el input.
         * Ejecutamos update justo después.
         */
        if (cashButton) {
            cashButton.addEventListener(
                "click",
                () => {
                    setTimeout(
                        update,
                        0
                    );
                }
            );
        }

        if (cardButton) {
            cardButton.addEventListener(
                "click",
                () => {
                    const box =
                        el(
                            "retail-cash-change"
                        );

                    if (box) {
                        box.classList.remove(
                            "is-short",
                            "is-ready"
                        );
                    }
                }
            );
        }

        update();
    }


    if (
        document.readyState
        === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            bind,
            {
                once: true,
            }
        );
    } else {
        bind();
    }


    return {
        update,
    };
})();
