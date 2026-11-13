window.CofiRetailApp = (() => {
    const MODULE_CODE = "PAPELERIA";

    const state = {
        catalog: [],
        cart: null,
        heldSales: [],
        query: "",
        pendingItem: null,
        paymentMethod: null,
        activeHeldSaleUuid: null,
        lastServerSale: null,
        lastReceipt: null,
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


    function uuid() {
        if (
            !window.CofiUUID
            || typeof (
                window.CofiUUID.v4
            ) !== "function"
        ) {
            throw new Error(
                "UUID generator is unavailable"
            );
        }

        return window.CofiUUID.v4();
    }


    function setSaleMessage(
        message,
        isError = false
    ) {
        const target =
            element(
                "retail-sale-message"
            );

        if (!target) {
            return;
        }

        target.textContent =
            message || "";

        target.dataset.state =
            isError
                ? "error"
                : "info";
    }


    function saleLinesToCart(
        sale
    ) {
        const cart =
            window.CofiRetailCart
                .create();

        const lines =
            Array.isArray(
                sale?.lines
            )
                ? sale.lines
                : [];

        for (
            const line
            of lines
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

            const quantity =
                Number(
                    line.quantity
                );

            let unitPrice =
                Number(
                    line.unit_price
                    ?? line
                        .unit_price_snapshot
                );

            if (
                !Number.isFinite(
                    unitPrice
                )
            ) {
                unitPrice =
                    Number(
                        window
                            .CofiRetailCatalog
                            .estimateUnitPrice(
                                item,
                                presentation,
                                quantity
                            )
                    );
            }

            if (
                !Number.isFinite(
                    unitPrice
                )
            ) {
                unitPrice = 0;
            }

            window.CofiRetailCart.add(
                cart,
                {
                    item_id:
                        item.id,

                    presentation_id:
                        presentation
                            ? presentation.id
                            : null,

                    quantity:
                        quantity > 0
                            ? quantity
                            : 1,

                    discount_amount:
                        Number(
                            line
                                .discount_amount
                            || 0
                        ),

                    unit_price:
                        unitPrice,

                    name:
                        item.name,

                    presentation_name:
                        presentation
                            ? presentation
                                .name
                            : "Servicio",
                }
            );
        }

        return cart;
    }


    function renderHeldSales() {
        const container =
            element(
                "retail-held-sales"
            );

        if (!container) {
            return;
        }

        container.replaceChildren();

        if (
            !state.heldSales.length
        ) {
            const empty =
                document.createElement(
                    "p"
                );

            empty.className =
                "retail-empty-state";

            empty.textContent =
                "No hay ventas en espera.";

            container.appendChild(
                empty
            );

            return;
        }

        for (
            const sale
            of state.heldSales
        ) {
            const button =
                document.createElement(
                    "button"
                );

            button.type =
                "button";

            button.className =
                "retail-held-sale";

            const label =
                document.createElement(
                    "strong"
                );

            label.textContent =
                sale.label
                || "Venta en espera";

            const total =
                document.createElement(
                    "span"
                );

            total.textContent =
                money(
                    sale.total
                    || sale.subtotal
                    || 0
                );

            const meta =
                document.createElement(
                    "small"
                );

            meta.textContent =
                String(
                    sale.sale_uuid
                    || ""
                );

            button.append(
                label,
                total,
                meta
            );

            button.addEventListener(
                "click",
                () => {
                    state.cart =
                        saleLinesToCart(
                            sale
                        );

                    state
                        .activeHeldSaleUuid =
                            sale.sale_uuid;

                    renderCart();

                    setSaleMessage(
                        `Venta recuperada: ${
                            sale.label
                            || sale.sale_uuid
                        }`
                    );
                }
            );

            container.appendChild(
                button
            );
        }
    }


    async function loadHeldSales() {
        try {
            const response =
                await window
                    .CofiRetailAPI
                    .listHeldSales();

            state.heldSales =
                Array.isArray(response)
                    ? response
                    : [];

            renderHeldSales();

        } catch (error) {
            console.error(
                "Held sales load failed",
                error
            );

            state.heldSales = [];

            renderHeldSales();

            setSaleMessage(
                "No fue posible cargar "
                + "ventas en espera.",
                true
            );
        }
    }


    async function holdCurrentSale() {
        if (
            !state.cart
            || !state.cart.lines
            || state.cart.lines.length
            === 0
        ) {
            setSaleMessage(
                "Agrega artículos antes "
                + "de guardar la venta.",
                true
            );

            return;
        }

        const defaultLabel =
            "Venta "
            + new Date()
                .toLocaleTimeString(
                    "es-MX",
                    {
                        hour:
                            "2-digit",
                        minute:
                            "2-digit",
                    }
                );

        const requested =
            window.prompt(
                "Nombre para la venta "
                + "en espera:",
                defaultLabel
            );

        if (requested === null) {
            return;
        }

        const payload =
            window
                .CofiRetailSales
                .buildHeldPayload(
                    state.cart,
                    requested
                );

        try {
            let saved;

            if (
                state
                    .activeHeldSaleUuid
            ) {
                saved =
                    await window
                        .CofiRetailAPI
                        .updateHeldSale(
                            state
                                .activeHeldSaleUuid,
                            payload
                        );
            } else {
                saved =
                    await window
                        .CofiRetailAPI
                        .holdSale(
                            payload
                        );
            }

            const savedUuid =
                saved?.sale_uuid
                || state
                    .activeHeldSaleUuid;

            state.cart =
                window
                    .CofiRetailCart
                    .create();

            state
                .activeHeldSaleUuid =
                    null;

            renderCart();

            await loadHeldSales();

            setSaleMessage(
                "Venta guardada"
                + (
                    savedUuid
                        ? `: ${savedUuid}`
                        : "."
                )
            );

        } catch (error) {
            console.error(
                "Hold sale failed",
                error
            );

            setSaleMessage(
                error.message
                || "No fue posible "
                + "guardar la venta.",
                true
            );
        }
    }


    function closePaymentModal() {
        const modal =
            element(
                "retail-payment-modal"
            );

        state.paymentMethod =
            null;

        if (
            modal
            && typeof modal.close
            === "function"
            && modal.open
        ) {
            modal.close();
        }
    }


    function openPaymentModal(
        method
    ) {
        if (
            !state.cart
            || !state.cart.lines
            || state.cart.lines.length
            === 0
        ) {
            setSaleMessage(
                "Agrega artículos antes "
                + "de cobrar.",
                true
            );

            return;
        }

        const normalized =
            String(method)
                .toUpperCase();

        state.paymentMethod =
            normalized;

        const modal =
            element(
                "retail-payment-modal"
            );

        const title =
            element(
                "retail-payment-title"
            );

        const estimate =
            element(
                "retail-payment-estimate"
            );

        const cashField =
            element(
                "retail-cash-field"
            );

        const cardField =
            element(
                "retail-card-field"
            );

        const cashInput =
            element(
                "retail-amount-tendered"
            );

        const cardInput =
            element(
                "retail-card-reference"
            );

        const error =
            element(
                "retail-payment-error"
            );

        if (
            !modal
            || !title
        ) {
            return;
        }

        title.textContent =
            normalized === "CASH"
                ? "Cobro en efectivo"
                : "Cobro con tarjeta";

        if (estimate) {
            estimate.textContent =
                money(
                    window
                        .CofiRetailCart
                        .total(
                            state.cart
                        )
                );
        }

        if (cashField) {
            cashField.hidden =
                normalized !== "CASH";
        }

        if (cardField) {
            cardField.hidden =
                normalized !== "CARD";
        }

        if (cashInput) {
            cashInput.value =
                normalized === "CASH"
                    ? String(
                        window
                            .CofiRetailCart
                            .total(
                                state.cart
                            )
                    )
                    : "";
        }

        if (cardInput) {
            cardInput.value = "";
        }

        if (error) {
            error.hidden = true;
            error.textContent = "";
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

        if (
            normalized === "CASH"
            && cashInput
        ) {
            cashInput.focus();
        }

        if (
            normalized === "CARD"
            && cardInput
        ) {
            cardInput.focus();
        }
    }


    function renderReceipt(
        sale,
        receipt
    ) {
        const modal =
            element(
                "retail-receipt-modal"
            );

        const body =
            element(
                "retail-receipt-body"
            );

        if (
            !modal
            || !body
        ) {
            return;
        }

        body.replaceChildren();

        const total =
            window
                .CofiRetailSales
                .serverTotal(
                    sale
                );

        const payment =
            window
                .CofiRetailSales
                .paymentSummary(
                    sale
                );

        const totalRow =
            document.createElement(
                "div"
            );

        totalRow.className =
            "retail-receipt-total";

        const totalLabel =
            document.createElement(
                "span"
            );

        totalLabel.textContent =
            "Total";

        const totalValue =
            document.createElement(
                "strong"
            );

        totalValue.textContent =
            money(total);

        totalRow.append(
            totalLabel,
            totalValue
        );

        const paymentBlock =
            document.createElement(
                "div"
            );

        paymentBlock.className =
            "retail-receipt-payment";

        const method =
            document.createElement(
                "strong"
            );

        method.textContent =
            payment.method === "CASH"
                ? "Efectivo"
                : "Tarjeta";

        paymentBlock.appendChild(
            method
        );

        if (
            payment.method
            === "CASH"
        ) {
            const received =
                document.createElement(
                    "span"
                );

            received.textContent =
                "Recibido: "
                + money(
                    payment
                        .amountTendered
                );

            const change =
                document.createElement(
                    "span"
                );

            change.textContent =
                "Cambio: "
                + money(
                    payment.changeDue
                );

            paymentBlock.append(
                received,
                change
            );
        }

        if (
            payment.method
            === "CARD"
        ) {
            const reference =
                document.createElement(
                    "span"
                );

            reference.textContent =
                "Referencia: "
                + (
                    payment
                        .externalReference
                    || "—"
                );

            paymentBlock.appendChild(
                reference
            );
        }

        const receiptCard =
            document.createElement(
                "section"
            );

        receiptCard.className =
            "retail-receipt-card";


        const receiptHeader =
            document.createElement(
                "div"
            );

        receiptHeader.className =
            "retail-receipt-meta";


        const folioBlock =
            document.createElement(
                "div"
            );

        const folioLabel =
            document.createElement(
                "small"
            );

        folioLabel.textContent =
            "Folio";

        const folioValue =
            document.createElement(
                "strong"
            );

        folioValue.textContent =
            String(
                receipt?.folio
                ?? sale?.folio
                ?? "—"
            );

        folioBlock.append(
            folioLabel,
            folioValue
        );


        const cashierBlock =
            document.createElement(
                "div"
            );

        const cashierLabel =
            document.createElement(
                "small"
            );

        cashierLabel.textContent =
            "Cajero";

        const cashierValue =
            document.createElement(
                "strong"
            );

        cashierValue.textContent =
            receipt?.cashier
                ?.display_name
            || "—";

        cashierBlock.append(
            cashierLabel,
            cashierValue
        );


        receiptHeader.append(
            folioBlock,
            cashierBlock
        );


        const linesContainer =
            document.createElement(
                "div"
            );

        linesContainer.className =
            "retail-receipt-lines";


        const receiptLines =
            Array.isArray(
                receipt?.lines
            )
                ? receipt.lines
                : [];


        receiptLines.forEach(
            line => {
                const row =
                    document.createElement(
                        "div"
                    );

                row.className =
                    "retail-receipt-line";


                const info =
                    document.createElement(
                        "div"
                    );

                const name =
                    document.createElement(
                        "strong"
                    );

                name.textContent =
                    line?.name
                    || "Producto";


                const presentation =
                    document.createElement(
                        "span"
                    );

                presentation.textContent =
                    [
                        line
                            ?.presentation_name,
                        `Cant. ${
                            Number(
                                line?.quantity
                                || 0
                            )
                        }`,
                        `${
                            money(
                                line
                                    ?.unit_price
                                || 0
                            )
                        } c/u`,
                    ]
                        .filter(Boolean)
                        .join(" · ");


                info.append(
                    name,
                    presentation
                );


                const lineTotal =
                    document.createElement(
                        "strong"
                    );

                lineTotal.className =
                    "retail-receipt-line-total";

                lineTotal.textContent =
                    money(
                        line?.line_total
                        ?? line
                            ?.line_subtotal
                        ?? 0
                    );


                row.append(
                    info,
                    lineTotal
                );

                linesContainer
                    .appendChild(
                        row
                    );
            }
        );


        const saleInfo =
            document.createElement(
                "div"
            );

        saleInfo.className =
            "retail-receipt-sale-info";


        const date =
            document.createElement(
                "span"
            );

        if (receipt?.sold_at) {
            const parsed =
                new Date(
                    receipt.sold_at
                );

            date.textContent =
                Number.isNaN(
                    parsed.getTime()
                )
                    ? String(
                        receipt.sold_at
                    )
                    : parsed
                        .toLocaleString(
                            "es-MX"
                        );
        }


        const terminal =
            document.createElement(
                "span"
            );

        terminal.textContent =
            receipt?.terminal_id
                ? `Terminal ${
                    receipt.terminal_id
                }`
                : "";


        if (date.textContent) {
            saleInfo.appendChild(
                date
            );
        }

        if (terminal.textContent) {
            saleInfo.appendChild(
                terminal
            );
        }


        receiptCard.append(
            receiptHeader,
            linesContainer,
            totalRow,
            paymentBlock,
            saleInfo
        );


        body.append(
            receiptCard
        );

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


    async function confirmPayment() {
        if (
            state.busy
            || !state.paymentMethod
        ) {
            return;
        }

        const errorTarget =
            element(
                "retail-payment-error"
            );

        const cashInput =
            element(
                "retail-amount-tendered"
            );

        const cardInput =
            element(
                "retail-card-reference"
            );

        try {
            state.busy = true;

            if (errorTarget) {
                errorTarget.hidden =
                    true;

                errorTarget.textContent =
                    "";
            }

            const payload =
                window
                    .CofiRetailSales
                    .buildCheckoutPayload(
                        {
                            cart:
                                state.cart,

                            saleUuid:
                                uuid(),

                            paymentUuid:
                                uuid(),

                            heldSaleUuid:
                                state
                                    .activeHeldSaleUuid,

                            paymentMethod:
                                state
                                    .paymentMethod,

                            amountTendered:
                                cashInput
                                    ? cashInput
                                        .value
                                    : null,

                            externalReference:
                                cardInput
                                    ? cardInput
                                        .value
                                    : null,
                        }
                    );

            const sale =
                await window
                    .CofiRetailAPI
                    .checkout(
                        payload
                    );

            const serverTotal =
                window
                    .CofiRetailSales
                    .serverTotal(
                        sale
                    );

            const saleUuid =
                sale.sale_uuid
                || payload.sale_uuid;

            const receipt =
                await window
                    .CofiRetailAPI
                    .receipt(
                        saleUuid
                    );

            state.lastServerSale =
                sale;

            state.lastReceipt =
                receipt;

            closePaymentModal();

            renderReceipt(
                sale,
                receipt
            );

            state.cart =
                window
                    .CofiRetailCart
                    .create();

            state
                .activeHeldSaleUuid =
                    null;

            renderCart();

            await loadHeldSales();

            setSaleMessage(
                "Venta cobrada: "
                + money(
                    serverTotal
                )
            );


            /*
             * Una venta NO cierra la caja.
             * Avisamos al controlador para que
             * confirme que el mismo turno sigue OPEN.
             */
            window.dispatchEvent(
                new CustomEvent(
                    "cofi:retail-sale-completed",
                    {
                        detail: {
                            sale,
                            receipt,
                        },
                    }
                )
            );

        } catch (error) {
            console.error(
                "Retail checkout failed",
                error
            );

            if (errorTarget) {
                errorTarget.hidden =
                    false;

                errorTarget.textContent =
                    error.message
                    || "No fue posible "
                    + "completar el cobro.";
            }

        } finally {
            state.busy = false;
        }
    }


    function bindSalesWorkflow() {
        const hold =
            element(
                "retail-hold-sale"
            );

        const cash =
            element(
                "retail-pay-cash"
            );

        const card =
            element(
                "retail-pay-card"
            );

        const confirm =
            element(
                "retail-payment-confirm"
            );

        const cancel =
            element(
                "retail-payment-cancel"
            );

        const receiptClose =
            element(
                "retail-receipt-close"
            );

        const receiptModal =
            element(
                "retail-receipt-modal"
            );

        if (hold) {
            hold.addEventListener(
                "click",
                holdCurrentSale
            );
        }

        if (cash) {
            cash.addEventListener(
                "click",
                () => {
                    openPaymentModal(
                        "CASH"
                    );
                }
            );
        }

        if (card) {
            card.addEventListener(
                "click",
                () => {
                    openPaymentModal(
                        "CARD"
                    );
                }
            );
        }

        if (confirm) {
            confirm.addEventListener(
                "click",
                confirmPayment
            );
        }

        if (cancel) {
            cancel.addEventListener(
                "click",
                closePaymentModal
            );
        }

        if (receiptClose) {
            receiptClose
                .addEventListener(
                    "click",
                    () => {
                        if (
                            receiptModal
                            && typeof (
                                receiptModal
                                    .close
                            ) === "function"
                            && receiptModal
                                .open
                        ) {
                            receiptModal
                                .close();
                        }
                    }
                );
        }
    }


    async function loadOperationalData() {
        await loadCatalog();
        await loadHeldSales();
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
        bindSalesWorkflow();

        renderCart();

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

        loadOperationalData,

        renderCatalog,

        renderCart,

        chooseItem,
    };
})();

/* TASK 6D RETAIL ADJUSTMENTS */
(function () {
    "use strict";

    if (
        window.CofiRetailAdjustmentsUI
    ) {
        return;
    }


    const localState = {
        returnedByLine:
            new Map(),
        busy:
            false,
    };


    function appState() {
        return (
            window.CofiRetailApp
                ?.state
            ?? null
        );
    }


    function currentSale() {
        return (
            appState()
                ?.lastServerSale
            ?? null
        );
    }


    function uuid() {
        return (
            window.CofiUUID.v4()
        );
    }


    function el(id) {
        return (
            document
                .getElementById(id)
        );
    }


    function setMessage(message) {
        const target =
            el(
                "retail-sale-message"
            );

        if (target) {
            target.textContent =
                String(
                    message ?? ""
                );
        }
    }


    function setError(
        id,
        message
    ) {
        const target =
            el(id);

        if (target) {
            target.textContent =
                String(
                    message ?? ""
                );
        }
    }


    function showDialog(dialog) {
        if (!dialog) {
            return;
        }

        if (
            typeof dialog.showModal
            === "function"
        ) {
            dialog.showModal();
            return;
        }

        dialog.setAttribute(
            "open",
            ""
        );
    }


    function closeDialog(dialog) {
        if (!dialog) {
            return;
        }

        if (
            typeof dialog.close
            === "function"
        ) {
            dialog.close();
            return;
        }

        dialog.removeAttribute(
            "open"
        );
    }


    function saleStatusAllowsAdjustment(
        sale
    ) {
        return [
            "PAID",
            "PARTIALLY_RETURNED",
        ].includes(
            String(
                sale?.status ?? ""
            ).toUpperCase()
        );
    }


    function originalMethod(sale) {
        return (
            window
                .CofiRetailAdjustments
                .originalPaymentMethod(
                    sale
                )
        );
    }


    function lineName(line) {
        return (
            line?.item_name
            ?? line?.name
            ?? (
                "Línea "
                + String(
                    line?.id ?? ""
                )
            )
        );
    }


    function lineQuantity(line) {
        const quantity =
            Number(
                line?.quantity
            );

        return (
            Number.isFinite(quantity)
                ? quantity
                : 0
        );
    }


    function returnedQuantity(
        lineId
    ) {
        return (
            localState
                .returnedByLine
                .get(
                    Number(lineId)
                )
            ?? 0
        );
    }


    function remainingQuantity(
        line
    ) {
        return Math.max(
            0,
            lineQuantity(line)
            - returnedQuantity(
                line.id
            )
        );
    }


    function renderReturnLines() {
        const container =
            el(
                "retail-return-lines"
            );

        const sale =
            currentSale();

        if (!container) {
            return;
        }

        container.replaceChildren();

        const lines =
            Array.isArray(
                sale?.lines
            )
                ? sale.lines
                : [];

        for (const line of lines) {
            const remaining =
                remainingQuantity(
                    line
                );

            if (remaining <= 0) {
                continue;
            }

            const wrapper =
                document.createElement(
                    "label"
                );

            wrapper.className =
                "retail-return-line";

            const description =
                document.createElement(
                    "div"
                );

            const name =
                document.createElement(
                    "div"
                );

            name.className =
                "retail-return-line-name";

            name.textContent =
                lineName(line);

            const meta =
                document.createElement(
                    "div"
                );

            meta.className =
                "retail-return-line-meta";

            meta.textContent =
                `Disponible: ${remaining}`;

            description.append(
                name,
                meta
            );

            const quantity =
                document.createElement(
                    "input"
                );

            quantity.type =
                "number";

            quantity.min =
                "0";

            quantity.max =
                String(remaining);

            quantity.step =
                "any";

            quantity.value =
                "0";

            quantity.dataset.saleLineId =
                String(line.id);

            quantity.dataset.maxQuantity =
                String(remaining);

            wrapper.append(
                description,
                quantity
            );

            container.append(
                wrapper
            );
        }

        if (
            container
                .children
                .length === 0
        ) {
            const empty =
                document.createElement(
                    "p"
                );

            empty.textContent =
                "No hay líneas disponibles "
                + "para devolución.";

            container.append(empty);
        }
    }


    function selectedReturnLines() {
        const container =
            el(
                "retail-return-lines"
            );

        if (!container) {
            return [];
        }

        return Array.from(
            container.querySelectorAll(
                "input[data-sale-line-id]"
            )
        )
            .map(
                input => ({
                    sale_line_id:
                        Number(
                            input.dataset
                                .saleLineId
                        ),

                    quantity:
                        input.value,
                })
            )
            .filter(
                line =>
                    Number(
                        line.quantity
                    ) > 0
            );
    }


    function applyMethodVisibility(
        prefix
    ) {
        const method =
            el(
                `retail-${prefix}`
                + "-refund-method"
            );

        const field =
            el(
                `retail-${prefix}`
                + "-reference-field"
            );

        if (
            !method
            || !field
        ) {
            return;
        }

        field.hidden =
            method.value !== "CARD";
    }


    function initializeRefundMethod(
        prefix,
        sale
    ) {
        const method =
            el(
                `retail-${prefix}`
                + "-refund-method"
            );

        if (!method) {
            return;
        }

        method.value =
            originalMethod(sale);

        applyMethodVisibility(
            prefix
        );
    }


    function openReturn() {
        const sale =
            currentSale();

        if (
            !sale
            || !saleStatusAllowsAdjustment(
                sale
            )
        ) {
            setMessage(
                "No hay una venta pagada "
                + "disponible para devolver."
            );
            return;
        }

        renderReturnLines();

        const reason =
            el(
                "retail-return-reason"
            );

        const reference =
            el(
                "retail-return-external-reference"
            );

        const pin =
            el(
                "retail-return-manager-pin"
            );

        if (reason) {
            reason.value = "";
        }

        if (reference) {
            reference.value = "";
        }

        if (pin) {
            pin.value = "";
        }

        setError(
            "retail-return-error",
            ""
        );

        initializeRefundMethod(
            "return",
            sale
        );

        showDialog(
            el(
                "retail-return-modal"
            )
        );
    }


    async function confirmReturn() {
        if (localState.busy) {
            return;
        }

        const sale =
            currentSale();

        if (!sale?.sale_uuid) {
            setError(
                "retail-return-error",
                "Venta no disponible."
            );
            return;
        }

        try {
            localState.busy = true;

            const payload =
                window
                    .CofiRetailAdjustments
                    .buildReturnPayload({
                        returnUuid:
                            uuid(),

                        reason:
                            el(
                                "retail-return-reason"
                            )?.value,

                        refundMethod:
                            el(
                                "retail-return-refund-method"
                            )?.value,

                        externalReference:
                            el(
                                "retail-return-external-reference"
                            )?.value,

                        managerStaffId:
                            el(
                                "retail-return-manager-staff-id"
                            )?.value,

                        managerPin:
                            el(
                                "retail-return-manager-pin"
                            )?.value,

                        lines:
                            selectedReturnLines(),
                    });

            const result =
                await window
                    .CofiRetailAPI
                    .returnItems(
                        sale.sale_uuid,
                        payload
                    );

            for (
                const line
                of payload.lines
            ) {
                const current =
                    returnedQuantity(
                        line.sale_line_id
                    );

                localState
                    .returnedByLine
                    .set(
                        Number(
                            line.sale_line_id
                        ),
                        current
                        + Number(
                            line.quantity
                        )
                    );
            }

            if (
                appState()
            ) {
                appState()
                    .lastReturn =
                    result;

                appState()
                    .lastServerSale
                    .status =
                    "PARTIALLY_RETURNED";
            }

            closeDialog(
                el(
                    "retail-return-modal"
                )
            );

            setMessage(
                "Devolución registrada "
                + "correctamente."
            );
        } catch (error) {
            setError(
                "retail-return-error",
                error?.message
                ?? "No se pudo registrar "
                + "la devolución."
            );
        } finally {
            localState.busy = false;
        }
    }


    function openCancellation() {
        const sale =
            currentSale();

        if (
            !sale
            || !saleStatusAllowsAdjustment(
                sale
            )
        ) {
            setMessage(
                "No hay una venta activa "
                + "para cancelar."
            );
            return;
        }

        const reason =
            el(
                "retail-cancel-reason"
            );

        const reference =
            el(
                "retail-cancel-external-reference"
            );

        const pin =
            el(
                "retail-cancel-manager-pin"
            );

        if (reason) {
            reason.value = "";
        }

        if (reference) {
            reference.value = "";
        }

        if (pin) {
            pin.value = "";
        }

        setError(
            "retail-cancel-error",
            ""
        );

        initializeRefundMethod(
            "cancel",
            sale
        );

        showDialog(
            el(
                "retail-cancel-modal"
            )
        );
    }


    async function confirmCancellation() {
        if (localState.busy) {
            return;
        }

        const sale =
            currentSale();

        if (!sale?.sale_uuid) {
            setError(
                "retail-cancel-error",
                "Venta no disponible."
            );
            return;
        }

        try {
            localState.busy = true;

            const payload =
                window
                    .CofiRetailAdjustments
                    .buildCancellationPayload({
                        cancellationUuid:
                            uuid(),

                        reason:
                            el(
                                "retail-cancel-reason"
                            )?.value,

                        refundMethod:
                            el(
                                "retail-cancel-refund-method"
                            )?.value,

                        externalReference:
                            el(
                                "retail-cancel-external-reference"
                            )?.value,

                        managerStaffId:
                            el(
                                "retail-cancel-manager-staff-id"
                            )?.value,

                        managerPin:
                            el(
                                "retail-cancel-manager-pin"
                            )?.value,
                    });

            const result =
                await window
                    .CofiRetailAPI
                    .cancelSale(
                        sale.sale_uuid,
                        payload
                    );

            if (
                appState()
            ) {
                appState()
                    .lastCancellation =
                    result;

                appState()
                    .lastServerSale
                    .status =
                    "CANCELLED";
            }

            closeDialog(
                el(
                    "retail-cancel-modal"
                )
            );

            setMessage(
                "Venta cancelada "
                + "correctamente."
            );
        } catch (error) {
            setError(
                "retail-cancel-error",
                error?.message
                ?? "No se pudo cancelar "
                + "la venta."
            );
        } finally {
            localState.busy = false;
        }
    }


    function bind() {
        el(
            "retail-return-sale"
        )?.addEventListener(
            "click",
            openReturn
        );

        el(
            "retail-cancel-sale"
        )?.addEventListener(
            "click",
            openCancellation
        );

        el(
            "retail-return-confirm"
        )?.addEventListener(
            "click",
            confirmReturn
        );

        el(
            "retail-return-close"
        )?.addEventListener(
            "click",
            () =>
                closeDialog(
                    el(
                        "retail-return-modal"
                    )
                )
        );

        el(
            "retail-cancel-confirm"
        )?.addEventListener(
            "click",
            confirmCancellation
        );

        el(
            "retail-cancel-close"
        )?.addEventListener(
            "click",
            () =>
                closeDialog(
                    el(
                        "retail-cancel-modal"
                    )
                )
        );

        el(
            "retail-return-refund-method"
        )?.addEventListener(
            "change",
            () =>
                applyMethodVisibility(
                    "return"
                )
        );

        el(
            "retail-cancel-refund-method"
        )?.addEventListener(
            "change",
            () =>
                applyMethodVisibility(
                    "cancel"
                )
        );
    }


    window.CofiRetailAdjustmentsUI = {
        openReturn,
        confirmReturn,
        openCancellation,
        confirmCancellation,
    };


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
})();
