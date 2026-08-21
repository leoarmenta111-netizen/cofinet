const ADMIN_API_BASE = "/api";
const ADMIN_TOKEN_KEY = "cofinet_admin_token";
const SUPER_ADMIN = "super_admin";
const PIN_OPERATOR = "pin_operator";

const adminState = { current: null };

class AdminApiError extends Error {
    constructor(message, status, payload = null) {
        super(message);
        this.name = "AdminApiError";
        this.status = status;
        this.payload = payload;
    }
}

function adminToken() {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
}

function storeAdminToken(token) {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
}

function clearAdminSession() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    adminState.current = null;
}

async function adminRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = adminToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (options.body) headers.set("Content-Type", "application/json");

    let response;
    try {
        response = await fetch(`${ADMIN_API_BASE}${path}`, { ...options, headers });
    } catch {
        throw new AdminApiError("No fue posible conectar con CofiNet.", 0);
    }

    const payload = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
        if (response.status === 401) clearAdminSession();
        const detail = Array.isArray(payload?.detail)
            ? payload.detail.map(item => item.msg).join(" ")
            : payload?.detail;
        throw new AdminApiError(detail || "No fue posible completar la solicitud.", response.status, payload);
    }
    return payload;
}

function adminLanding(role) {
    return role === PIN_OPERATOR ? "pins.html" : "dashboard.html";
}

async function currentAdmin({ refresh = false } = {}) {
    if (!refresh && adminState.current) return adminState.current;
    adminState.current = await adminRequest("/admin/me");
    return adminState.current;
}

async function bootstrapAdmin({ allowedRoles = [SUPER_ADMIN, PIN_OPERATOR] } = {}) {
    if (!adminToken()) {
        window.location.replace("login.html");
        return null;
    }
    try {
        const admin = await currentAdmin({ refresh: true });
        if (!allowedRoles.includes(admin.role)) {
            window.location.replace(adminLanding(admin.role));
            return null;
        }
        renderAdminChrome(admin);
        document.body.classList.remove("auth-pending");
        return admin;
    } catch (error) {
        if (error.status === 401 || error.status === 403) {
            clearAdminSession();
            window.location.replace("login.html");
            return null;
        }
        document.body.classList.remove("auth-pending");
        showToast(error.message, "error");
        throw error;
    }
}

async function redirectAuthenticatedAdmin() {
    if (!adminToken()) {
        document.body.classList.remove("auth-pending");
        return;
    }
    try {
        const admin = await currentAdmin({ refresh: true });
        window.location.replace(adminLanding(admin.role));
    } catch {
        clearAdminSession();
        document.body.classList.remove("auth-pending");
    }
}

function renderAdminChrome(admin) {
    const nav = document.querySelector("[data-admin-nav]");
    const page = document.body.dataset.page;
    const items = admin.role === SUPER_ADMIN
        ? [
            ["dashboard", "dashboard.html", "Dashboard"],
            ["pins", "pins.html", "PINs de efectivo"],
            ["payments", "payments.html", "Payments"],
            ["sales", "sales.html", "Ventas POS"],
            ["plans", "plans.html", "Planes"],
            ["administrators", "administrators.html", "Administradores"]
        ]
        : [
            ["pins", "pins.html", "Generar PIN"],
            ["plans", "plans.html", "Planes"]
        ];

    if (nav) {
        nav.replaceChildren();
        for (const [key, href, label] of items) {
            const link = document.createElement("a");
            link.href = href;
            link.textContent = label;
            if (page === key) link.setAttribute("aria-current", "page");
            nav.append(link);
        }
        if (admin.role === SUPER_ADMIN) {
            const unavailable = document.createElement("div");
            unavailable.className = "nav-coming-soon";
            unavailable.innerHTML = "<span>Reports</span><small>Próximamente</small><span>Settings</span><small>Próximamente</small>";
            nav.append(unavailable);
        }
    }

    document.querySelectorAll("[data-admin-name]").forEach(element => {
        element.textContent = admin.full_name;
    });
    document.querySelectorAll("[data-admin-role]").forEach(element => {
        element.textContent = admin.role === SUPER_ADMIN ? "Super admin" : "Operador de PINs";
    });
    document.querySelectorAll("[data-admin-initials]").forEach(element => {
        element.textContent = initials(admin.full_name);
    });

    const toggle = document.querySelector("[data-menu-toggle]");
    const sidebar = document.querySelector(".sidebar");
    toggle?.addEventListener("click", () => {
        const open = sidebar?.classList.toggle("is-open") || false;
        toggle.setAttribute("aria-expanded", String(open));
    });
}

