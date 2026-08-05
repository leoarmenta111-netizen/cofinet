let timerInterval = null;
let totalSegundos = 3 * 3600 + 58 * 60 + 23;

cuandoDocumentoListo(enlazarControlesLogin);

function cuandoDocumentoListo(callback) {
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", callback);
    } else {
        callback();
    }
}

function enlazarControlesLogin() {
    document.querySelectorAll("[data-membership-login]").forEach(control => {
        control.addEventListener("click", () => iniciarSesionMembresia(control.dataset.membershipLogin === "desktop"));
    });
    document.querySelectorAll("[data-pin-submit='mobile']").forEach(control => control.addEventListener("click", validarPinServidor));
    document.querySelectorAll("[data-pin-submit='desktop']").forEach(control => control.addEventListener("click", validarPinServidorDesktop));
    document.querySelectorAll("[data-disconnect]").forEach(control => control.addEventListener("click", desconectarPrueba));
    enlazarInputsPin("mobile", ".pin-box", moverSiguienteInput, manejarBorradoInput);
    enlazarInputsPin("desktop", ".pin-box-desktop", moverSiguienteInputDesktop, manejarBorradoInputDesktop);
}

function enlazarInputsPin(scope, selector, onInput, onKeydown) {
    document.querySelectorAll(`[data-pin-scope='${scope}']`).forEach(input => {
        const index = Number(input.dataset.pinIndex);
        input.addEventListener("input", () => onInput(input, index));
        input.addEventListener("keydown", event => onKeydown(event, index));
    });
}

function moverSiguienteInput(input, index) {
    input.value = input.value.replace(/[^0-9]/g, "");
    if (input.value.length === 1 && index < 6) document.querySelectorAll(".pin-box")[index].focus();
}

function manejarBorradoInput(event, index) {
    const inputs = document.querySelectorAll(".pin-box");
    if (event.key === "Backspace" && index > 1 && inputs[index - 1].value === "") inputs[index - 2].focus();
}

function moverSiguienteInputDesktop(input, index) {
    input.value = input.value.replace(/[^0-9]/g, "");
    if (input.value.length === 1 && index < 6) document.querySelectorAll(".pin-box-desktop")[index].focus();
}

function manejarBorradoInputDesktop(event, index) {
    const inputs = document.querySelectorAll(".pin-box-desktop");
    if (event.key === "Backspace" && index > 1 && inputs[index - 1].value === "") inputs[index - 2].focus();
}

function validarPinServidor() {
    const pin = [...document.querySelectorAll(".pin-box")].map(input => input.value).join("");
    alert(pin.length === 6 ? "La validación de PIN estará disponible próximamente." : "Por favor ingresa los 6 dígitos del código de tu ticket.");
}

function validarPinServidorDesktop() {
    const pin = [...document.querySelectorAll(".pin-box-desktop")].map(input => input.value).join("");
    alert(pin.length === 6 ? "La validación de PIN estará disponible próximamente." : "Por favor ingresa los 6 dígitos del código de tu ticket.");
}

async function iniciarSesionMembresia(isDesktop) {
    const userField = isDesktop ? "membresia-usuario-desktop" : "membresia-usuario";
    const passField = isDesktop ? "membresia-clave-desktop" : "membresia-clave";
    const usuario = document.getElementById(userField).value.trim();
    const clave = document.getElementById(passField).value.trim();

    if (!usuario || !clave) {
        alert("Por favor ingresa tu correo y contraseña.");
        return;
    }

    try {
        const data = await window.CofiApi.login(usuario, clave);
        localStorage.setItem("access_token", data.access_token);
        const user = await window.CofiApi.getCurrentUser();
        mostrarUsuarioAutenticado(user);
        activarConexionExitoso();
    } catch (error) {
        console.error(error);
        if (error.status === 401) localStorage.removeItem("access_token");
        alert(mensajeErrorAmigable(error, "No fue posible iniciar sesión."));
    }
}

function seleccionarMembresia(nombreMembresia) {
    alert(`Has seleccionado el plan corporativo/suscripción: ${nombreMembresia}`);
}

function activarConexionExitoso(duracionSegundos = null) {
    document.getElementById("success-screen-title").textContent = "Ya cuentas con conexión CofiNet+";
    document.getElementById("success-screen-subtitle").textContent = "Disfruta la experiencia Coficenter®.";
    document.getElementById("connection-timer").classList.remove("hidden");
    document.getElementById("guest-purchase-details").classList.add("hidden");
    document.getElementById("contenedor-portal").classList.add("hidden");
    const finalScreen = document.getElementById("pantalla-final");
    finalScreen.classList.remove("hidden");
    finalScreen.style.display = "flex";
    if (typeof duracionSegundos === "number") totalSegundos = duracionSegundos;
    if (timerInterval) clearInterval(timerInterval);
    actualizarRelojUI();
    timerInterval = setInterval(() => {
        if (totalSegundos > 0) {
            totalSegundos--;
            actualizarRelojUI();
        } else {
            clearInterval(timerInterval);
            alert("Tu tiempo de conexión ha terminado.");
            desconectarPrueba();
        }
    }, 1000);
}

