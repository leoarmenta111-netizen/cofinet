(() => {
    const modal = document.getElementById("membership-modal");
    const form = document.getElementById("membership-form");
    const planInput = document.getElementById("membership-plan");
    const planLabel = document.getElementById("membership-plan-label");
    const submit = document.getElementById("membership-submit");
    const error = document.getElementById("membership-error");
    const API_BASE_URL = `http://${window.location.hostname}:8000`;

    document.querySelectorAll("[data-membership-plan]").forEach(button => button.addEventListener("click", () => {
        planInput.value = button.dataset.membershipPlan;
        planLabel.textContent = button.dataset.membershipName;
        error.classList.add("hidden");
        modal.classList.remove("hidden");
        document.getElementById("membership-name").focus();
    }));
    document.querySelectorAll("[data-membership-close]").forEach(button => button.addEventListener("click", () => modal.classList.add("hidden")));

    form.addEventListener("submit", async event => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(form));
        if (data.password !== data.confirm_password) return showError("Las contraseñas no coinciden.");
        submit.disabled = true;
        submit.textContent = "Redirigiendo a Mercado Pago…";
        try {
            const response = await fetch(`${API_BASE_URL}/memberships/checkout`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload.detail || "No fue posible iniciar la suscripción.");
            window.location.assign(payload.checkout_url);
        } catch (requestError) {
            showError(requestError.message);
            submit.disabled = false;
            submit.textContent = "Continuar con Mercado Pago";
        }
    });
    function showError(message) { error.textContent = message; error.classList.remove("hidden"); }
})();
