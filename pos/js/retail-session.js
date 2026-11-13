window.CofiRetailSession = (() => {
    "use strict";

    const MODULE_CODE = "PAPELERIA";

    const state = {
        branchCode: null,
        terminalId: null,
        session: null,
        busy: false,
    };


    function el(id) {
        return document.getElementById(id);
    }


    function branchFromUrl() {
        const params =
            new URLSearchParams(
                window.location.search
            );

        return (
            params.get("branch")
                ?.trim()
                .toLowerCase()
            || "papeleria-dev"
        );
    }


    function setError(message = "") {
        const target =
            el("retail-staff-unlock-error");

        if (target) {
            target.textContent =
                String(message || "");
        }
    }


    function setBusy(busy) {
        state.busy = busy;

        const button =
            el("retail-staff-unlock-submit");

        if (button) {
            button.disabled = busy;
            button.textContent =
                busy
                    ? "Entrando..."
                    : "Entrar al POS";
        }
    }


    function showLogin() {
        const login =
            el("retail-staff-lock");

        const pos =
            el("retail-pos");

        if (login) {
            login.hidden = false;
        }

        if (pos) {
            pos.hidden = true;
        }
    }


    function showPOS() {
        const login =
            el("retail-staff-lock");

        const pos =
            el("retail-pos");

        if (login) {
            login.hidden = true;
        }

        if (pos) {
            pos.hidden = false;
        }
    }


    async function configureTerminal() {
        state.branchCode =
            branchFromUrl();

        localStorage.setItem(
            "cofi_pos_branch",
            state.branchCode
        );

        await window.CofiPosDB.put(
            "meta",
            state.branchCode,
            "branch_code"
        );

        state.terminalId =
            await window.CofiPosDB
                .getOrCreateTerminalId(
                    state.branchCode
                );

        const terminal =
            el("retail-terminal-id");

        if (terminal) {
            terminal.textContent =
                state.terminalId;
        }
    }


    async function authenticate(
        staffId,
        pin
    ) {
        /*
         * Importante:
         * enviamos module_code explícitamente.
         * No usamos el default CAFE.
         */
        const result =
            await window.CofiPosAPI.request(
                "/pos/staff/unlock",
                {
                    method: "POST",
                    body: JSON.stringify({
                        staff_id:
                            Number(staffId),

                        pin:
                            String(pin),

                        branch_code:
                            state.branchCode,

                        terminal_id:
                            state.terminalId,

                        module_code:
                            MODULE_CODE,
                    }),
                }
            );

        if (
            !result ||
            !result.access_token
        ) {
            throw new Error(
                "El servidor no devolvió "
                + "una sesión válida."
            );
        }

        if (
            result.module_code
            !== MODULE_CODE
        ) {
            throw new Error(
                "Este empleado no pertenece "
                + "al módulo Papelería."
            );
        }

        /*
         * Segunda validación real del token.
         */
        await window.CofiPosAPI.request(
            "/pos/staff/session",
            {
                accessToken:
                    result.access_token,
            }
        );

        return result;
    }


    async function handleSubmit(event) {
        event.preventDefault();

        if (state.busy) {
            return;
        }

        setError("");

        const staffId =
            Number(
                el("retail-staff-id")
                    ?.value
            );

        const pin =
            String(
                el("retail-staff-pin")
                    ?.value || ""
            ).trim();

        if (
            !Number.isInteger(staffId)
            || staffId <= 0
        ) {
            setError(
                "Ingresa un ID de empleado válido."
            );
            return;
        }

        if (!pin) {
            setError(
                "Ingresa tu PIN."
            );
            return;
        }

        setBusy(true);

        try {
            const session =
                await authenticate(
                    staffId,
                    pin
                );

            state.session =
                session;

            window.CofiRetailAPI
                .setAccessToken(
                    session.access_token
                );

            const status =
                el(
                    "retail-session-status"
                );

            if (status) {
                status.innerHTML =
                    `<strong>${
                        session.display_name
                    }</strong>`
                    + `<span>${
                        session.role
                    } · ${
                        state.terminalId
                    }</span>`;
            }

            const pinInput =
                el("retail-staff-pin");

            if (pinInput) {
                pinInput.value = "";
            }

            showPOS();

            await window.CofiRetailApp
                .loadOperationalData();

        } catch (error) {
            console.error(
                "Papelería unlock error:",
                error
            );

            state.session = null;

            window.CofiRetailAPI
                .setAccessToken(null);

            showLogin();

            setError(
                error?.message
                || "No se pudo entrar al POS."
            );

        } finally {
            setBusy(false);
        }
    }


    async function init() {
        showLogin();
        setBusy(false);

        try {
            await configureTerminal();

            const form =
                el(
                    "retail-staff-unlock-form"
                );

            if (!form) {
                throw new Error(
                    "No se encontró el formulario "
                    + "de acceso."
                );
            }

            form.addEventListener(
                "submit",
                handleSubmit
            );

            el(
                "retail-staff-id"
            )?.focus();

        } catch (error) {
            console.error(error);

            setError(
                error?.message
                || "No fue posible iniciar "
                + "la terminal."
            );
        }
    }


    function current() {
        return state.session
            ? { ...state.session }
            : null;
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
        current,
        state,
    };
})();
