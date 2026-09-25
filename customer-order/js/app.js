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

        closeOverlays();
        renderCart();

        $("#menu-screen").hidden =
            true;

        $("#start-screen").hidden =
            false;
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
                "button"
            );

        card.type = "button";
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

        price.textContent =
            money(product.price);

        const add =
            document.createElement(
                "span"
            );

        add.className =
            "product-add";

        add.textContent = "+";

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

        card.addEventListener(
            "click",
            () => selectProduct(product)
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


    function selectProduct(product) {
        if (
            !product.modifiers ||
            !product.modifiers.length
        ) {
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

        state.modifierProduct =
            product;

        state.modifierQuantity =
            1;

        $("#modifier-title")
            .textContent =
                product.name;

        $("#modifier-base-price")
            .textContent =
                `Desde ${money(
                    product.price
                )}`;

        $("#modifier-quantity")
            .textContent =
                "1";

        $("#modifier-error").hidden =
            true;

        renderModifierGroups(product);
        updateModifierPrice();

        $("#modifier-dialog").hidden =
            false;
    }


    function renderModifierGroups(
        product
    ) {
        const container =
            $("#modifier-groups");

        container.replaceChildren();

        (product.modifiers || [])
            .forEach(group => {
                const section =
                    document.createElement(
                        "section"
                    );

                section.className =
                    "modifier-group";

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

                const min =
                    Number(
                        group.min_select ??
                        (
                            group.required
                                ? 1
                                : 0
                        )
                    );

                const hint =
                    document.createElement(
                        "small"
                    );

                hint.textContent =
                    min > 0
                        ? "Elige una opción"
                        : "Opcional";

                title.append(
                    strong,
                    hint
                );

                const badge =
                    document.createElement(
                        "span"
                    );

                badge.textContent =
                    min > 0
                        ? "Obligatorio"
                        : "Opcional";

                heading.append(
                    title,
                    badge
                );

                section.append(
                    heading
                );

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
                                group.max_select ??
                                1
                            );

                        input.addEventListener(
                            "change",
                            event => {
                                enforceMax(event);
                                updateModifierPrice();
                            }
                        );

                        const optionName =
                            document.createElement(
                                "span"
                            );

                        optionName.textContent =
                            option.name;

                        const delta =
                            document.createElement(
                                "strong"
                            );

                        const amount =
                            Number(
                                option.price_delta ||
                                0
                            );

                        delta.textContent =
                            amount
                                ? `+${money(amount)}`
                                : "Incluido";

                        label.append(
                            input,
                            optionName,
                            delta
                        );

                        section.append(
                            label
                        );
                    });

                container.append(
                    section
                );
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
                input.dataset.maxSelect ||
                1
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


    function updateModifierPrice() {
        const product =
            state.modifierProduct;

        if (!product) {
            return;
        }

        const selected =
            new Set(
                selectedOptionIds()
            );

        const modifierTotal =
            (product.modifiers || [])
                .flatMap(
                    group =>
                        group.options ||
                        []
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
                            option.price_delta ||
                            0
                        ),
                    0
                );

        const total =
            (
                Number(product.price) +
                modifierTotal
            ) *
            state.modifierQuantity;

        $("#modifier-total")
            .textContent =
                money(total);
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

            error.hidden =
                false;

            return;
        }

        const line =
            window.CofiCustomerCart.makeLine({
                product,
                selectedOptionIds:
                    selected,
                quantity:
                    state.modifierQuantity,
                lineUuid:
                    uuid(),
            });

        state.cart.push(line);

        state.modifierProduct =
            null;

        $("#modifier-dialog").hidden =
            true;

        renderCart();
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

                actions.append(
                    price,
                    remove
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
                () => {
                    $("#modifier-dialog")
                        .hidden =
                            true;
                }
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

                    updateModifierPrice();
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

                    updateModifierPrice();
                }
            );

        $("#add-customized-product")
            .addEventListener(
                "click",
                addCustomizedProduct
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
    }


    async function init() {
        state.deviceCode =
            resolveDeviceCode();

        bindEvents();
        renderCart();

        await loadCatalog();
    }


    document.addEventListener(
        "DOMContentLoaded",
        init
    );
})();
