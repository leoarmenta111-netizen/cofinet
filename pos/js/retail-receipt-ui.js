window.CofiRetailReceiptUI = (() => {
    "use strict";

    let enhancing = false;


    function el(id) {
        return document.getElementById(id);
    }


    function formatDate(value) {
        if (!value) {
            return "";
        }

        const date =
            new Date(value);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return String(value);
        }

        return new Intl.DateTimeFormat(
            "es-MX",
            {
                day: "numeric",
                month: "short",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
            }
        ).format(date);
    }


    function setupLayout() {
        const modal =
            el("retail-receipt-modal");

        const body =
            el("retail-receipt-body");

        if (
            !modal
            || !body
        ) {
            return;
        }


        /* ================================================
           HEADER
           ================================================ */

        if (
            !modal.querySelector(
                ".retail-receipt-head"
            )
        ) {
            const title =
                modal.querySelector(
                    "h2"
                );

            const close =
                el(
                    "retail-receipt-close"
                );


            const head =
                document.createElement(
                    "header"
                );

            head.className =
                "retail-receipt-head";


            const icon =
                document.createElement(
                    "span"
                );

            icon.className =
                "retail-receipt-success-icon";

            icon.setAttribute(
                "aria-hidden",
                "true"
            );


            const titleGroup =
                document.createElement(
                    "div"
                );

            titleGroup.className =
                "retail-receipt-title-group";


            if (title) {
                title.textContent =
                    "Venta completada";

                titleGroup.appendChild(
                    title
                );
            }


            const subtitle =
                document.createElement(
                    "p"
                );

            subtitle.id =
                "retail-receipt-subtitle";

            subtitle.textContent =
                "La venta se registró correctamente.";

            titleGroup.appendChild(
                subtitle
            );


            head.append(
                icon,
                titleGroup
            );


            if (close) {
                close.textContent =
                    "×";

                close.setAttribute(
                    "aria-label",
                    "Cerrar"
                );

                head.appendChild(
                    close
                );
            }


            modal.insertBefore(
                head,
                modal.firstChild
            );
        }


        /* ================================================
           ACCIONES PRINCIPALES
           ================================================ */

        if (
            !el(
                "retail-receipt-primary-actions"
            )
        ) {
            const actions =
                document.createElement(
                    "div"
                );

            actions.id =
                "retail-receipt-primary-actions";

            actions.className =
                "retail-receipt-primary-actions";


            const newSale =
                document.createElement(
                    "button"
                );

            newSale.id =
                "retail-new-sale";

            newSale.type =
                "button";

            newSale.textContent =
                "Nueva venta";


            const print =
                document.createElement(
                    "button"
                );

            print.id =
                "retail-print-ticket";

            print.type =
                "button";

            print.textContent =
                "Imprimir ticket";


            newSale.addEventListener(
                "click",
                () => {
                    if (
                        modal.open
                        && typeof modal.close
                            === "function"
                    ) {
                        modal.close();
                    }

                    window.requestAnimationFrame(
                        () => {
                            el(
                                "retail-search"
                            )?.focus();
                        }
                    );
                }
            );


            print.addEventListener(
                "click",
                () => {
                    window.print();
                }
            );


            actions.append(
                newSale,
                print
            );


            body.insertAdjacentElement(
                "afterend",
                actions
            );
        }


        /* ================================================
           ACCIONES SECUNDARIAS
           ================================================ */

        if (
            !el(
                "retail-receipt-secondary-actions"
            )
        ) {
            const secondary =
                document.createElement(
                    "div"
                );

            secondary.id =
                "retail-receipt-secondary-actions";

            secondary.className =
                "retail-receipt-secondary-actions";


            const returnButton =
                el(
                    "retail-return-sale"
                );

            const cancelButton =
                el(
                    "retail-cancel-sale"
                );


            if (returnButton) {
                secondary.appendChild(
                    returnButton
                );
            }


            if (cancelButton) {
                secondary.appendChild(
                    cancelButton
                );
            }


            const primary =
                el(
                    "retail-receipt-primary-actions"
                );

            primary.insertAdjacentElement(
                "afterend",
                secondary
            );
        }
    }


    function enhancePayment() {
        const payment =
            document.querySelector(
                "#retail-receipt-body "
                + ".retail-receipt-payment"
            );

        if (
            !payment
            || payment.dataset
                .receiptEnhanced
                === "true"
        ) {
            return;
        }


        payment.dataset
            .receiptEnhanced =
            "true";


        const method =
            payment.querySelector(
                ":scope > strong"
            );


        const originalDetails =
            Array.from(
                payment.querySelectorAll(
                    ":scope > span"
                )
            );


        const details =
            document.createElement(
                "div"
            );

        details.className =
            "retail-receipt-payment-details";


        originalDetails.forEach(
            item => {
                const text =
                    String(
                        item.textContent
                        || ""
                    ).trim();

                const separator =
                    text.indexOf(":");


                const row =
                    document.createElement(
                        "div"
                    );

                row.className =
                    "retail-receipt-payment-row";


                const label =
                    document.createElement(
                        "span"
                    );

                const value =
                    document.createElement(
                        "strong"
                    );


                if (separator >= 0) {
                    label.textContent =
                        text
                            .slice(
                                0,
                                separator
                            )
                            .trim();

                    value.textContent =
                        text
                            .slice(
                                separator + 1
                            )
                            .trim();
                } else {
                    label.textContent =
                        text;

                    value.textContent =
                        "";
                }


                row.append(
                    label,
                    value
                );

                details.appendChild(
                    row
                );
            }
        );


        payment.replaceChildren();

        if (method) {
            payment.appendChild(
                method
            );
        }

        payment.appendChild(
            details
        );
    }


    function enhanceReceipt() {
        if (enhancing) {
            return;
        }

        enhancing = true;

        try {
            setupLayout();


            const app =
                window.CofiRetailApp;

            const receipt =
                app?.state
                    ?.lastReceipt
                || null;

            const sale =
                app?.state
                    ?.lastServerSale
                || null;


            const folio =
                receipt?.folio
                ?? sale?.folio
                ?? null;


            const soldAt =
                receipt?.sold_at
                ?? sale?.sold_at
                ?? null;


            /* Header subtitle */

            const subtitle =
                el(
                    "retail-receipt-subtitle"
                );

            if (subtitle) {
                const parts = [];

                if (folio != null) {
                    parts.push(
                        `Venta #${folio}`
                    );
                }

                if (soldAt) {
                    parts.push(
                        formatDate(
                            soldAt
                        )
                    );
                }

                subtitle.textContent =
                    parts.length
                        ? parts.join(" · ")
                        : "La venta se registró correctamente.";
            }


            /* Meta compacta */

            const meta =
                document.querySelector(
                    "#retail-receipt-body "
                    + ".retail-receipt-meta"
                );

            if (meta) {
                const blocks =
                    Array.from(
                        meta.children
                    );

                if (blocks[0]) {
                    const label =
                        blocks[0]
                            .querySelector(
                                "small"
                            );

                    const value =
                        blocks[0]
                            .querySelector(
                                "strong"
                            );

                    if (label) {
                        label.textContent =
                            "Venta";
                    }

                    if (
                        value
                        && folio != null
                    ) {
                        value.textContent =
                            `#${folio}`;
                    }
                }
            }


            /* Producto: presentación · 1 × $22 */

            document
                .querySelectorAll(
                    "#retail-receipt-body "
                    + ".retail-receipt-line "
                    + "> div > span"
                )
                .forEach(
                    target => {
                        const current =
                            String(
                                target
                                    .textContent
                                || ""
                            );

                        const match =
                            current.match(
                                /^(.+?)\s*·\s*Cant\.\s*([^·]+)\s*·\s*(.+?)\s+c\/u$/i
                            );

                        if (match) {
                            target.textContent =
                                `${match[1]} · `
                                + `${match[2].trim()} × `
                                + `${match[3].trim()}`;
                        }
                    }
                );


            /* Pago alineado */

            enhancePayment();


            /* Fecha inferior sin formato ambiguo */

            const saleInfo =
                document.querySelector(
                    "#retail-receipt-body "
                    + ".retail-receipt-sale-info"
                );

            if (
                saleInfo
                && soldAt
                && saleInfo
                    .firstElementChild
            ) {
                saleInfo
                    .firstElementChild
                    .textContent =
                    formatDate(
                        soldAt
                    );
            }

        } finally {
            enhancing = false;
        }
    }


    function init() {
        setupLayout();

        const body =
            el(
                "retail-receipt-body"
            );

        if (!body) {
            return;
        }


        const observer =
            new MutationObserver(
                () => {
                    window.setTimeout(
                        enhanceReceipt,
                        0
                    );
                }
            );


        observer.observe(
            body,
            {
                childList: true,
                subtree: true,
            }
        );


        enhanceReceipt();
    }


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


    return {
        enhance:
            enhanceReceipt,
    };
})();
