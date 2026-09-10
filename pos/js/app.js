(() => {
    const state = {
        branchCode: null,
        terminalId: null,
        catalog: null,
        selectedCategoryId: "all",
        searchQuery: "",

        selectedCustomer: null,
        customerResults: [],
        customersBusy: false,

        cart: [],

        modifierProduct: null,
        modifierQuantity: 1,

        paymentMethod: "CASH",
        paymentBusy: false,
        paymentCheckoutTotals: null,
        lastReceipt: null,

        receiptSettings: null,

        cloudOnline: null,
        syncing: false,
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

    async function loadReceiptSettingsForBranch(
        branchCode
    ) {
        const cachedReceiptSettings =
            await window.CofiPosDB
                .getReceiptSettings(
                    branchCode
                );

        state.receiptSettings =
            cachedReceiptSettings;

        try {
            const refreshedReceiptSettings =
                await window.CofiPosAPI
                    .getReceiptSettings(
                        branchCode
                    );

            await window.CofiPosDB
                .setReceiptSettings(
                    branchCode,
                    refreshedReceiptSettings
                );

            state.receiptSettings =
                refreshedReceiptSettings;

        } catch (error) {
            state.receiptSettings =
                cachedReceiptSettings;

            console.warn(
                "Receipt settings refresh unavailable:",
                error
            );
        }

        return state.receiptSettings;
    }


    async function configureTerminal() {
        const requestedBranch =
            resolveBranchCode();

        const savedBranch =
            await window.CofiPosDB.get(
                "meta",
                "branch_code"
            );

        const localBranch =
            window.localStorage.getItem(
                "cofi_pos_branch"
            );

        state.branchCode =
            requestedBranch ||
            savedBranch ||
            localBranch;

        if (!state.branchCode) {
            throw new Error(
                "Esta terminal no tiene sucursal configurada."
            );
        }

        await window.CofiPosDB.put(
            "meta",
            state.branchCode,
            "branch_code"
        );

        window.localStorage.setItem(
            "cofi_pos_branch",
            state.branchCode
        );

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
            "is-offline",
            "is-syncing"
        );

        container.classList.add(
            state.syncing
                ? "is-syncing"
                : online
                ? "is-online"
                : "is-offline"
        );

        $("#connection-label").textContent =
            state.syncing
                ? "Sincronizando…"
                : online
                    ? "En línea"
                    : "Sin conexión";

        $("#connection-detail").textContent =
            state.syncing
                ? "Enviando ventas pendientes"
                : online
                    ? "Conectado al servidor"
                    : "Operación local activa";

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

        if (count > 0 && state.cloudOnline) {
            $("#connection-detail").textContent =
                `${count} ${count === 1 ? "venta pendiente" : "ventas pendientes"}`;
        }
    }

    function setSyncing(syncing) {
        state.syncing = syncing;
        updateConnectionState(state.cloudOnline);
    }

    async function syncPendingWithStatus() {
        const pending =
            await window.CofiPosDB.countPending();

        if (!pending || !state.cloudOnline) return;

        setSyncing(true);

        try {
            await window.CofiPosSync.syncPending();
            await updatePendingCount();
        } finally {
            setSyncing(false);
        }
    }


    /* =====================================================
       CATALOG
       ===================================================== */

    function cacheCatalogImages() {
        if (
            !("serviceWorker" in navigator) ||
            !navigator.serviceWorker.controller ||
            !state.catalog
        ) {
            return;
        }

        const urls =
            (state.catalog.categories || [])
                .flatMap(
                    category =>
                        category.products || []
                )
                .map(
                    product =>
                        product.image_url
                )
                .filter(Boolean);

        if (!urls.length) {
            return;
        }

        navigator.serviceWorker.controller
            .postMessage({
                type:
                    "CACHE_PRODUCT_IMAGES",
                urls,
            });
    }


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

            cacheCatalogImages();

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

        const allCount = categories.reduce(
            (sum, category) =>
                sum + (category.products?.length || 0),
            0
        );

        const filters = [
            {
                id: "all",
                name: "Todos",
                products: { length: allCount },
            },
            ...categories,
        ];

        if (
            state.selectedCategoryId !== "all" &&
            !categories.some(
                category =>
                    category.id === state.selectedCategoryId
            )
        ) {
            state.selectedCategoryId = "all";
        }

        filters.forEach(category => {
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

            const label = document.createElement("span");
            label.textContent = category.name;

            const count = document.createElement("span");
            count.className = "category-tab-count";
            count.textContent = category.products?.length || 0;

            button.append(label, count);

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

        const categories =
            state.catalog?.categories || [];

        const products = (
            state.selectedCategoryId === "all"
                ? categories.flatMap(category =>
                    category.products || []
                )
                : categories.find(
                    item =>
                        item.id === state.selectedCategoryId
                )?.products || []
        ).filter(product => {
            if (!state.searchQuery) return true;

            const haystack = [
                product.name,
                product.sku,
                product.description,
            ]
                .filter(Boolean)
                .join(" ")
                .toLocaleLowerCase("es-MX");

            return haystack.includes(state.searchQuery);
        });

        $("#product-result-count").textContent =
            `${products.length} ${
                products.length === 1
                    ? "disponible"
                    : "disponibles"
            }`;

        if (!products.length) {
            message.hidden = false;

            message.textContent =
                state.searchQuery
                    ? "No encontramos productos con esa búsqueda."
                    : "No hay productos disponibles.";

            return;
        }

        message.hidden = true;

        products.forEach(product => {
            const card =
                document.createElement("button");

            card.type = "button";
            card.className =
                "product-card";

            const visual =
                document.createElement("span");

            visual.className = "product-visual";

            if (product.image_url) {
                const image = document.createElement("img");
                image.className = "product-image";
                image.src = product.image_url;
                image.alt = "";
                image.loading = "lazy";
                image.addEventListener("error", () => {
                    image.remove();
                    visual.append(createProductPlaceholder());
                }, { once: true });
                visual.append(image);
            } else {
                visual.append(createProductPlaceholder());
            }

            if (product.modifiers?.length) {
                const badge = document.createElement("span");
                badge.className = "product-badge";
                badge.textContent = "Personalizable";
                visual.append(badge);
            }

            const content = document.createElement("span");
            content.className = "product-content";

            const name = document.createElement("strong");
            name.className = "product-name";
            name.textContent = product.name;

            const description =
                document.createElement("span");

            description.className =
                "product-description";

            description.textContent =
                product.description ||
                (product.sku ? `SKU ${product.sku}` : "Producto Cofi");

            const price =
                document.createElement("span");

            price.className =
                "product-price";

            price.textContent =
                money(product.price);

            const footer = document.createElement("span");
            footer.className = "product-footer";

            const add = document.createElement("span");
            add.className = "product-add";
            add.textContent = "+";

            footer.append(price, add);
            content.append(name, description, footer);
            card.append(visual, content);

            card.addEventListener(
                "click",
                () => selectProduct(product)
            );

            grid.append(card);
        });
    }

    function createProductPlaceholder() {
        const placeholder = document.createElement("span");
        placeholder.className = "product-placeholder";
        placeholder.innerHTML =
            '<svg aria-hidden="true"><use href="#i-coffee"></use></svg>';
        return placeholder;
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
                product.name;

        $("#modifier-base-price").textContent =
            `Precio base ${money(product.price)}`;

        $("#modifier-qty")
            .textContent = "1";

        renderModifierGroups(product);
        updateModifierTotal();

        $("#modifier-error").hidden = true;

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

            const titleBox = document.createElement("div");

            const title = document.createElement("strong");
            title.textContent = group.name;

            const selection = document.createElement("small");
            selection.textContent =
                group.max_select === 1
                    ? "Selecciona una opción"
                    : `Selecciona de ${group.min_select} a ${group.max_select}`;

            titleBox.append(title, selection);

            const rule =
                document.createElement("span");

            rule.className = "modifier-rule";
            rule.classList.toggle(
                "is-required",
                group.min_select > 0
            );
            rule.textContent =
                group.min_select > 0
                    ? "Obligatorio"
                    : "Opcional";

            header.append(titleBox, rule);
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

                input.addEventListener("change", event => {
                    enforceModifierLimit(event);
                    section
                        .querySelectorAll(".modifier-option")
                        .forEach(optionLabel =>
                            optionLabel.classList.toggle(
                                "is-selected",
                                optionLabel.querySelector("input").checked
                            )
                        );
                    $("#modifier-error").hidden = true;
                    updateModifierTotal();
                });

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

    function updateModifierTotal() {
        const product = state.modifierProduct;
        if (!product) return;

        const optionsTotal = selectedModifiers().reduce(
            (sum, option) => sum + option.price_delta,
            0
        );

        $("#modifier-add-total").textContent = money(
            (Number(product.price) + optionsTotal) *
            state.modifierQuantity
        );
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
                $("#modifier-error").textContent =
                    `Selecciona ${group.name} para continuar.`;
                $("#modifier-error").hidden = false;

                return false;
            }

            if (count > group.max_select) {
                $("#modifier-error").textContent =
                    `Sólo puedes seleccionar ${group.max_select} en ${group.name}.`;
                $("#modifier-error").hidden = false;

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

    function calculateCheckoutTotals({
        merchandiseCents,
        discountCents = 0,
        tipCents = 0,
        receiptSettings,
    }) {
        if (!receiptSettings) {
            throw new Error(
                "Receipt settings unavailable"
            );
        }

        const subtotalCents =
            merchandiseCents;

        const normalizedDiscountCents =
            discountCents;

        const normalizedTipCents =
            tipCents;

        const taxMode =
            String(
                receiptSettings.tax_mode ||
                ""
            ).toUpperCase();

        const taxRate =
            Number(
                receiptSettings.tax_rate ??
                0
            );

        const {
            taxCents,
            totalCents,
        } =
            window.CofiPosReceipt
                .calculateTax({
                    merchandiseCents:
                        subtotalCents,

                    discountCents:
                        normalizedDiscountCents,

                    tipCents:
                        normalizedTipCents,

                    taxMode,
                    taxRate,
                });

        return {
            subtotalCents,

            discountCents:
                normalizedDiscountCents,

            taxMode,
            taxRate,
            taxCents,

            tipCents:
                normalizedTipCents,

            totalCents,
        };
    }


    function canonicalMoneyString(
        value,
        name = "money"
    ) {
        const numeric =
            typeof value === "string"
                ? Number(
                    value.trim()
                )
                : Number(value);

        if (
            !Number.isFinite(numeric) ||
            numeric < 0
        ) {
            throw new Error(
                `${name} must be a non-negative money value`
            );
        }

        return numeric.toFixed(2);
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

            const title = document.createElement("div");
            title.className = "cart-item-title";

            const quantityBadge = document.createElement("span");
            quantityBadge.className = "cart-item-quantity";
            quantityBadge.textContent = item.quantity;

            const name = document.createElement("span");

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

            title.append(quantityBadge, name);
            header.append(title, price);

            row.append(header);

            const unitPrice = document.createElement("div");
            unitPrice.className = "cart-unit-price";
            unitPrice.textContent = `${money(item.unit_price)} por unidad`;
            row.append(unitPrice);

            if (item.modifiers.length) {
                const modifiers =
                    document.createElement("div");

                modifiers.className =
                    "cart-modifiers";

                item.modifiers.forEach(modifier => {
                    const modifierRow = document.createElement("div");
                    modifierRow.className = "cart-modifier";

                    const modifierName = document.createElement("span");
                    modifierName.textContent = modifier.option_name;

                    const modifierPrice = document.createElement("span");
                    modifierPrice.textContent = modifier.price_delta
                        ? `+${money(modifier.price_delta)}`
                        : "Incluido";

                    modifierRow.append(modifierName, modifierPrice);
                    modifiers.append(modifierRow);
                });

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

            remove.title = "Eliminar producto";
            remove.setAttribute("aria-label", "Eliminar producto");
            remove.innerHTML =
                '<svg aria-hidden="true"><use href="#i-trash"></use></svg>';

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

        $("#checkout-total").textContent =
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

        const merchandiseCents =
            window.CofiPosReceipt
                .moneyToCents(
                    canonicalMoneyString(
                        cartTotal(),
                        "cart total"
                    ),
                    "cart total"
                );

        state.paymentCheckoutTotals =
            calculateCheckoutTotals({
                merchandiseCents,
                discountCents: 0,
                tipCents: 0,
                receiptSettings:
                    state.receiptSettings,
            });

        const paymentTotal =
            window.CofiPosReceipt
                .centsToMoney(
                    state
                        .paymentCheckoutTotals
                        .totalCents
                );

        $("#payment-total").textContent =
            money(paymentTotal);

        $("#confirm-payment-total").textContent =
            money(paymentTotal);

        $("#cash-received").value =
            paymentTotal;

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
        const receivedCents =
            window.CofiPosReceipt
                .moneyToCents(
                    canonicalMoneyString(
                        $("#cash-received")
                            .value || "0",
                        "cash received"
                    ),
                    "cash received"
                );

        const totalCents =
            state.paymentCheckoutTotals
                ?.totalCents ?? 0;

        const changeCents =
            Math.max(
                0,
                receivedCents -
                    totalCents
            );

        $("#change-due").textContent =
            money(
                window.CofiPosReceipt
                    .centsToMoney(
                        changeCents
                    )
            );
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

            customer_uuid:
                state.selectedCustomer
                    ? state.selectedCustomer.customer_uuid
                    : null,

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

        if (!state.receiptSettings) {
            showPaymentError(
                "Conecta esta terminal a internet una vez para cargar la configuración del ticket."
            );

            return;
        }

        const checkoutTotals =
            state.paymentCheckoutTotals;

        if (!checkoutTotals) {
            showPaymentError(
                "No fue posible confirmar el total del cobro. Cierra y vuelve a abrir el pago."
            );

            return;
        }

        let amountTenderedCents =
            null;

        let changeDueCents =
            null;

        if (
            state.paymentMethod ===
            "CASH"
        ) {
            try {
                amountTenderedCents =
                    window.CofiPosReceipt
                        .moneyToCents(
                            canonicalMoneyString(
                                $("#cash-received")
                                    .value || "0",
                                "cash received"
                            ),
                            "cash received"
                        );
            } catch {
                showPaymentError(
                    "Ingresa un monto de efectivo válido."
                );

                return;
            }

            if (
                amountTenderedCents <
                checkoutTotals.totalCents
            ) {
                showPaymentError(
                    "El efectivo recibido es menor al total."
                );

                return;
            }

            changeDueCents =
                amountTenderedCents -
                checkoutTotals.totalCents;
        }

        state.paymentBusy = true;

        const button =
            $("#confirm-payment");

        button.disabled = true;

        const buttonLabel =
            button.querySelector("span");

        if (buttonLabel) {
            buttonLabel.textContent =
                "Guardando…";
        }

        $("#payment-error").hidden =
            true;

        try {
            if (
                typeof state.terminalId !==
                    "string" ||
                !state.terminalId.trim()
            ) {
                state.terminalId =
                    await window.CofiPosDB
                        .getOrCreateTerminalId(
                            state.branchCode
                        );

                $("#terminal-id")
                    .textContent =
                        state.terminalId;
            }

            if (!state.terminalId) {
                throw new Error(
                    "No se pudo identificar esta terminal."
                );
            }

            /*
             * buildOrderPayload() captures one timestamp
             * and one order UUID. Those values become part
             * of the frozen sale identity below.
             */
            const payload =
                buildOrderPayload();

            const soldAt =
                payload.created_at_client;

            const soldAtDate =
                new Date(soldAt);

            const folio =
                window.CofiPosFolio
                    .generate({
                        branchPrefix:
                            state
                                .receiptSettings
                                .folio_prefix,

                        soldAt:
                            soldAtDate,

                        timeZone:
                            state
                                .receiptSettings
                                .timezone,
                    });

            const receiptItems =
                state.cart.map(
                    item => {
                        const unitPriceCents =
                            window.CofiPosReceipt
                                .moneyToCents(
                                    canonicalMoneyString(
                                        item.unit_price,
                                        "item unit price"
                                    ),
                                    "item unit price"
                                );

                        const quantity =
                            Number(
                                item.quantity
                            );

                        return {
                            product_id:
                                Number(
                                    item.product_id
                                ),

                            product_name:
                                String(
                                    item.product_name ||
                                    ""
                                ),

                            quantity,

                            unit_price_cents:
                                unitPriceCents,

                            line_total_cents:
                                unitPriceCents *
                                quantity,

                            modifiers:
                                (
                                    item.modifiers ||
                                    []
                                ).map(
                                    modifier => ({
                                        modifier_group_id:
                                            modifier.group_id ==
                                            null
                                                ? null
                                                : Number(
                                                    modifier.group_id
                                                ),

                                        modifier_option_id:
                                            modifier.option_id ==
                                            null
                                                ? null
                                                : Number(
                                                    modifier.option_id
                                                ),

                                        group_name:
                                            modifier.group_name ??
                                            null,

                                        option_name:
                                            String(
                                                modifier.option_name ??
                                                modifier.name ??
                                                ""
                                            ),

                                        price_delta_cents:
                                            window.CofiPosReceipt
                                                .moneyToCents(
                                                    canonicalMoneyString(
                                                        modifier.price_delta ??
                                                        0,
                                                        "modifier price delta"
                                                    ),
                                                    "modifier price delta"
                                                ),

                                        customer_visible:
                                            true,
                                    })
                                ),
                        };
                    }
                );

            const receiptSnapshot =
                window.CofiPosReceipt
                    .buildSnapshot({
                        order_uuid:
                            payload.order_uuid,

                        folio,

                        sold_at:
                            soldAt,

                        currency:
                            state
                                .receiptSettings
                                .currency ||
                            "MXN",

                        business: {
                            business_name:
                                state
                                    .receiptSettings
                                    .business_name,

                            logo_ref:
                                state
                                    .receiptSettings
                                    .logo_ref ??
                                null,

                            phone:
                                state
                                    .receiptSettings
                                    .phone ??
                                null,

                            web_social:
                                state
                                    .receiptSettings
                                    .web_social ??
                                null,

                            footer_message:
                                state
                                    .receiptSettings
                                    .footer_message ??
                                null,
                        },

                        branch: {
                            branch_code:
                                state.branchCode,

                            branch_name:
                                state
                                    .receiptSettings
                                    .branch_name,

                            address:
                                state
                                    .receiptSettings
                                    .address ??
                                null,

                            phone:
                                state
                                    .receiptSettings
                                    .phone ??
                                null,
                        },

                        terminal: {
                            terminal_id:
                                state.terminalId,
                        },

                        customer:
                            state.selectedCustomer
                                ? {
                                    name:
                                        state
                                            .selectedCustomer
                                            .name,
                                }
                                : null,

                        items:
                            receiptItems,

                        totals: {
                            subtotal_cents:
                                checkoutTotals
                                    .subtotalCents,

                            discount_cents:
                                checkoutTotals
                                    .discountCents,

                            tax_mode:
                                checkoutTotals
                                    .taxMode,

                            tax_rate:
                                String(
                                    state
                                        .receiptSettings
                                        .tax_rate ??
                                    checkoutTotals
                                        .taxRate
                                ),

                            tax_cents:
                                checkoutTotals
                                    .taxCents,

                            tip_cents:
                                checkoutTotals
                                    .tipCents,

                            total_cents:
                                checkoutTotals
                                    .totalCents,
                        },

                        payment: {
                            method:
                                state
                                    .paymentMethod,

                            amount_cents:
                                checkoutTotals
                                    .totalCents,

                            amount_tendered_cents:
                                amountTenderedCents,

                            change_due_cents:
                                changeDueCents,
                        },
                    });

            window.CofiPosReceipt
                .validateSnapshot(
                    receiptSnapshot
                );

            /*
             * The API/sync payload receives the exact same
             * identity and snapshot. Nothing gets rebuilt.
             */
            payload.folio =
                folio;

            payload.receipt_snapshot =
                receiptSnapshot;

            payload.created_at_client =
                soldAt;

            payload.payment
                .created_at_client =
                    soldAt;

            payload.payment
                .amount_tendered =
                    amountTenderedCents ===
                    null
                        ? null
                        : window
                            .CofiPosReceipt
                            .centsToMoney(
                                amountTenderedCents
                            );

            const localTotal =
                Number(
                    window.CofiPosReceipt
                        .centsToMoney(
                            checkoutTotals
                                .totalCents
                        )
                );

            const localOrder = {
                order_uuid:
                    payload.order_uuid,

                payload,

                folio,

                receipt_snapshot:
                    receiptSnapshot,

                local_total:
                    localTotal,

                sync_status:
                    "PENDING_SYNC",

                created_at:
                    soldAt,
            };

            const syncEvent = {
                event_uuid:
                    payload.order_uuid,

                event_type:
                    "ORDER_CREATED",

                payload,

                sync_status:
                    "PENDING_SYNC",

                attempts: 0,

                last_error: null,

                created_at:
                    soldAt,
            };

            /*
             * This is the sale boundary:
             * local order + receipt + queue event are one
             * IndexedDB transaction.
             */
            try {
                await window.CofiPosDB
                    .finalizePaidSale({
                        order_uuid:
                            payload.order_uuid,

                        local_order:
                            localOrder,

                        receipt_snapshot:
                            receiptSnapshot,

                        sync_event:
                            syncEvent,
                    });
            } catch (error) {
                const localError =
                    new Error(
                        "No se pudo guardar la venta localmente. El carrito sigue intacto; intenta confirmar el cobro nuevamente."
                    );

                localError.cause =
                    error;

                throw localError;
            }

            state.lastReceipt =
                receiptSnapshot;

            /*
             * Network state may change after local
             * finalization, but never the sale identity.
             */
            let pendingSync =
                true;

            if (navigator.onLine) {
                try {
                    await window.CofiPosSync
                        .syncPending();

                    const persistedOrder =
                        await window.CofiPosDB
                            .getLocalOrder(
                                payload
                                    .order_uuid
                            );

                    pendingSync =
                        persistedOrder
                            ?.sync_status !==
                        "SYNCED";

                } catch (syncError) {
                    pendingSync =
                        true;

                    console.warn(
                        "Venta guardada localmente; sincronización pendiente.",
                        syncError
                    );
                }
            }

            showSaleSuccess({
                offline:
                    pendingSync,

                folio,

                receipt:
                    receiptSnapshot,
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
            state.paymentBusy =
                false;

            button.disabled =
                false;

            const buttonLabel =
                button.querySelector(
                    "span"
                );

            if (buttonLabel) {
                buttonLabel.textContent =
                    "Confirmar cobro";
            }

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
        receipt = null,
    }) {
        $("#payment-modal").hidden =
            true;

        if (receipt) {
            state.lastReceipt =
                receipt;
        }

        $("#success-title").textContent =
            offline
                ? "Venta guardada sin conexión"
                : "Venta registrada";

        $("#success-message").textContent =
            offline
                ? "La venta quedó guardada en esta terminal y se sincronizará automáticamente cuando regrese Internet."
                : "La venta se registró correctamente en Cofi POS.";

        $("#success-folio").textContent =
            folio || "";

        $("#success-modal").hidden =
            false;

        const viewReceiptButton =
            $("#success-view-receipt");

        const printReceiptButton =
            $("#success-print-receipt");

        const newSaleButton =
            $("#success-close");

        if (viewReceiptButton) {
            viewReceiptButton.onclick =
                () => {
                    if (
                        !state.lastReceipt
                    ) {
                        return;
                    }

                    window
                        .CofiPosReceiptRenderer
                        .open(
                            state.lastReceipt
                        );
                };
        }

        if (printReceiptButton) {
            printReceiptButton.onclick =
                () => {
                    if (
                        !state.lastReceipt
                    ) {
                        return;
                    }

                    window
                        .CofiPosReceiptRenderer
                        .print(
                            state.lastReceipt
                        );
                };
        }

        if (newSaleButton) {
            newSaleButton.onclick =
                () => {
                    window
                        .CofiPosReceiptRenderer
                        ?.close();

                    $("#success-modal").hidden =
                        true;

                    clearCart();
                };
        }

        /*
         * Preserve existing Task 5 behavior:
         * the completed sale is already frozen locally,
         * while the working cart is reset for the next sale.
         */
        clearCart();
    }


    function customerDate(value) {
        if (!value) {
            return "Sin compras";
        }

        const parsed =
            new Date(value);

        if (
            Number.isNaN(
                parsed.getTime()
            )
        ) {
            return "—";
        }

        return parsed.toLocaleDateString(
            "es-MX",
            {
                day: "2-digit",
                month: "short",
                year: "numeric",
            }
        );
    }


    function renderSelectedCustomer() {
        const customer =
            state.selectedCustomer;

        const empty =
            $("#no-selected-customer");

        const card =
            $("#selected-customer-card");

        if (!empty || !card) {
            return;
        }

        empty.hidden =
            Boolean(customer);

        card.hidden =
            !customer;

        if (!customer) {
            return;
        }

        $("#selected-customer-name")
            .textContent =
                customer.name || "Cliente";

        $("#selected-customer-phone")
            .textContent =
                customer.phone || "—";

        $("#selected-customer-points")
            .textContent =
                String(
                    customer.loyalty_points || 0
                );

        $("#selected-customer-visits")
            .textContent =
                String(
                    customer.visits || 0
                );

        $("#selected-customer-spend")
            .textContent =
                money(
                    customer.total_spent || 0
                );

        $("#selected-customer-last-purchase")
            .textContent =
                customerDate(
                    customer.last_purchase_at
                );
    }


    function showSaleFromCustomers() {
        const sale =
            $("#sale-view");

        const orders =
            $("#orders-view");

        const customers =
            $("#customers-view");

        if (sale) {
            sale.hidden = false;
        }

        if (orders) {
            orders.hidden = true;
        }

        if (customers) {
            customers.hidden = true;
        }

        $(".workspace")
            ?.classList.remove(
                "orders-mode",
                "customers-mode"
            );

        $("#nav-sale")
            ?.classList.add(
                "is-active"
            );

        $("#nav-orders")
            ?.classList.remove(
                "is-active"
            );

        $("#nav-customers")
            ?.classList.remove(
                "is-active"
            );
    }


    function clearSelectedCustomer() {
        state.selectedCustomer =
            null;

        renderSelectedCustomer();
    }


    function selectCustomer(customer) {
        state.selectedCustomer =
            customer || null;

        renderSelectedCustomer();

        showSaleFromCustomers();
    }


    function renderCustomerResults() {
        const container =
            $("#customer-results");

        const message =
            $("#customers-message");

        if (!container) {
            return;
        }

        container.replaceChildren();

        if (
            !state.customerResults.length
        ) {
            if (message) {
                message.hidden = false;
                message.textContent =
                    "No encontramos clientes con esa búsqueda.";
            }

            return;
        }

        if (message) {
            message.hidden = true;
        }

        state.customerResults
            .forEach(customer => {
                const card =
                    document.createElement(
                        "article"
                    );

                card.className =
                    "customer-card";


                const top =
                    document.createElement(
                        "div"
                    );

                top.className =
                    "customer-card-top";


                const identity =
                    document.createElement(
                        "div"
                    );

                identity.className =
                    "customer-card-identity";


                const name =
                    document.createElement(
                        "strong"
                    );

                name.textContent =
                    customer.name;


                const phone =
                    document.createElement(
                        "span"
                    );

                phone.textContent =
                    customer.phone;


                identity.append(
                    name,
                    phone
                );


                const choose =
                    document.createElement(
                        "button"
                    );

                choose.type =
                    "button";

                choose.className =
                    "customer-select-button";

                choose.textContent =
                    "Seleccionar";

                choose.addEventListener(
                    "click",
                    () => {
                        selectCustomer(
                            customer
                        );
                    }
                );


                top.append(
                    identity,
                    choose
                );


                const metrics =
                    document.createElement(
                        "div"
                    );

                metrics.className =
                    "customer-metrics customer-card-metrics";


                const values = [
                    [
                        "Puntos",
                        customer.loyalty_points || 0,
                    ],
                    [
                        "Visitas",
                        customer.visits || 0,
                    ],
                    [
                        "Gasto",
                        money(
                            customer.total_spent || 0
                        ),
                    ],
                ];


                values.forEach(
                    ([label, value]) => {
                        const item =
                            document.createElement(
                                "div"
                            );

                        const small =
                            document.createElement(
                                "span"
                            );

                        small.textContent =
                            label;

                        const strong =
                            document.createElement(
                                "strong"
                            );

                        strong.textContent =
                            String(value);

                        item.append(
                            small,
                            strong
                        );

                        metrics.append(
                            item
                        );
                    }
                );


                const last =
                    document.createElement(
                        "div"
                    );

                last.className =
                    "customer-card-last";


                const lastLabel =
                    document.createElement(
                        "span"
                    );

                lastLabel.textContent =
                    "Última compra";


                const lastValue =
                    document.createElement(
                        "strong"
                    );

                lastValue.textContent =
                    customerDate(
                        customer.last_purchase_at
                    );


                last.append(
                    lastLabel,
                    lastValue
                );


                card.append(
                    top,
                    metrics,
                    last
                );

                container.append(
                    card
                );
            });
    }


    async function searchCustomers(
        query = ""
    ) {
        const message =
            $("#customers-message");

        if (!navigator.onLine) {
            if (message) {
                message.hidden = false;
                message.textContent =
                    "Clientes requiere conexión";
            }

            return;
        }

        if (state.customersBusy) {
            return;
        }

        state.customersBusy = true;

        if (message) {
            message.hidden = false;
            message.textContent =
                "Buscando clientes…";
        }

        try {
            const response =
                await window
                    .CofiPosAPI
                    .searchCustomers(
                        query
                    );

            state.customerResults =
                Array.isArray(response)
                    ? response
                    : [];

            renderCustomerResults();

        } catch (error) {
            state.customerResults = [];

            if (message) {
                message.hidden = false;

                message.textContent =
                    error.isHttpError
                        ? (
                            error.message ||
                            "No fue posible cargar clientes."
                        )
                        : "Clientes requiere conexión";
            }

        } finally {
            state.customersBusy =
                false;
        }
    }


    async function showCustomers() {
        const sale =
            $("#sale-view");

        const orders =
            $("#orders-view");

        const customers =
            $("#customers-view");

        if (sale) {
            sale.hidden = true;
        }

        if (orders) {
            orders.hidden = true;
        }

        if (customers) {
            customers.hidden = false;
        }

        $(".workspace")
            ?.classList.remove(
                "orders-mode"
            );

        $(".workspace")
            ?.classList.add(
                "customers-mode"
            );

        $("#nav-sale")
            ?.classList.remove(
                "is-active"
            );

        $("#nav-orders")
            ?.classList.remove(
                "is-active"
            );

        $("#nav-customers")
            ?.classList.add(
                "is-active"
            );


        const search =
            $("#customer-search");

        search?.focus();

        await searchCustomers(
            search?.value || ""
        );
    }


    async function createCustomerFromForm(
        event
    ) {
        event.preventDefault();

        const form =
            event.currentTarget;

        const error =
            $("#customer-create-error");

        if (error) {
            error.hidden = true;
        }

        if (!navigator.onLine) {
            if (error) {
                error.hidden = false;
                error.textContent =
                    "Clientes requiere conexión";
            }

            return;
        }

        const data =
            new FormData(form);

        const payload = {
            name:
                String(
                    data.get("name") || ""
                ).trim(),

            phone:
                String(
                    data.get("phone") || ""
                ).trim(),

            email:
                String(
                    data.get("email") || ""
                ).trim() || null,

            birthday:
                String(
                    data.get("birthday") || ""
                ).trim() || null,
        };


        const button =
            form.querySelector(
                'button[type="submit"]'
            );

        const originalLabel =
            button?.textContent;


        if (button) {
            button.disabled = true;
            button.textContent =
                "Guardando…";
        }


        try {
            const customer =
                await window
                    .CofiPosAPI
                    .createCustomer(
                        payload
                    );

            form.reset();

            const panel =
                $("#customer-create-panel");

            if (panel) {
                panel.hidden = true;
            }

            selectCustomer(
                customer
            );

        } catch (requestError) {
            if (error) {
                error.hidden = false;
                error.textContent =
                    requestError.message ||
                    "No fue posible guardar el cliente.";
            }

        } finally {
            if (button) {
                button.disabled = false;
                button.textContent =
                    originalLabel;
            }
        }
    }


    async function checkConnectivity() {
        const previous =
            state.cloudOnline;

        try {
            await window.CofiPosAPI.checkHealth();

            updateConnectionState(true);

            if (previous === false) {
                await syncPendingWithStatus();
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

        await loadReceiptSettingsForBranch(
            state.branchCode
        );

        await updatePendingCount();
        await loadCatalog();

        await registerServiceWorker();

        if (navigator.onLine) {
            await syncPendingWithStatus();
        }

        await checkConnectivity();

        setInterval(
            checkConnectivity,
            10000
        );

        updateClock();
        setInterval(updateClock, 30000);
    }

    function updateClock() {
        const now = new Date();
        $("#current-time").textContent =
            now.toLocaleTimeString("es-MX", {
                hour: "numeric",
                minute: "2-digit",
            });
        $("#current-date").textContent =
            now.toLocaleDateString("es-MX", {
                day: "numeric",
                month: "short",
                year: "numeric",
            });
    }


    /* =====================================================
       EVENTS
       ===================================================== */

    $("#refresh-catalog")
        .addEventListener(
            "click",
            loadCatalog
        );

    $("#product-search")
        .addEventListener("input", event => {
            state.searchQuery = event.currentTarget.value
                .trim()
                .toLocaleLowerCase("es-MX");
            renderProducts();
        });

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

                updateModifierTotal();
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

                updateModifierTotal();
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

                clearSelectedCustomer();
            }
        );

    $("#nav-customers")
        ?.addEventListener(
            "click",
            showCustomers
        );


    $("#open-customers-from-sale")
        ?.addEventListener(
            "click",
            showCustomers
        );


    $("#remove-selected-customer")
        ?.addEventListener(
            "click",
            clearSelectedCustomer
        );


    $("#customer-search-form")
        ?.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                searchCustomers(
                    $("#customer-search")
                        ?.value || ""
                );
            }
        );


    $("#new-customer-button")
        ?.addEventListener(
            "click",
            () => {
                const panel =
                    $("#customer-create-panel");

                if (panel) {
                    panel.hidden = false;
                }

                $("#new-customer-name")
                    ?.focus();
            }
        );


    $("#customer-create-close")
        ?.addEventListener(
            "click",
            () => {
                const panel =
                    $("#customer-create-panel");

                if (panel) {
                    panel.hidden = true;
                }
            }
        );


    $("#customer-create-form")
        ?.addEventListener(
            "submit",
            createCustomerFromForm
        );


    renderSelectedCustomer();


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

            await syncPendingWithStatus();

            await loadCatalog();
        }
    );

    document.addEventListener("keydown", event => {
        if (
            (event.ctrlKey || event.metaKey) &&
            event.key.toLowerCase() === "k"
        ) {
            event.preventDefault();
            $("#product-search").focus();
        }

        if (event.key === "Escape") {
            [
                "#modifier-modal",
                "#payment-modal",
            ].forEach(selector => {
                $(selector).hidden = true;
            });
        }
    });

    boot().catch(error => {
        console.error(error);

        $("#catalog-message").textContent =
            error.message;
    });

})();
