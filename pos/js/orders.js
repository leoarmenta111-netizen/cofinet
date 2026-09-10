(() => {
    const state = {
        branchCode: null,
        orders: [],
        filter: "ALL",
        selectedOrder: null,
        loading: false,
        cloudUnavailable: false,
    };

    const $ = selector =>
        document.querySelector(selector);

    function money(value) {
        return new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN",
            }
        ).format(Number(value || 0));
    }

    function statusLabel(status) {
        return {
            NEW: "Nueva",
            PREPARING: "Preparando",
            READY: "Lista",
            DELIVERED: "Entregada",
            CANCELLED: "Cancelada",
        }[status] || status;
    }

    function paymentLabel(method) {
        return {
            CASH: "Efectivo",
            CARD_EXTERNAL: "Tarjeta",
        }[method] || method || "—";
    }

    function formatTime(value) {
        if (!value) return "—";

        return new Date(value)
            .toLocaleTimeString(
                "es-MX",
                {
                    hour: "2-digit",
                    minute: "2-digit",
                }
            );
    }

    function formatDateTime(value) {
        if (!value) return "—";

        return new Date(value)
            .toLocaleString(
                "es-MX",
                {
                    dateStyle: "medium",
                    timeStyle: "short",
                }
            );
    }

    async function getBranchCode() {
        if (state.branchCode) {
            return state.branchCode;
        }

        const params =
            new URLSearchParams(
                window.location.search
            );

        const requested =
            params
                .get("branch")
                ?.trim()
                .toLowerCase();

        const saved =
            await window.CofiPosDB.get(
                "meta",
                "branch_code"
            );

        state.branchCode =
            requested ||
            saved ||
            null;

        return state.branchCode;
    }

    function dayRange() {
        const start = new Date();

        start.setHours(
            0,
            0,
            0,
            0
        );

        const end =
            new Date(start);

        end.setDate(
            end.getDate() + 1
        );

        return {
            fromAt:
                start.toISOString(),

            toAt:
                end.toISOString(),
        };
    }

    function normalizeBranchCode(value) {
        const normalized =
            String(value || "")
                .trim()
                .toLowerCase();

        return normalized === "principal"
            ? "nuevo-vallarta"
            : normalized;
    }


    async function loadPendingLocalOrders(
        branchCode,
        range
    ) {
        const rows =
            await window.CofiPosDB
                .getAll(
                    "local_orders"
                );

        const cached =
            await window.CofiPosDB
                .get(
                    "catalogs",
                    branchCode
                );

        const catalog =
            cached?.catalog || {
                categories: [],
            };

        const currentBranch =
            normalizeBranchCode(
                branchCode
            );

        const from =
            new Date(
                range.fromAt
            ).getTime();

        const to =
            new Date(
                range.toAt
            ).getTime();


        return window
            .CofiPosOrdersLocal
            .pendingLocalOrders(
                rows
            )
            .filter(row => {
                const rowBranch =
                    normalizeBranchCode(
                        row
                            ?.payload
                            ?.branch_code
                    );

                return (
                    rowBranch ===
                    currentBranch
                );
            })
            .map(row =>
                window
                    .CofiPosOrdersLocal
                    .buildLocalOrder(
                        row,
                        catalog
                    )
            )
            .filter(order => {
                const value =
                    order
                        .created_at_client ||
                    order.created_at;

                const timestamp =
                    new Date(
                        value
                    ).getTime();

                return (
                    Number.isFinite(
                        timestamp
                    ) &&
                    timestamp >= from &&
                    timestamp < to
                );
            });
    }


    function activateNavigation(view) {
        const sale =
            $("#nav-sale");

        const orders =
            $("#nav-orders");

        const customers =
            $("#nav-customers");

        sale?.classList.toggle(
            "is-active",
            view === "sale"
        );

        orders?.classList.toggle(
            "is-active",
            view === "orders"
        );

        customers?.classList.toggle(
            "is-active",
            view === "customers"
        );
    }

    function showSale() {
        $("#sale-view").hidden =
            false;

        $("#orders-view").hidden =
            true;

        const customers =
            $("#customers-view");

        if (customers) {
            customers.hidden = true;
        }

        $(".workspace")
            .classList.remove(
                "orders-mode",
                "customers-mode"
            );

        activateNavigation("sale");
    }

    async function showOrders() {
        $("#sale-view").hidden =
            true;

        $("#orders-view").hidden =
            false;

        const customers =
            $("#customers-view");

        if (customers) {
            customers.hidden = true;
        }

        $(".workspace")
            .classList.remove(
                "customers-mode"
            );

        $(".workspace")
            .classList.add(
                "orders-mode"
            );

        activateNavigation("orders");

        await loadOrders();
    }

    async function loadOrders() {
        if (state.loading) return;

        state.loading = true;

        const message =
            $("#orders-message");

        const list =
            $("#orders-list");

        message.hidden = false;
        message.textContent =
            "Cargando órdenes…";

        list.replaceChildren();

        try {
            const branchCode =
                await getBranchCode();

            if (!branchCode) {
                throw new Error(
                    "Esta terminal no tiene sucursal configurada."
                );
            }

            const range =
                dayRange();


            /*
             * LOCAL
             *
             * IndexedDB se consulta siempre.
             * De esta forma una venta hecha sin Internet
             * aparece inmediatamente en Órdenes.
             */
            let localOrders = [];

            try {
                localOrders =
                    await loadPendingLocalOrders(
                        branchCode,
                        range
                    );

            } catch (error) {
                console.warn(
                    "No fue posible leer órdenes locales:",
                    error
                );
            }


            /*
             * CLOUD
             */
            let cloudOrders = [];
            let cloudError = null;

            state.cloudUnavailable =
                !navigator.onLine;


            if (navigator.onLine) {
                try {
                    const response =
                        await window
                            .CofiPosAPI
                            .listOrders(
                                branchCode,
                                {
                                    fromAt:
                                        range.fromAt,

                                    toAt:
                                        range.toAt,

                                    limit: 200,
                                }
                            );

                    cloudOrders =
                        response?.orders || [];

                    state.cloudUnavailable =
                        false;

                } catch (error) {
                    cloudError = error;

                    state.cloudUnavailable =
                        true;

                    console.warn(
                        "Cloud orders unavailable:",
                        error
                    );
                }
            }


            /*
             * Cloud gana cuando existe el mismo
             * order_uuid en ambos lados.
             */
            state.orders =
                window
                    .CofiPosOrdersLocal
                    .mergeOrders(
                        cloudOrders,
                        localOrders
                    );


            renderOrders();


            /*
             * Si Cloud falló pero tenemos ventas locales,
             * no ocultamos las ventas.
             *
             * Si no existe ninguna orden que mostrar,
             * explicamos el problema de conexión.
             */
            if (
                cloudError &&
                !state.orders.length
            ) {
                message.hidden = false;

                message.textContent =
                    cloudError.isHttpError
                        ? (
                            cloudError.message ||
                            "No fue posible cargar las órdenes."
                        )
                        : (
                            "Sin conexión al servidor. " +
                            "Las ventas locales aparecerán aquí " +
                            "hasta que puedan sincronizarse."
                        );
            }

        } catch (error) {
            state.orders = [];
            state.cloudUnavailable = true;

            message.hidden = false;

            message.textContent =
                error.message ||
                "No fue posible cargar las órdenes.";

            $("#orders-summary")
                .textContent =
                    "Sin datos disponibles";

        } finally {
            state.loading = false;
        }
    }


    function renderOrders() {
        const list =
            $("#orders-list");

        const message =
            $("#orders-message");

        list.replaceChildren();

        const orders =
            state.filter === "ALL"
                ? state.orders
                : state.orders.filter(
                    order =>
                        order.status ===
                        state.filter
                );

        const ordersSummary =
            `${state.orders.length} ${
                state.orders.length === 1
                    ? "orden hoy"
                    : "órdenes hoy"
            }${
                state.cloudUnavailable
                    ? " • modo local"
                    : ""
            }`;

        $("#orders-summary")
            .textContent =
                ordersSummary;

        if (!orders.length) {
            message.hidden = false;

            message.textContent =
                state.orders.length
                    ? "No hay órdenes con este estado."
                    : "Todavía no hay órdenes registradas hoy.";

            return;
        }

        message.hidden = true;

        orders.forEach(order => {
            const card =
                document.createElement(
                    "button"
                );

            card.type = "button";

            card.className =
                "order-list-card";

            const header =
                document.createElement(
                    "div"
                );

            header.className =
                "order-list-card-header";

            const folio =
                document.createElement(
                    "strong"
                );

            folio.textContent =
                order.folio;

            const time =
                document.createElement(
                    "span"
                );

            time.textContent =
                formatTime(
                    order.created_at_client
                );

            header.append(
                folio,
                time
            );

            const items =
                document.createElement(
                    "div"
                );

            items.className =
                "order-list-items";

            (order.items || [])
                .slice(0, 3)
                .forEach(item => {
                    const row =
                        document.createElement(
                            "span"
                        );

                    row.textContent =
                        `${item.quantity} × ${item.product_name}`;

                    items.append(row);
                });

            if (
                (order.items || []).length > 3
            ) {
                const more =
                    document.createElement(
                        "small"
                    );

                more.textContent =
                    `+${
                        order.items.length - 3
                    } productos`;

                items.append(more);
            }

            const footer =
                document.createElement(
                    "div"
                );

            footer.className =
                "order-list-card-footer";

            const total =
                document.createElement(
                    "strong"
                );

            total.textContent =
                money(order.total);

            const badge =
                document.createElement(
                    "span"
                );

            const isLocal =
                order.is_local === true;

            badge.className =
                `order-status-badge status-${
                    isLocal
                        ? "new"
                        : order.status.toLowerCase()
                }`;

            badge.textContent =
                isLocal
                    ? "Pendiente de sincronizar"
                    : statusLabel(
                        order.status
                    );

            footer.append(
                total,
                badge
            );

            card.append(
                header,
                items,
                footer
            );

            card.addEventListener(
                "click",
                () =>
                    openOrder(
                        order.order_uuid
                    )
            );

            list.append(card);
        });
    }

    async function openOrder(orderUuid) {
        try {
            const listedOrder =
                state.orders.find(
                    order =>
                        order.order_uuid ===
                        orderUuid
                );

            /*
             * Una orden local todavía no existe
             * en el backend.
             *
             * También reutilizamos la orden ya cargada
             * si Cloud se cayó después de abrir la lista.
             */
            if (
                listedOrder &&
                (
                    listedOrder.is_local ||
                    !navigator.onLine
                )
            ) {
                state.selectedOrder =
                    listedOrder;

                renderOrderDetail(
                    listedOrder
                );

                $("#order-detail-modal")
                    .hidden = false;

                return;
            }


            const branchCode =
                await getBranchCode();

            const order =
                await window.CofiPosAPI
                    .getOrder(
                        orderUuid,
                        branchCode
                    );

            state.selectedOrder =
                order;

            renderOrderDetail(order);

            $("#order-detail-modal")
                .hidden = false;

        } catch (error) {
            alert(
                error.message ||
                "No fue posible abrir la orden."
            );
        }
    }


    function preparationStationLabel(
        station
    ) {
        const labels = {
            KITCHEN: "Cocina",
            BAR: "Barra",
        };

        return labels[station] || station;
    }


    function preparationStatusLabel(
        status
    ) {
        const labels = {
            NEW: "Nueva",
            PREPARING: "Preparando",
            READY: "Lista",
        };

        return labels[status] || status;
    }


    function renderPreparationProgress(
        order
    ) {
        const stations =
            Array.isArray(order.stations)
                ? order.stations.filter(
                    station =>
                        station.station ===
                            "KITCHEN" ||
                        station.station ===
                            "BAR"
                )
                : [];

        if (!stations.length) {
            return null;
        }

        const section =
            document.createElement(
                "section"
            );

        section.className =
            "order-preparation";

        const title =
            document.createElement(
                "h3"
            );

        title.className =
            "order-preparation-title";

        title.textContent =
            "Preparación";

        section.append(title);

        stations.forEach(
            station => {

                const row =
                    document.createElement(
                        "div"
                    );

                row.className =
                    "order-preparation-station";

                row.dataset.status =
                    station.status;

                const name =
                    document.createElement(
                        "span"
                    );

                name.className =
                    "order-preparation-name";

                name.textContent =
                    preparationStationLabel(
                        station.station
                    );

                const status =
                    document.createElement(
                        "span"
                    );

                status.className =
                    "order-preparation-status";

                status.dataset.status =
                    station.status;

                status.textContent =
                    preparationStatusLabel(
                        station.status
                    );

                row.append(
                    name,
                    status
                );

                section.append(row);
            }
        );

        return section;
    }


    function renderOrderDetail(order) {
        $("#order-detail-folio")
            .textContent =
                order.folio;

        const status =
            $("#order-detail-status");

        const isLocal =
            order.is_local === true;

        status.className =
            `order-status-badge status-${
                isLocal
                    ? "new"
                    : order.status.toLowerCase()
            }`;

        status.textContent =
            isLocal
                ? "Pendiente de sincronizar"
                : statusLabel(
                    order.status
                );

        const body =
            $("#order-detail-body");

        body.replaceChildren();

        const meta =
            document.createElement(
                "div"
            );

        meta.className =
            "order-detail-meta";

        const date =
            document.createElement(
                "span"
            );

        date.textContent =
            formatDateTime(
                order.created_at_client
            );

        const payment =
            document.createElement(
                "span"
            );

        payment.textContent =
            paymentLabel(
                order.payment?.method
            );

        meta.append(
            date,
            payment
        );

        body.append(meta);

        const items =
            document.createElement(
                "div"
            );

        items.className =
            "order-detail-items";

        (order.items || [])
            .forEach(item => {
                const row =
                    document.createElement(
                        "article"
                    );

                row.className =
                    "order-detail-item";

                const top =
                    document.createElement(
                        "div"
                    );

                const name =
                    document.createElement(
                        "strong"
                    );

                name.textContent =
                    `${item.quantity} × ${item.product_name}`;

                const price =
                    document.createElement(
                        "strong"
                    );

                price.textContent =
                    money(
                        item.line_total
                    );

                top.append(
                    name,
                    price
                );

                row.append(top);

                (item.modifiers || [])
                    .forEach(modifier => {
                        const option =
                            document.createElement(
                                "small"
                            );

                        option.textContent =
                            `• ${modifier.option_name}`;

                        row.append(option);
                    });

                items.append(row);
            });

        body.append(items);

        const preparation =
            renderPreparationProgress(
                order
            );

        if (preparation) {
            body.append(
                preparation
            );
        }

        const summary =
            document.createElement(
                "div"
            );

        summary.className =
            "order-detail-total";

        const label =
            document.createElement(
                "span"
            );

        label.textContent =
            "Total";

        const total =
            document.createElement(
                "strong"
            );

        total.textContent =
            money(order.total);

        summary.append(
            label,
            total
        );

        body.append(summary);

        configureStatusAction(order);
    }

    function configureStatusAction(order) {
        const action =
            $("#order-status-action");


        if (order?.is_local) {
            action.hidden = true;

            delete action.dataset
                .nextStatus;

            return;
        }


        const transitions = {
            NEW: {
                status: "PREPARING",
                label: "Iniciar preparación",
            },

            PREPARING: {
                status: "READY",
                label: "Marcar como lista",
            },

            READY: {
                status: "DELIVERED",
                label: "Marcar como entregada",
            },
        };

        const next =
            transitions[
                order.status
            ];

        if (!next) {
            action.hidden = true;

            delete action.dataset
                .nextStatus;

            return;
        }

        action.hidden = false;

        action.dataset.nextStatus =
            next.status;

        action.textContent =
            next.label;
    }

    async function advanceSelectedOrder() {
        const order =
            state.selectedOrder;

        const nextStatus =
            $("#order-status-action")
                .dataset.nextStatus;

        if (
            !order ||
            !nextStatus
        ) {
            return;
        }

        const button =
            $("#order-status-action");

        button.disabled = true;

        try {
            const branchCode =
                await getBranchCode();

            const updated =
                await window.CofiPosAPI
                    .updateOrderStatus(
                        order.order_uuid,
                        branchCode,
                        nextStatus
                    );

            state.selectedOrder =
                updated;

            renderOrderDetail(
                updated
            );

            await loadOrders();

        } catch (error) {
            alert(
                error.message ||
                "No fue posible actualizar la orden."
            );

        } finally {
            button.disabled = false;
        }
    }

    function init() {
        $("#nav-sale")
            ?.addEventListener(
                "click",
                showSale
            );

        $("#nav-orders")
            ?.addEventListener(
                "click",
                showOrders
            );

        $("#refresh-orders")
            ?.addEventListener(
                "click",
                loadOrders
            );

        $("#order-detail-close")
            ?.addEventListener(
                "click",
                () => {
                    $("#order-detail-modal")
                        .hidden = true;
                }
            );

        $("#order-status-action")
            ?.addEventListener(
                "click",
                advanceSelectedOrder
            );

        document
            .querySelectorAll(
                "[data-order-filter]"
            )
            .forEach(button => {
                button.addEventListener(
                    "click",
                    () => {
                        state.filter =
                            button.dataset
                                .orderFilter;

                        document
                            .querySelectorAll(
                                "[data-order-filter]"
                            )
                            .forEach(item =>
                                item.classList.toggle(
                                    "is-active",
                                    item === button
                                )
                            );

                        renderOrders();
                    }
                );
            });

        $("#order-detail-modal")
            ?.addEventListener(
                "click",
                event => {
                    if (
                        event.target ===
                        $("#order-detail-modal")
                    ) {
                        $("#order-detail-modal")
                            .hidden = true;
                    }
                }
            );
    }

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }
})();
