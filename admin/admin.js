const ADMIN_API_BASE = `http://${window.location.hostname}:8000`;
const ADMIN_TOKEN_KEY = "cofinet_admin_token";

function adminToken() {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
}

async function adminRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = adminToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body) headers.set("Content-Type", "application/json");
    const response = await fetch(`${ADMIN_API_BASE}${path}`, { ...options, headers });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
        if (response.status === 401 || response.status === 403) localStorage.removeItem(ADMIN_TOKEN_KEY);
        throw new Error(payload?.detail || "No fue posible completar la solicitud.");
    }
    return payload;
}

function requireAdmin() {
    if (!adminToken()) window.location.replace("login.html");
}

function logoutAdmin() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    window.location.replace("login.html");
}
