window.CofiRetailCashControl = (() => {
    "use strict";

    const state = {
        module: null,
        shift: null,
        busy: false,
        closeBusy: false,
    };


    function el(id) {
        return document.getElementById(id);
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


    function currentStaff() {
        return window
            .CofiRetailSession
            ?.current?.()
            || null;
    }


    function normalizeShift(value) {
        if (!value) {
            return null;
        }

        return {
            ...value,

            status:
                String(
                    value.status || ""
                )
                    .trim()
                    .toUpperCase(),
        };
    }


    function ensureModule() {
        if (state.module) {
            return state.module;
        }

        if (
            !window.CofiPosCashShiftModule
        ) {
            throw new Error(
                "Módulo de caja no disponible."
            );
        }

        /*
         * CofiPosCashShiftModule solo necesita
         * staffSession.current().
         *
         * Adaptamos la sesión propia de Papelería.
         */
        const staffSessionAdapter = {
            current() {
                return currentStaff();
            },
        };

        state.module =
            window
                .CofiPosCashShiftModule
                .createCashShift({
                    api:
                        window.CofiPosAPI,

                    staffSession:
                        staffSessionAdapter,

                    isOnline:
                        () =>
                            navigator.onLine
                            !== false,
                });

        return state.module;
    }


    function ensureUI() {
        if (
            !el(
                "retail-cash-status"
            )
        ) {
            const header =
                document.querySelector(
                    ".app-header"
                );

            if (header) {
                const button =
                    document.createElement(
                        "button"
                    );

                button.id =
                    "retail-cash-status";

                button.type =
                    "button";

                button.className =
                    "retail-cash-status is-loading";

                button.innerHTML = `
                    <span
                        class="retail-cash-dot"
                    ></span>

                    <span>
                        Caja
                    </span>

                    <strong>
                        Verificando...
                    </strong>
                `;

                header.appendChild(
                    button
                );

                button.addEventListener(
                    "click",
                    () => {
                        const status =
                            state.shift?.status;

                        if (
                            status === "OPEN"
                            || status === "CLOSING"
                        ) {
                            openCloseDialog();
                            return;
                        }

                        openDialog();
                    }
                );
            }
        }


        if (
            !el(
                "retail-cash-opening-modal"
            )
        ) {
            const dialog =
                document.createElement(
                    "dialog"
                );

            dialog.id =
                "retail-cash-opening-modal";

            dialog.className =
                "retail-cash-opening-modal";

            dialog.innerHTML = `
                <form
                    id="retail-cash-opening-form"
                >
                    <header>
                        <div>
                            <span
                                class="retail-modal-eyebrow"
                            >
                                Inicio de turno
                            </span>

                            <h2>
                                Apertura de caja
                            </h2>

                            <p>
                                Registra el fondo inicial
                                antes de comenzar a vender.
                            </p>
                        </div>
                    </header>

                    <label
                        for="retail-opening-amount"
                    >
                        Fondo inicial
                    </label>

                    <div
                        class="retail-money-input"
                    >
                        <span>$</span>

                        <input
                            id="retail-opening-amount"
                            type="number"
                            min="0"
                            step="0.01"
                            value="0"
                            required
                            inputmode="decimal"
                            autocomplete="off"
                        >
                    </div>

                    <div
                        class="retail-manager-box"
                    >
                        <div>
                            <strong>
                                Autorización de gerente
                            </strong>

                            <small>
                                Se requiere PIN de Manager
                                para abrir la caja.
                            </small>
                        </div>

                        <label
                            for="retail-opening-manager-id"
                        >
                            ID de gerente
                        </label>

                        <input
                            id="retail-opening-manager-id"
                            type="number"
                            min="1"
                            required
                            inputmode="numeric"
                            autocomplete="off"
                        >

                        <label
                            for="retail-opening-manager-pin"
                        >
                            PIN de gerente
                        </label>

                        <input
                            id="retail-opening-manager-pin"
                            type="password"
                            required
                            inputmode="numeric"
                            autocomplete="off"
                        >
                    </div>

                    <p
                        id="retail-cash-opening-error"
                        class="retail-cash-opening-error"
                        hidden
                    ></p>

                    <button
                        id="retail-cash-opening-submit"
                        class="retail-primary-action"
                        type="submit"
                    >
                        Abrir caja
                    </button>
                </form>
            `;

            document.body.appendChild(
                dialog
            );


            el(
                "retail-cash-opening-form"
            ).addEventListener(
                "submit",
                handleOpen
            );
        }
    }



    function ensureCloseUI() {
        if (
            el(
                "retail-cash-closing-modal"
            )
        ) {
            return;
        }

        const dialog =
            document.createElement(
                "dialog"
            );

        dialog.id =
            "retail-cash-closing-modal";

        dialog.className =
            "retail-cash-closing-modal";

        dialog.innerHTML = `
            <form
                id="retail-cash-closing-form"
                onsubmit="return false;"
            >
                <div class="retail-cash-closing-head">
                    <div>
                        <span class="retail-modal-eyebrow">
                            Fin de turno
                        </span>

                        <h2>Cerrar caja</h2>

                        <p>
                            Cuenta el efectivo físico antes
                            de finalizar el turno.
                        </p>
                    </div>

                    <button
                        id="retail-cash-closing-cancel"
                        type="button"
                        aria-label="Cerrar"
                    >
                        ×
                    </button>
                </div>

                <section
                    id="retail-cash-closing-count-step"
                    class="retail-cash-closing-step"
                >
                    <label for="retail-closing-amount">
                        Efectivo contado
                    </label>

                    <div class="retail-money-input">
                        <span>$</span>

                        <input
                            id="retail-closing-amount"
                            type="number"
                            min="0"
                            step="0.01"
                            inputmode="decimal"
                            autocomplete="off"
                            required
                        >
                    </div>

                    <button
                        id="retail-cash-closing-count-submit"
                        type="button"
                        class="retail-primary-action"
                    >
                        Revisar cierre
                    </button>
                </section>

                <section
                    id="retail-cash-closing-review-step"
                    class="retail-cash-closing-step"
                    hidden
                >
                    <div class="retail-shift-sales-summary">
                        <div class="retail-shift-sales-title">
                            <span>Corte de ventas</span>
                            <strong id="retail-closing-net-sales">—</strong>
                        </div>

                        <div class="retail-shift-sales-grid">
                            <div>
                                <span>Efectivo neto</span>
                                <strong id="retail-closing-cash-net">—</strong>
                                <small id="retail-closing-cash-detail">—</small>
                            </div>

                            <div>
                                <span>Tarjeta neta</span>
                                <strong id="retail-closing-card-net">—</strong>
                                <small id="retail-closing-card-detail">—</small>
                            </div>

                            <div>
                                <span>Venta bruta</span>
                                <strong id="retail-closing-gross-sales">—</strong>
                                <small>Antes de devoluciones</small>
                            </div>
                        </div>
                    </div>

                    <div class="retail-cash-reconciliation">
                        <div>
                            <span>Esperado</span>
                            <strong id="retail-closing-expected">—</strong>
                        </div>

                        <div>
                            <span>Contado</span>
                            <strong id="retail-closing-counted">—</strong>
                        </div>

                        <div>
                            <span>Diferencia</span>
                            <strong id="retail-closing-difference">—</strong>
                        </div>
                    </div>

                    <label
                        id="retail-closing-note-field"
                        hidden
                    >
                        Motivo de la diferencia

                        <textarea
                            id="retail-closing-note"
                            rows="3"
                            maxlength="500"
                            placeholder="Explica la diferencia encontrada"
                        ></textarea>
                    </label>

                    <div class="retail-manager-box">
                        <div>
                            <strong>
                                Autorización de gerente
                            </strong>

                            <small>
                                Se requiere PIN de Manager
                                para cerrar la caja.
                            </small>
                        </div>

                        <label for="retail-closing-manager-id">
                            ID de gerente
                        </label>

                        <input
                            id="retail-closing-manager-id"
                            type="number"
                            min="1"
                            required
                            inputmode="numeric"
                            autocomplete="off"
                        >

                        <label for="retail-closing-manager-pin">
                            PIN de gerente
                        </label>

                        <input
                            id="retail-closing-manager-pin"
                            type="password"
                            required
                            inputmode="numeric"
                            autocomplete="off"
                        >
                    </div>

                    <button
                        id="retail-cash-closing-finalize"
                        type="button"
                        class="retail-primary-action"
                    >
                        Cerrar caja
                    </button>
                </section>

                <p
                    id="retail-cash-closing-error"
                    class="retail-cash-opening-error"
                    hidden
                ></p>
            </form>
        `;

        document.body.appendChild(
            dialog
        );

        el(
            "retail-cash-closing-cancel"
        )?.addEventListener(
            "click",
            () => {
                if (
                    dialog.open
                    && typeof dialog.close
                        === "function"
                ) {
                    dialog.close();
                }
            }
        );

        el(
            "retail-cash-closing-count-submit"
        )?.addEventListener(
            "click",
            handleClosingCount
        );

        el(
            "retail-cash-closing-finalize"
        )?.addEventListener(
            "click",
            handleFinalizeClose
        );
    }


    function setClosingError(
        message = ""
    ) {
        const target =
            el(
                "retail-cash-closing-error"
            );

        if (!target) {
            return;
        }

        target.textContent =
            String(
                message || ""
            );

        target.hidden =
            !message;
    }


    function renderReconciliation(
        reconciliation
    ) {
        if (!reconciliation) {
            return;
        }

        const expected =
            Number(
                reconciliation
                    .expected_cash
            );

        const counted =
            Number(
                reconciliation
                    .counted_cash
            );

        const difference =
            Number(
                reconciliation
                    .difference
            );

        const cashSales =
            Number(
                reconciliation
                    .cash_sales
                || 0
            );

        const cardSales =
            Number(
                reconciliation
                    .card_sales
                || 0
            );

        const cashRefunds =
            Number(
                reconciliation
                    .cash_refunds
                || 0
            );

        const cardRefunds =
            Number(
                reconciliation
                    .card_refunds
                || 0
            );

        const cashNet =
            Number(
                reconciliation
                    .cash_net
                ?? (
                    cashSales
                    - cashRefunds
                )
            );

        const cardNet =
            Number(
                reconciliation
                    .card_net
                ?? (
                    cardSales
                    - cardRefunds
                )
            );

        const grossSales =
            Number(
                reconciliation
                    .gross_sales
                ?? (
                    cashSales
                    + cardSales
                )
            );

        const netSales =
            Number(
                reconciliation
                    .net_sales
                ?? (
                    cashNet
                    + cardNet
                )
            );

        el(
            "retail-closing-cash-net"
        ).textContent =
            money(cashNet);

        el(
            "retail-closing-card-net"
        ).textContent =
            money(cardNet);

        el(
            "retail-closing-gross-sales"
        ).textContent =
            money(grossSales);

        el(
            "retail-closing-net-sales"
        ).textContent =
            money(netSales);

        el(
            "retail-closing-cash-detail"
        ).textContent =
            "Ventas "
            + money(cashSales)
            + " · Dev. "
            + money(cashRefunds);

        el(
            "retail-closing-card-detail"
        ).textContent =
            "Ventas "
            + money(cardSales)
            + " · Dev. "
            + money(cardRefunds);


        el(
            "retail-closing-expected"
        ).textContent =
            money(expected);

        el(
            "retail-closing-counted"
        ).textContent =
            money(counted);

        const differenceNode =
            el(
                "retail-closing-difference"
            );

        differenceNode.textContent =
            money(difference);

        differenceNode.classList.toggle(
            "has-difference",
            difference !== 0
        );

        const noteField =
            el(
                "retail-closing-note-field"
            );

        if (noteField) {
            noteField.hidden =
                difference === 0;
        }

        el(
            "retail-cash-closing-count-step"
        ).hidden = true;

        el(
            "retail-cash-closing-review-step"
        ).hidden = false;
    }


    function openCloseDialog() {
        ensureUI();
        ensureCloseUI();

        if (
            state.closeBusy
            || !state.shift
            || ![
                "OPEN",
                "CLOSING",
            ].includes(
                state.shift.status
            )
        ) {
            return;
        }

        setClosingError("");

        const module =
            ensureModule();

        const reconciliation =
            module.reconciliation();

        const countStep =
            el(
                "retail-cash-closing-count-step"
            );

        const reviewStep =
            el(
                "retail-cash-closing-review-step"
            );

        if (reconciliation) {
            renderReconciliation(
                reconciliation
            );
        } else {
            countStep.hidden = false;
            reviewStep.hidden = true;

            el(
                "retail-closing-amount"
            ).value = "";
        }

        el(
            "retail-closing-manager-pin"
        ).value = "";

        el(
            "retail-closing-note"
        ).value = "";

        const dialog =
            el(
                "retail-cash-closing-modal"
            );

        if (
            dialog
            && typeof dialog.showModal
                === "function"
            && !dialog.open
        ) {
            dialog.showModal();
        }

        setTimeout(
            () => {
                if (reconciliation) {
                    el(
                        "retail-closing-manager-id"
                    )?.focus();
                } else {
                    el(
                        "retail-closing-amount"
                    )?.focus();
                }
            },
            0
        );
    }


    async function handleClosingCount() {
        if (state.closeBusy) {
            return;
        }

        setClosingError("");

        const amount =
            Number(
                el(
                    "retail-closing-amount"
                )?.value
            );

        if (
            !Number.isFinite(amount)
            || amount < 0
        ) {
            setClosingError(
                "Ingresa el efectivo contado."
            );
            return;
        }

        state.closeBusy = true;

        const button =
            el(
                "retail-cash-closing-count-submit"
            );

        if (button) {
            button.disabled = true;
            button.textContent =
                "Calculando...";
        }

        try {
            const module =
                ensureModule();

            const reconciliation =
                await module
                    .submitClosingCount(
                        amount
                    );

            state.shift =
                normalizeShift(
                    module.current()
                );

            renderStatus();
            syncCheckoutAvailability();

            renderReconciliation(
                reconciliation
            );

        } catch (error) {
            setClosingError(
                error?.message
                || "No fue posible registrar "
                + "el conteo de cierre."
            );

        } finally {
            state.closeBusy = false;

            if (button) {
                button.disabled = false;
                button.textContent =
                    "Revisar cierre";
            }
        }
    }


    async function handleFinalizeClose() {
        if (state.closeBusy) {
            return;
        }

        setClosingError("");

        const managerId =
            Number(
                el(
                    "retail-closing-manager-id"
                )?.value
            );

        const managerPin =
            String(
                el(
                    "retail-closing-manager-pin"
                )?.value
                || ""
            ).trim();

        const differenceNote =
            String(
                el(
                    "retail-closing-note"
                )?.value
                || ""
            ).trim();

        if (
            !Number.isInteger(managerId)
            || managerId <= 0
        ) {
            setClosingError(
                "Ingresa el ID del gerente."
            );
            return;
        }

        if (!managerPin) {
            setClosingError(
                "Ingresa el PIN del gerente."
            );
            return;
        }

        state.closeBusy = true;

        const button =
            el(
                "retail-cash-closing-finalize"
            );

        if (button) {
            button.disabled = true;
            button.textContent =
                "Cerrando caja...";
        }

        try {
            const module =
                ensureModule();

            const result =
                await module.finalizeClose(
                    {
                        staffId:
                            managerId,
                        pin:
                            managerPin,
                    },
                    differenceNote
                );

            state.shift =
                normalizeShift(
                    result
                );

            await refresh();

            renderStatus();
            syncCheckoutAvailability();

            const dialog =
                el(
                    "retail-cash-closing-modal"
                );

            if (
                dialog?.open
                && typeof dialog.close
                    === "function"
            ) {
                dialog.close();
            }

            window.dispatchEvent(
                new CustomEvent(
                    "cofi:retail-cash-closed",
                    {
                        detail:
                            result,
                    }
                )
            );

        } catch (error) {
            setClosingError(
                error?.message
                || "No fue posible cerrar la caja."
            );

        } finally {
            state.closeBusy = false;

            if (button) {
                button.disabled = false;
                button.textContent =
                    "Cerrar caja";
            }
        }
    }


    function setError(
        message = ""
    ) {
        const target =
            el(
                "retail-cash-opening-error"
            );

        if (!target) {
            return;
        }

        target.textContent =
            String(
                message || ""
            );

        target.hidden =
            !message;
    }


    function setBusy(busy) {
        state.busy =
            Boolean(busy);

        const button =
            el(
                "retail-cash-opening-submit"
            );

        if (button) {
            button.disabled =
                state.busy;

            button.textContent =
                state.busy
                    ? "Abriendo caja..."
                    : "Abrir caja";
        }
    }


    function syncCheckoutAvailability() {
        const open =
            state.shift?.status
            === "OPEN";

        [
            "retail-pay-cash",
            "retail-pay-card",
        ].forEach(id => {
            const button =
                el(id);

            if (!button) {
                return;
            }

            button.disabled =
                !open;

            if (!open) {
                button.title =
                    "Primero abre la caja";
            } else {
                button.removeAttribute(
                    "title"
                );
            }
        });
    }


    function renderStatus() {
        const button =
            el(
                "retail-cash-status"
            );

        if (!button) {
            return;
        }

        button.classList.remove(
            "is-loading",
            "is-open",
            "is-closed",
            "is-closing"
        );


        if (
            state.shift?.status
            === "OPEN"
        ) {
            button.classList.add(
                "is-open"
            );

            const initial =
                state.shift
                    .opening_amount
                ?? state.shift
                    .opening_total
                ?? null;

            button.innerHTML = `
                <span
                    class="retail-cash-dot"
                ></span>

                <span>
                    Caja abierta
                </span>

                <strong>
                    ${
                        initial != null
                            ? money(initial)
                            : "Activa"
                    }
                </strong>
            `;

            return;
        }


        if (
            state.shift?.status
            === "CLOSING"
        ) {
            button.classList.add(
                "is-closing"
            );

            button.innerHTML = `
                <span
                    class="retail-cash-dot"
                ></span>

                <span>
                    Caja
                </span>

                <strong>
                    En cierre
                </strong>
            `;

            return;
        }


        button.classList.add(
            "is-closed"
        );

        button.innerHTML = `
            <span
                class="retail-cash-dot"
            ></span>

            <span>
                Caja cerrada
            </span>

            <strong>
                Abrir
            </strong>
        `;
    }


    function openDialog() {
        ensureUI();

        const dialog =
            el(
                "retail-cash-opening-modal"
            );

        if (
            !dialog
            || state.busy
        ) {
            return;
        }

        setError("");

        el(
            "retail-opening-manager-pin"
        ).value = "";

        if (
            typeof dialog.showModal
            === "function"
            && !dialog.open
        ) {
            dialog.showModal();
        }

        setTimeout(
            () => {
                el(
                    "retail-opening-amount"
                )?.focus();
            },
            0
        );
    }


    async function refresh() {
        ensureUI();

        const session =
            currentStaff();

        if (!session) {
            state.shift =
                null;

            renderStatus();
            syncCheckoutAvailability();

            return null;
        }

        const module =
            ensureModule();

        const previousShift =
            state.shift
                ? {
                    ...state.shift,
                }
                : null;


        const shift =
            await module
                .loadCurrent();


        const normalized =
            normalizeShift(
                shift
            );


        /*
         * Una venta nunca debe cerrar la caja.
         *
         * Si ya conocíamos un turno OPEN y una
         * consulta temporal devuelve vacío,
         * conservamos el estado OPEN.
         *
         * El cierre real se hará únicamente
         * mediante el flujo explícito de
         * "Cerrar caja".
         */
        if (normalized) {
            state.shift =
                normalized;

        } else if (
            previousShift?.status
            === "OPEN"
        ) {
            console.warn(
                "Cash shift lookup returned empty; "
                + "preserving known OPEN shift"
            );

            state.shift =
                previousShift;

        } else {
            state.shift =
                null;
        }


        console.log(
            "Papelería current cash shift:",
            state.shift
        );

        renderStatus();
        syncCheckoutAvailability();

        return state.shift;
    }


    async function afterUnlock() {
        ensureUI();

        try {
            await refresh();

            if (
                !state.shift
                || state.shift
                    .status
                    !== "OPEN"
            ) {
                openDialog();
            }

        } catch (error) {
            console.error(
                "Cash shift load failed:",
                error
            );

            state.shift =
                null;

            renderStatus();
            syncCheckoutAvailability();

            openDialog();

            setError(
                error?.message
                || "No fue posible consultar la caja."
            );
        }
    }


    async function handleOpen(
        event
    ) {
        event.preventDefault();

        if (state.busy) {
            return;
        }

        setError("");


        const amount =
            Number(
                el(
                    "retail-opening-amount"
                )?.value
            );


        const managerId =
            Number(
                el(
                    "retail-opening-manager-id"
                )?.value
            );


        const managerPin =
            String(
                el(
                    "retail-opening-manager-pin"
                )?.value
                || ""
            ).trim();


        if (
            !Number.isFinite(amount)
            || amount < 0
        ) {
            setError(
                "Ingresa un fondo inicial válido."
            );

            return;
        }


        if (
            !Number.isInteger(
                managerId
            )
            || managerId <= 0
        ) {
            setError(
                "Ingresa el ID del gerente."
            );

            return;
        }


        if (!managerPin) {
            setError(
                "Ingresa el PIN del gerente."
            );

            return;
        }


        setBusy(true);

        try {
            /*
             * Antes de solicitar una nueva apertura,
             * consultamos al servidor.
             *
             * Si ya existe un turno OPEN/CLOSING,
             * lo adoptamos y NO hacemos POST /open.
             */
            const existing =
                await refresh();

            if (
                existing
                && (
                    existing.status === "OPEN"
                    || existing.status === "CLOSING"
                )
            ) {
                const dialog =
                    el(
                        "retail-cash-opening-modal"
                    );

                if (
                    dialog?.open
                    && typeof dialog.close
                        === "function"
                ) {
                    dialog.close();
                }

                setError("");

                console.log(
                    "Existing cash shift detected before open:",
                    existing
                );

                return;
            }


            const module =
                ensureModule();

            const shift =
                await module.open(
                    amount,
                    {
                        staffId:
                            managerId,

                        pin:
                            managerPin,
                    }
                );

            state.shift =
                normalizeShift(
                    shift
                );

            renderStatus();
            syncCheckoutAvailability();


            const dialog =
                el(
                    "retail-cash-opening-modal"
                );

            if (
                dialog?.open
                && typeof dialog.close
                    === "function"
            ) {
                dialog.close();
            }


            el(
                "retail-opening-manager-pin"
            ).value = "";


            window.dispatchEvent(
                new CustomEvent(
                    "cofi:retail-cash-opened",
                    {
                        detail:
                            shift,
                    }
                )
            );

        } catch (error) {
            /*
             * 409 significa que otra consulta/terminal
             * abrió la caja entre nuestro preflight
             * y el POST. Es recuperable y no debe
             * mostrarse como error de aplicación.
             */
            if (
                Number(
                    error?.status
                ) !== 409
            ) {
                console.error(
                    "Cash opening failed:",
                    error
                );
            }


            /*
             * Si backend responde 409 significa
             * que ya existe una caja activa.
             *
             * No mostramos error al cajero:
             * consultamos /current y adoptamos
             * esa caja existente.
             */
            if (
                Number(
                    error?.status
                ) === 409
            ) {
                try {
                    const existing =
                        await refresh();

                    if (
                        existing
                        && (
                            existing.status
                            === "OPEN"
                            || existing.status
                            === "CLOSING"
                        )
                    ) {
                        const dialog =
                            el(
                                "retail-cash-opening-modal"
                            );

                        if (
                            dialog?.open
                            && typeof dialog.close
                                === "function"
                        ) {
                            dialog.close();
                        }

                        setError("");

                        console.log(
                            "Existing cash shift adopted:",
                            existing
                        );

                        return;
                    }

                } catch (
                    refreshError
                ) {
                    console.error(
                        "Unable to recover existing shift:",
                        refreshError
                    );
                }
            }


            setError(
                error?.message
                || "No fue posible abrir la caja."
            );

        } finally {
            setBusy(false);
        }
    }


    function init() {
        ensureUI();
        ensureCloseUI();

        renderStatus();
        syncCheckoutAvailability();

        window.addEventListener(
            "cofi:retail-session-unlocked",
            afterUnlock
        );


        window.addEventListener(
            "cofi:retail-sale-completed",
            async () => {
                try {
                    await refresh();

                    console.log(
                        "Cash shift preserved after sale:",
                        state.shift
                    );

                } catch (error) {
                    /*
                     * No marcamos la caja cerrada por
                     * un error temporal de red/API.
                     */
                    console.warn(
                        "Cash shift refresh after sale failed:",
                        error
                    );

                    renderStatus();
                    syncCheckoutAvailability();
                }
            }
        );
    }


    if (
        document.readyState
        === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            init,
            {
                once: true,
            }
        );
    } else {
        init();
    }


    return {
        state,
        refresh,
        afterUnlock,
        openDialog,
        openCloseDialog,
    };
})();
