window.CofiRetailHeldUI = (() => {
    "use strict";


    function el(id) {
        return document.getElementById(id);
    }


    function heldCount() {
        const sales =
            window.CofiRetailApp
                ?.state
                ?.heldSales;

        return Array.isArray(sales)
            ? sales.length
            : 0;
    }


    function updateButton() {
        const button =
            el("retail-held-toggle");

        const badge =
            el("retail-held-count");

        const count =
            heldCount();


        if (badge) {
            badge.textContent =
                String(count);

            badge.hidden =
                count <= 0;
        }


        if (button) {
            button.classList.toggle(
                "has-held-sales",
                count > 0
            );

            button.setAttribute(
                "aria-label",
                count === 1
                    ? "1 venta en espera"
                    : `${count} ventas en espera`
            );
        }
    }


    function openPanel() {
        const dialog =
            el(
                "retail-held-modal"
            );

        if (
            dialog
            && !dialog.open
            && typeof dialog.showModal
                === "function"
        ) {
            dialog.showModal();
        }

        updateButton();
    }


    function closePanel() {
        const dialog =
            el(
                "retail-held-modal"
            );

        if (
            dialog?.open
            && typeof dialog.close
                === "function"
        ) {
            dialog.close();
        }
    }


    function setup() {
        const originalSection =
            el(
                "retail-held-sales"
            );

        const header =
            document.querySelector(
                ".app-header"
            );


        if (
            !originalSection
            || !header
        ) {
            console.warn(
                "Held sales UI unavailable"
            );

            return;
        }


        /* ================================================
           BOTÓN EN HEADER
           ================================================ */

        if (
            !el(
                "retail-held-toggle"
            )
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.id =
                "retail-held-toggle";

            button.type =
                "button";

            button.className =
                "retail-held-toggle";

            button.innerHTML = `
                <span
                    class="retail-held-icon"
                    aria-hidden="true"
                >
                    ◷
                </span>

                <span>
                    Ventas en espera
                </span>

                <strong
                    id="retail-held-count"
                    hidden
                >
                    0
                </strong>
            `;

            button.addEventListener(
                "click",
                openPanel
            );


            const cash =
                el(
                    "retail-cash-status"
                );


            if (cash) {
                header.insertBefore(
                    button,
                    cash
                );
            } else {
                header.appendChild(
                    button
                );
            }
        }


        /* ================================================
           DIALOG
           ================================================ */

        if (
            !el(
                "retail-held-modal"
            )
        ) {
            const dialog =
                document.createElement(
                    "dialog"
                );

            dialog.id =
                "retail-held-modal";

            dialog.className =
                "retail-held-modal";


            const head =
                document.createElement(
                    "header"
                );

            head.className =
                "retail-held-modal-head";


            const titleGroup =
                document.createElement(
                    "div"
                );

            titleGroup.innerHTML = `
                <span>
                    Ventas pendientes
                </span>

                <h2>
                    Ventas en espera
                </h2>

                <p>
                    Recupera una venta para
                    continuar agregando productos
                    o cobrarla.
                </p>
            `;


            const close =
                document.createElement(
                    "button"
                );

            close.type =
                "button";

            close.className =
                "retail-held-modal-close";

            close.textContent =
                "×";

            close.setAttribute(
                "aria-label",
                "Cerrar"
            );

            close.addEventListener(
                "click",
                closePanel
            );


            head.append(
                titleGroup,
                close
            );


            const content =
                document.createElement(
                    "div"
                );

            content.className =
                "retail-held-modal-content";


            /*
             * Movemos la sección REAL existente.
             * No clonamos nada, por lo que sus
             * eventos y lógica siguen funcionando.
             */
            content.appendChild(
                originalSection
            );


            dialog.append(
                head,
                content
            );


            document.body.appendChild(
                dialog
            );


            dialog.addEventListener(
                "click",
                event => {
                    if (
                        event.target === dialog
                    ) {
                        closePanel();
                    }
                }
            );


            /*
             * Si se pulsa un botón de recuperar/
             * continuar, cerramos el panel después
             * de que retail-app procese el clic.
             */
            originalSection.addEventListener(
                "click",
                event => {
                    const button =
                        event.target.closest(
                            "button"
                        );

                    if (!button) {
                        return;
                    }

                    const label =
                        String(
                            button.textContent
                            || ""
                        )
                            .trim()
                            .toLowerCase();


                    if (
                        /continuar|recuperar|retomar|reanudar/.test(
                            label
                        )
                    ) {
                        window.setTimeout(
                            () => {
                                closePanel();
                                updateButton();

                                el(
                                    "retail-search"
                                )?.focus();
                            },
                            80
                        );
                    }
                }
            );
        }


        /*
         * loadHeldSales() vuelve a pintar esta
         * sección. Observamos esos cambios para
         * actualizar el contador.
         */
        const observer =
            new MutationObserver(
                () => {
                    window.setTimeout(
                        updateButton,
                        0
                    );
                }
            );


        observer.observe(
            originalSection,
            {
                childList: true,
                subtree: true,
                characterData: true,
            }
        );


        /*
         * El estado puede actualizarse después
         * del DOM; damos algunas sincronizaciones
         * cortas al iniciar.
         */
        updateButton();

        window.setTimeout(
            updateButton,
            250
        );

        window.setTimeout(
            updateButton,
            800
        );
    }


    if (
        document.readyState
        === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            setup,
            {
                once: true,
            }
        );
    } else {
        setup();
    }


    return {
        open: openPanel,
        close: closePanel,
        update: updateButton,
    };
})();