function logoutAdmin() {
    clearAdminSession();
    window.location.replace("login.html");
}

function initials(name) {
    return name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase();
}

function formatMoney(value, currency = "MXN") {
    return new Intl.NumberFormat("es-MX", { style: "currency", currency }).format(Number(value || 0));
}

function formatDate(value) {
    if (!value) return "—";
    return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function formatDuration(minutes) {
    const total = Number(minutes);
    if (total < 60) return `${total} min`;
    if (total % 1440 === 0) return `${total / 1440} día${total === 1440 ? "" : "s"}`;
    if (total % 60 === 0) return `${total / 60} h`;
    return `${Math.floor(total / 60)} h ${total % 60} min`;
}

function statusLabel(status) {
    const labels = {
        approved: "Aprobado",
        pending: "Pendiente",
        paid: "Pagado",
        expired: "Expirado",
        cancelled: "Cancelado"
    };
    return labels[status] || status;
}

function statusClass(status) {
    if (["approved", "paid", "active"].includes(status)) return "success";
    if (status === "pending") return "warning";
    if (["error", "failed", "cancelled", "expired"].includes(status)) return "danger";
    return "neutral";
}

function setButtonLoading(button, loading, label = "Procesando…") {
    if (!button) return;
    if (loading) {
        button.dataset.label = button.textContent;
        button.textContent = label;
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
    } else {
        button.textContent = button.dataset.label || button.textContent;
        button.disabled = false;
        button.removeAttribute("aria-busy");
    }
}

async function copyText(value) {
    await navigator.clipboard.writeText(value);
    showToast("PIN copiado al portapapeles.", "success");
}

function showToast(message, tone = "success") {
    let region = document.getElementById("toast-region");
    if (!region) {
        region = document.createElement("div");
        region.id = "toast-region";
        region.className = "toast-region";
        region.setAttribute("aria-live", "polite");
        document.body.append(region);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${tone}`;
    toast.textContent = message;
    region.append(toast);
    window.setTimeout(() => toast.remove(), 4200);
}

function showEmpty(container, title, description) {
    container.replaceChildren();
    const state = document.createElement("div");
    state.className = "empty-state";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const copy = document.createElement("p");
    copy.textContent = description;
    state.append(heading, copy);
    container.append(state);
}

function confirmAdminAction({ title, message, confirmLabel = "Confirmar", danger = false }) {
    let dialog = document.getElementById("admin-confirm-dialog");
    if (!dialog) {
        dialog = document.createElement("dialog");
        dialog.id = "admin-confirm-dialog";
        dialog.className = "dialog";
        dialog.innerHTML = `
            <form method="dialog">
                <h2 data-dialog-title></h2>
                <p data-dialog-message></p>
                <div class="dialog-actions">
                    <button class="button button-secondary" value="cancel">Cancelar</button>
                    <button class="button" data-dialog-confirm value="confirm"></button>
                </div>
            </form>`;
        document.body.append(dialog);
    }
    dialog.querySelector("[data-dialog-title]").textContent = title;
    dialog.querySelector("[data-dialog-message]").textContent = message;
    const confirm = dialog.querySelector("[data-dialog-confirm]");
    confirm.textContent = confirmLabel;
    confirm.className = `button ${danger ? "button-danger" : "button-primary"}`;
    dialog.showModal();
    return new Promise(resolve => {
        dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
    });
}

function printPinTicket(pin) {
    const ticket = document.getElementById("print-ticket");
    if (!ticket) return;
    ticket.querySelector("[data-ticket-pin]").textContent = pin.pin;

    const branchNode = ticket.querySelector("[data-ticket-branch]");
    if (branchNode) {
        branchNode.textContent = pin.branch_name || "—";
    }

    ticket.querySelector("[data-ticket-plan]").textContent = pin.plan_name;
    ticket.querySelector("[data-ticket-duration]").textContent = formatDuration(pin.duration_minutes);
    ticket.querySelector("[data-ticket-issued]").textContent = formatDate(pin.issued_at);
    ticket.querySelector("[data-ticket-expires]").textContent = formatDate(pin.expires_at);
    window.print();
}

window.CofiAdmin = {
    SUPER_ADMIN,
    PIN_OPERATOR,
    adminLanding,
    adminRequest,
    bootstrapAdmin,
    clearAdminSession,
    confirmAdminAction,
    copyText,
    currentAdmin,
    formatDate,
    formatDuration,
    formatMoney,
    logoutAdmin,
    printPinTicket,
    redirectAuthenticatedAdmin,
    setButtonLoading,
    showEmpty,
    showToast,
    statusClass,
    statusLabel,
    storeAdminToken
};
