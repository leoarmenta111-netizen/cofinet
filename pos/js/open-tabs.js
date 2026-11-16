(() => {
    "use strict";

    const $ = selector =>
        document.querySelector(selector);

    const state = {
        busy: false,
        tabs: [],

        precheckTab: null,
        precheck: null,

        closeTab: null,
        cancelTab: null,
        cancelBusy: false,
        closePrecheck: null,
        closeMethod: "CASH",
        closeBusy: false,
        pendingClosePayload: null,
    };


    function bridge() {
        return window.CofiPosAppBridge;
    }


    function context() {
        return bridge()
            ?.getSaleContext?.() || {};
    }


    function online() {
        return Boolean(
            bridge()
                ?.isCloudOnline?.()
        );
    }


    function escapeHtml(value) {
        return String(
            value ?? ""
        )
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
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


    function errorMessage(
        target,
        message = ""
    ) {
        if (!target) {
            return;
        }

        target.textContent =
            message;

        target.hidden =
            !message;
    }


    function setBusy(value) {
        state.busy =
            Boolean(value);

        [
            "#open-tab-create-submit",
            "#open-tabs-refresh",
        ].forEach(selector => {
            const button =
                $(selector);

            if (button) {
                button.disabled =
                    state.busy;
            }
        });
    }


    function roundPayload(cart) {
        return {
            round_uuid:
                window.CofiUUID.v4(),

            created_at_client:
                new Date().toISOString(),

            notes: null,

            items:
                cart.map(item => ({
                    product_id:
                        item.product_id,

                    product_variant_id:
                        item.product_variant_id ??
                        null,

                    quantity:
                        Number(
                            item.quantity || 1
                        ),

                    modifier_option_ids:
                        (
                            item.modifiers ||
                            []
                        ).map(
                            modifier =>
                                modifier.option_id
                        ),

                    notes:
                        item.notes ||
                        null,
                })),
        };
    }


    function openCreateModal() {
        const sale =
            context();

        if (!online()) {
            window.alert(
                "Abrir una cuenta requiere conexión a internet."
            );
            return;
        }

        if (!sale.cart?.length) {
            return;
        }

        errorMessage(
            $("#open-tab-create-error")
        );

        $("#open-tab-table").value =
            "";

        $("#open-tab-name").value =
            sale.selectedCustomer
                ?.name || "";

        $("#open-tab-create-modal")
            .hidden = false;

        $("#open-tab-table")
            ?.focus();
    }


    function closeCreateModal() {
        $("#open-tab-create-modal")
            .hidden = true;

        errorMessage(
            $("#open-tab-create-error")
        );
    }


    async function createFromCurrentOrder() {
        if (state.busy) {
            return;
        }

        const sale =
            context();

        if (!online()) {
            errorMessage(
                $("#open-tab-create-error"),
                "Abrir una cuenta requiere conexión."
            );
            return;
        }

        if (!sale.cart?.length) {
            errorMessage(
                $("#open-tab-create-error"),
                "La orden está vacía."
            );
            return;
        }

        const tableNumber =
            $("#open-tab-table")
                .value
                .trim();

        const orderName =
            $("#open-tab-name")
                .value
                .trim();

        if (
            !tableNumber &&
            !orderName
        ) {
            errorMessage(
                $("#open-tab-create-error"),
                "Indica una mesa o un nombre para identificar la cuenta."
            );
            return;
        }

        setBusy(true);

        errorMessage(
            $("#open-tab-create-error")
        );

        const tabUuid =
            window.CofiUUID.v4();

        try {
            await window.CofiPosAPI
                .createTab({
                    tab_uuid:
                        tabUuid,

                    branch_code:
                        sale.branchCode,

                    terminal_id:
                        sale.terminalId,

                    customer_uuid:
                        sale.selectedCustomer
                            ?.customer_uuid ||
                        null,

                    order_type:
                        "DINE_IN",

                    order_name:
                        orderName || null,

                    table_number:
                        tableNumber || null,

                    opened_at_client:
                        new Date()
                            .toISOString(),
                });

            await window.CofiPosAPI
                .addTabRound(
                    tabUuid,
                    sale.branchCode,
                    roundPayload(
                        sale.cart
                    )
                );

            bridge()
                ?.clearCart?.();

            closeCreateModal();

            await refreshTabs();

            window.alert(
                "Cuenta abierta y pedido enviado a preparación."
            );

        } catch (error) {
            errorMessage(
                $("#open-tab-create-error"),
                error.message ||
                "No se pudo abrir la cuenta."
            );

        } finally {
            setBusy(false);
        }
    }


    function tabIdentity(tab) {
        return [
            tab.table_number,
            tab.order_name,
        ]
            .filter(Boolean)
            .join(" · ") ||
            "Cuenta";
    }


    function renderTabs() {
        const list =
            $("#open-tabs-list");

        const summary =
            $("#open-tabs-summary");

        if (!list) {
            return;
        }

        list.replaceChildren();

        if (summary) {
            summary.textContent =
                state.tabs.length
                    ? `${state.tabs.length} ${
                        state.tabs.length === 1
                            ? "cuenta abierta"
                            : "cuentas abiertas"
                    }`
                    : "Sin cuentas abiertas";
        }

        if (!state.tabs.length) {
            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "open-tabs-empty";

            empty.textContent =
                "No hay cuentas abiertas.";

            list.append(empty);

            return;
        }

        state.tabs.forEach(tab => {
            const card =
                document.createElement(
                    "article"
                );

            card.className =
                "open-tab-card";

            const main =
                document.createElement(
                    "div"
                );

            main.className =
                "open-tab-card-main";

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                tabIdentity(tab);

            const meta =
                document.createElement(
                    "span"
                );

            meta.textContent =
                `${tab.rounds?.length || 0} ${
                    (tab.rounds?.length || 0) === 1
                        ? "pedido"
                        : "pedidos"
                }`;

            main.append(
                title,
                meta
            );

            const total =
                document.createElement(
                    "strong"
                );

            total.className =
                "open-tab-card-total";

            total.textContent =
                money(
                    tab.total
                );

            const actions =
                document.createElement(
                    "div"
                );

            actions.className =
                "open-tab-card-actions";


            const continueButton =
                document.createElement(
                    "button"
                );

            continueButton.type =
                "button";

            continueButton.className =
                "open-tab-continue";

            continueButton.textContent =
                "Continuar pedido";

            continueButton.addEventListener(
                "click",
                () => {
                    continueTab(tab);
                }
            );


            const precheckButton =
                document.createElement(
                    "button"
                );

            precheckButton.type =
                "button";

            precheckButton.className =
                "open-tab-card-action";

            precheckButton.textContent =
                "Precuenta";

            precheckButton.addEventListener(
                "click",
                () => {
                    openPrecheck(tab);
                }
            );


            const closeButton =
                document.createElement(
                    "button"
                );

            closeButton.type =
                "button";

            closeButton.className =
                "open-tab-card-action is-primary";

            closeButton.textContent =
                "Cobrar";

            closeButton.addEventListener(
                "click",
                () => {
                    openCloseTab(tab);
                }
            );


            actions.append(
                continueButton,
                precheckButton,
                closeButton
            );


            card.append(
                main,
                total,
                actions
            );

            list.append(card);
        });
    }


    async function refreshTabs() {
        const sale =
            context();

        if (!sale.branchCode) {
            return;
        }

        if (!online()) {
            errorMessage(
                $("#open-tabs-error"),
                "Las cuentas abiertas requieren conexión."
            );

            state.tabs = [];
            renderTabs();
            return;
        }

        errorMessage(
            $("#open-tabs-error")
        );

        try {
            const response =
                await window
                    .CofiPosAPI
                    .listOpenTabs(
                        sale.branchCode
                    );

            state.tabs =
                response?.tabs ||
                response?.items ||
                [];

            renderTabs();

        } catch (error) {
            state.tabs = [];

            renderTabs();

            errorMessage(
                $("#open-tabs-error"),
                error.message ||
                "No se pudieron consultar las cuentas."
            );
        }
    }


    async function openTabsModal() {
        $("#open-tabs-modal")
            .hidden = false;

        await refreshTabs();
    }


    function closeTabsModal() {
        $("#open-tabs-modal")
            .hidden = true;
    }


    async function continueTab(tab) {
        const sale =
            context();

        if (
            sale.cart?.length &&
            !window.confirm(
                "Hay productos en la orden actual. ¿Vaciar la orden y continuar con esta cuenta?"
            )
        ) {
            return;
        }

        if (!online()) {
            window.alert(
                "Continuar una cuenta requiere conexión."
            );
            return;
        }

        try {
            const fresh =
                await window.CofiPosAPI
                    .getTab(
                        tab.tab_uuid,
                        sale.branchCode
                    );

            bridge()
                ?.clearCart?.();

            bridge()
                ?.setActiveOpenTab?.(
                    fresh
                );

            if (
                fresh.customer_uuid
            ) {
                try {
                    const customer =
                        await window
                            .CofiPosAPI
                            .getCustomer(
                                fresh.customer_uuid
                            );

                    bridge()
                        ?.setSelectedCustomer?.(
                            customer
                        );

                } catch {
                    // The tab remains usable even
                    // if customer refresh fails.
                }
            } else {
                bridge()
                    ?.setSelectedCustomer?.(
                        null
                    );
            }

            closeTabsModal();

        } catch (error) {
            window.alert(
                error.message ||
                "No se pudo abrir la cuenta."
            );
        }
    }


    async function sendCurrentRound() {
        if (state.busy) {
            return;
        }

        const sale =
            context();

        const tab =
            sale.activeOpenTab;

        if (!tab) {
            return;
        }

        if (!sale.cart?.length) {
            return;
        }

        if (!online()) {
            window.alert(
                "Enviar un pedido a una cuenta requiere conexión."
            );
            return;
        }

        setBusy(true);

        try {
            const updated =
                await window.CofiPosAPI
                    .addTabRound(
                        tab.tab_uuid,
                        sale.branchCode,
                        roundPayload(
                            sale.cart
                        )
                    );

            bridge()
                ?.clearCart?.();

            bridge()
                ?.setActiveOpenTab?.(
                    updated
                );

            window.alert(
                "Nuevo pedido enviado a preparación."
            );

        } catch (error) {
            window.alert(
                error.message ||
                "No se pudo enviar el pedido."
            );

        } finally {
            setBusy(false);
        }
    }


    function leaveActiveTab() {
        const sale =
            context();

        if (
            sale.cart?.length &&
            !window.confirm(
                "Hay productos sin enviar. ¿Salir de la cuenta y vaciar la orden?"
            )
        ) {
            return;
        }

        bridge()
            ?.clearCart?.();

        bridge()
            ?.clearActiveOpenTab?.();

        bridge()
            ?.setSelectedCustomer?.(
                null
            );
    }


    // POS_OPEN_TABS_CLOSE_UI_V1

    function tabIdentityText(tab) {
        return [
            tab?.table_number,
            tab?.order_name,
        ]
            .filter(Boolean)
            .join(" · ") ||
            "Cuenta abierta";
    }


    function precheckItemHtml(item) {
        const modifiers =
            (
                item.modifiers ||
                []
            )
                .map(modifier => {
                    const delta =
                        Number(
                            modifier.price_delta ||
                            0
                        );

                    return `
                        <div class="open-tab-precheck-modifier">
                            <span>
                                + ${escapeHtml(
                                    modifier.option_name
                                )}
                            </span>

                            <span>
                                ${
                                    delta
                                        ? money(delta)
                                        : ""
                                }
                            </span>
                        </div>
                    `;
                })
                .join("");


        const variant =
            item.variant_name
                ? `
                    <small>
                        ${escapeHtml(
                            item.variant_name
                        )}
                    </small>
                `
                : "";


        return `
            <div class="open-tab-precheck-item">
                <div class="open-tab-precheck-line">
                    <span>
                        ${escapeHtml(
                            item.quantity
                        )} ×
                        ${escapeHtml(
                            item.product_name
                        )}
                    </span>

                    <strong>
                        ${money(
                            item.line_total
                        )}
                    </strong>
                </div>

                ${variant}
                ${modifiers}
            </div>
        `;
    }


    function renderPrecheck(
        precheck
    ) {
        const documentElement =
            $("#open-tab-precheck-document");

        if (!documentElement) {
            return;
        }

        const customer =
            precheck.customer_name
                ? `
                    <div>
                        Cliente:
                        <strong>
                            ${escapeHtml(
                                precheck.customer_name
                            )}
                        </strong>
                    </div>
                `
                : "";


        const identity = [
            precheck.table_number,
            precheck.order_name,
        ]
            .filter(Boolean)
            .join(" · ");


        const taxLine =
            Number(
                precheck.tax || 0
            ) !== 0
                ? `
                    <div>
                        <span>Impuestos</span>
                        <strong>
                            ${money(
                                precheck.tax
                            )}
                        </strong>
                    </div>
                `
                : "";


        documentElement.innerHTML = `
            <article class="open-tab-precheck-ticket">

                <header>
                    <h2>
                        ${escapeHtml(
                            precheck.business_name
                        )}
                    </h2>

                    <div>
                        ${escapeHtml(
                            precheck.branch_name
                        )}
                    </div>

                    ${
                        precheck.address
                            ? `
                                <div>
                                    ${escapeHtml(
                                        precheck.address
                                    )}
                                </div>
                            `
                            : ""
                    }

                    ${
                        precheck.phone
                            ? `
                                <div>
                                    ${escapeHtml(
                                        precheck.phone
                                    )}
                                </div>
                            `
                            : ""
                    }
                </header>

                <div class="open-tab-precheck-divider"></div>

                <section class="open-tab-precheck-title">
                    <strong>
                        PRECUENTA
                    </strong>

                    <span>
                        PENDIENTE DE PAGO
                    </span>
                </section>

                <div class="open-tab-precheck-divider"></div>

                <section class="open-tab-precheck-meta">
                    ${
                        identity
                            ? `
                                <div>
                                    ${escapeHtml(
                                        identity
                                    )}
                                </div>
                            `
                            : ""
                    }

                    ${customer}

                    <div>
                        Pedidos:
                        <strong>
                            ${escapeHtml(
                                precheck.round_count
                            )}
                        </strong>
                    </div>
                </section>

                <div class="open-tab-precheck-divider"></div>

                <section>
                    ${
                        (
                            precheck.items ||
                            []
                        )
                            .map(
                                precheckItemHtml
                            )
                            .join("")
                    }
                </section>

                <div class="open-tab-precheck-divider"></div>

                <section class="open-tab-precheck-totals">
                    <div>
                        <span>Subtotal</span>
                        <strong>
                            ${money(
                                precheck.subtotal
                            )}
                        </strong>
                    </div>

                    ${taxLine}

                    <div class="is-total">
                        <span>Total</span>
                        <strong>
                            ${money(
                                precheck.total
                            )}
                        </strong>
                    </div>
                </section>

                <div class="open-tab-precheck-divider"></div>

                <footer>
                    PRECUENTA · NO ES COMPROBANTE DE PAGO
                </footer>
            </article>
        `;
    }


    async function openPrecheck(tab) {
        const sale =
            context();

        if (!online()) {
            window.alert(
                "La precuenta requiere conexión."
            );
            return;
        }

        try {
            const precheck =
                await window.CofiPosAPI
                    .getTabPrecheck(
                        tab.tab_uuid,
                        sale.branchCode
                    );

            state.precheckTab =
                tab;

            state.precheck =
                precheck;

            renderPrecheck(
                precheck
            );

            $("#open-tab-precheck-modal")
                .hidden = false;

        } catch (error) {
            window.alert(
                error.message ||
                "No se pudo generar la precuenta."
            );
        }
    }


    function closePrecheck() {
        $("#open-tab-precheck-modal")
            .hidden = true;

        state.precheckTab =
            null;

        state.precheck =
            null;
    }


    function printPrecheck() {
        if (!state.precheck) {
            return;
        }

        document.body.classList.add(
            "open-tab-precheck-printing"
        );

        const cleanup = () => {
            document.body.classList.remove(
                "open-tab-precheck-printing"
            );

            window.removeEventListener(
                "afterprint",
                cleanup
            );
        };

        window.addEventListener(
            "afterprint",
            cleanup,
            {
                once: true,
            }
        );

        window.print();

        window.setTimeout(
            cleanup,
            1500
        );
    }


    function setCloseMethod(method) {
        state.closeMethod =
            method;

        document
            .querySelectorAll(
                "[data-tab-close-method]"
            )
            .forEach(button => {
                button.classList.toggle(
                    "is-active",
                    button.dataset
                        .tabCloseMethod ===
                        method
                );
            });


        $("#open-tab-close-cash-fields")
            .hidden =
            method !== "CASH";

        $("#open-tab-close-card-fields")
            .hidden =
            method !== "CARD_EXTERNAL";

        updateCloseChange();
    }


    function closeAmount() {
        return Number(
            state.closePrecheck
                ?.total || 0
        );
    }


    function updateCloseChange() {
        const target =
            $("#open-tab-close-change");

        if (!target) {
            return;
        }

        if (
            state.closeMethod !==
            "CASH"
        ) {
            target.textContent =
                money(0);

            return;
        }

        const received =
            Number(
                $("#open-tab-close-cash-received")
                    ?.value || 0
            );

        target.textContent =
            money(
                Math.max(
                    0,
                    received -
                    closeAmount()
                )
            );
    }


    async function openCloseTab(tab) {
        const sale =
            context();

        if (!online()) {
            window.alert(
                "Cobrar una cuenta requiere conexión."
            );
            return;
        }

        if (sale.cart?.length) {
            window.alert(
                "Hay productos sin enviar en la orden actual. Envíalos o vacía la orden antes de cobrar una cuenta."
            );
            return;
        }

        try {
            const precheck =
                await window.CofiPosAPI
                    .getTabPrecheck(
                        tab.tab_uuid,
                        sale.branchCode
                    );

            state.closeTab =
                tab;

            state.closePrecheck =
                precheck;

            state.pendingClosePayload =
                null;

            $("#open-tab-close-identity")
                .textContent =
                tabIdentityText(tab);

            $("#open-tab-close-total")
                .textContent =
                money(
                    precheck.total
                );

            $("#open-tab-close-cash-received")
                .value =
                Number(
                    precheck.total
                ).toFixed(2);

            $("#open-tab-close-card-reference")
                .value =
                "";

            errorMessage(
                $("#open-tab-close-error")
            );

            setCloseMethod(
                "CASH"
            );

            $("#open-tab-close-modal")
                .hidden = false;

        } catch (error) {
            window.alert(
                error.message ||
                "No se pudo preparar el cobro."
            );
        }
    }


    function dismissCloseTab() {
        if (state.closeBusy) {
            return;
        }

        $("#open-tab-close-modal")
            .hidden = true;

        state.closeTab =
            null;

        state.closePrecheck =
            null;

        state.pendingClosePayload =
            null;

        errorMessage(
            $("#open-tab-close-error")
        );
    }


    async function confirmCloseTab() {
        if (
            state.closeBusy ||
            !state.closeTab ||
            !state.closePrecheck
        ) {
            return;
        }

        const sale =
            context();

        if (!online()) {
            errorMessage(
                $("#open-tab-close-error"),
                "El cobro requiere conexión."
            );
            return;
        }

        const total =
            closeAmount();

        let amountTendered =
            null;

        let externalReference =
            null;


        if (
            state.closeMethod ===
            "CASH"
        ) {
            amountTendered =
                Number(
                    $("#open-tab-close-cash-received")
                        .value || 0
                );

            if (
                !Number.isFinite(
                    amountTendered
                ) ||
                amountTendered <
                    total
            ) {
                errorMessage(
                    $("#open-tab-close-error"),
                    "El efectivo recibido es menor al total de la cuenta."
                );
                return;
            }
        }


        if (
            state.closeMethod ===
            "CARD_EXTERNAL"
        ) {
            externalReference =
                $("#open-tab-close-card-reference")
                    .value
                    .trim() ||
                null;
        }


        if (
            !state.pendingClosePayload
        ) {
            state.pendingClosePayload = {
                order_uuid:
                    window.CofiUUID.v4(),

                payment_uuid:
                    window.CofiUUID.v4(),

                method:
                    state.closeMethod,

                amount_tendered:
                    amountTendered,

                external_reference:
                    externalReference,

                created_at_client:
                    new Date()
                        .toISOString(),
            };
        }


        state.closeBusy =
            true;

        const button =
            $("#open-tab-close-confirm");

        if (button) {
            button.disabled =
                true;

            const label =
                button.querySelector(
                    "span"
                );

            if (label) {
                label.textContent =
                    "Procesando…";
            }
        }


        errorMessage(
            $("#open-tab-close-error")
        );


        try {
            const result =
                await window.CofiPosAPI
                    .closeTab(
                        state.closeTab
                            .tab_uuid,

                        sale.branchCode,

                        state
                            .pendingClosePayload
                    );


            $("#open-tab-close-modal")
                .hidden = true;

            $("#open-tabs-modal")
                .hidden = true;


            const active =
                sale.activeOpenTab;

            if (
                active?.tab_uuid ===
                state.closeTab.tab_uuid
            ) {
                bridge()
                    ?.clearActiveOpenTab?.();
            }


            const folio =
                result.final_order
                    ?.folio || "";


            bridge()
                ?.showClosedTabSuccess?.({
                    folio,

                    receipt:
                        result
                            .receipt_snapshot,
                });


            state.closeTab =
                null;

            state.closePrecheck =
                null;

            state.pendingClosePayload =
                null;


            await refreshTabs();


        } catch (error) {
            errorMessage(
                $("#open-tab-close-error"),
                error.message ||
                "No se pudo cerrar la cuenta."
            );

        } finally {
            state.closeBusy =
                false;

            if (button) {
                button.disabled =
                    false;

                const label =
                    button.querySelector(
                        "span"
                    );

                if (label) {
                    label.textContent =
                        "Confirmar cobro";
                }
            }
        }
    }


    // POS_OPEN_TAB_MANAGER_CANCEL_UI_V1

    function tabIdentity(tab) {
        return [
            tab?.table_number,
            tab?.order_name,
        ]
            .filter(Boolean)
            .join(" · ") ||
            "Cuenta abierta";
    }


    function openCancelTab(tab) {
        if (!tab) {
            return;
        }

        if (!online()) {
            window.alert(
                "Eliminar una cuenta requiere conexión."
            );
            return;
        }

        state.cancelTab = tab;

        const identity =
            $("#open-tab-cancel-identity");

        if (identity) {
            identity.textContent =
                `${tabIdentity(tab)} · ${
                    money(tab.total || 0)
                }`;
        }

        $("#open-tab-cancel-pin").value =
            "";

        errorMessage(
            $("#open-tab-cancel-error")
        );

        $("#open-tab-cancel-modal")
            .hidden = false;

        $("#open-tab-cancel-pin")
            ?.focus();
    }


    function dismissCancelTab() {
        if (state.cancelBusy) {
            return;
        }

        $("#open-tab-cancel-modal")
            .hidden = true;

        state.cancelTab = null;

        errorMessage(
            $("#open-tab-cancel-error")
        );
    }


    async function confirmCancelTab() {
        if (
            state.cancelBusy ||
            !state.cancelTab
        ) {
            return;
        }

        if (!online()) {
            errorMessage(
                $("#open-tab-cancel-error"),
                "Eliminar una cuenta requiere conexión."
            );
            return;
        }

        const managerPin =
            String(
                $("#open-tab-cancel-pin")
                    ?.value || ""
            ).trim();

        if (managerPin.length < 4) {
            errorMessage(
                $("#open-tab-cancel-error"),
                "Ingresa el código/PIN del manager."
            );
            return;
        }

        const tab = state.cancelTab;

        const confirmButton =
            $("#open-tab-cancel-confirm");

        state.cancelBusy = true;

        if (confirmButton) {
            confirmButton.disabled = true;
            confirmButton.textContent =
                "Autorizando…";
        }

        try {
            await window.CofiPosAPI
                .cancelTab(
                    tab.tab_uuid,
                    context().branchCode,
                    {
                        manager_pin:
                            managerPin,
                    }
                );

            const active =
                context().activeOpenTab;

            if (
                active?.tab_uuid ===
                tab.tab_uuid
            ) {
                window.CofiPosAppBridge
                    ?.clearActiveOpenTab?.();

                window.CofiPosAppBridge
                    ?.clearCart?.();
            }

            $("#open-tab-cancel-modal")
                .hidden = true;

            state.cancelTab = null;

            await refreshTabs();

        } catch (error) {
            errorMessage(
                $("#open-tab-cancel-error"),
                error.message ||
                "No se pudo eliminar la cuenta."
            );

        } finally {
            state.cancelBusy = false;

            if (confirmButton) {
                confirmButton.disabled =
                    false;

                confirmButton.textContent =
                    "Autorizar y eliminar";
            }
        }
    }


    function decorateCancelButtons() {
        const cards = [
            ...document.querySelectorAll(
                "#open-tabs-list .open-tab-card"
            ),
        ];

        cards.forEach(
            (card, index) => {
                const tab =
                    state.tabs[index];

                const actions =
                    card.querySelector(
                        ".open-tab-card-actions"
                    );

                if (
                    !tab ||
                    !actions ||
                    actions.querySelector(
                        "[data-open-tab-delete]"
                    )
                ) {
                    return;
                }

                const button =
                    document.createElement(
                        "button"
                    );

                button.type =
                    "button";

                button.className =
                    "open-tab-card-action is-danger";

                button.dataset
                    .openTabDelete =
                    tab.tab_uuid;

                button.textContent =
                    "Eliminar";

                button.addEventListener(
                    "click",
                    event => {
                        event.preventDefault();
                        event.stopPropagation();

                        openCancelTab(tab);
                    }
                );

                actions.append(button);
            }
        );
    }


    function openActiveCancel() {
        const tab =
            activeTab();

        if (tab) {
            openCancelTab(tab);
        }
    }


    function activeTab() {
        return context()
            .activeOpenTab;
    }


    function openActivePrecheck() {
        const tab =
            activeTab();

        if (tab) {
            openPrecheck(tab);
        }
    }


    function openActiveClose() {
        const tab =
            activeTab();

        if (tab) {
            openCloseTab(tab);
        }
    }


    function boot() {
        $("#active-open-tab-delete")
            ?.addEventListener(
                "click",
                openActiveCancel
            );

        $("#open-tab-cancel-dismiss")
            ?.addEventListener(
                "click",
                dismissCancelTab
            );

        $("#open-tab-cancel-dismiss-secondary")
            ?.addEventListener(
                "click",
                dismissCancelTab
            );

        $("#open-tab-cancel-confirm")
            ?.addEventListener(
                "click",
                confirmCancelTab
            );

        const tabsList =
            $("#open-tabs-list");

        if (tabsList) {
            state.cancelObserver =
                new MutationObserver(
                    decorateCancelButtons
                );

            state.cancelObserver
                .observe(
                    tabsList,
                    {
                        childList: true,
                    }
                );

            decorateCancelButtons();
        }

        $("#open-tab-button")
            ?.addEventListener(
                "click",
                openCreateModal
            );

        $("#open-tab-create-close")
            ?.addEventListener(
                "click",
                closeCreateModal
            );

        $("#open-tab-create-submit")
            ?.addEventListener(
                "click",
                createFromCurrentOrder
            );

        $("#nav-open-tabs")
            ?.addEventListener(
                "click",
                openTabsModal
            );

        $("#open-tabs-close")
            ?.addEventListener(
                "click",
                closeTabsModal
            );

        $("#open-tabs-refresh")
            ?.addEventListener(
                "click",
                refreshTabs
            );

        $("#active-open-tab-precheck")
            ?.addEventListener(
                "click",
                openActivePrecheck
            );

        $("#active-open-tab-close-account")
            ?.addEventListener(
                "click",
                openActiveClose
            );

        $("#active-open-tab-exit")
            ?.addEventListener(
                "click",
                leaveActiveTab
            );

        $("#open-tab-precheck-close")
            ?.addEventListener(
                "click",
                closePrecheck
            );

        $("#open-tab-precheck-print")
            ?.addEventListener(
                "click",
                printPrecheck
            );

        document
            .querySelectorAll(
                "[data-tab-close-method]"
            )
            .forEach(button => {
                button.addEventListener(
                    "click",
                    () => {
                        setCloseMethod(
                            button.dataset
                                .tabCloseMethod
                        );
                    }
                );
            });

        $("#open-tab-close-cash-received")
            ?.addEventListener(
                "input",
                updateCloseChange
            );

        $("#open-tab-close-dismiss")
            ?.addEventListener(
                "click",
                dismissCloseTab
            );

        $("#open-tab-close-confirm")
            ?.addEventListener(
                "click",
                confirmCloseTab
            );

        window.addEventListener(
            "online",
            refreshTabs
        );
    }


    window.CofiPosOpenTabs = {
        refreshTabs,
        openTabsModal,
        sendCurrentRound,
        openPrecheck,
        openCloseTab,
        openCancelTab,
    };

    boot();
})();
