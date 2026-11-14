window.CofiRetailManagerInventory = (() => {
    "use strict";

    const state = {
        managers: [],
        inventory: [],
        selectedItem: null,
        busy: false,
    };

    const el = id =>
        document.getElementById(id);


    function showDialog(dialog) {
        if (!dialog) return;

        if (
            typeof dialog.showModal
            === "function"
        ) {
            dialog.showModal();
        } else {
            dialog.setAttribute(
                "open",
                ""
            );
        }
    }


    function closeDialog(dialog) {
        if (!dialog) return;

        if (
            typeof dialog.close
            === "function"
        ) {
            if (dialog.open) {
                dialog.close();
            }
        } else {
            dialog.removeAttribute(
                "open"
            );
        }
    }


    function setError(
        id,
        message = ""
    ) {
        const node = el(id);

        if (node) {
            node.textContent =
                String(message || "");
        }
    }


    function statusLabel(status) {
        return ({
            AVAILABLE:
                "Disponible",

            LOW_STOCK:
                "Stock bajo",

            OUT_OF_STOCK:
                "Sin stock",

            REVIEW:
                "Revisar",
        })[status] || status || "—";
    }


    function idempotencyKey() {
        if (
            window.crypto
            && typeof window.crypto
                .randomUUID
                === "function"
        ) {
            return window.crypto
                .randomUUID();
        }

        return (
            "retail-manager-"
            + Date.now()
            + "-"
            + Math.random()
                .toString(16)
                .slice(2)
        );
    }


    function renderManagers() {
        const select =
            el(
                "retail-manager-inventory-manager-id"
            );

        if (!select) return;

        select.replaceChildren(
            new Option(
                "Selecciona gerente",
                ""
            )
        );

        for (
            const manager
            of state.managers
        ) {
            select.add(
                new Option(
                    manager.display_name,
                    String(manager.id)
                )
            );
        }

        select.disabled =
            state.managers.length === 0;
    }


    function renderInventory() {
        const body =
            el(
                "retail-manager-inventory-rows"
            );

        if (!body) return;

        body.replaceChildren();

        if (!state.inventory.length) {
            const row =
                document.createElement(
                    "tr"
                );

            const cell =
                document.createElement(
                    "td"
                );

            cell.colSpan = 5;

            cell.textContent =
                "No hay productos con "
                + "inventario controlado.";

            row.append(cell);
            body.append(row);

            return;
        }

        for (
            const item
            of state.inventory
        ) {
            const row =
                document.createElement(
                    "tr"
                );

            const name =
                document.createElement(
                    "td"
                );

            name.textContent =
                item.item_name;

            const sku =
                document.createElement(
                    "td"
                );

            sku.textContent =
                item.sku || "—";

            const quantity =
                document.createElement(
                    "td"
                );

            quantity.textContent =
                String(
                    item.quantity_on_hand
                );

            const status =
                document.createElement(
                    "td"
                );

            status.textContent =
                statusLabel(
                    item.status
                );

            const action =
                document.createElement(
                    "td"
                );

            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.className =
                "retail-secondary-button";

            button.textContent =
                "Movimiento";

            button.addEventListener(
                "click",
                () => openOperation(
                    item
                )
            );

            action.append(button);

            row.append(
                name,
                sku,
                quantity,
                status,
                action
            );

            body.append(row);
        }
    }


    async function loadData() {
        const [
            managers,
            inventory,
        ] = await Promise.all([
            window.CofiRetailAPI
                .listRetailManagers(),

            window.CofiRetailAPI
                .listManagerInventory(),
        ]);

        state.managers =
            Array.isArray(managers)
                ? managers
                : [];

        state.inventory =
            Array.isArray(inventory)
                ? inventory
                : [];

        const status =
            el(
                "retail-manager-inventory-manager-status"
            );

        if (status) {
            status.textContent =
                "Gerentes: "
                + state.managers.length;
        }

        renderManagers();
        renderInventory();
    }


    async function openPanel() {
        setError(
            "retail-manager-inventory-error",
            ""
        );

        try {
            await loadData();
        } catch (error) {
            setError(
                "retail-manager-inventory-error",
                error?.message
                || "No se pudo cargar "
                + "el inventario."
            );
        }

        showDialog(
            el(
                "retail-manager-modal"
            )
        );
    }


    function updateOperationUI() {
        const operation =
            el(
                "retail-manager-inventory-operation"
            )?.value;

        const label =
            el(
                "retail-manager-inventory-quantity-label"
            );

        const quantity =
            el(
                "retail-manager-inventory-quantity"
            );

        if (label) {
            label.textContent =
                operation === "adjust"
                    ? "Conteo físico"
                    : "Cantidad";
        }

        if (quantity) {
            quantity.min =
                operation === "adjust"
                    ? "0"
                    : "0.001";
        }
    }


    function openOperation(item) {
        state.selectedItem = item;

        closeDialog(
            el(
                "retail-manager-modal"
            )
        );

        el(
            "retail-manager-inventory-item-id"
        ).value =
            item.item_id;

        el(
            "retail-manager-inventory-item-name"
        ).textContent =
            item.item_name;

        el(
            "retail-manager-inventory-operation"
        ).value =
            "entry";

        el(
            "retail-manager-inventory-quantity"
        ).value = "";

        el(
            "retail-manager-inventory-note"
        ).value = "";

        el(
            "retail-manager-inventory-manager-pin"
        ).value = "";

        setError(
            "retail-manager-inventory-operation-error",
            ""
        );

        renderManagers();
        updateOperationUI();

        showDialog(
            el(
                "retail-manager-inventory-operation-modal"
            )
        );
    }


    function buildPayload() {
        const operation =
            el(
                "retail-manager-inventory-operation"
            )?.value;

        const managerId =
            Number(
                el(
                    "retail-manager-inventory-manager-id"
                )?.value
            );

        const managerPin =
            String(
                el(
                    "retail-manager-inventory-manager-pin"
                )?.value
                || ""
            ).trim();

        const note =
            String(
                el(
                    "retail-manager-inventory-note"
                )?.value
                || ""
            ).trim();

        const quantity =
            Number(
                el(
                    "retail-manager-inventory-quantity"
                )?.value
            );

        if (
            !Number.isInteger(managerId)
            || managerId <= 0
        ) {
            throw new Error(
                "Selecciona un gerente."
            );
        }

        if (!managerPin) {
            throw new Error(
                "Ingresa el PIN del gerente."
            );
        }

        if (!note) {
            throw new Error(
                "Ingresa el motivo "
                + "del movimiento."
            );
        }

        const validQuantity =
            operation === "adjust"
                ? (
                    Number.isFinite(quantity)
                    && quantity >= 0
                )
                : (
                    Number.isFinite(quantity)
                    && quantity > 0
                );

        if (!validQuantity) {
            throw new Error(
                operation === "adjust"
                    ? "El conteo físico no "
                        + "puede ser negativo."
                    : "La cantidad debe ser "
                        + "mayor a cero."
            );
        }

        const payload = {
            authorizing_manager_staff_id:
                managerId,

            manager_pin:
                managerPin,

            idempotency_key:
                idempotencyKey(),

            note,
        };

        if (operation === "adjust") {
            payload.physical_quantity =
                String(quantity);
        } else {
            payload.quantity =
                String(quantity);
        }

        return {
            operation,
            payload,
        };
    }


    async function confirmOperation() {
        if (
            state.busy
            || !state.selectedItem
        ) {
            return;
        }

        setError(
            "retail-manager-inventory-operation-error",
            ""
        );

        try {
            state.busy = true;

            const {
                operation,
                payload,
            } = buildPayload();

            const itemId =
                state.selectedItem.item_id;

            if (operation === "entry") {
                await window
                    .CofiRetailAPI
                    .managerInventoryEntry(
                        itemId,
                        payload
                    );

            } else if (
                operation === "removal"
            ) {
                await window
                    .CofiRetailAPI
                    .managerInventoryRemoval(
                        itemId,
                        payload
                    );

            } else {
                await window
                    .CofiRetailAPI
                    .managerInventoryAdjust(
                        itemId,
                        payload
                    );
            }

            /*
             * El PIN nunca se persiste.
             * Se elimina inmediatamente.
             */
            el(
                "retail-manager-inventory-manager-pin"
            ).value = "";

            closeDialog(
                el(
                    "retail-manager-inventory-operation-modal"
                )
            );

            state.selectedItem = null;

            await loadData();

            showDialog(
                el(
                    "retail-manager-modal"
                )
            );

            const message =
                el(
                    "retail-sale-message"
                );

            if (message) {
                message.textContent =
                    "Inventario actualizado "
                    + "correctamente.";
            }

        } catch (error) {
            setError(
                "retail-manager-inventory-operation-error",
                error?.message
                || "No se pudo registrar "
                + "el movimiento."
            );

        } finally {
            state.busy = false;
        }
    }


    async function cancelOperation() {
        const pin =
            el(
                "retail-manager-inventory-manager-pin"
            );

        if (pin) {
            pin.value = "";
        }

        closeDialog(
            el(
                "retail-manager-inventory-operation-modal"
            )
        );

        state.selectedItem = null;

        showDialog(
            el(
                "retail-manager-modal"
            )
        );
    }


    function bind() {
        el(
            "retail-manager-inventory-open"
        )?.addEventListener(
            "click",
            openPanel
        );

        el(
            "retail-manager-inventory-close"
        )?.addEventListener(
            "click",
            () =>
                closeDialog(
                    el(
                        "retail-manager-modal"
                    )
                )
        );

        el(
            "retail-manager-inventory-refresh"
        )?.addEventListener(
            "click",
            async () => {
                setError(
                    "retail-manager-inventory-error",
                    ""
                );

                try {
                    await loadData();
                } catch (error) {
                    setError(
                        "retail-manager-inventory-error",
                        error?.message
                        || "No se pudo actualizar."
                    );
                }
            }
        );

        el(
            "retail-manager-inventory-operation"
        )?.addEventListener(
            "change",
            updateOperationUI
        );

        el(
            "retail-manager-inventory-operation-cancel"
        )?.addEventListener(
            "click",
            cancelOperation
        );

        el(
            "retail-manager-inventory-operation-confirm"
        )?.addEventListener(
            "click",
            confirmOperation
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
        state,
        openPanel,
        loadData,
        buildPayload,
    };
})();
