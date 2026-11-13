window.CofiRetailCashControl = (() => {
    "use strict";

    const state = {
        module: null,
        shift: null,
        busy: false,
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
                        if (
                            !state.shift
                            || state.shift
                                .status
                                !== "OPEN"
                        ) {
                            openDialog();
                        }
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
    };
})();
