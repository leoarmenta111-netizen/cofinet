(() => {
    const state = {
        branchCode: null,
        terminalId: null,
        catalog: null,
        selectedCategoryId: null,

        cart: [],

        modifierProduct: null,
        modifierQuantity: 1,

        paymentMethod: "CASH",
        paymentBusy: false,

        cloudOnline: null,
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

    function resolveBranchCode() {
        const params =
            new URLSearchParams(
                window.location.search
            );

        return params
            .get("branch")
            ?.trim()
            .toLowerCase() || null;
    }

    async function configureTerminal() {
        const requestedBranch =
            resolveBranchCode();

        const savedBranch =
            await window.CofiPosDB.get(
                "meta",
                "branch_code"
            );

        if (!requestedBranch && !savedBranch) {
            throw new Error(
                "Esta terminal no tiene sucursal configurada."
            );
        }

        state.branchCode =
            requestedBranch || savedBranch;

        if (
            requestedBranch &&
            requestedBranch !== savedBranch
        ) {
            await window.CofiPosDB.put(
                "meta",
                requestedBranch,
                "branch_code"
            );
        }

        state.terminalId =
            await window.CofiPosDB
                .getOrCreateTerminalId(
                    state.branchCode
                );

        $("#terminal-id").textContent =
            state.terminalId;
    }

    function updateConnectionState(forcedState = null) {
        const online =
            forcedState === null
                ? navigator.onLine
                : forcedState;

        state.cloudOnline = online;

        const container =
            $("#connection-status");

        container.classList.remove(
            "is-loading",
            "is-online",
            "is-offline"
        );

        container.classList.add(
            online
                ? "is-online"
                : "is-offline"
        );

        $("#connection-label").textContent =
            online
                ? "ONLINE"
                : "OFFLINE";

        $("#offline-banner").hidden =
            online;
    }

    async function updatePendingCount() {
        const count =
            await window.CofiPosDB.countPending();

        $("#pending-count").textContent =
            `${count} ${
                count === 1
                    ? "pendiente"
                    : "pendientes"
            }`;
    }


    /* =====================================================
       CATALOG
       ===================================================== */

    async function loadCatalog() {
        $("#catalog-message").hidden = false;

        $("#catalog-message").textContent =
            navigator.onLine
                ? "Sincronizando catálogo…"
                : "Cargando catálogo local…";

        try {
            const result =
                await window.CofiPosCatalog.load(
                    state.branchCode
                );

            state.catalog = result.catalog;

            updateConnectionState(
                result.source === "cloud"
            );

            $("#branch-name").textContent =
                state.catalog.branch.name;

            renderCategories();
            renderProducts();

            $("#catalog-source").textContent =
                result.source === "cloud"
                    ? "Fuente: Cloud"
                    : "Fuente: Cache local";

            const date =
                new Date(result.cachedAt);

            $("#last-sync").textContent =
                `Última sincronización: ${
                    date.toLocaleString("es-MX")
                }`;

        } catch (error) {
            $("#catalog-message").hidden = false;
            $("#catalog-message").textContent =
                error.message;

            $("#product-grid").replaceChildren();
        }
    }

    function renderCategories() {
        const tabs =
            $("#category-tabs");

        tabs.replaceChildren();

        const categories =
            state.catalog?.categories || [];

        if (!categories.length) {
            state.selectedCategoryId = null;
            return;
        }

        if (
            !categories.some(
                c =>
                    c.id ===
                    state.selectedCategoryId
            )
        ) {
            state.selectedCategoryId =
                categories[0].id;
        }

        categories.forEach(category => {
            const button =
                document.createElement("button");

            button.type = "button";
            button.className =
                "category-tab";

            if (
                category.id ===
                state.selectedCategoryId
            ) {
                button.classList.add(
                    "is-active"
                );
            }

            button.textContent =
                category.name;

            button.addEventListener(
                "click",
                () => {
                    state.selectedCategoryId =
                        category.id;

                    renderCategories();
                    renderProducts();
                }
            );

            tabs.append(button);
        });
    }

    function renderProducts() {
        const grid =
            $("#product-grid");

        const message =
            $("#catalog-message");

        grid.replaceChildren();

        const category =
            state.catalog?.categories?.find(
                item =>
                    item.id ===
                    state.selectedCategoryId
            );

        if (
            !category ||
            !category.products.length
        ) {
            message.hidden = false;

            message.textContent =
                "No hay productos disponibles.";

            return;
        }

        message.hidden = true;

        category.products.forEach(product => {
            const card =
                document.createElement("button");

            card.type = "button";
            card.className =
                "product-card";

            const name =
                document.createElement("strong");

            name.textContent =
                product.name;

            const description =
                document.createElement("span");

            description.className =
                "product-description";

            description.textContent =
                product.description ||
                "Producto CofiCenter";

            const price =
                document.createElement("span");

            price.className =
                "product-price";

            price.textContent =
                money(product.price);

            card.append(
                name,
                description,
                price
            );

            if (product.modifiers?.length) {
                const hint =
                    document.createElement("span");

                hint.className =
                    "product-modifier-hint";

                hint.textContent =
                    "Personalizable";

                card.append(hint);
            }

            card.addEventListener(
                "click",
                () => selectProduct(product)
            );

            grid.append(card);
        });
    }


    /* =====================================================
       MODIFIERS
       ===================================================== */

    function selectProduct(product) {
        if (!product.modifiers?.length) {
            addCartItem(
                product,
                [],
                1
            );

            return;
        }

        state.modifierProduct =
            product;

        state.modifierQuantity =
            1;

        $("#modifier-product-name")
            .textContent =
                `${product.name} · ${money(product.price)}`;

        $("#modifier-qty")
            .textContent = "1";

        renderModifierGroups(product);

        $("#modifier-modal").hidden =
            false;
    }

    function renderModifierGroups(product) {
        const container =
            $("#modifier-groups");

        container.replaceChildren();

        product.modifiers.forEach(group => {
            const section =
                document.createElement("section");

            section.className =
                "modifier-group";

            const header =
                document.createElement("div");

            header.className =
                "modifier-group-title";

            const title =
                document.createElement("strong");

            title.textContent =
                group.name;

            const rule =
                document.createElement("span");

            rule.textContent =
                group.min_select > 0
                    ? "Requerido"
                    : "Opcional";

            header.append(title, rule);
            section.append(header);

            group.options.forEach(option => {
                const label =
                    document.createElement("label");

                label.className =
                    "modifier-option";

                const input =
                    document.createElement("input");

                input.type =
                    group.max_select === 1
                        ? "radio"
                        : "checkbox";

                input.name =
                    `modifier-group-${group.id}`;

                input.value =
                    String(option.id);

                input.dataset.groupId =
                    String(group.id);

                input.dataset.maxSelect =
                    String(group.max_select);

                input.dataset.optionName =
                    option.name;

                input.dataset.groupName =
                    group.name;

                input.dataset.priceDelta =
                    String(option.price_delta);

                if (
                    group.max_select === 1 &&
                    group.min_select > 0 &&
                    group.options.length === 1
                ) {
                    input.checked = true;
                }

                input.addEventListener(
                    "change",
                    enforceModifierLimit
                );

                const name =
                    document.createElement("span");

                name.className =
                    "modifier-option-name";

                name.textContent =
                    option.name;

                const price =
                    document.createElement("span");

                price.className =
                    "modifier-option-price";

                const delta =
                    Number(option.price_delta);

                price.textContent =
                    delta
                        ? `+${money(delta)}`
                        : "Incluido";

                label.append(
                    input,
                    name,
                    price
                );

                section.append(label);
            });

            container.append(section);
        });
    }

    function enforceModifierLimit(event) {
        const input =
            event.currentTarget;

        if (
            input.type !== "checkbox" ||
            !input.checked
        ) {
            return;
        }

        const groupId =
            input.dataset.groupId;

        const maxSelect =
            Number(input.dataset.maxSelect);

        const checked = [
            ...document.querySelectorAll(
                `input[data-group-id="${groupId}"]:checked`
            )
        ];

        if (checked.length > maxSelect) {
            input.checked = false;
        }
    }

    function selectedModifiers() {
        return [
            ...$("#modifier-groups")
                .querySelectorAll(
                    "input:checked"
                )
        ].map(input => ({
            option_id:
                Number(input.value),

            group_id:
                Number(input.dataset.groupId),

            option_name:
                input.dataset.optionName,

            group_name:
                input.dataset.groupName,

            price_delta:
                Number(
                    input.dataset.priceDelta
                ),
        }));
    }

    function validateModifiers(product, selected) {
        for (
            const group
            of product.modifiers || []
        ) {
            const count =
                selected.filter(
                    item =>
                        item.group_id === group.id
                ).length;

            if (count < group.min_select) {
                alert(
                    `Selecciona ${group.name}.`
                );

                return false;
            }

            if (count > group.max_select) {
                alert(
                    `Demasiadas opciones en ${group.name}.`
                );

                return false;
            }
        }

        return true;
    }


    /* =====================================================
       CART
       ===================================================== */

    function addCartItem(
        product,
        modifiers,
        quantity
    ) {
        const modifierTotal =
            modifiers.reduce(
                (sum, item) =>
                    sum + Number(item.price_delta),
                0
            );

        state.cart.push({
            line_uuid:
                window.CofiUUID.v4(),

            product_id:
                product.id,

            product_name:
                product.name,

            base_price:
                Number(product.price),

            modifiers,

            quantity,

            unit_price:
                Number(product.price) +
                modifierTotal,
        });

        renderCart();

        $("#modifier-modal").hidden =
            true;
    }

    function cartTotal() {
        return state.cart.reduce(
            (sum, item) =>
                sum +
                item.unit_price *
                item.quantity,
            0
        );
    }

    function renderCart() {
        const container =
            $("#cart-items");

        container.replaceChildren();

        const hasItems =
            state.cart.length > 0;

        $("#empty-order").hidden =
            hasItems;

        $("#clear-cart").hidden =
            !hasItems;

        $("#checkout-button").disabled =
            !hasItems;

        state.cart.forEach(item => {
            const row =
                document.createElement("article");

            row.className =
                "cart-item";

            const header =
                document.createElement("div");

            header.className =
                "cart-item-header";

            const name =
                document.createElement("span");

            name.className =
                "cart-item-name";

            name.textContent =
                item.product_name;

            const price =
                document.createElement("span");

            price.className =
                "cart-item-price";

            price.textContent =
                money(
                    item.unit_price *
                    item.quantity
                );

            header.append(name, price);

            row.append(header);

            if (item.modifiers.length) {
                const modifiers =
                    document.createElement("div");

                modifiers.className =
                    "cart-modifiers";

                modifiers.textContent =
                    item.modifiers
                        .map(modifier =>
                            modifier.price_delta
                                ? `${modifier.option_name} +${money(modifier.price_delta)}`
                                : modifier.option_name
                        )
                        .join(" · ");

                row.append(modifiers);
            }

            const controls =
                document.createElement("div");

            controls.className =
                "cart-controls";

            const qty =
                document.createElement("div");

            qty.className =
                "quantity-control";

            const minus =
                document.createElement("button");

            minus.type = "button";
            minus.textContent = "−";

            minus.addEventListener(
                "click",
                () => {
                    if (item.quantity <= 1) {
                        removeCartItem(
                            item.line_uuid
                        );
                    } else {
                        item.quantity -= 1;
                        renderCart();
                    }
                }
            );

            const amount =
                document.createElement("strong");

            amount.textContent =
                String(item.quantity);

            const plus =
                document.createElement("button");

            plus.type = "button";
            plus.textContent = "+";

            plus.addEventListener(
                "click",
                () => {
                    item.quantity += 1;
                    renderCart();
                }
            );

            qty.append(
                minus,
                amount,
                plus
            );

            const remove =
                document.createElement("button");

            remove.type = "button";
            remove.className =
                "remove-item";

            remove.textContent =
                "Eliminar";

            remove.addEventListener(
                "click",
                () =>
                    removeCartItem(
                        item.line_uuid
                    )
            );

            controls.append(
                qty,
                remove
            );

            row.append(controls);

            container.append(row);
        });

        const total =
            cartTotal();

        $("#cart-subtotal")
            .textContent =
                money(total);

        $("#cart-total")
            .textContent =
                money(total);
    }

    function removeCartItem(lineUuid) {
        state.cart =
            state.cart.filter(
                item =>
                    item.line_uuid !==
                    lineUuid
            );

        renderCart();
    }

    function clearCart() {
        state.cart = [];
        renderCart();
    }


    /* =====================================================
       PAYMENT
       ===================================================== */

    function openPayment() {
        if (!state.cart.length) return;

        state.paymentMethod =
            "CASH";

        $("#payment-total").textContent =
            money(cartTotal());

        $("#cash-received").value =
            cartTotal().toFixed(2);

        $("#card-reference").value =
            "";

        $("#payment-error").hidden =
            true;

        setPaymentMethod("CASH");

        updateChange();

        $("#payment-modal").hidden =
            false;
    }

    function setPaymentMethod(method) {
        state.paymentMethod = method;

        document
            .querySelectorAll(
                ".payment-method"
            )
            .forEach(button => {
                button.classList.toggle(
                    "is-active",
                    button.dataset.method ===
                    method
                );
            });

        $("#cash-fields").hidden =
            method !== "CASH";

        $("#card-fields").hidden =
            method !== "CARD_EXTERNAL";
    }

    function updateChange() {
        const received =
            Number(
                $("#cash-received").value || 0
            );

        const change =
            Math.max(
                0,
                received - cartTotal()
            );

        $("#change-due").textContent =
            money(change);
    }

    function buildOrderPayload() {
        const now =
            new Date().toISOString();

        const orderUuid =
            window.CofiUUID.v4();

        return {
            order_uuid: orderUuid,

            branch_code:
                state.branchCode,

            terminal_id:
                state.terminalId,

            created_at_client:
                now,

            notes: null,

            items:
                state.cart.map(item => ({
                    product_id:
                        item.product_id,

                    quantity:
                        item.quantity,

                    modifier_option_ids:
                        item.modifiers.map(
                            modifier =>
                                modifier.option_id
                        ),

                    notes: null,
                })),

            payment: {
                payment_uuid:
                    window.CofiUUID.v4(),

                method:
                    state.paymentMethod,

                amount_tendered:
                    state.paymentMethod === "CASH"
                        ? Number(
                            $("#cash-received")
                                .value
                        )
                        : null,

                external_reference:
                    state.paymentMethod ===
                    "CARD_EXTERNAL"
                        ? (
                            $("#card-reference")
                                .value
                                .trim() || null
                        )
                        : null,

                created_at_client:
                    now,
            },
        };
    }

    async function confirmPayment() {
        if (state.paymentBusy) return;

        const total =
            cartTotal();

        if (
            state.paymentMethod === "CASH"
        ) {
            const received =
                Number(
                    $("#cash-received")
                        .value
                );

            if (
                !Number.isFinite(received) ||
                received < total
            ) {
                showPaymentError(
                    "El efectivo recibido es menor al total."
                );

                return;
            }
        }

        state.paymentBusy = true;

        const button =
            $("#confirm-payment");

        button.disabled = true;
        button.textContent =
            "Guardando…";

        $("#payment-error").hidden =
            true;

        try {
            // Defensive recovery: a sale must never leave
            // this terminal without terminal identity.
            if (
                typeof state.terminalId !== "string" ||
                !state.terminalId.trim()
            ) {
                state.terminalId =
                    await window.CofiPosDB
                        .getOrCreateTerminalId(
                            state.branchCode
                        );

                $("#terminal-id").textContent =
                    state.terminalId;
            }

            if (
                !state.terminalId
            ) {
                throw new Error(
                    "No se pudo identificar esta terminal."
                );
            }

            const payload =
                buildOrderPayload();

            if (navigator.onLine) {
                try {
                    const response =
                        await window.CofiPosAPI
                            .createOrder(payload);

                    showSaleSuccess({
                        offline: false,
                        folio:
                            response.folio,
                    });

                    return;

                } catch (error) {
                    // The server DID answer. This is not an
                    // offline sale and must not be hidden.
                    if (error.isHttpError) {
                        console.error(
                            "Error del servidor al registrar venta",
                            error.status,
                            error.payload
                        );

                        showPaymentError(
                            `No se pudo registrar la venta: ${
                                error.message
                            }`
                        );

                        return;
                    }

                    // Network/timeout only: safe offline fallback.
                    console.warn(
                        "Sin conexión con el servidor. " +
                        "Guardando venta localmente.",
                        error
                    );
                }
            }

            await window.CofiPosSync
                .enqueueOrder(
                    payload,
                    total
                );

            showSaleSuccess({
                offline: true,
                folio:
                    `LOCAL-${
                        payload.order_uuid
                            .slice(0, 8)
                            .toUpperCase()
                    }`,
            });

        } catch (error) {
            console.error(
                "Error de venta:",
                error
            );

            showPaymentError(
                error.message ||
                "No se pudo registrar la venta."
            );

        } finally {
            state.paymentBusy = false;

            button.disabled = false;
            button.textContent =
                "Confirmar venta";

            await updatePendingCount();
        }
    }

    function showPaymentError(message) {
        const element =
            $("#payment-error");

        element.textContent =
            message;

        element.hidden = false;
    }

    function showSaleSuccess({
        offline,
        folio,
    }) {
        $("#payment-modal").hidden =
            true;

        $("#success-title").textContent =
            offline
                ? "Venta guardada offline"
                : "Venta registrada";

        $("#success-message").textContent =
            offline
                ? "La venta quedó guardada en esta terminal y se sincronizará automáticamente cuando regrese Internet."
                : "La venta se registró correctamente en Cofi POS.";

        $("#success-folio").textContent =
            folio || "";

        $("#success-modal").hidden =
            false;

        clearCart();
    }


    async function checkConnectivity() {
        const previous =
            state.cloudOnline;

        try {
            await window.CofiPosAPI.checkHealth();

            updateConnectionState(true);

            if (previous === false) {
                await window.CofiPosSync.syncPending();
                await updatePendingCount();
                await loadCatalog();
            }

        } catch {
            updateConnectionState(false);
        }
    }


    /* =====================================================
       SERVICE WORKER / BOOT
       ===================================================== */

    async function registerServiceWorker() {
        if (
            !("serviceWorker" in navigator) ||
            !window.isSecureContext
        ) {
            return;
        }

        await navigator.serviceWorker
            .register(
                "./sw.js",
                { scope: "./" }
            );
    }

    async function boot() {
        updateConnectionState();

        await window.CofiPosDB.open();
        await configureTerminal();

        await updatePendingCount();
        await loadCatalog();

        await registerServiceWorker();

        if (navigator.onLine) {
            await window.CofiPosSync
                .syncPending();

            await updatePendingCount();
        }

        await checkConnectivity();

        setInterval(
            checkConnectivity,
            10000
        );
    }


    /* =====================================================
       EVENTS
       ===================================================== */

    $("#refresh-catalog")
        .addEventListener(
            "click",
            loadCatalog
        );

    $("#clear-cart")
        .addEventListener(
            "click",
            clearCart
        );

    $("#checkout-button")
        .addEventListener(
            "click",
            openPayment
        );

    $("#modifier-close")
        .addEventListener(
            "click",
            () => {
                $("#modifier-modal").hidden =
                    true;
            }
        );

    $("#modifier-qty-minus")
        .addEventListener(
            "click",
            () => {
                state.modifierQuantity =
                    Math.max(
                        1,
                        state.modifierQuantity - 1
                    );

                $("#modifier-qty")
                    .textContent =
                        state.modifierQuantity;
            }
        );

    $("#modifier-qty-plus")
        .addEventListener(
            "click",
            () => {
                state.modifierQuantity += 1;

                $("#modifier-qty")
                    .textContent =
                        state.modifierQuantity;
            }
        );

    $("#modifier-add")
        .addEventListener(
            "click",
            () => {
                const selected =
                    selectedModifiers();

                if (
                    !validateModifiers(
                        state.modifierProduct,
                        selected
                    )
                ) {
                    return;
                }

                addCartItem(
                    state.modifierProduct,
                    selected,
                    state.modifierQuantity
                );
            }
        );

    $("#payment-close")
        .addEventListener(
            "click",
            () => {
                $("#payment-modal").hidden =
                    true;
            }
        );

    document
        .querySelectorAll(
            ".payment-method"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                () =>
                    setPaymentMethod(
                        button.dataset.method
                    )
            );
        });

    $("#cash-received")
        .addEventListener(
            "input",
            updateChange
        );

    $("#confirm-payment")
        .addEventListener(
            "click",
            confirmPayment
        );

    $("#success-close")
        .addEventListener(
            "click",
            () => {
                $("#success-modal").hidden =
                    true;
            }
        );

    window.addEventListener(
        "offline",
        async () => {
            updateConnectionState();
            await updatePendingCount();
        }
    );

    window.addEventListener(
        "online",
        async () => {
            updateConnectionState();

            await window.CofiPosSync
                .syncPending();

            await updatePendingCount();

            await loadCatalog();
        }
    );

    boot().catch(error => {
        console.error(error);

        $("#catalog-message").textContent =
            error.message;
    });

})();
