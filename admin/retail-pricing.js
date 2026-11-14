(() => {
    "use strict";

    const {
        adminRequest,
        confirmAdminAction,
        setButtonLoading,
        showToast,
    } = window.CofiAdmin;


    const state = {
        item: null,
        branch: null,
    };


    function el(id) {
        return document.getElementById(id);
    }


    function optional(value) {
        const normalized =
            String(value ?? "").trim();

        return normalized || null;
    }


    function close(dialog) {
        if (
            dialog
            && dialog.open
        ) {
            dialog.close();
        }
    }


    function show(dialog) {
        if (!dialog) {
            return;
        }

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


    async function refreshItem() {
        const admin =
            window.CofiRetailAdmin;

        if (
            !admin
            || typeof admin.reload
                !== "function"
        ) {
            return;
        }

        const itemId =
            state.item?.id;

        await admin.reload();

        if (
            itemId
            && typeof admin.getItem
                === "function"
        ) {
            state.item =
                admin.getItem(
                    itemId
                );
        }

        if (
            typeof admin.currentBranch
                === "function"
        ) {
            state.branch =
                admin.currentBranch();
        }
    }


    function actionButton(
        label,
        handler,
        danger = false
    ) {
        const button =
            document.createElement(
                "button"
            );

        button.type = "button";

        button.className =
            danger
                ? "button button-danger"
                : "button button-secondary";

        button.textContent = label;

        button.addEventListener(
            "click",
            handler
        );

        return button;
    }


    function renderPresentations() {
        const body =
            el(
                "retail-presentation-rows"
            );

        body.replaceChildren();

        const presentations =
            Array.isArray(
                state.item
                    ?.presentations
            )
                ? state.item
                    .presentations
                    .slice()
                : [];

        presentations.sort(
            (a, b) =>
                Number(a.id)
                - Number(b.id)
        );

        if (!presentations.length) {
            const row =
                document.createElement(
                    "tr"
                );

            row.innerHTML =
                '<td colspan="7" '
                + 'class="muted">'
                + "No hay presentaciones."
                + "</td>";

            body.append(row);
            return;
        }

        for (
            const presentation
            of presentations
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
                presentation.name;

            const barcode =
                document.createElement(
                    "td"
                );

            barcode.textContent =
                presentation.barcode
                || "—";

            const factor =
                document.createElement(
                    "td"
                );

            factor.textContent =
                String(
                    presentation
                        .conversion_factor
                );

            const price =
                document.createElement(
                    "td"
                );

            price.textContent =
                money(
                    presentation
                        .sale_price
                );

            const bulk =
                document.createElement(
                    "td"
                );

            if (
                presentation.bulk_price
                != null
                && presentation
                    .bulk_min_quantity
                != null
            ) {
                bulk.textContent =
                    money(
                        presentation
                            .bulk_price
                    )
                    + " desde "
                    + String(
                        presentation
                            .bulk_min_quantity
                    );
            } else {
                bulk.textContent = "—";
            }

            const status =
                document.createElement(
                    "td"
                );

            const labels = [];

            if (
                presentation.is_default
            ) {
                labels.push(
                    "Predeterminada"
                );
            }

            labels.push(
                presentation.is_active
                    ? "Activa"
                    : "Inactiva"
            );

            status.textContent =
                labels.join(" · ");

            const actions =
                document.createElement(
                    "td"
                );

            actions.append(
                actionButton(
                    "Editar",
                    () =>
                        openPresentationForm(
                            presentation
                        )
                )
            );

            row.append(
                name,
                barcode,
                factor,
                price,
                bulk,
                status,
                actions
            );

            body.append(row);
        }
    }


    function openProduct(
        item,
        branch
    ) {
        state.item = item;
        state.branch = branch;

        el(
            "retail-presentations-item-name"
        ).textContent =
            item.name;

        renderPresentations();

        show(
            el(
                "retail-presentations-dialog"
            )
        );
    }


    function openPresentationForm(
        presentation = null
    ) {
        close(
            el(
                "retail-presentations-dialog"
            )
        );

        const form =
            el(
                "retail-presentation-form"
            );

        form.reset();

        el(
            "retail-presentation-item-id"
        ).value =
            state.item.id;

        el(
            "retail-presentation-item-name"
        ).textContent =
            state.item.name;

        el(
            "retail-presentation-error"
        ).textContent = "";

        if (presentation) {
            el(
                "retail-presentation-title"
            ).textContent =
                "Editar presentación";

            el(
                "retail-presentation-id"
            ).value =
                presentation.id;

            el(
                "retail-presentation-name"
            ).value =
                presentation.name
                || "";

            el(
                "retail-presentation-barcode"
            ).value =
                presentation.barcode
                || "";

            el(
                "retail-presentation-factor"
            ).value =
                presentation
                    .conversion_factor;

            el(
                "retail-presentation-price"
            ).value =
                presentation.sale_price;

            el(
                "retail-presentation-bulk-price"
            ).value =
                presentation.bulk_price
                ?? "";

            el(
                "retail-presentation-bulk-min"
            ).value =
                presentation
                    .bulk_min_quantity
                ?? "";

            el(
                "retail-presentation-default"
            ).checked =
                Boolean(
                    presentation
                        .is_default
                );

            el(
                "retail-presentation-active"
            ).checked =
                Boolean(
                    presentation
                        .is_active
                );

        } else {
            el(
                "retail-presentation-title"
            ).textContent =
                "Nueva presentación";

            el(
                "retail-presentation-id"
            ).value = "";

            el(
                "retail-presentation-factor"
            ).value =
                "1.000";

            el(
                "retail-presentation-active"
            ).checked = true;

            el(
                "retail-presentation-default"
            ).checked =
                !Array.isArray(
                    state.item
                        ?.presentations
                )
                || state.item
                    .presentations
                    .length === 0;
        }

        show(
            el(
                "retail-presentation-dialog"
            )
        );

        el(
            "retail-presentation-name"
        ).focus();
    }


    function presentationPayload() {
        if (!state.branch) {
            throw new Error(
                "Sucursal no disponible."
            );
        }

        const bulkPrice =
            optional(
                el(
                    "retail-presentation-bulk-price"
                ).value
            );

        const bulkMinimum =
            optional(
                el(
                    "retail-presentation-bulk-min"
                ).value
            );

        if (
            Boolean(bulkPrice)
            !== Boolean(bulkMinimum)
        ) {
            throw new Error(
                "Precio mayoreo y cantidad mínima "
                + "deben capturarse juntos."
            );
        }

        return {
            branch_id:
                state.branch.id,

            name:
                el(
                    "retail-presentation-name"
                ).value,

            barcode:
                optional(
                    el(
                        "retail-presentation-barcode"
                    ).value
                ),

            conversion_factor:
                el(
                    "retail-presentation-factor"
                ).value,

            sale_price:
                el(
                    "retail-presentation-price"
                ).value,

            bulk_price:
                bulkPrice,

            bulk_min_quantity:
                bulkMinimum,

            is_default:
                el(
                    "retail-presentation-default"
                ).checked,

            is_active:
                el(
                    "retail-presentation-active"
                ).checked,
        };
    }


    async function savePresentation(
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
                "retail-presentation-save"
            );

        const errorNode =
            el(
                "retail-presentation-error"
            );

        errorNode.textContent = "";

        try {
            setButtonLoading(
                button,
                true,
                "Guardando…"
            );

            const payload =
                presentationPayload();

            const presentationId =
                el(
                    "retail-presentation-id"
                ).value;

            if (presentationId) {
                const {
                    branch_id,
                    ...changes
                } = payload;

                void branch_id;

                await adminRequest(
                    "/admin/retail/catalog/"
                    + "presentations/"
                    + encodeURIComponent(
                        presentationId
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
                    "/admin/retail/catalog/items/"
                    + encodeURIComponent(
                        state.item.id
                    )
                    + "/presentations",
                    {
                        method: "POST",
                        body:
                            JSON.stringify(
                                payload
                            ),
                    }
                );
            }

            close(
                el(
                    "retail-presentation-dialog"
                )
            );

            await refreshItem();

            showToast(
                presentationId
                    ? "Presentación actualizada."
                    : "Presentación creada.",
                "success"
            );

            if (state.item) {
                openProduct(
                    state.item,
                    state.branch
                );
            }

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


    function renderTiers() {
        const body =
            el(
                "retail-tier-rows"
            );

        body.replaceChildren();

        const tiers =
            Array.isArray(
                state.item
                    ?.service_price_tiers
            )
                ? state.item
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
            const row =
                document.createElement(
                    "tr"
                );

            row.innerHTML =
                '<td colspan="4" '
                + 'class="muted">'
                + "No hay tarifas configuradas."
                + "</td>";

            body.append(row);
            return;
        }

        for (const tier of tiers) {
            const row =
                document.createElement(
                    "tr"
                );

            const minimum =
                document.createElement(
                    "td"
                );

            minimum.textContent =
                String(
                    tier.min_quantity
                );

            const maximum =
                document.createElement(
                    "td"
                );

            maximum.textContent =
                tier.max_quantity == null
                    ? "Sin límite"
                    : String(
                        tier.max_quantity
                    );

            const price =
                document.createElement(
                    "td"
                );

            price.textContent =
                money(
                    tier.unit_price
                );

            const actions =
                document.createElement(
                    "td"
                );

            actions.append(
                actionButton(
                    "Editar",
                    () =>
                        openTierForm(
                            tier
                        )
                ),
                document.createTextNode(
                    " "
                ),
                actionButton(
                    "Eliminar",
                    () =>
                        deleteTier(
                            tier
                        ),
                    true
                )
            );

            row.append(
                minimum,
                maximum,
                price,
                actions
            );

            body.append(row);
        }
    }


    function openService(
        item,
        branch
    ) {
        state.item = item;
        state.branch = branch;

        el(
            "retail-tiers-item-name"
        ).textContent =
            item.name;

        renderTiers();

        show(
            el(
                "retail-tiers-dialog"
            )
        );
    }


    function openTierForm(
        tier = null
    ) {
        close(
            el(
                "retail-tiers-dialog"
            )
        );

        const form =
            el(
                "retail-tier-form"
            );

        form.reset();

        el(
            "retail-tier-item-id"
        ).value =
            state.item.id;

        el(
            "retail-tier-item-name"
        ).textContent =
            state.item.name;

        el(
            "retail-tier-error"
        ).textContent = "";

        if (tier) {
            el(
                "retail-tier-title"
            ).textContent =
                "Editar rango";

            el(
                "retail-tier-id"
            ).value =
                tier.id;

            el(
                "retail-tier-min"
            ).value =
                tier.min_quantity;

            el(
                "retail-tier-max"
            ).value =
                tier.max_quantity
                ?? "";

            el(
                "retail-tier-price"
            ).value =
                tier.unit_price;

        } else {
            el(
                "retail-tier-title"
            ).textContent =
                "Nuevo rango";

            el(
                "retail-tier-id"
            ).value = "";
        }

        show(
            el(
                "retail-tier-dialog"
            )
        );

        el(
            "retail-tier-min"
        ).focus();
    }


    function tierPayload() {
        return {
            min_quantity:
                el(
                    "retail-tier-min"
                ).value,

            max_quantity:
                optional(
                    el(
                        "retail-tier-max"
                    ).value
                ),

            unit_price:
                el(
                    "retail-tier-price"
                ).value,
        };
    }


    async function saveTier(
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
                "retail-tier-save"
            );

        const errorNode =
            el(
                "retail-tier-error"
            );

        errorNode.textContent = "";

        try {
            setButtonLoading(
                button,
                true,
                "Guardando…"
            );

            const tierId =
                el(
                    "retail-tier-id"
                ).value;

            const payload =
                tierPayload();

            if (tierId) {
                await adminRequest(
                    "/admin/retail/catalog/"
                    + "service-price-tiers/"
                    + encodeURIComponent(
                        tierId
                    ),
                    {
                        method: "PATCH",
                        body:
                            JSON.stringify(
                                payload
                            ),
                    }
                );

            } else {
                await adminRequest(
                    "/admin/retail/catalog/items/"
                    + encodeURIComponent(
                        state.item.id
                    )
                    + "/service-price-tiers",
                    {
                        method: "POST",
                        body:
                            JSON.stringify(
                                payload
                            ),
                    }
                );
            }

            close(
                el(
                    "retail-tier-dialog"
                )
            );

            await refreshItem();

            showToast(
                tierId
                    ? "Tarifa actualizada."
                    : "Tarifa creada.",
                "success"
            );

            if (state.item) {
                openService(
                    state.item,
                    state.branch
                );
            }

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


    async function deleteTier(
        tier
    ) {
        const confirmed =
            await confirmAdminAction({
                title:
                    "Eliminar tarifa",
                message:
                    "Esta tarifa dejará de "
                    + "estar disponible para "
                    + "calcular precios.",
                confirmLabel:
                    "Eliminar",
                danger:
                    true,
            });

        if (!confirmed) {
            return;
        }

        try {
            await adminRequest(
                "/admin/retail/catalog/"
                + "service-price-tiers/"
                + encodeURIComponent(
                    tier.id
                ),
                {
                    method:
                        "DELETE",
                }
            );

            await refreshItem();

            showToast(
                "Tarifa eliminada.",
                "success"
            );

            if (state.item) {
                renderTiers();
            }

        } catch (error) {
            showToast(
                error.message,
                "error"
            );
        }
    }


    function returnToPresentations() {
        close(
            el(
                "retail-presentation-dialog"
            )
        );

        if (state.item) {
            openProduct(
                state.item,
                state.branch
            );
        }
    }


    function returnToTiers() {
        close(
            el(
                "retail-tier-dialog"
            )
        );

        if (state.item) {
            openService(
                state.item,
                state.branch
            );
        }
    }


    function bind() {
        el(
            "retail-presentations-close"
        )?.addEventListener(
            "click",
            () =>
                close(
                    el(
                        "retail-presentations-dialog"
                    )
                )
        );

        el(
            "retail-presentation-new"
        )?.addEventListener(
            "click",
            () =>
                openPresentationForm()
        );

        el(
            "retail-presentation-cancel"
        )?.addEventListener(
            "click",
            returnToPresentations
        );

        el(
            "retail-presentation-form"
        )?.addEventListener(
            "submit",
            savePresentation
        );

        el(
            "retail-tiers-close"
        )?.addEventListener(
            "click",
            () =>
                close(
                    el(
                        "retail-tiers-dialog"
                    )
                )
        );

        el(
            "retail-tier-new"
        )?.addEventListener(
            "click",
            () =>
                openTierForm()
        );

        el(
            "retail-tier-cancel"
        )?.addEventListener(
            "click",
            returnToTiers
        );

        el(
            "retail-tier-form"
        )?.addEventListener(
            "submit",
            saveTier
        );
    }


    window.CofiRetailPricingUI = {
        openProduct,
        openService,
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