function actualizarRelojUI() {
    const hrs = Math.floor(totalSegundos / 3600);
    const mins = Math.floor((totalSegundos % 3600) / 60);
    const segs = totalSegundos % 60;
    document.getElementById("reloj-hrs").innerText = String(hrs).padStart(2, "0");
    document.getElementById("reloj-min").innerText = String(mins).padStart(2, "0");
    document.getElementById("reloj-seg").innerText = String(segs).padStart(2, "0");
}

async function desconectarPrueba() {
    if (timerInterval) clearInterval(timerInterval);
    try {
        if (localStorage.getItem("access_token")) await window.CofiApi.logout();
    } catch (error) {
        console.warn("No fue posible cerrar la sesión en el servidor.", error);
    } finally {
        localStorage.removeItem("access_token");
    }

    totalSegundos = 3 * 3600 + 58 * 60 + 23;
    document.querySelectorAll(".pin-box, .pin-box-desktop").forEach(input => input.value = "");
    document.getElementById("pantalla-final").classList.add("hidden");
    document.getElementById("pantalla-final").style.display = "none";
    document.getElementById("contenedor-portal").classList.remove("hidden");
    document.getElementById("session-user-name").classList.add("hidden");
    document.getElementById("purchase-success-details").classList.add("hidden");
    document.getElementById("guest-purchase-details").classList.add("hidden");
    document.getElementById("connection-timer").classList.remove("hidden");
    toggleAcordion(null);
    cambiarVistaDesktop("inicio");
}

function mensajeErrorAmigable(error, fallback) {
    const messages = {
        0: "No fue posible conectar con el servidor.",
        401: "Tu sesión no es válida. Inicia sesión nuevamente.",
        403: "Tu cuenta no tiene permiso para realizar esta acción.",
        404: "No encontramos el recurso solicitado.",
        500: "Ocurrió un error en el servidor. Intenta nuevamente."
    };
    return messages[error?.status] || error?.message || fallback;
}

function mostrarUsuarioAutenticado(user) {
    document.querySelectorAll("[data-user-name]").forEach(element => element.textContent = user.name);
    document.getElementById("session-user-name").classList.remove("hidden");
}

function mostrarPantallaInicioSesion() {
    toggleAcordion("membresia");
    cambiarVistaDesktop("membresia");
}

async function restaurarSesion() {
    if (!localStorage.getItem("access_token")) return;
    try {
        const user = await window.CofiApi.getCurrentUser();
        mostrarUsuarioAutenticado(user);
        activarConexionExitoso();
    } catch (error) {
        console.error(error);
        if ([401, 403, 404].includes(error.status)) localStorage.removeItem("access_token");
        mostrarPantallaInicioSesion();
        alert(mensajeErrorAmigable(error, "No fue posible restaurar la sesión."));
    }
}

function mostrarCompraExitosa(purchase) {
    document.getElementById("success-screen-title").textContent = "Pago confirmado";
    document.getElementById("success-screen-subtitle").textContent = "Tu código de acceso está listo.";
    document.getElementById("purchase-plan-name").textContent = purchase.plan;
    document.getElementById("purchase-pin").textContent = purchase.pin;
    document.getElementById("purchase-duration").textContent = `${purchase.duration_minutes} min`;
    document.getElementById("purchase-expires-at").textContent = new Date(purchase.expires_at).toLocaleString("es-MX");
    document.getElementById("purchase-success-details").classList.remove("hidden");
    activarConexionExitoso(purchase.duration_minutes * 60);
}

function mostrarCompraPendiente(checkout, plan) {

    if (timerInterval) clearInterval(timerInterval);

    document.getElementById("success-screen-title").textContent =
        "Esperando confirmación del pago";

    document.getElementById("success-screen-subtitle").textContent =
        "Mercado Pago se abrió en una nueva pestaña. Completa el pago y vuelve a esta ventana.";

    document.getElementById("guest-purchase-plan").textContent =
        plan?.name || "Plan seleccionado";

    document.getElementById("guest-purchase-amount").textContent =
        `$${
            Number(plan?.price || 0).toLocaleString("es-MX")
        } MXN`;
const checkoutButton = document.querySelector("[data-mercadopago-checkout]");

        if (checkoutButton) {
        checkoutButton.dataset.checkoutUrl = checkout.checkout_url;
        }

    document.getElementById("purchase-success-details")
        .classList.add("hidden");

    document.getElementById("connection-timer")
        .classList.add("hidden");

    document.getElementById("guest-purchase-details")
        .classList.remove("hidden");

    document.getElementById("contenedor-portal")
        .classList.add("hidden");

    const finalScreen =
        document.getElementById("pantalla-final");

    finalScreen.classList.remove("hidden");
    finalScreen.style.display = "flex";

    
}
