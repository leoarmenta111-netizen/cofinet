(() => {
    "use strict";

    const {
        SUPER_ADMIN,
        adminRequest,
        bootstrapAdmin,
        setButtonLoading,
        showToast,
    } = window.CofiAdmin;


    const BRANCH_STORAGE_KEY =
        "cofinet_retail_admin_branch";


    const state = {
        branches: [],
        catalog: [],
        inventory: [],
        branchCode: "",
        query: "",
    };


    function el(id) {
        return document.getElementById(id);
    }


    function decimalOrNull(value) {
        const normalized =
            String(value ?? "").trim();

        return normalized
            ? normalized
            : null;
    }


    function uuid() {
        if (
            window.crypto
            && typeof window.crypto.randomUUID
                === "function"
        ) {
            return window.crypto.randomUUID();
        }

        return (
            "retail-admin-"
            + Date.now()
            + "-"
            + Math.random()
                .toString(16)
                .slice(2)
        );
    }


    function currentBranch() {
        return state.branches.find(
            branch =>
                branch.code
                === state.branchCode
        ) || null;
    }


    function inventoryByItem(itemId) {
        return state.inventory.find(
            row =>
                Number(row.item_id)
                === Number(itemId)
        ) || null;
    }


    function statusText(status) {
        const labels = {
            AVAILABLE: "Disponible",
            LOW_STOCK: "Stock bajo",
            OUT_OF_STOCK: "Sin stock",
            REVIEW: "Revisar",
        };

        return labels[status] || status || "—";
    }


    function statusTone(status) {
        if (status === "AVAILABLE") {
            return "success";
        }

        if (
            status === "LOW_STOCK"
            || status === "REVIEW"
        ) {
            return "warning";
        }

        if (status === "OUT_OF_STOCK") {
            return "danger";
        }

        return "neutral";
    }


    function filteredCatalog() {
        const query =
            state.query
                .trim()
                .toLowerCase();

        if (!query) {
            return state.catalog;
        }

        return state.catalog.filter(
            item => {
                const haystack = [
                    item.name,
                    item.sku,
                    item.category,
                    item.item_type,
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();

                return haystack.includes(
                    query
                );
            }
        );
    }


    function makeButton(
        label,
        className,
        handler
    ) {
        const button =
            document.createElement(
                "button"
            );

        button.type = "button";
        button.className = className;
        button.textContent = label;

        button.addEventListener(
            "click",
            handler
        );

        return button;
    }


    function renderCatalog() {
        const body =
            el("retail-catalog-rows");

        const rows =
            filteredCatalog();

        body.replaceChildren();

        el("retail-item-count")
            .textContent =
            String(rows.length);

        if (!state.branchCode) {
            const row =
                document.createElement("tr");

            row.innerHTML =
                '<td colspan="7" '
                + 'class="muted">'
                + "Selecciona una sucursal."
                + "</td>";

            body.append(row);
            return;
        }

        if (!rows.length) {
            const row =
                document.createElement("tr");

            row.innerHTML =
                '<td colspan="7" '
                + 'class="muted">'
                + "No hay artículos."
                + "</td>";

            body.append(row);
            return;
        }

        for (const item of rows) {
            const row =
                document.createElement("tr");

            const name =
                document.createElement("td");

            const nameStrong =
                document.createElement(
                    "strong"
                );

            nameStrong.textContent =
                item.name;

            name.append(nameStrong);

            if (item.description) {
                const description =
                    document.createElement(
                        "small"
                    );

                description.className =
                    "muted";

                description.textContent =
                    item.description;

                name.append(
                    document.createElement(
                        "br"
                    ),
                    description
                );
            }

            const type =
                document.createElement("td");

            type.textContent =
                item.item_type === "SERVICE"
                    ? "Servicio"
                    : "Producto";

            const sku =
                document.createElement("td");

            sku.textContent =
                item.sku || "—";

            const category =
                document.createElement("td");

            category.textContent =
                item.category || "—";

            const stock =
                document.createElement("td");

            const inventory =
                inventoryByItem(
                    item.id
                );

            if (
                item.item_type === "SERVICE"
                || !item.inventory_tracked
            ) {
                stock.textContent = "No aplica";
            } else if (!inventory) {
                stock.textContent = "Sin balance";
            } else {
                stock.textContent =
                    String(
                        inventory.quantity
                        ?? inventory.quantity_on_hand
                        ?? "0"
                    );
            }

            const stateCell =
                document.createElement("td");

            const activeBadge =
                document.createElement(
                    "span"
                );

            activeBadge.className =
                "badge "
                + (
                    item.is_active
                        ? "badge-success"
                        : "badge-neutral"
                );

            activeBadge.textContent =
                item.is_active
                    ? "Activo"
                    : "Inactivo";

            stateCell.append(
                activeBadge
            );

            if (inventory?.status) {
                const inventoryBadge =
                    document.createElement(
                        "span"
                    );

                inventoryBadge.className =
                    "badge badge-"
                    + statusTone(
                        inventory.status
                    );

                inventoryBadge.textContent =
                    statusText(
                        inventory.status
                    );

                stateCell.append(
                    document.createTextNode(
                        " "
                    ),
                    inventoryBadge
                );
            }

            const actions =
                document.createElement("td");

            actions.append(
                makeButton(
                    "Editar",
                    "button button-secondary",
                    () => openEditItem(item)
                )
            );

            actions.append(
                document.createTextNode(
                    " "
                ),
                makeButton(
                    item.item_type === "SERVICE"
                        ? "Tarifas"
                        : "Presentaciones",
                    "button button-secondary",
                    () => {
                        const pricing =
                            window.CofiRetailPricingUI;

                        if (!pricing) {
                            showToast(
                                "El módulo de precios no está disponible.",
                                "error"
                            );
                            return;
                        }

                        if (
                            item.item_type
                            === "SERVICE"
                        ) {
                            pricing.openService(
                                item,
                                currentBranch()
                            );
                        } else {
                            pricing.openProduct(
                                item,
                                currentBranch()
                            );
                        }
                    }
                )
            );

            if (
                item.item_type === "PRODUCT"
                && item.inventory_tracked
            ) {
                actions.append(
                    document.createTextNode(
                        " "
                    ),
                    makeButton(
                        "Inventario",
                        "button button-ghost",
                        () =>
                            openInventory(
                                item
                            )
                    )
                );
            }

            row.append(
                name,
                type,
                sku,
                category,
                stock,
                stateCell,
                actions
            );

            body.append(row);
        }
    }


    function applyItemTypeRules() {
        const type =
            el("retail-item-type")
                .value;

        const inventoryFields =
            el(
                "retail-inventory-fields"
            );

        const tracked =
            el(
                "retail-item-tracked"
            );

        const isService =
            type === "SERVICE";

        inventoryFields.hidden =
            isService;

        if (isService) {
            tracked.checked = false;

            el(
                "retail-item-low-stock"
            ).value = "";

            el(
                "retail-item-max-stock"
            ).value = "";
        }
    }


    function openNewItem() {
        const form =
            el("retail-item-form");

        form.reset();

        el("retail-item-id")
            .value = "";

        el(
            "retail-item-dialog-title"
        ).textContent =
            "Nuevo artículo";

        el("retail-item-type")
            .disabled = false;

        el("retail-item-unit")
            .value = "PIECE";

        el("retail-item-cost")
            .value = "0.00";

        el("retail-item-active")
            .checked = true;

        el("retail-item-error")
            .textContent = "";

        applyItemTypeRules();

        el("retail-item-dialog")
            .showModal();

        el("retail-item-name")
            .focus();
    }


    function openEditItem(item) {
        const form =
            el("retail-item-form");

        form.reset();

        el("retail-item-id")
            .value = item.id;

        el(
            "retail-item-dialog-title"
        ).textContent =
            "Editar artículo";

        el("retail-item-type")
            .value = item.item_type;

        el("retail-item-type")
            .disabled = true;

        el("retail-item-name")
            .value = item.name || "";

        el("retail-item-sku")
            .value = item.sku || "";

        el("retail-item-category")
            .value = item.category || "";

        el("retail-item-unit")
            .value =
            item.base_unit_code || "";

        el("retail-item-cost")
            .value =
            item.cost ?? "0.00";

        el("retail-item-description")
            .value =
            item.description || "";

        el("retail-item-tracked")
            .checked =
            Boolean(
                item.inventory_tracked
            );

        el("retail-item-low-stock")
            .value =
            item.low_stock_threshold
            ?? "";

        el("retail-item-max-stock")
            .value =
            item.max_stock
            ?? "";

        el("retail-item-active")
            .checked =
            Boolean(item.is_active);

        el("retail-item-error")
            .textContent = "";

        applyItemTypeRules();

        el("retail-item-dialog")
            .showModal();

        el("retail-item-name")
            .focus();
    }


    function itemPayload() {
        const branch =
            currentBranch();

        if (!branch) {
            throw new Error(
                "Selecciona una sucursal."
            );
        }

        const type =
            el("retail-item-type")
                .value;

        const tracked =
            type === "PRODUCT"
            && el(
                "retail-item-tracked"
            ).checked;

        return {
            branch_id:
                branch.id,

            item_type:
                type,

            sku:
                decimalOrNull(
                    el(
                        "retail-item-sku"
                    ).value
                ),

            name:
                el(
                    "retail-item-name"
                ).value,

            description:
                decimalOrNull(
                    el(
                        "retail-item-description"
                    ).value
                ),

            category:
                decimalOrNull(
                    el(
                        "retail-item-category"
                    ).value
                ),

            base_unit_code:
                el(
                    "retail-item-unit"
                ).value,

            cost:
                el(
                    "retail-item-cost"
                ).value,

            inventory_tracked:
                tracked,

            low_stock_threshold:
                tracked
                    ? decimalOrNull(
                        el(
                            "retail-item-low-stock"
                        ).value
                    )
                    : null,

            max_stock:
                tracked
                    ? decimalOrNull(
                        el(
                            "retail-item-max-stock"
                        ).value
                    )
                    : null,

            is_active:
                el(
                    "retail-item-active"
                ).checked,
        };
    }


    async function saveItem(event) {
        event.preventDefault();

        const form =
            event.currentTarget;

        if (!form.reportValidity()) {
            return;
        }

        const button =
            el("retail-item-save");

        const errorNode =
            el("retail-item-error");

        errorNode.textContent = "";

        try {
            setButtonLoading(
                button,
                true,
                "Guardando…"
            );

            const payload =
                itemPayload();

            const itemId =
                el("retail-item-id")
                    .value;

            if (itemId) {
                const {
                    branch_id,
                    item_type,
                    ...changes
                } = payload;

                void branch_id;
                void item_type;

                await adminRequest(
                    "/admin/retail/catalog/items/"
                    + encodeURIComponent(
                        itemId
                    ),
                    {
                        method: "PATCH",
                        body:
                            JSON.stringify(
                                changes
                            ),
                    }
                );
            } else {
                await adminRequest(
                    "/admin/retail/catalog/items",
                    {
                        method: "POST",
                        body:
                            JSON.stringify(
                                payload
                            ),
                    }
                );
            }

            el("retail-item-dialog")
                .close();

            showToast(
                itemId
                    ? "Artículo actualizado."
                    : "Artículo creado.",
                "success"
            );

            await loadWorkspace();

        } catch (error) {
            errorNode.textContent =
                error.message;

        } finally {
            setButtonLoading(
                button,
                false
            );
        }
    }


    function openInventory(item) {
        el(
            "retail-inventory-item-id"
        ).value = item.id;

        el(
            "retail-inventory-item-name"
        ).textContent =
            item.name;

        el(
            "retail-inventory-operation"
        ).value =
            "entry";

        el(
            "retail-inventory-quantity"
        ).value = "";

        el(
            "retail-inventory-note"
        ).value = "";

        el(
            "retail-inventory-error"
        ).textContent = "";

        updateInventoryLabel();

        el(
            "retail-inventory-dialog"
        ).showModal();

        el(
            "retail-inventory-quantity"
        ).focus();
    }


    function updateInventoryLabel() {
        const operation =
            el(
                "retail-inventory-operation"
            ).value;

        el(
            "retail-inventory-quantity-label"
        ).textContent =
            operation === "adjust"
                ? "Conteo físico"
                : "Cantidad";
    }


    async function saveInventory(
        event
    ) {
        event.preventDefault();

        const form =
            event.currentTarget;

        if (!form.reportValidity()) {
            return;
        }

        const button =
            el(
                "retail-inventory-save"
            );

        const errorNode =
            el(
                "retail-inventory-error"
            );

        errorNode.textContent = "";

        const itemId =
            el(
                "retail-inventory-item-id"
            ).value;

        const operation =
            el(
                "retail-inventory-operation"
            ).value;

        const quantity =
            el(
                "retail-inventory-quantity"
            ).value;

        const note =
            el(
                "retail-inventory-note"
            ).value;

        try {
            setButtonLoading(
                button,
                true,
                "Registrando…"
            );

            const payload = {
                branch_code:
                    state.branchCode,

                note,

                idempotency_key:
                    uuid(),
            };

            if (operation === "adjust") {
                payload.physical_quantity =
                    quantity;
            } else {
                payload.quantity =
                    quantity;
            }

            await adminRequest(
                "/admin/retail/inventory/"
                + encodeURIComponent(
                    itemId
                )
                + "/"
                + operation,
                {
                    method: "POST",
                    body:
                        JSON.stringify(
                            payload
                        ),
                }
            );

            el(
                "retail-inventory-dialog"
            ).close();

            showToast(
                "Inventario actualizado.",
                "success"
            );

            await loadWorkspace();

        } catch (error) {
            errorNode.textContent =
                error.message;

        } finally {
            setButtonLoading(
                button,
                false
            );
        }
    }


    async function loadWorkspace() {
        if (!state.branchCode) {
            state.catalog = [];
            state.inventory = [];
            renderCatalog();
            return;
        }

        const encoded =
            encodeURIComponent(
                state.branchCode
            );

        const [
            catalog,
            inventory,
        ] = await Promise.all([
            adminRequest(
                "/admin/retail/catalog"
                + "?branch_code="
                + encoded
            ),

            adminRequest(
                "/admin/retail/inventory"
                + "?branch_code="
                + encoded
            ),
        ]);

        state.catalog =
            Array.isArray(catalog)
                ? catalog
                : [];

        state.inventory =
            Array.isArray(inventory)
                ? inventory
                : [];

        renderCatalog();
    }


    async function loadBranches() {
        state.branches =
            await adminRequest(
                "/branches"
            );

        const select =
            el("retail-branch");

        select.replaceChildren();

        if (!state.branches.length) {
            select.add(
                new Option(
                    "No hay sucursales",
                    ""
                )
            );

            select.disabled = true;
            return;
        }

        select.disabled = false;

        for (
            const branch
            of state.branches
        ) {
            select.add(
                new Option(
                    branch.name,
                    branch.code
                )
            );
        }

        const saved =
            localStorage.getItem(
                BRANCH_STORAGE_KEY
            );

        const selected =
            state.branches.some(
                branch =>
                    branch.code === saved
            )
                ? saved
                : state.branches[0].code;

        select.value = selected;

        state.branchCode =
            selected;

        el(
            "retail-branch-badge"
        ).textContent =
            select.selectedOptions[0]
                ?.textContent
            || selected;
    }


    function bind() {
        el("retail-new-item")
            .addEventListener(
                "click",
                openNewItem
            );

        el("retail-item-cancel")
            .addEventListener(
                "click",
                () =>
                    el(
                        "retail-item-dialog"
                    ).close()
            );

        el("retail-item-form")
            .addEventListener(
                "submit",
                saveItem
            );

        el("retail-item-type")
            .addEventListener(
                "change",
                applyItemTypeRules
            );

        el(
            "retail-inventory-cancel"
        ).addEventListener(
            "click",
            () =>
                el(
                    "retail-inventory-dialog"
                ).close()
        );

        el(
            "retail-inventory-operation"
        ).addEventListener(
            "change",
            updateInventoryLabel
        );

        el(
            "retail-inventory-form"
        ).addEventListener(
            "submit",
            saveInventory
        );

        el("retail-search")
            .addEventListener(
                "input",
                event => {
                    state.query =
                        event.target.value;

                    renderCatalog();
                }
            );

        el("retail-branch")
            .addEventListener(
                "change",
                async event => {
                    state.branchCode =
                        event.target.value;

                    localStorage.setItem(
                        BRANCH_STORAGE_KEY,
                        state.branchCode
                    );

                    el(
                        "retail-branch-badge"
                    ).textContent =
                        event.target
                            .selectedOptions[0]
                            ?.textContent
                        || state.branchCode;

                    try {
                        await loadWorkspace();
                    } catch (error) {
                        showToast(
                            error.message,
                            "error"
                        );
                    }
                }
            );
    }


    window.CofiRetailAdmin = {
        reload: loadWorkspace,

        getItem(itemId) {
            return state.catalog.find(
                item =>
                    Number(item.id)
                    === Number(itemId)
            ) || null;
        },

        currentBranch,
    };


    (async () => {
        const admin =
            await bootstrapAdmin({
                allowedRoles: [
                    SUPER_ADMIN,
                ],
            });

        if (!admin) {
            return;
        }

        bind();

        await loadBranches();
        await loadWorkspace();

    })().catch(
        error =>
            showToast(
                error.message,
                "error"
            )
    );

})();
