(() => {
    const API_BASE_URL = "/api";
    const form = document.getElementById("pin-form");
    const pinBoxes = Array.from(document.querySelectorAll(".pin-box"));
    const button = document.getElementById("connect-button");
    const buttonLabel = document.getElementById("connect-label");
    const spinner = document.getElementById("connect-spinner");
    const result = document.getElementById("access-result");

    function showToast(message, type = "error") {
        const toast = document.createElement("div");
        const tone = type === "success"
            ? "border-emerald-500/40 bg-emerald-950 text-emerald-100"
            : "border-red-500/40 bg-red-950 text-red-100";
        toast.className = `pointer-events-auto rounded-2xl border px-4 py-3 text-sm font-medium shadow-xl ${tone}`;
        toast.textContent = message;
        document.getElementById("toast-region").append(toast);
        window.setTimeout(() => toast.remove(), 4500);
    }

    function setLoading(isLoading) {
        button.disabled = isLoading;
        pinBoxes.forEach(input => { input.disabled = isLoading; });
        buttonLabel.textContent = isLoading ? "VALIDANDO" : "CONECTAR";
        spinner.classList.toggle("hidden", !isLoading);
    }

    function formatExpiration(expiresAt) {
        const date = new Date(expiresAt);
        if (Number.isNaN(date.getTime())) return expiresAt;
        return new Intl.DateTimeFormat("es-MX", {
            dateStyle: "medium",
            timeStyle: "short"
        }).format(date);
    }

    function showAccessGranted(data) {
        window.CofiNetSession = {
            purchaseId: data.purchase_id,
            plan: data.plan,
            minutes: data.minutes,
            expiresAt: data.expires_at
        };

        document.getElementById("result-plan").textContent = data.plan;
        if (data.permanent === true) {
            document.getElementById("result-minutes").textContent = "Sin límite";
            document.getElementById("result-expires-at").textContent = "No expira";
        } else {
            document.getElementById("result-minutes").textContent =
                `${data.minutes} minutos`;
            document.getElementById("result-expires-at").textContent =
                formatExpiration(data.expires_at);
        }
        result.classList.remove("hidden");
        showToast("Acceso concedido. Tu conexión está lista.", "success");
    }

    async function validatePin(pin) {
        let response;
        try {
            response = await fetch(`${API_BASE_URL}/pins/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pin })
            });
        } catch {
            throw new Error("No fue posible conectar con el servicio de validación.");
        }

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            const messages = {
                "PIN not found": "No encontramos ese PIN.",
                "PIN expired": "Este PIN ha expirado.",
                "PIN inactive": "Este PIN no está activo."
            };
            throw new Error(messages[payload.message] || payload.message || payload.detail || "No fue posible validar el PIN.");
        }
        return payload;
    }

    function pinValue() {
        return pinBoxes.map(input => input.value).join("");
    }

    function fillPin(value) {
        const digits = value.replace(/\D/g, "").slice(0, pinBoxes.length);
        pinBoxes.forEach((input, index) => { input.value = digits[index] || ""; });
        (pinBoxes[Math.min(digits.length, pinBoxes.length - 1)] || pinBoxes[0]).focus();
    }

    pinBoxes.forEach((input, index) => {
        input.addEventListener("input", () => {
            const digit = input.value.replace(/\D/g, "").slice(-1);
            input.value = digit;
            if (digit && index < pinBoxes.length - 1) pinBoxes[index + 1].focus();
        });
        input.addEventListener("keydown", event => {
            if (event.key === "Backspace" && !input.value && index > 0) pinBoxes[index - 1].focus();
            if (event.key === "Enter") form.requestSubmit();
        });
    });

    pinBoxes[0].addEventListener("paste", event => {
        const text = event.clipboardData?.getData("text") || "";
        if (/^\d{6}$/.test(text)) {
            event.preventDefault();
            fillPin(text);
        }
    });

    window.addEventListener("DOMContentLoaded", () => pinBoxes[0].focus());


    function decodeHotspotValue(value) {
        if (!value) return "";

        let decoded = value;

        for (let attempt = 0; attempt < 2; attempt += 1) {
            try {
                const nextValue = decodeURIComponent(decoded);

                if (nextValue === decoded) break;

                decoded = nextValue;
            } catch {
                break;
            }
        }

        return decoded;
    }

    function loginToHotspot(pin) {
        const params = new URLSearchParams(window.location.search);
        const loginUrl = decodeHotspotValue(params.get("login_url"));

        if (!loginUrl) return false;

        const destination =
            decodeHotspotValue(params.get("dst")) ||
            "http://neverssl.com/";

        const hotspotForm = document.createElement("form");
        hotspotForm.method = "POST";
        hotspotForm.action = loginUrl;
        hotspotForm.style.display = "none";

        const fields = {
            username: pin,
            password: pin,
            dst: destination,
            popup: "false"
        };

        Object.entries(fields).forEach(([name, value]) => {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = name;
            input.value = value;
            hotspotForm.appendChild(input);
        });

        document.body.appendChild(hotspotForm);
        hotspotForm.submit();

        return true;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const pin = pinValue();
        result.classList.add("hidden");

        if (!/^\d{6}$/.test(pin)) {
            showToast("Ingresa un PIN válido de 6 dígitos.");
            pinBoxes.find(input => !input.value)?.focus();
            return;
        }

        setLoading(true);
        try {
            const access = await validatePin(pin);

            if (!loginToHotspot(pin)) {
                showAccessGranted(access);
            }
        } catch (error) {
            showToast(error.message || "No fue posible validar el PIN.");
        } finally {
            setLoading(false);
        }
    });
})();
