window.CofiRetailCartRemoveFix = (() => {
    "use strict";

    function bind() {
        const container =
            document.getElementById(
                "retail-cart-lines"
            );

        if (!container) {
            console.error(
                "Retail cart container not found"
            );
            return;
        }

        /*
         * IMPORTANTE:
         * true = CAPTURE PHASE.
         *
         * Ejecutamos esto ANTES que los handlers
         * originales de los botones.
         */
        container.addEventListener(
            "click",
            event => {
                const button =
                    event.target.closest(
                        "button"
                    );

                if (!button) {
                    return;
                }

                if (
                    button.textContent
                        .trim()
                        .toLowerCase()
                    !== "eliminar"
                ) {
                    return;
                }

                const row =
                    button.closest(
                        ".retail-cart-line"
                    );

                if (!row) {
                    return;
                }

                const app =
                    window.CofiRetailApp;

                const cart =
                    app?.state?.cart;

                if (
                    !cart
                    || !Array.isArray(
                        cart.lines
                    )
                ) {
                    console.error(
                        "Cart state unavailable"
                    );
                    return;
                }

                /*
                 * Se obtiene el índice ANTES de que
                 * cualquier listener original pueda
                 * volver a renderizar el carrito.
                 */
                const rows =
                    Array.from(
                        container.children
                    ).filter(
                        element =>
                            element.classList
                                .contains(
                                    "retail-cart-line"
                                )
                    );

                const index =
                    rows.indexOf(row);

                if (
                    index < 0
                    || index >= cart.lines.length
                ) {
                    console.error(
                        "Unable to resolve cart line",
                        {
                            index,
                            rows:
                                rows.length,
                            lines:
                                cart.lines.length,
                        }
                    );

                    return;
                }

                /*
                 * Bloquear cualquier handler viejo
                 * del botón Eliminar.
                 */
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();

                const removed =
                    cart.lines[index];

                cart.lines.splice(
                    index,
                    1
                );

                console.log(
                    "Cart line removed:",
                    removed
                );

                /*
                 * Actualiza cantidades, precios
                 * y total inmediatamente.
                 */
                app.renderCart();

                if (
                    cart.lines.length === 0
                ) {
                    app.state.paymentMethod =
                        null;
                }

                const search =
                    document.getElementById(
                        "retail-search"
                    );

                search?.focus();
            },
            true
        );

        console.log(
            "Retail remove fix active - capture mode"
        );
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
        bind,
    };
})();
