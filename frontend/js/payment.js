cuandoDocumentoListoPago(enlazarControlesPago);


function guardarContextoHotspot() {
    const params = new URLSearchParams(window.location.search);

    const loginUrl = params.get("login_url");
    const destination = params.get("dst");
    const mac = params.get("mac");

    if (!loginUrl) return;

    localStorage.setItem(
        "cofinet_hotspot_context",
        JSON.stringify({
            loginUrl,
            destination: destination || "http://neverssl.com/",
            mac: mac || ""
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
        const checkout = await window.CofiApi.createGuestCheckout(planId);
        const selectedPlan = window.CofiPlans?.find(plan => plan.id === planId);
        guardarContextoHotspot();

        localStorage.setItem("cofinet_pending_purchase", JSON.stringify({
            purchaseId: checkout.purchase_id,
            plan: selectedPlan?.name || "Plan seleccionado",
            durationMinutes: selectedPlan?.duration_minutes || 0
        }));
        mostrarCompraPendiente(checkout, selectedPlan);
    } catch (error) {
        console.error(error);
        alert(mensajeErrorAmigable(error, "No fue posible crear la compra."));
    } finally {
        button.disabled = false;
        button.textContent = originalLabel;
    }
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

    if (!pendingPurchase) return;

    const purchaseId = pendingPurchase.purchaseId;

    async function revisarCompra() {

    try {

        const purchase = await window.CofiApi.getGuestPurchaseStatus(purchaseId);

        if (purchase.status !== "paid") return;

        window.clearInterval(intervalId);

        localStorage.removeItem("cofinet_pending_purchase");

        const purchaseData = {
            plan: pendingPurchase.plan,
            pin: purchase.pin,
            duration_minutes: pendingPurchase.durationMinutes,
            expires_at: purchase.expires_at
        };

        mostrarCompraExitosa(purchaseData);

        window.setTimeout(() => {
            iniciarSesionHotspotDespuesDelPago(purchase.pin);
        }, 1200);

    } catch (error) {

        console.warn("No fue posible consultar el estado.", error);

    }

}

// Revisar inmediatamente
revisarCompra();

// Después seguir revisando cada 3 segundos
const intervalId = window.setInterval(revisarCompra, 3000);
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
