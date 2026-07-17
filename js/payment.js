cuandoDocumentoListoPago(enlazarControlesPago);

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
            if (button.dataset.checkoutUrl) window.location.assign(button.dataset.checkoutUrl);
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
        sessionStorage.setItem("cofinet_pending_purchase", JSON.stringify({
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
    const purchaseId = Number(new URLSearchParams(window.location.search).get("purchase_id"));
    if (!Number.isInteger(purchaseId) || purchaseId <= 0) return;

    let pendingPurchase;
    try {
        pendingPurchase = JSON.parse(sessionStorage.getItem("cofinet_pending_purchase") || "null");
    } catch {
        pendingPurchase = null;
    }
    if (!pendingPurchase || pendingPurchase.purchaseId !== purchaseId) return;

    const intervalId = window.setInterval(async () => {
        try {
            const purchase = await window.CofiApi.getGuestPurchaseStatus(purchaseId);
            if (purchase.status !== "paid") return;

            window.clearInterval(intervalId);
            sessionStorage.removeItem("cofinet_pending_purchase");
            window.history.replaceState({}, document.title, window.location.pathname);
            mostrarCompraExitosa({
                plan: pendingPurchase.plan,
                pin: purchase.pin,
                duration_minutes: pendingPurchase.durationMinutes,
                expires_at: purchase.expires_at
            });
        } catch (error) {
            console.warn("No fue posible consultar el estado del pago.", error);
        }
    }, 3000);
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
