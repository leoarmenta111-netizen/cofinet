cuandoDocumentoListoPago(enlazarControlesPago);

let cofinetPurchasePollingIntervalId = null;
let cofinetPurchasePollingGeneration = 0;


function obtenerCodigoSucursalActual() {
    const params = new URLSearchParams(window.location.search);
    const branchCode = params.get("branch");

    if (!branchCode) {
        return null;
    }

    const normalized = branchCode.trim().toLowerCase();

    return normalized || null;
}


function guardarContextoHotspot() {
    const params = new URLSearchParams(window.location.search);

    const loginUrl = params.get("login_url");
    const destination = params.get("dst");
    const mac = params.get("mac");
    const branchCode = obtenerCodigoSucursalActual();

    if (!loginUrl) return;

    localStorage.setItem(
        "cofinet_hotspot_context",
        JSON.stringify({
            loginUrl,
            destination: destination || "http://neverssl.com/",
            mac: mac || "",
            branchCode
        })
    );
}

function iniciarSesionHotspotDespuesDelPago(pin) {
    let context;

    try {
        context = JSON.parse(
            localStorage.getItem("cofinet_hotspot_context") || "null"
        );
    } catch {
        context = null;
    }

    if (!context?.loginUrl || !pin) {
        return false;
    }

    const form = document.createElement("form");
    form.method = "POST";
    form.action = context.loginUrl;
    form.style.display = "none";

    const fields = {
        username: pin,
        password: pin,
        dst: context.destination || "http://neverssl.com/",
        popup: "false"
    };

    Object.entries(fields).forEach(([name, value]) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        form.appendChild(input);
    });

    document.body.appendChild(form);

    localStorage.removeItem("cofinet_hotspot_context");

    form.submit();
    return true;
}



function cuandoDocumentoListoPago(callback) {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", callback);
    } else {
        callback();
    }
}

function enlazarControlesPago() {
    document.addEventListener("click", event => {
        const control = event.target.closest("[data-payment-plan-id]");
        if (control) comprarPlan(Number(control.dataset.paymentPlanId), control);
    });

    document.querySelectorAll("[data-payment-close]").forEach(control => {
        control.addEventListener("click", cerrarFormularioPago);
    });
    document.querySelectorAll("[data-payment-form]").forEach(form => {
        form.addEventListener("submit", event => event.preventDefault());
    });
    document.querySelectorAll("[data-mercadopago-checkout]").forEach(button => {
    button.addEventListener("click", () => {

        if (!button.dataset.checkoutUrl) return;

        window.open(
            button.dataset.checkoutUrl,
            "_blank"
        );

    });
});
    document.querySelectorAll("[data-card-format='number']").forEach(input => {
        input.addEventListener("input", () => formatearTarjeta(input));
    });
    document.querySelectorAll("[data-card-format='expiry']").forEach(input => {
        input.addEventListener("input", () => formatearVencimiento(input));
    });
    restaurarCompraPendiente();
}

async function comprarPlan(planId, button) {
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Procesando...";

    try {
        const branchCode = obtenerCodigoSucursalActual();

        const checkout = await window.CofiApi.createGuestCheckout(
            planId,
            branchCode
        );

        const selectedPlan = window.CofiPlans?.find(plan => plan.id === planId);
        guardarContextoHotspot();

        const pendingPurchase = {
            purchaseId: checkout.purchase_id,
            plan: selectedPlan?.name || "Plan seleccionado",
            durationMinutes: selectedPlan?.duration_minutes || 0,
            branchCode
        };

        localStorage.setItem(
            "cofinet_pending_purchase",
            JSON.stringify(pendingPurchase)
        );

        mostrarCompraPendiente(checkout, selectedPlan);

        // Una compra nueva siempre sustituye cualquier polling anterior.
        iniciarPollingCompraPendiente(pendingPurchase);
    } catch (error) {
        console.error(error);
        alert(mensajeErrorAmigable(error, "No fue posible crear la compra."));
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
}

function detenerPollingCompraPendiente() {
    if (cofinetPurchasePollingIntervalId !== null) {
        window.clearInterval(cofinetPurchasePollingIntervalId);
        cofinetPurchasePollingIntervalId = null;
    }

    // Invalida cualquier request anterior que todavía esté en vuelo.
    cofinetPurchasePollingGeneration += 1;
}

function iniciarPollingCompraPendiente(pendingPurchase) {
    if (!pendingPurchase?.purchaseId) return;

    detenerPollingCompraPendiente();

    const purchaseId = Number(pendingPurchase.purchaseId);

    if (!Number.isInteger(purchaseId) || purchaseId <= 0) {
        console.warn("purchaseId inválido:", pendingPurchase.purchaseId);
        return;
    }

    const generation = cofinetPurchasePollingGeneration;

    console.info(
        `[CofiNet] Iniciando seguimiento de compra ${purchaseId}`
    );

    async function revisarCompra() {
        try {
            const purchase =
                await window.CofiApi.getGuestPurchaseStatus(purchaseId);

            // Si durante este request comenzó otra compra,
            // ignorar la respuesta de la compra vieja.
            if (generation !== cofinetPurchasePollingGeneration) {
                return;
            }

            if (purchase.status !== "paid") {
                return;
            }

            // Verificar que esta siga siendo la compra activa.
            let currentPurchase = null;

            try {
                currentPurchase = JSON.parse(
                    localStorage.getItem("cofinet_pending_purchase") || "null"
                );
            } catch {
                currentPurchase = null;
            }

            if (
                Number(currentPurchase?.purchaseId) !== purchaseId
            ) {
                console.info(
                    `[CofiNet] Compra ${purchaseId} ya no es la compra activa`
                );
                detenerPollingCompraPendiente();
                return;
            }

            detenerPollingCompraPendiente();

            localStorage.removeItem("cofinet_pending_purchase");

            const purchaseData = {
                plan: pendingPurchase.plan,
                pin: purchase.pin,
                duration_minutes:
                    purchase.duration_minutes ??
                    pendingPurchase.durationMinutes,
                expires_at: purchase.expires_at
            };

            console.info(
                `[CofiNet] Compra ${purchaseId} aprobada. PIN recibido.`
            );

            mostrarCompraExitosa(purchaseData);

            window.setTimeout(() => {
                iniciarSesionHotspotDespuesDelPago(purchase.pin);
            }, 1200);

        } catch (error) {
            console.warn(
                `[CofiNet] No fue posible consultar compra ${purchaseId}.`,
                error
            );
        }
    }

    // Primera revisión inmediatamente.
    revisarCompra();

    // Después cada 3 segundos.
    cofinetPurchasePollingIntervalId =
        window.setInterval(revisarCompra, 3000);
}

function restaurarCompraPendiente() {
    let pendingPurchase;

    try {
        pendingPurchase = JSON.parse(
            localStorage.getItem("cofinet_pending_purchase") || "null"
        );
    } catch {
        pendingPurchase = null;
    }

    if (!pendingPurchase?.purchaseId) {
        return;
    }

    iniciarPollingCompraPendiente(pendingPurchase);
}

function cerrarFormularioPago() {
    document.getElementById("modal-pago").classList.add("hidden");
}

function formatearTarjeta(input) {
    const value = input.value.replace(/\s+/g, "").replace(/[^0-9]/g, "");
    input.value = value.replace(/(.{4})/g, "$1 ").trim();
}

function formatearVencimiento(input) {
    const value = input.value.replace(/\//g, "").replace(/[^0-9]/g, "");
    input.value = value.length >= 2 ? `${value.substring(0, 2)}/${value.substring(2, 4)}` : value;
}
