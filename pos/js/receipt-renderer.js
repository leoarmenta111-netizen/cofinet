(() => {
    "use strict";

    let activeSnapshot = null;

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatMoney(
        cents,
        currency
    ) {
        const numericCents =
            Number(cents ?? 0);

        const amount =
            Number.isFinite(numericCents)
                ? numericCents / 100
                : 0;

        const safeCurrency =
            String(
                currency || "MXN"
            ).toUpperCase();

        try {
            return new Intl.NumberFormat(
                "es-MX",
                {
                    style: "currency",
                    currency:
                        safeCurrency,
                }
            ).format(amount);
        } catch {
            return `${amount.toFixed(
                2
            )} ${escapeHtml(
                safeCurrency
            )}`;
        }
    }

    function resolveTimezone(
        snapshot
    ) {
        const timezone =
            snapshot?.branch
                ?.timezone ??
            snapshot?.branch
                ?.time_zone ??
            snapshot?.branch_timezone ??
            snapshot?.timezone ??
            "America/Mexico_City";

        try {
            new Intl.DateTimeFormat(
                "es-MX",
                {
                    timeZone:
                        timezone,
                }
            );

            return timezone;
        } catch {
            return "UTC";
        }
    }

    function formatSaleDate(
        value,
        snapshot
    ) {
        const date =
            new Date(value);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return escapeHtml(
                value || "—"
            );
        }

        return escapeHtml(
            new Intl.DateTimeFormat(
                "es-MX",
                {
                    dateStyle:
                        "medium",
                    timeStyle:
                        "short",
                    timeZone:
                        resolveTimezone(
                            snapshot
                        ),
                }
            ).format(date)
        );
    }

    function localLogoRef(
        value
    ) {
        const ref =
            String(
                value || ""
            ).trim();

        if (!ref) {
            return null;
        }

        if (
            ref.startsWith("./") ||
            ref.startsWith("../") ||
            ref.startsWith("/") ||
            ref.startsWith(
                "data:image/"
            )
        ) {
            return ref;
        }

        return null;
    }

    function itemName(item) {
        return (
            item?.name ??
            item?.product_name ??
            item?.item_name ??
            item?.description ??
            "Producto"
        );
    }

    function modifierName(
        modifier
    ) {
        return (
            modifier?.option_name ??
            modifier?.name ??
            modifier?.description ??
            ""
        );
    }

    function itemTotalCents(item) {
        const explicit =
            item?.line_total_cents ??
            item?.total_cents ??
            item?.item_total_cents;

        if (
            Number.isFinite(
                Number(explicit)
            )
        ) {
            return Number(
                explicit
            );
        }

        const quantity =
            Number(
                item?.quantity ?? 1
            );

        const unit =
            Number(
                item?.unit_price_cents ??
                item?.price_cents ??
                0
            );

        const modifiers =
            (
                item?.modifiers || []
            ).reduce(
                (
                    total,
                    modifier
                ) => {
                    if (
                        modifier
                            ?.customer_visible ===
                        false
                    ) {
                        return total;
                    }

                    return (
                        total +
                        Number(
                            modifier
                                ?.price_delta_cents ??
                            0
                        )
                    );
                },
                0
            );

        return (
            quantity *
            (unit + modifiers)
        );
    }

    function renderItem(
        item,
        currency
    ) {
        const quantity =
            Number(
                item?.quantity ?? 1
            );

        const paidModifiers =
            (
                item?.modifiers || []
            )
                .filter(
                    modifier => {
                        if (
                            modifier
                                ?.customer_visible ===
                            false
                        ) {
                            return false;
                        }

                        const delta =
                            Number(
                                modifier
                                    ?.price_delta_cents ??
                                0
                            );

                        return (
                            Number.isFinite(delta) &&
                            delta > 0
                        );
                    }
                );

        const paidModifiersTotal =
            paidModifiers.reduce(
                (
                    total,
                    modifier
                ) =>
                    total +
                    (
                        Number(
                            modifier
                                .price_delta_cents
                        ) *
                        quantity
                    ),
                0
            );

        const finalLineTotal =
            itemTotalCents(
                item
            );

        const baseLineTotal =
            Math.max(
                0,
                finalLineTotal -
                    paidModifiersTotal
            );

        const modifiers =
            paidModifiers
                .map(
                    modifier => {
                        const name =
                            modifierName(
                                modifier
                            );

                        if (!name) {
                            return "";
                        }

                        const amount =
                            Number(
                                modifier
                                    .price_delta_cents
                            ) *
                            quantity;

                        return `
                            <div class="receipt-modifier">
                                <span>+ ${escapeHtml(
                                    name
                                )}</span>
                                <span>${formatMoney(
                                    amount,
                                    currency
                                )}</span>
                            </div>
                        `;
                    }
                )
                .join("");

        return `
            <div class="receipt-item">
                <div class="receipt-row receipt-item-main">
                    <span>
                        ${escapeHtml(
                            quantity
                        )} ×
                        ${escapeHtml(
                            itemName(
                                item
                            )
                        )}
                    </span>
                    <strong>
                        ${formatMoney(
                            baseLineTotal,
                            currency
                        )}
                    </strong>
                </div>
                ${modifiers}
            </div>
        `;
    }


    function totalRow(
        label,
        cents,
        currency,
        className = ""
    ) {
        return `
            <div class="receipt-row ${className}">
                <span>${escapeHtml(
                    label
                )}</span>
                <strong>${formatMoney(
                    cents,
                    currency
                )}</strong>
            </div>
        `;
    }

    function paymentLabel(
        method
    ) {
        switch (
            String(
                method || ""
            ).toUpperCase()
        ) {
            case "CASH":
                return "Efectivo";

            case "CARD_EXTERNAL":
                return "Tarjeta";

            default:
                return (
                    method ||
                    "Pago"
                );
        }
    }

    function render(snapshot) {
        if (
            !snapshot ||
            typeof snapshot !==
                "object"
        ) {
            throw new TypeError(
                "Receipt snapshot is required"
            );
        }

        const currency =
            snapshot.currency ||
            "MXN";

        const business =
            snapshot.business ||
            {};

        const branch =
            snapshot.branch ||
            {};

        const totals =
            snapshot.totals ||
            {};

        const payment =
            snapshot.payment ||
            {};

        const logo =
            localLogoRef(
                business.logo_ref
            );

        const customerName =
            snapshot.customer
                ?.name;

        const branchLines = [
            branch.branch_name,
            branch.address,
            branch.phone ||
                business.phone,
            business.web_social,
        ]
            .filter(Boolean)
            .map(
                value =>
                    `<div>${escapeHtml(
                        value
                    )}</div>`
            )
            .join("");

        const items =
            (
                snapshot.items || []
            )
                .map(item =>
                    renderItem(
                        item,
                        currency
                    )
                )
                .join("");

        const discount =
            Number(
                totals.discount_cents ??
                0
            );

        const tax =
            Number(
                totals.tax_cents ??
                0
            );

        const tip =
            Number(
                totals.tip_cents ??
                0
            );

        const optionalTotals = [
            discount > 0
                ? totalRow(
                    "Descuento",
                    -discount,
                    currency
                )
                : "",

            tax > 0
                ? totalRow(
                    "Impuestos",
                    tax,
                    currency
                )
                : "",

            tip > 0
                ? totalRow(
                    "Propina",
                    tip,
                    currency
                )
                : "",
        ].join("");

        const cashDetails =
            String(
                payment.method ||
                ""
            ).toUpperCase() ===
                "CASH"
                ? `
                    ${
                        payment.amount_tendered_cents !=
                        null
                            ? totalRow(
                                "Recibido",
                                payment.amount_tendered_cents,
                                currency
                            )
                            : ""
                    }
                    ${
                        payment.change_due_cents !=
                        null
                            ? totalRow(
                                "Cambio",
                                payment.change_due_cents,
                                currency
                            )
                            : ""
                    }
                `
                : "";

        return `
            <article class="receipt-paper" aria-label="Ticket de venta">
                <header class="receipt-header">
                    ${
                        logo
                            ? `<img
                                class="receipt-logo"
                                src="${escapeHtml(
                                    logo
                                )}"
                                alt=""
                            >`
                            : ""
                    }

                    <h1>${escapeHtml(
                        business.business_name ||
                        "CofiCenter"
                    )}</h1>

                    <div class="receipt-branch">
                        ${branchLines}
                    </div>
                </header>

                <div class="receipt-divider"></div>

                <section class="receipt-meta">
                    <div class="receipt-row">
                        <span>Folio</span>
                        <strong>${escapeHtml(
                            snapshot.folio ||
                            "—"
                        )}</strong>
                    </div>

                    <div class="receipt-row">
                        <span>Fecha</span>
                        <strong>${formatSaleDate(
                            snapshot.sold_at,
                            snapshot
                        )}</strong>
                    </div>

                    ${
                        customerName
                            ? `
                                <div class="receipt-row">
                                    <span>Cliente</span>
                                    <strong>${escapeHtml(
                                        customerName
                                    )}</strong>
                                </div>
                            `
                            : ""
                    }
                </section>

                <div class="receipt-divider"></div>

                <section class="receipt-items">
                    ${items}
                </section>

                <div class="receipt-divider"></div>

                <section class="receipt-totals">
                    ${totalRow(
                        "Subtotal",
                        totals.subtotal_cents ??
                            0,
                        currency
                    )}

                    ${optionalTotals}

                    ${totalRow(
                        "TOTAL",
                        totals.total_cents ??
                            payment.amount_cents ??
                            0,
                        currency,
                        "receipt-grand-total"
                    )}
                </section>

                <div class="receipt-divider"></div>

                <section class="receipt-payment">
                    <div class="receipt-row">
                        <span>Método de pago</span>
                        <strong>${escapeHtml(
                            paymentLabel(
                                payment.method
                            )
                        )}</strong>
                    </div>

                    ${cashDetails}
                </section>

                ${
                    business.footer_message
                        ? `
                            <div class="receipt-divider"></div>

                            <footer class="receipt-footer">
                                ${escapeHtml(
                                    business.footer_message
                                )}
                            </footer>
                        `
                        : ""
                }
            </article>
        `;
    }

    function open(snapshot) {
        const modal =
            document.getElementById(
                "receipt-modal"
            );

        const documentElement =
            document.getElementById(
                "receipt-document"
            );

        if (
            !modal ||
            !documentElement
        ) {
            throw new Error(
                "Receipt modal is not available"
            );
        }

        activeSnapshot =
            snapshot;

        documentElement.innerHTML =
            render(snapshot);

        modal.hidden = false;

        const closeButton =
            document.getElementById(
                "receipt-close"
            );

        const printButton =
            document.getElementById(
                "receipt-print"
            );

        if (closeButton) {
            closeButton.onclick =
                close;
        }

        if (printButton) {
            printButton.onclick =
                () => {
                    if (
                        activeSnapshot
                    ) {
                        print(
                            activeSnapshot
                        );
                    }
                };
        }
    }

    function close() {
        const modal =
            document.getElementById(
                "receipt-modal"
            );

        if (modal) {
            modal.hidden = true;
        }
    }

    function print(snapshot) {
        open(snapshot);

        window.print();
    }

    window.CofiPosReceiptRenderer = {
        render,
        open,
        close,
        print,
    };
})();
