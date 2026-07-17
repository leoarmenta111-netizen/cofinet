const API_BASE_URL = `http://${window.location.hostname}:8000`;

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

async function requestApi(path, { includeAuth = true, ...options } = {}) {
    const headers = new Headers(options.headers || {});
    const token = localStorage.getItem("access_token");

    if (includeAuth && token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body) headers.set("Content-Type", "application/json");

    let response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
    } catch {
        throw new ApiError("No fue posible conectar con el servidor.", 0);
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
        throw new ApiError(payload?.detail || "La solicitud no pudo completarse.", response.status);
    }
    return payload;
}

window.CofiApi = {
    login(email, password) {
        return requestApi("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });
    },
    getCurrentUser() {
        return requestApi("/auth/me");
    },
    logout() {
        return requestApi("/auth/logout", { method: "POST" });
    },
    getPlans() {
        return requestApi("/plans");
    },
    createPurchase(planId) {
        return requestApi("/purchases", {
            method: "POST",
            body: JSON.stringify({ plan_id: planId })
        });
    },
    createGuestCheckout(planId) {
        return requestApi("/guest-purchases", {
            method: "POST",
            includeAuth: false,
            body: JSON.stringify({ plan_id: planId })
        });
    },
    getGuestPurchaseStatus(purchaseId) {
        return requestApi(`/guest-purchases/${purchaseId}`, {
            includeAuth: false
        });
    }
};

window.CofiApiError = ApiError;
