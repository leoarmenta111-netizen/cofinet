window.CofiRetailApp = (() => {
    const MODULE_CODE = "PAPELERIA";

    const state = {
        catalog: [],
        cart: null,
        heldSales: [],
        query: "",
        pendingItem: null,
        paymentMethod: null,
        busy: false,
        initialized: false,
    };


    function money(value) {
        const amount =
            Number(value || 0);

        return new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN",
            }
        ).format(amount);
    }


    function element(id) {
        return document.getElementById(id);
    }


    function activePresentations(item) {
        return (
            window.CofiRetailCatalog
                .activePresentations(item)
        );
    }


    function itemById(itemId) {
        return state.catalog.find(
            item =>
                Number(item.id)
                === Number(itemId)
        ) || null;
    }


    function presentationById(
        item,
        presentationId
    ) {
        if (
            !item
            || presentationId === null
            || presentationId === undefined
        ) {
            return null;
        }

        return activePresentations(item)
            .find(
                presentation =>
                    Number(
                        presentation.id
                    )
                    === Number(
                        presentationId
                    )
            ) || null;
    }


    function estimatedDisplayPrice(item) {
        if (!item) {
            return null;
        }

        if (
            String(item.item_type)
                .toUpperCase()
            === "SERVICE"
        ) {
            const tiers =
                Array.isArray(
                    item.service_price_tiers
                )
                    ? item
                        .service_price_tiers
                        .slice()
                    : [];

            tiers.sort(
                (a, b) =>
                    Number(
                        a.min_quantity
                    )
                    - Number(
                        b.min_quantity
                    )
            );

            if (!tiers.length) {
                return null;
            }

            return Number(
                tiers[0].unit_price
            );
        }

        const presentations =
            activePresentations(item);

        if (!presentations.length) {
            return null;
        }

        const prices =
            presentations
                .map(
                    presentation =>
                        Number(
                            presentation
                                .sale_price
                        )
                )
                .filter(
                    value =>
                        Number.isFinite(
                            value
                        )
                );

        if (!prices.length) {
            return null;
        }

        return Math.min(...prices);
    }


    function priceLabel(item) {
        const price =
            estimatedDisplayPrice(item);

        if (price === null) {
            return "Precio no disponible";
        }

        const presentations =
            activePresentations(item);

        const prefix =
            (
                String(item.item_type)
                    .toUpperCase()
                === "SERVICE"
                || presentations.length > 1
            )
                ? "Desde "
                : "";

        return (
            prefix
            + money(price)
        );
    }


    function repriceCart() {
        if (
            !state.cart
            || !Array.isArray(
                state.cart.lines
            )
        ) {
            return;
        }

        for (
            const line
            of state.cart.lines
        ) {
            const item =
                itemById(
                    line.item_id
                );

            if (!item) {
                continue;
            }

            const presentation =
                presentationById(
                    item,
                    line.presentation_id
                );

            const estimated =
                window.CofiRetailCatalog
                    .estimateUnitPrice(
                        item,
                        presentation,
                        Number(
                            line.quantity
                        )
                    );

            if (
                estimated !== null
                && Number.isFinite(
                    Number(estimated)
                )
            ) {
                line.unit_price =
                    Number(estimated);
            }
        }
    }


    function renderCatalog() {
        const grid =
            element(
                "retail-product-grid"
            );

        if (!grid) {
            return;
        }

        grid.replaceChildren();

        const items =
            window.CofiRetailCatalog
                .search(
                    state.catalog,
                    state.query
                );

        if (!items.length) {
            const empty =
                document.createElement(
                    "p"
                );

            empty.className =
                "retail-empty-state";

            empty.textContent =
                state.query
                    ? "No encontramos productos o servicios."
                    : "No hay productos disponibles.";

            grid.appendChild(empty);
            return;
        }

        for (const item of items) {
            const card =
                document.createElement(
                    "button"
                );

            card.type = "button";
            card.className =
                "retail-product-card";

            card.dataset.itemId =
                String(item.id);

            const category =
                document.createElement(
                    "span"
                );

            category.className =
                "retail-product-category";

            category.textContent =
                item.category
                || (
                    String(
                        item.item_type
                    ).toUpperCase()
                    === "SERVICE"
                        ? "Servicio"
                        : "Producto"
                );

            const name =
                document.createElement(
                    "strong"
                );

            name.className =
                "retail-product-name";

            name.textContent =
                item.name;

            const sku =
                document.createElement(
                    "span"
                );

            sku.className =
                "retail-product-sku";

            sku.textContent =
                item.sku
                    ? `SKU ${item.sku}`
                    : (
                        String(
                            item.item_type
                        ).toUpperCase()
                        === "SERVICE"
                            ? "Servicio"
                            : "Sin SKU"
                    );

            const price =
                document.createElement(
                    "span"
                );

            price.className =
                "retail-product-price";

            price.textContent =
                priceLabel(item);

            card.append(
                category,
                name,
                sku,
                price
            );

            card.addEventListener(
                "click",
                () => {
                    chooseItem(item);
                }
            );

            grid.appendChild(card);
        }
    }


    function renderCart() {
        const container =
            element(
                "retail-cart-lines"
            );

        const totalElement =
            element(
                "retail-cart-total"
            );

        if (
            !container
            || !totalElement
        ) {
            return;
        }

        repriceCart();

        container.replaceChildren();

        const lines =
            state.cart?.lines || [];

        if (!lines.length) {
            const empty =
                document.createElement(
                    "p"
                );

            empty.className =
                "retail-empty-state";

            empty.textContent =
                "La venta está vacía.";

            container.appendChild(empty);

            totalElement.textContent =
                money(0);

            return;
        }

        for (const line of lines) {
            const item =
                itemById(
                    line.item_id
                );

            const presentation =
                presentationById(
                    item,
                    line.presentation_id
                );

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "retail-cart-line";

            const info =
                document.createElement(
                    "div"
                );

            info.className =
                "retail-cart-line-info";

            const name =
                document.createElement(
                    "strong"
                );

            name.textContent =
                line.name
                || item?.name
                || "Artículo";

            const presentationName =
                document.createElement(
                    "span"
                );

            presentationName.className =
                "retail-cart-presentation";

            presentationName.textContent =
                line.presentation_name
                || presentation?.name
                || (
                    String(
                        item?.item_type
                    ).toUpperCase()
                    === "SERVICE"
                        ? "Servicio"
                        : ""
                );

            const unitPrice =
                document.createElement(
                    "span"
                );

            unitPrice.className =
                "retail-cart-unit-price";

            unitPrice.textContent =
                `${money(
                    line.unit_price
                )} c/u`;

            info.append(
                name,
                presentationName,
                unitPrice
            );

            const controls =
                document.createElement(
                    "div"
                );

            controls.className =
                "retail-cart-controls";

            const decrease =
                document.createElement(
                    "button"
                );

            decrease.type = "button";
            decrease.textContent = "−";
            decrease.setAttribute(
                "aria-label",
                `Disminuir ${name.textContent}`
            );

            decrease.addEventListener(
                "click",
                () => {
                    changeQuantity(
                        line,
                        Number(
                            line.quantity
                        ) - 1
                    );
                }
            );

            const quantity =
                document.createElement(
                    "span"
                );

            quantity.className =
                "retail-cart-quantity";

            quantity.textContent =
                String(line.quantity);

            const increase =
                document.createElement(
                    "button"
                );

            increase.type = "button";
            increase.textContent = "+";
            increase.setAttribute(
                "aria-label",
                `Aumentar ${name.textContent}`
            );

            increase.addEventListener(
                "click",
                () => {
                    changeQuantity(
                        line,
                        Number(
                            line.quantity
                        ) + 1
                    );
                }
            );

            const remove =
                document.createElement(
                    "button"
                );

            remove.type = "button";
            remove.className =
                "retail-cart-remove";

            remove.textContent =
                "Eliminar";

            remove.addEventListener(
                "click",
                () => {
                    window.CofiRetailCart
                        .remove(
                            state.cart,
                            line.id
                        );

                    renderCart();
                }
            );

            controls.append(
                decrease,
                quantity,
                increase,
                remove
            );

            const subtotal =
                document.createElement(
                    "strong"
                );

            subtotal.className =
                "retail-cart-line-total";

            subtotal.textContent =
                money(
                    Number(
                        line.quantity
                    )
                    * Number(
                        line.unit_price
                    )
                );

            row.append(
                info,
                controls,
                subtotal
            );

            container.appendChild(row);
        }

        totalElement.textContent =
            money(
                window.CofiRetailCart
                    .total(
                        state.cart
                    )
            );
    }


    function changeQuantity(
        line,
        quantity
    ) {
        if (quantity <= 0) {
            window.CofiRetailCart
                .remove(
                    state.cart,
                    line.id
                );
        } else {
            window.CofiRetailCart
                .setQuantity(
                    state.cart,
                    line.id,
                    quantity
                );
        }

        renderCart();
    }


    function addToCart(
        item,
        presentation
    ) {
        const estimated =
            window.CofiRetailCatalog
                .estimateUnitPrice(
                    item,
                    presentation,
                    1
                );

        if (
            estimated === null
            || !Number.isFinite(
                Number(estimated)
            )
        ) {
            return;
        }

        window.CofiRetailCart.add(
            state.cart,
            {
                item_id:
                    item.id,

                presentation_id:
                    presentation
                        ? presentation.id
                        : null,

                quantity: 1,

                discount_amount: 0,

                unit_price:
                    Number(estimated),

                name:
                    item.name,

                presentation_name:
                    presentation
                        ? presentation.name
                        : "Servicio",
            }
        );

        repriceCart();
        renderCart();
    }


    function closePresentationModal() {
        const modal =
            element(
                "retail-presentation-modal"
            );

        state.pendingItem = null;

        if (
            modal
            && typeof modal.close
            === "function"
            && modal.open
        ) {
            modal.close();
        }
    }


    function openPresentationModal(
        item,
        presentations
    ) {
        const modal =
            element(
                "retail-presentation-modal"
            );

        const title =
            element(
                "retail-presentation-title"
            );

        const options =
            element(
                "retail-presentation-options"
            );

        if (
            !modal
            || !title
            || !options
        ) {
            return;
        }

        state.pendingItem = item;

        title.textContent =
            `Presentación — ${item.name}`;

        options.replaceChildren();

        for (
            const presentation
            of presentations
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";
            button.className =
                "retail-presentation-option";

            const name =
                document.createElement(
                    "strong"
                );

            name.textContent =
                presentation.name;

            const price =
                document.createElement(
                    "span"
                );

            price.textContent =
                money(
                    presentation
                        .sale_price
                );

            const barcode =
                document.createElement(
                    "small"
                );

            barcode.textContent =
                presentation.barcode
                    ? `Código: ${presentation.barcode}`
                    : "Sin código de barras";

            button.append(
                name,
                price,
                barcode
            );

            button.addEventListener(
                "click",
                () => {
                    addToCart(
                        item,
                        presentation
                    );

                    closePresentationModal();
                }
            );

            options.appendChild(button);
        }

        if (
            typeof modal.showModal
            === "function"
        ) {
            modal.showModal();
        } else {
            modal.setAttribute(
                "open",
                ""
            );
        }
    }


    function chooseItem(item) {
        const decision =
            window.CofiRetailCatalog
                .selectionFor(item);

        if (
            decision.action
            === "ADD"
        ) {
            addToCart(
                item,
                decision.presentation
            );

            return;
        }

        if (
            decision.action
            === "CHOOSE_PRESENTATION"
        ) {
            openPresentationModal(
                item,
                decision.presentations
            );
        }
    }


    function handleSearchInput(
        event
    ) {
        state.query =
            event.target.value;

        renderCatalog();
    }


    function handleSearchKeydown(
        event
    ) {
        if (event.key !== "Enter") {
            return;
        }

        const raw =
            event.target.value;

        const barcodeMatch =
            window.CofiRetailCatalog
                .findBarcode(
                    state.catalog,
                    raw
                );

        if (!barcodeMatch) {
            state.query = raw;
            renderCatalog();
            return;
        }

        event.preventDefault();

        addToCart(
            barcodeMatch.item,
            barcodeMatch.presentation
        );

        event.target.value = "";
        state.query = "";

        renderCatalog();

        event.target.focus();
    }


    function bindPresentationModal() {
        const modal =
            element(
                "retail-presentation-modal"
            );

        const close =
            element(
                "retail-presentation-close"
            );

        if (close) {
            close.addEventListener(
                "click",
                closePresentationModal
            );
        }

        if (modal) {
            modal.addEventListener(
                "cancel",
                event => {
                    event.preventDefault();
                    closePresentationModal();
                }
            );
        }
    }


    function bindSearch() {
        const search =
            element(
                "retail-search"
            );

        if (!search) {
            return;
        }

        search.addEventListener(
            "input",
            handleSearchInput
        );

        search.addEventListener(
            "keydown",
            handleSearchKeydown
        );
    }


    async function loadCatalog() {
        const grid =
            element(
                "retail-product-grid"
            );

        if (grid) {
            grid.textContent =
                "Cargando catálogo…";
        }

        try {
            const response =
                await window
                    .CofiRetailAPI
                    .loadCatalog();

            state.catalog =
                Array.isArray(response)
                    ? response
                    : [];

            renderCatalog();
        } catch (error) {
            console.error(
                "Retail catalog load failed",
                error
            );

            state.catalog = [];

            if (grid) {
                grid.textContent =
                    "No fue posible cargar el catálogo.";
            }
        }
    }


    async function init() {
        if (state.initialized) {
            return;
        }

        state.initialized = true;

        const root =
            element(
                "retail-pos"
            );

        if (root) {
            root.dataset.module =
                MODULE_CODE;
        }

        state.cart =
            window.CofiRetailCart
                .create();

        bindSearch();
        bindPresentationModal();

        renderCart();

        await loadCatalog();

        const search =
            element(
                "retail-search"
            );

        if (search) {
            search.focus();
        }
    }


    if (
        document.readyState
        === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }


    return {
        moduleCode:
            MODULE_CODE,

        state,

        init,

        renderCatalog,

        renderCart,

        chooseItem,
    };
})();
