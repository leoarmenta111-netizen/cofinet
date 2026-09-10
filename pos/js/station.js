(() => {
    const station =
        document.body.dataset.station;

    const $ = selector =>
        document.querySelector(selector);

    const state = {
        station,
        branchCode: null,
        orders: [],
        loading: false,
    };

    const labels = {
        KITCHEN: "Cocina",
        BAR: "Barra",
        NEW: "Nueva",
        PREPARING: "Preparando",
        READY: "Lista",
    };

    function getBranchCode() {
        const params =
            new URLSearchParams(
                window.location.search
            );

        return (
            params.get("branch")
            || params.get("branch_code")
            || ""
        )
            .trim()
            .toLowerCase();
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function formatTime(value) {
        if (!value) {
            return "—";
        }

        return new Date(value)
            .toLocaleTimeString(
                "es-MX",
                {
                    hour: "2-digit",
                    minute: "2-digit",
                }
            );
    }

    function nextStatus(status) {
        return {
            NEW: "PREPARING",
            PREPARING: "READY",
        }[status] || null;
    }

    function actionLabel(status) {
        return {
            NEW: "Comenzar preparación",
            PREPARING: "Marcar como lista",
        }[status] || "";
    }

    function renderModifiers(modifiers) {
        if (
            !Array.isArray(modifiers)
            || !modifiers.length
        ) {
            return "";
        }

        return `
            <ul class="station-modifiers">
                ${
                    modifiers
                        .map(
                            modifier => `
                                <li>
                                    ${escapeHtml(
                                        modifier.option_name
                                    )}
                                </li>
                            `
                        )
                        .join("")
                }
            </ul>
        `;
    }

    function renderItem(item) {
        const notes =
            item.notes
                ? `
                    <div class="station-item-note">
                        ${escapeHtml(item.notes)}
                    </div>
                `
                : "";

        return `
            <li class="station-item">
                <div class="station-item-main">
                    <strong class="station-item-quantity">
                        ${escapeHtml(item.quantity)}×
                    </strong>

                    <span class="station-item-name">
                        ${escapeHtml(
                            item.product_name
                        )}
                    </span>
                </div>

                ${renderModifiers(
                    item.modifiers
                )}

                ${notes}
            </li>
        `;
    }

    function renderOrder(order) {
        const status =
            order.station_status;

        const next =
            nextStatus(status);

        const button =
            next
                ? `
                    <button
                        class="station-action"
                        type="button"
                        data-order-uuid="${
                            escapeHtml(
                                order.order_uuid
                            )
                        }"
                        data-next-status="${
                            next
                        }"
                    >
                        ${actionLabel(status)}
                    </button>
                `
                : `
                    <div class="station-ready-label">
                        ✓ Lista para entregar
                    </div>
                `;

        const orderNotes =
            order.notes
                ? `
                    <div class="station-order-note">
                        <strong>Nota:</strong>
                        ${escapeHtml(
                            order.notes
                        )}
                    </div>
                `
                : "";

        return `
            <article
                class="station-order-card"
                data-status="${status}"
            >
                <header class="station-order-header">
                    <div>
                        <span class="station-folio">
                            ${escapeHtml(
                                order.folio
                            )}
                        </span>

                        <span class="station-time">
                            ${formatTime(
                                order.created_at_client
                            )}
                        </span>
                    </div>

                    <span
                        class="station-status-badge"
                        data-status="${status}"
                    >
                        ${labels[status] || status}
                    </span>
                </header>

                ${orderNotes}

                <ul class="station-items">
                    ${
                        order.items
                            .map(renderItem)
                            .join("")
                    }
                </ul>

                <footer class="station-order-footer">
                    ${button}
                </footer>
            </article>
        `;
    }

    function renderColumn(status) {
        const container =
            document.querySelector(
                `[data-column="${status}"]`
            );

        const orders =
            state.orders.filter(
                order =>
                    order.station_status
                    === status
            );

        const count =
            container.querySelector(
                ".station-column-count"
            );

        const list =
            container.querySelector(
                ".station-column-list"
            );

        count.textContent =
            String(orders.length);

        if (!orders.length) {
            list.innerHTML = `
                <div class="station-empty">
                    Sin órdenes
                </div>
            `;

            return;
        }

        list.innerHTML =
            orders
                .map(renderOrder)
                .join("");
    }

    function render() {
        [
            "NEW",
            "PREPARING",
            "READY",
        ].forEach(renderColumn);

        $("#station-total").textContent =
            String(state.orders.length);

        $("#station-updated").textContent =
            `Actualizado ${
                new Date()
                    .toLocaleTimeString(
                        "es-MX",
                        {
                            hour: "2-digit",
                            minute: "2-digit",
                        }
                    )
            }`;
    }

    function showConnectionState(
        text,
        type = "ok"
    ) {
        const element =
            $("#station-connection");

        element.textContent = text;
        element.dataset.state = type;
    }

    async function loadStation() {
        if (
            state.loading
            || !state.branchCode
        ) {
            return;
        }

        state.loading = true;

        try {
            const response =
                await window.CofiPosAPI
                    .listStationOrders(
                        state.station,
                        state.branchCode
                    );

            state.orders =
                response.orders || [];

            render();

            showConnectionState(
                "En línea",
                "ok"
            );

        } catch (error) {
            console.error(
                "Station feed error",
                error
            );

            showConnectionState(
                "Sin conexión",
                "error"
            );

        } finally {
            state.loading = false;
        }
    }

    async function updateOrder(
        orderUuid,
        nextStatus,
        button
    ) {
        button.disabled = true;

        try {
            await window.CofiPosAPI
                .updateStationStatus(
                    orderUuid,
                    state.station,
                    state.branchCode,
                    nextStatus
                );

            await loadStation();

        } catch (error) {
            console.error(
                "Station update error",
                error
            );

            showConnectionState(
                "No se pudo actualizar",
                "error"
            );

            button.disabled = false;
        }
    }

    document.addEventListener(
        "click",
        event => {
            const button =
                event.target.closest(
                    ".station-action"
                );

            if (!button) {
                return;
            }

            updateOrder(
                button.dataset.orderUuid,
                button.dataset.nextStatus,
                button
            );
        }
    );

    state.branchCode =
        getBranchCode();

    $("#station-name").textContent =
        labels[state.station]
        || state.station;

    $("#station-branch").textContent =
        state.branchCode
            ? state.branchCode
                .replaceAll("-", " ")
            : "Sucursal no definida";

    if (!state.branchCode) {
        showConnectionState(
            "Falta ?branch=",
            "error"
        );

        return;
    }

    loadStation();

    setInterval(
        loadStation,
        5000
    );
})();
