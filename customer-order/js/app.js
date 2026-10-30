(() => {
    const DEVICE_CODES = {
        kiosk: "KIOSK-IXTAPA-01",
        "bar-tablet":
            "BAR-TABLET-IXTAPA-01",
    };

    const state = {
        branchCode: "ixtapa",
        deviceCode: null,
        catalog: null,
        selectedCategoryId: "all",
        cart: [],
        modifierProduct: null,
        modifierQuantity: 1,
        modifierEditingLineUuid: null,
        modifierReturnToReview: false,

        selfOrderUuid: null,
        selfOrderStatus: null,
        paymentAttemptUuid: null,
        lastSelfOrder: null,
        paymentBusy: false,

        idleWarningTimer: null,
        idleResetTimer: null,
        idleCountdownTimer: null,
        idleSecondsRemaining: 15,
    };

    const $ = selector =>
        document.querySelector(selector);


    const IDLE_WARNING_MS =
        90000;

    const IDLE_GRACE_SECONDS =
        15;


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


    function uuid() {
        if (
            window.crypto &&
            typeof window.crypto.randomUUID ===
                "function"
        ) {
            return window.crypto.randomUUID();
        }

        return (
            "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
        ).replace(
            /[xy]/g,
            character => {
                const random =
                    Math.random() * 16 | 0;

                const value =
                    character === "x"
                        ? random
                        : (
                            random &
                            0x3 |
                            0x8
                        );

                return value.toString(16);
            }
        );
    }


    function resolveDeviceCode() {
        const params =
            new URLSearchParams(
                window.location.search
            );

        const requested =
            params
                .get("device")
                ?.trim()
                .toLowerCase();

        return (
            DEVICE_CODES[requested] ||
            DEVICE_CODES.kiosk
        );
    }


    function showMenu() {
        $("#start-screen").hidden =
            true;

        $("#menu-screen").hidden =
            false;
    }


    function closeOverlays() {
        $("#modifier-dialog").hidden =
            true;

        $("#review-sheet").hidden =
            true;
    }


    function resetOrder() {
        state.cart = [];
        state.modifierProduct = null;
        state.modifierQuantity = 1;
        state.modifierEditingLineUuid = null;
        state.modifierReturnToReview = false;

        state.selfOrderUuid = null;
        state.selfOrderStatus = null;
        state.paymentAttemptUuid = null;
        state.lastSelfOrder = null;
        state.paymentBusy = false;

        clearCheckoutSession();
        closeOverlays();

        $("#payment-sheet").hidden =
            true;

        $("#idle-warning").hidden =
            true;

        renderCart();

        $("#menu-screen").hidden =
            true;

        $("#start-screen").hidden =
            false;

        scheduleIdleTracking();
    }


    function categories() {
        return (
            state.catalog?.categories ||
            []
        );
    }


    async function loadCatalog() {
        const message =
            $("#catalog-message");

        message.hidden = false;
        message.textContent =
            "Cargando menú…";

        try {
            state.catalog =
                await window.CofiCustomerAPI.getCatalog(
                    state.branchCode
                );

            $("#branch-label").textContent =
                state.catalog?.branch?.name ||
                "CofiCenter Ixtapa";

            renderCategories();
            renderProducts();

            message.hidden = true;

        } catch (error) {
            message.hidden = false;
            message.textContent =
                error.message ||
                "No pudimos cargar el menú.";
        }
    }


    function categoryButton(
        id,
        label
    ) {
        const button =
            document.createElement(
                "button"
            );

        button.type = "button";
        button.className =
            "category-tab";
        button.textContent =
            label;

        if (
            String(
                state.selectedCategoryId
            ) === String(id)
        ) {
            button.classList.add(
                "is-active"
            );
        }

        button.addEventListener(
            "click",
            () => {
                state.selectedCategoryId =
                    id;

                renderCategories();
                renderProducts();
            }
        );

        return button;
    }


    function renderCategories() {
        const container =
            $("#category-tabs");

        container.replaceChildren();

        container.append(
            categoryButton(
                "all",
                "Todo"
            )
        );

        categories().forEach(
            category => {
                container.append(
                    categoryButton(
                        category.id,
                        category.name
                    )
                );
            }
        );
    }


    function visibleProducts() {
        if (
            state.selectedCategoryId ===
            "all"
        ) {
            return categories()
                .flatMap(
                    category =>
                        category.products ||
                        []
                );
        }

        return (
            categories()
                .find(
                    category =>
                        String(category.id) ===
                        String(
                            state
                                .selectedCategoryId
                        )
                )
                ?.products ||
            []
        );
    }


    function productPlaceholder() {
        const placeholder =
            document.createElement(
                "span"
            );

        placeholder.className =
            "product-placeholder";

        placeholder.textContent =
            "☕";

        return placeholder;
    }


    function productCard(product) {
        const card =
            document.createElement(
                "article"
            );

        card.className =
            "product-card";

        const visual =
            document.createElement(
                "span"
            );

        visual.className =
            "product-visual";

        if (product.image_url) {
            const image =
                document.createElement(
                    "img"
                );

            image.className =
                "product-image";

            image.src =
                product.image_url;

            image.alt =
                product.name;

            image.loading =
                "lazy";

            image.addEventListener(
                "error",
                () => {
                    image.remove();

                    visual.append(
                        productPlaceholder()
                    );
                },
                {
                    once: true,
                }
            );

            visual.append(image);

        } else {
            visual.append(
                productPlaceholder()
            );
        }

        if (
            product.modifiers &&
            product.modifiers.length
        ) {
            const badge =
                document.createElement(
                    "span"
                );

            badge.className =
                "product-badge";

            badge.textContent =
                "Personalizable";

            visual.append(
                badge
            );
        }

        const copy =
            document.createElement(
                "span"
            );

        copy.className =
            "product-copy";

        const name =
            document.createElement(
                "strong"
            );

        name.className =
            "product-name";

        name.textContent =
            product.name;

        const description =
            document.createElement(
                "span"
            );

        description.className =
            "product-description";

        description.textContent =
            product.description ||
            "Preparado al momento";

        const footer =
            document.createElement(
                "span"
            );

        footer.className =
            "product-footer";

        const price =
            document.createElement(
                "strong"
            );

        price.className =
            "product-price";

        price.textContent =
            money(product.price);

        const add =
            document.createElement(
                "button"
            );

        add.type = "button";

        add.className =
            "product-add";

        add.innerHTML = `
            <span class="product-add-icon" aria-hidden="true">+</span>
            <span class="product-add-label">Agregar</span>
        `;

        add.setAttribute(
            "aria-label",
            `Agregar ${product.name}`
        );

        add.addEventListener(
            "click",
            event => {
                event.stopPropagation();
                selectProduct(product);
            }
        );

        footer.append(
            price,
            add
        );

        copy.append(
            name,
            description,
            footer
        );

        card.append(
            visual,
            copy
        );

        return card;
    }


    function renderProducts() {
        const grid =
            $("#product-grid");

        grid.replaceChildren();

        const products =
            visibleProducts();

        if (!products.length) {
            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "catalog-empty";

            empty.textContent =
                "No hay productos disponibles en esta categoría.";

            grid.append(empty);

            return;
        }

        products.forEach(
            product => {
                grid.append(
                    productCard(product)
                );
            }
        );
    }


    function findProductById(productId) {
        const numericId = Number(productId);

        for (const category of categories()) {
            const product =
                (category.products || [])
                    .find(
                        item =>
                            Number(item.id) ===
                            numericId
                    );

            if (product) {
                return product;
            }
        }

        return null;
    }


    function productHasModifiers(product) {
        return Boolean(
            product?.modifiers?.length
        );
    }


    function setModifierProductVisual(product) {
        const image =
            $("#modifier-product-image");

        const fallback =
            $("#modifier-product-fallback");

        const description =
            $("#modifier-description");

        if (product.image_url) {
            image.hidden = false;
            image.src = product.image_url;
            image.alt = product.name;
            fallback.hidden = true;

            image.onerror = () => {
                image.hidden = true;
                fallback.hidden = false;
            };
        } else {
            image.hidden = true;
            image.removeAttribute("src");
            image.alt = "";
            fallback.hidden = false;
        }

        fallback.textContent =
            String(product.name || "C")
                .trim()
                .charAt(0)
                .toUpperCase() || "C";

        description.textContent =
            product.description ||
            "Personaliza tu producto a tu gusto.";
    }


    function selectProduct(product) {
        if (!productHasModifiers(product)) {
            const line =
                window.CofiCustomerCart.makeLine({
                    product,
                    selectedOptionIds: [],
                    quantity: 1,
                    lineUuid: uuid(),
                });

            state.cart.push(line);
            renderCart();

            return;
        }

        openProductCustomizer(product);
    }


    function modifierGroupHint(group) {
        const min = Number(
            group.min_select ??
            (group.required ? 1 : 0)
        );

        const max = Number(
            group.max_select ?? 1
        );

        if (min > 0 && max === 1) {
            return "Elige una opción";
        }

        if (min > 0) {
            return min === max
                ? `Elige ${min} opciones`
                : `Elige entre ${min} y ${max}`;
        }

        if (max === 1) {
            return "Elige una opción si quieres";
        }

        return `Puedes elegir hasta ${max}`;
    }


    function optionMonogram(option) {
        return String(option.name || "+")
            .trim()
            .charAt(0)
            .toUpperCase() || "+";
    }


    function renderModifierGroups(product) {
        const container =
            $("#modifier-groups");

        container.replaceChildren();

        (product.modifiers || [])
            .forEach((group, groupIndex) => {
                const section =
                    document.createElement(
                        "section"
                    );

                section.className =
                    "modifier-group";

                section.dataset.groupId =
                    String(group.id);

                section.dataset.minSelect =
                    String(
                        group.min_select ??
                        (group.required ? 1 : 0)
                    );

                section.dataset.maxSelect =
                    String(group.max_select ?? 1);

                const heading =
                    document.createElement(
                        "div"
                    );

                heading.className =
                    "modifier-group-heading";

                const title =
                    document.createElement(
                        "div"
                    );

                const strong =
                    document.createElement(
                        "strong"
                    );

                strong.textContent =
                    group.name;

                const hint =
                    document.createElement(
                        "small"
                    );

                hint.textContent =
                    modifierGroupHint(group);

                title.append(
                    strong,
                    hint
                );

                const status =
                    document.createElement(
                        "span"
                    );

                status.className =
                    "modifier-group-status";

                const min =
                    Number(
                        section.dataset.minSelect
                    );

                status.textContent =
                    min > 0
                        ? "Obligatorio"
                        : "Opcional";

                heading.append(
                    title,
                    status
                );

                const optionGrid =
                    document.createElement(
                        "div"
                    );

                optionGrid.className =
                    "modifier-option-grid";

                (group.options || [])
                    .forEach(option => {
                        const label =
                            document.createElement(
                                "label"
                            );

                        label.className =
                            "modifier-option";

                        const input =
                            document.createElement(
                                "input"
                            );

                        input.type =
                            Number(
                                group.max_select
                            ) === 1
                                ? "radio"
                                : "checkbox";

                        input.name =
                            `modifier-${group.id}`;

                        input.value =
                            String(option.id);

                        input.dataset.groupId =
                            String(group.id);

                        input.dataset.maxSelect =
                            String(
                                group.max_select ?? 1
                            );

                        input.addEventListener(
                            "change",
                            event => {
                                enforceMax(event);
                                refreshModifierUi();
                            }
                        );

                        const visual =
                            document.createElement(
                                "span"
                            );

                        visual.className =
                            "modifier-option-visual";

                        if (option.image_url) {
                            const optionImage =
                                document.createElement(
                                    "img"
                                );

                            optionImage.src =
                                option.image_url;

                            optionImage.alt = "";

                            visual.append(
                                optionImage
                            );
                        } else {
                            const monogram =
                                document.createElement(
                                    "span"
                                );

                            monogram.className =
                                "modifier-option-monogram";

                            monogram.textContent =
                                optionMonogram(option);

                            visual.append(
                                monogram
                            );
                        }

                        const copy =
                            document.createElement(
                                "span"
                            );

                        copy.className =
                            "modifier-option-copy";

                        const optionName =
                            document.createElement(
                                "strong"
                            );

                        optionName.textContent =
                            option.name;

                        copy.append(optionName);

                        const amount =
                            Number(
                                option.price_delta || 0
                            );

                        if (amount) {
                            const delta =
                                document.createElement(
                                    "small"
                                );

                            delta.textContent =
                                `+${money(amount)}`;

                            copy.append(delta);
                        }

                        const check =
                            document.createElement(
                                "span"
                            );

                        check.className =
                            "modifier-option-check";

                        check.textContent = "✓";

                        label.append(
                            input,
                            visual,
                            copy,
                            check
                        );

                        optionGrid.append(label);
                    });

                section.append(
                    heading,
                    optionGrid
                );

                if (groupIndex > 0) {
                    section.classList.add(
                        "modifier-group--separated"
                    );
                }

                container.append(section);
            });
    }


    function enforceMax(event) {
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

        const max =
            Number(
                input.dataset.maxSelect || 1
            );

        const checked = [
            ...document.querySelectorAll(
                `input[data-group-id="${groupId}"]:checked`
            ),
        ];

        if (checked.length > max) {
            input.checked = false;
        }
    }


    function selectedOptionIds() {
        return [
            ...$("#modifier-groups")
                .querySelectorAll(
                    "input:checked"
                ),
        ].map(
            input =>
                Number(input.value)
        );
    }


    function hydrateModifierSelection(line) {
        const selected =
            new Set(
                (line?.modifiers || [])
                    .map(
                        item =>
                            Number(item.option_id)
                    )
            );

        $("#modifier-groups")
            .querySelectorAll("input")
            .forEach(input => {
                input.checked =
                    selected.has(
                        Number(input.value)
                    );
            });
    }


    function modifierEstimate() {
        const product =
            state.modifierProduct;

        if (!product) {
            return 0;
        }

        const selected =
            new Set(
                selectedOptionIds()
            );

        const modifierTotal =
            (product.modifiers || [])
                .flatMap(
                    group =>
                        group.options || []
                )
                .filter(
                    option =>
                        selected.has(
                            Number(option.id)
                        )
                )
                .reduce(
                    (sum, option) =>
                        sum +
                        Number(
                            option.price_delta || 0
                        ),
                    0
                );

        return (
            Number(product.price) +
            modifierTotal
        ) * state.modifierQuantity;
    }


    function updateModifierCompletion() {
        const selected =
            selectedOptionIds();

        $("#modifier-groups")
            .querySelectorAll(
                ".modifier-group"
            )
            .forEach(section => {
                const min = Number(
                    section.dataset.minSelect || 0
                );

                const max = Number(
                    section.dataset.maxSelect || 1
                );

                const count =
                    section
                        .querySelectorAll(
                            "input:checked"
                        )
                        .length;

                const complete =
                    count >= min &&
                    count <= max;

                section.classList.toggle(
                    "modifier-group--incomplete",
                    !complete && min > 0
                );

                const status =
                    section.querySelector(
                        ".modifier-group-status"
                    );

                if (status) {
                    status.textContent =
                        complete
                            ? (
                                min > 0
                                    ? "Listo"
                                    : "Opcional"
                            )
                            : "Falta elegir";
                }
            });

        const validation =
            window.CofiCustomerCart.validateModifiers(
                    state.modifierProduct,
                    selected
                );

        const addButton =
            $("#add-customized-product");

        addButton.disabled =
            !validation.valid;

        addButton.setAttribute(
            "aria-disabled",
            String(!validation.valid)
        );

        $("#modifier-required-hint")
            .textContent =
                validation.valid
                    ? "Listo para agregar"
                    : "Completa las opciones obligatorias";

        return validation;
    }


    function updateModifierOrderSummary() {
        const count =
            window.CofiCustomerCart.cartCount(
                state.cart
            );

        const total =
            window.CofiCustomerCart.cartTotal(
                state.cart
            );

        $("#modifier-cart-count")
            .textContent =
                count
                    ? `${count} ${
                        count === 1
                            ? "producto"
                            : "productos"
                    }`
                    : "Orden vacía";

        $("#modifier-cart-total")
            .textContent = money(total);
    }


    function refreshModifierUi() {
        if (!state.modifierProduct) {
            return;
        }

        $("#modifier-total")
            .textContent =
                money(modifierEstimate());

        updateModifierCompletion();
        updateModifierOrderSummary();
    }


    function openProductCustomizer(
        product,
        {
            line = null,
            returnToReview = false,
        } = {}
    ) {
        state.modifierProduct = product;
        state.modifierQuantity =
            Number(line?.quantity || 1);
        state.modifierEditingLineUuid =
            line?.line_uuid || null;
        state.modifierReturnToReview =
            Boolean(returnToReview);

        $("#modifier-title")
            .textContent = product.name;

        $("#modifier-base-price")
            .textContent =
                `Desde ${money(product.price)}`;

        $("#modifier-quantity")
            .textContent =
                String(state.modifierQuantity);

        $("#modifier-notes")
            .value = line?.notes || "";

        $("#modifier-note-count")
            .textContent =
                `${$("#modifier-notes").value.length}/150`;

        $("#modifier-error").hidden =
            true;

        $("#modifier-add-label")
            .textContent =
                state.modifierEditingLineUuid
                    ? "Guardar cambios"
                    : "Agregar al pedido";

        setModifierProductVisual(product);
        renderModifierGroups(product);

        if (line) {
            hydrateModifierSelection(line);
        }

        refreshModifierUi();

        $("#review-sheet").hidden =
            true;

        $("#modifier-dialog").hidden =
            false;

        const sheet =
            $("#modifier-dialog .modifier-sheet");

        if (sheet) {
            sheet.scrollTop = 0;
        }
    }


    function closeProductCustomizer() {
        const returnToReview =
            state.modifierReturnToReview;

        $("#modifier-dialog").hidden =
            true;

        state.modifierProduct = null;
        state.modifierQuantity = 1;
        state.modifierEditingLineUuid = null;
        state.modifierReturnToReview = false;

        if (
            returnToReview &&
            state.cart.length
        ) {
            renderReview();
            $("#review-sheet").hidden =
                false;
        }
    }


    function addCustomizedProduct() {
        const product =
            state.modifierProduct;

        if (!product) {
            return;
        }

        const selected =
            selectedOptionIds();

        const validation =
            window.CofiCustomerCart.validateModifiers(
                    product,
                    selected
                );

        if (!validation.valid) {
            const error =
                $("#modifier-error");

            error.textContent =
                validation.message;

            error.hidden = false;

            const firstIncomplete =
                $("#modifier-groups")
                    .querySelector(
                        ".modifier-group--incomplete"
                    );

            firstIncomplete?.scrollIntoView({
                behavior: "smooth",
                block: "center",
            });

            return;
        }

        const notes =
            $("#modifier-notes")
                .value
                .trim();

        const editingLineUuid =
            state.modifierEditingLineUuid;

        const returnToReview =
            state.modifierReturnToReview;

        const line =
            window.CofiCustomerCart.makeLine({
                product,
                selectedOptionIds: selected,
                quantity:
                    state.modifierQuantity,
                lineUuid:
                    editingLineUuid || uuid(),
                notes,
            });

        if (editingLineUuid) {
            state.cart =
                state.cart.map(
                    item =>
                        item.line_uuid ===
                        editingLineUuid
                            ? line
                            : item
                );
        } else {
            state.cart.push(line);
        }

        state.modifierProduct = null;
        state.modifierQuantity = 1;
        state.modifierEditingLineUuid = null;
        state.modifierReturnToReview = false;

        $("#modifier-dialog").hidden =
            true;

        renderCart();

        if (returnToReview) {
            renderReview();
            $("#review-sheet").hidden =
                false;
        }
    }


    function renderCart() {
        const count =
            window.CofiCustomerCart.cartCount(
                state.cart
            );

        const total =
            window.CofiCustomerCart.cartTotal(
                state.cart
            );

        $("#customer-cart-bar").hidden =
            count === 0;

        $("#cart-count").textContent =
            `${count} ${
                count === 1
                    ? "producto"
                    : "productos"
            }`;

        $("#cart-total").textContent =
            money(total);

        if (!count) {
            $("#review-sheet").hidden =
                true;
        }
    }


    function renderReview() {
        const container =
            $("#review-items");

        container.replaceChildren();

        state.cart.forEach(
            line => {
                const row =
                    document.createElement(
                        "article"
                    );

                row.className =
                    "review-item";

                const copy =
                    document.createElement(
                        "div"
                    );

                const name =
                    document.createElement(
                        "strong"
                    );

                name.textContent =
                    `${line.quantity} × ${line.product_name}`;

                const modifiers =
                    document.createElement(
                        "small"
                    );

                modifiers.textContent =
                    (line.modifiers || [])
                        .map(
                            item =>
                                item.option_name
                        )
                        .join(", ") ||
                    "Sin modificaciones";

                copy.append(
                    name,
                    modifiers
                );

                if (line.notes) {
                    const note =
                        document.createElement(
                            "small"
                        );

                    note.className =
                        "review-item-note";

                    note.textContent =
                        `Nota: ${line.notes}`;

                    copy.append(note);
                }

                const actions =
                    document.createElement(
                        "div"
                    );

                actions.className =
                    "review-item-actions";

                const price =
                    document.createElement(
                        "strong"
                    );

                price.textContent =
                    money(line.line_total);

                const actionRow =
                    document.createElement(
                        "div"
                    );

                actionRow.className =
                    "review-item-action-row";

                const product =
                    findProductById(
                        line.product_id
                    );

                if (productHasModifiers(product)) {
                    const edit =
                        document.createElement(
                            "button"
                        );

                    edit.type = "button";
                    edit.className =
                        "review-edit";
                    edit.textContent =
                        "Editar";

                    edit.addEventListener(
                        "click",
                        () => {
                            openProductCustomizer(
                                product,
                                {
                                    line,
                                    returnToReview:
                                        true,
                                }
                            );
                        }
                    );

                    actionRow.append(edit);
                }

                const remove =
                    document.createElement(
                        "button"
                    );

                remove.type = "button";
                remove.className =
                    "review-remove";
                remove.textContent =
                    "Eliminar";

                remove.addEventListener(
                    "click",
                    () => {
                        state.cart =
                            state.cart.filter(
                                item =>
                                    item.line_uuid !==
                                    line.line_uuid
                            );

                        renderCart();
                        renderReview();
                    }
                );

                actionRow.append(remove);

                actions.append(
                    price,
                    actionRow
                );

                row.append(
                    copy,
                    actions
                );

                container.append(row);
            }
        );

        $("#review-total").textContent =
            money(
                window.CofiCustomerCart.cartTotal(
                    state.cart
                )
            );

        window.CofiCustomerCart
            .toSelfOrderItems(
                state.cart
            );
    }


    function openReview() {
        if (!state.cart.length) {
            return;
        }

        renderReview();

        $("#review-sheet").hidden =
            false;
    }



    function saveCheckoutSession() {
        if (!state.selfOrderUuid) {
            return;
        }

        const session =
            window.CofiCustomerCheckout
                .buildSession({
                    selfOrderUuid:
                        state.selfOrderUuid,
                    branchCode:
                        state.branchCode,
                    deviceCode:
                        state.deviceCode,
                    paymentAttemptUuid:
                        state.paymentAttemptUuid,
                });

        window.localStorage.setItem(
            window.CofiCustomerCheckout
                .SESSION_KEY,
            JSON.stringify(session)
        );
    }


    function readCheckoutSession() {
        const raw =
            window.localStorage.getItem(
                window.CofiCustomerCheckout
                    .SESSION_KEY
            );

        if (!raw) {
            return null;
        }

        try {
            return JSON.parse(raw);
        } catch {
            window.localStorage.removeItem(
                window.CofiCustomerCheckout
                    .SESSION_KEY
            );

            return null;
        }
    }


    function clearCheckoutSession() {
        window.localStorage.removeItem(
            window.CofiCustomerCheckout
                .SESSION_KEY
        );
    }


    function setPaymentMessage(
        message = null
    ) {
        const element =
            $("#payment-message");

        element.hidden =
            !message;

        element.textContent =
            message || "";
    }


    function hidePaymentStates() {
        [
            "#payment-ready",
            "#payment-processing",
            "#payment-declined",
            "#payment-unknown",
            "#payment-success",
        ].forEach(selector => {
            $(selector).hidden = true;
        });
    }


    function applySelfOrder(order) {
        state.lastSelfOrder =
            order;

        state.selfOrderUuid =
            order.self_order_uuid;

        state.selfOrderStatus =
            order.status;

        saveCheckoutSession();

        return order;
    }


    function renderPaymentView(order) {
        const current =
            order ||
            state.lastSelfOrder ||
            {
                status:
                    state.selfOrderStatus,
            };

        const view =
            window.CofiCustomerCheckout
                .viewForStatus(
                    current.status
                );

        hidePaymentStates();
        setPaymentMessage();

        $("#payment-sheet").hidden =
            false;

        if (view === "PAYMENT") {
            $("#payment-ready").hidden =
                false;
        }

        if (view === "PROCESSING") {
            $("#payment-processing").hidden =
                false;
        }

        if (view === "DECLINED") {
            $("#payment-declined").hidden =
                false;
        }

        if (view === "UNKNOWN") {
            $("#payment-unknown").hidden =
                false;
        }

        if (view === "SUCCESS") {
            $("#payment-success").hidden =
                false;

            $("#success-folio").textContent =
                current.folio || "—";
        }

        scheduleIdleTracking();
    }


    function simulatedOutcome() {
        const params =
            new URLSearchParams(
                window.location.search
            );

        const requested =
            String(
                params.get(
                    "payment_outcome"
                ) ||
                "APPROVED"
            ).toUpperCase();

        if (
            [
                "APPROVED",
                "DECLINED",
                "UNKNOWN",
            ].includes(requested)
        ) {
            return requested;
        }

        return "APPROVED";
    }


    async function createStagedOrder() {
        if (state.selfOrderUuid) {
            const existing =
                await window.CofiCustomerAPI
                    .getSelfOrder(
                        state.selfOrderUuid,
                        state.deviceCode
                    );

            return applySelfOrder(
                existing
            );
        }

        state.selfOrderUuid =
            uuid();

        state.selfOrderStatus =
            "AWAITING_PAYMENT";

        saveCheckoutSession();

        const payload = {
            self_order_uuid:
                state.selfOrderUuid,
            branch_code:
                state.branchCode,
            device_code:
                state.deviceCode,
            items:
                window.CofiCustomerCart
                    .toSelfOrderItems(
                        state.cart
                    ),
        };

        const order =
            await window.CofiCustomerAPI
                .createSelfOrder(
                    payload
                );

        return applySelfOrder(
            order
        );
    }


    async function beginCheckout() {
        if (
            !state.cart.length ||
            state.paymentBusy
        ) {
            return;
        }

        state.paymentBusy = true;

        const button =
            $("#continue-payment-button");

        button.disabled = true;

        try {
            const order =
                await createStagedOrder();

            $("#review-sheet").hidden =
                true;

            renderPaymentView(order);

        } catch (error) {
            setPaymentMessage(
                error.message ||
                "No pudimos preparar el pago."
            );

            $("#payment-sheet").hidden =
                false;

        } finally {
            state.paymentBusy = false;
            button.disabled = false;
        }
    }


    async function refreshSelfOrder({
        uncertainPayment = false,
    } = {}) {
        if (!state.selfOrderUuid) {
            return null;
        }

        try {
            const order =
                await window.CofiCustomerAPI
                    .getSelfOrder(
                        state.selfOrderUuid,
                        state.deviceCode
                    );

            applySelfOrder(order);

            if (
                order.status ===
                "PAYMENT_DECLINED"
            ) {
                state.paymentAttemptUuid =
                    null;

                saveCheckoutSession();
            }

            renderPaymentView(order);

            return order;

        } catch (error) {
            if (error.status === 404) {
                clearCheckoutSession();

                state.selfOrderUuid =
                    null;

                state.paymentAttemptUuid =
                    null;

                state.selfOrderStatus =
                    null;

                if (!uncertainPayment) {
                    $("#payment-sheet").hidden =
                        true;
                }

                return null;
            }

            if (uncertainPayment) {
                state.selfOrderStatus =
                    "PAYMENT_UNKNOWN";

                saveCheckoutSession();

                renderPaymentView({
                    status:
                        "PAYMENT_UNKNOWN",
                    folio: null,
                });

                return null;
            }

            throw error;
        }
    }


    async function startCardPayment() {
        if (
            state.paymentBusy ||
            !window.CofiCustomerCheckout
                .canStartPayment(
                    state.selfOrderStatus
                )
        ) {
            return;
        }

        state.paymentBusy = true;

        state.paymentAttemptUuid =
            window.CofiCustomerCheckout
                .ensureAttemptUuid(
                    state.paymentAttemptUuid,
                    uuid
                );

        saveCheckoutSession();

        state.selfOrderStatus =
            "PAYMENT_PROCESSING";

        renderPaymentView({
            status:
                "PAYMENT_PROCESSING",
        });

        try {
            const order =
                await window.CofiCustomerAPI
                    .createPaymentAttempt(
                        state.selfOrderUuid,
                        {
                            device_code:
                                state.deviceCode,
                            payment_attempt_uuid:
                                state
                                    .paymentAttemptUuid,
                            simulated_outcome:
                                simulatedOutcome(),
                        }
                    );

            applySelfOrder(order);

            if (
                order.status ===
                "PAYMENT_DECLINED"
            ) {
                state.paymentAttemptUuid =
                    null;

                saveCheckoutSession();
            }

            renderPaymentView(order);

        } catch {
            await refreshSelfOrder({
                uncertainPayment: true,
            });

        } finally {
            state.paymentBusy = false;
        }
    }


    async function cancelStagedOrder() {
        if (!state.selfOrderUuid) {
            $("#payment-sheet").hidden =
                true;

            $("#review-sheet").hidden =
                false;

            return;
        }

        if (
            !window.CofiCustomerCheckout
                .canStartPayment(
                    state.selfOrderStatus
                )
        ) {
            return;
        }

        try {
            await window.CofiCustomerAPI
                .cancelSelfOrder(
                    state.selfOrderUuid,
                    state.deviceCode
                );
        } catch {
            return;
        }

        state.selfOrderUuid = null;
        state.selfOrderStatus = null;
        state.paymentAttemptUuid = null;
        state.lastSelfOrder = null;

        clearCheckoutSession();

        $("#payment-sheet").hidden =
            true;

        $("#review-sheet").hidden =
            false;

        scheduleIdleTracking();
    }


    async function recoverCheckoutSession() {
        const session =
            readCheckoutSession();

        if (!session) {
            return;
        }

        if (
            session.branch_code !==
                state.branchCode ||
            session.device_code !==
                state.deviceCode
        ) {
            clearCheckoutSession();
            return;
        }

        state.selfOrderUuid =
            session.self_order_uuid;

        state.paymentAttemptUuid =
            session.payment_attempt_uuid ||
            null;

        const order =
            await refreshSelfOrder();

        if (!order) {
            return;
        }

        if (
            [
                "CANCELLED",
                "EXPIRED",
            ].includes(order.status)
        ) {
            clearCheckoutSession();

            state.selfOrderUuid = null;
            state.selfOrderStatus = null;
            state.paymentAttemptUuid = null;
            state.lastSelfOrder = null;

            return;
        }

        $("#start-screen").hidden =
            true;

        $("#menu-screen").hidden =
            false;

        renderPaymentView(order);
    }


    function clearIdleTimers() {
        if (state.idleWarningTimer) {
            clearTimeout(
                state.idleWarningTimer
            );
        }

        if (state.idleResetTimer) {
            clearTimeout(
                state.idleResetTimer
            );
        }

        if (state.idleCountdownTimer) {
            clearInterval(
                state.idleCountdownTimer
            );
        }

        state.idleWarningTimer =
            null;

        state.idleResetTimer =
            null;

        state.idleCountdownTimer =
            null;
    }


    function updateIdleCountdown() {
        $("#idle-countdown")
            .textContent =
                String(
                    state
                        .idleSecondsRemaining
                );
    }


    async function performIdleReset() {
        if (
            !window.CofiCustomerCheckout
                .canIdleReset(
                    state.selfOrderStatus
                )
        ) {
            $("#idle-warning").hidden =
                true;

            scheduleIdleTracking();
            return;
        }

        if (
            state.selfOrderUuid &&
            window.CofiCustomerCheckout
                .canStartPayment(
                    state.selfOrderStatus
                )
        ) {
            try {
                await window.CofiCustomerAPI
                    .cancelSelfOrder(
                        state.selfOrderUuid,
                        state.deviceCode
                    );
            } catch {
                // Local reset remains safe:
                // cancellable unpaid order can expire.
            }
        }

        resetOrder();
    }


    function showIdleWarning() {
        if (
            !window.CofiCustomerCheckout
                .canIdleReset(
                    state.selfOrderStatus
                )
        ) {
            return;
        }

        state.idleSecondsRemaining =
            IDLE_GRACE_SECONDS;

        updateIdleCountdown();

        $("#idle-warning").hidden =
            false;

        state.idleCountdownTimer =
            setInterval(
                () => {
                    state.idleSecondsRemaining -= 1;

                    updateIdleCountdown();

                    if (
                        state
                            .idleSecondsRemaining <=
                        0
                    ) {
                        clearInterval(
                            state
                                .idleCountdownTimer
                        );

                        state.idleCountdownTimer =
                            null;
                    }
                },
                1000
            );

        state.idleResetTimer =
            setTimeout(
                performIdleReset,
                IDLE_GRACE_SECONDS *
                    1000
            );
    }


    function scheduleIdleTracking() {
        clearIdleTimers();

        $("#idle-warning").hidden =
            true;

        if (
            !window.CofiCustomerCheckout
                .canIdleReset(
                    state.selfOrderStatus
                )
        ) {
            return;
        }

        state.idleWarningTimer =
            setTimeout(
                showIdleWarning,
                IDLE_WARNING_MS
            );
    }


    function registerActivity() {
        /*
         * Do not dismiss the warning on pointerdown.
         * Otherwise the button disappears before
         * its click event can fire.
         */
        if (
            !$("#idle-warning").hidden
        ) {
            return;
        }

        if (
            !window.CofiCustomerCheckout
                .canIdleReset(
                    state.selfOrderStatus
                )
        ) {
            return;
        }

        scheduleIdleTracking();
    }


    function bindEvents() {
        $("#start-order-button")
            .addEventListener(
                "click",
                showMenu
            );

        $("#restart-order-button")
            .addEventListener(
                "click",
                resetOrder
            );

        $("#close-modifier-button")
            .addEventListener(
                "click",
                closeProductCustomizer
            );

        $("#modifier-minus")
            .addEventListener(
                "click",
                () => {
                    state.modifierQuantity =
                        Math.max(
                            1,
                            state.modifierQuantity -
                            1
                        );

                    $("#modifier-quantity")
                        .textContent =
                            String(
                                state
                                    .modifierQuantity
                            );

                    refreshModifierUi();
                }
            );

        $("#modifier-plus")
            .addEventListener(
                "click",
                () => {
                    state.modifierQuantity =
                        Math.min(
                            99,
                            state.modifierQuantity +
                            1
                        );

                    $("#modifier-quantity")
                        .textContent =
                            String(
                                state
                                    .modifierQuantity
                            );

                    refreshModifierUi();
                }
            );

        $("#add-customized-product")
            .addEventListener(
                "click",
                addCustomizedProduct
            );

        $("#modifier-notes")
            .addEventListener(
                "input",
                event => {
                    $("#modifier-note-count")
                        .textContent =
                            `${event.currentTarget.value.length}/150`;
                }
            );

        $("#review-order-button")
            .addEventListener(
                "click",
                openReview
            );

        $("#close-review-button")
            .addEventListener(
                "click",
                () => {
                    $("#review-sheet").hidden =
                        true;
                }
            );

        $("#continue-payment-button")
            .addEventListener(
                "click",
                beginCheckout
            );

        $("#pay-card-button")
            .addEventListener(
                "click",
                startCardPayment
            );

        $("#retry-payment-button")
            .addEventListener(
                "click",
                startCardPayment
            );

        $("#recover-payment-button")
            .addEventListener(
                "click",
                () => {
                    refreshSelfOrder({
                        uncertainPayment:
                            true,
                    });
                }
            );

        $("#cancel-payment-button")
            .addEventListener(
                "click",
                cancelStagedOrder
            );

        $("#new-order-button")
            .addEventListener(
                "click",
                resetOrder
            );

        $("#continue-idle-button")
            .addEventListener(
                "click",
                scheduleIdleTracking
            );

        document.addEventListener(
            "pointerdown",
            registerActivity,
            {
                passive: true,
            }
        );

        document.addEventListener(
            "keydown",
            registerActivity
        );
    }


    async function init() {
        state.deviceCode =
            resolveDeviceCode();

        bindEvents();
        renderCart();

        await loadCatalog();

        try {
            await recoverCheckoutSession();
        } catch (error) {
            console.warn(
                "Checkout recovery unavailable:",
                error
            );
        }

        scheduleIdleTracking();
    }


    document.addEventListener(
        "DOMContentLoaded",
        init
    );
})();
