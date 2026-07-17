window.tailwind = window.tailwind || {};

window.tailwind.config = {
    theme: {
        extend: {
            colors: {
                cofiDark: "#0D0D0D",
                cofiCard: "#161616",
                cofiOlive: "#A3A375",
                cofiOliveHover: "#8C8C5E"
            },
            fontFamily: {
                sans: ["Inter", "sans-serif"],
                grotesk: ["Space Grotesk", "sans-serif"],
                outfit: ["Outfit", "sans-serif"]
            }
        }
    }
};

/* ==========================================================
   COFINET+
   APP.JS
   Navegación General
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    enlazarControlesApp();

    iniciarPortal();

});


/* ==========================================================
   INICIALIZACIÓN
========================================================== */

function iniciarPortal(){

    cambiarVistaDesktop("inicio");

    crearIconosLucide();

    if(typeof cargarPlanes === "function"){

        cargarPlanes();

    }

    if(typeof restaurarSesion === "function"){

        restaurarSesion();

    }

}

function crearIconosLucide(){

    if(window.lucide && typeof window.lucide.createIcons==="function"){

        window.lucide.createIcons();

    }

}


/* ==========================================================
   NAVEGACIÓN DESKTOP
========================================================== */

function cambiarVistaDesktop(vistaId){

    const vistas=[
        "inicio",
        "membresia",
        "comprar",
        "codigo"
    ];

    vistas.forEach(v=>{

        const vista=document.getElementById("desktop-"+v);

        if(!vista) return;

        vista.classList.add("hidden");

        vista.classList.remove("grid");
        vista.classList.remove("block");

    });

    const activa=document.getElementById("desktop-"+vistaId);

    if(!activa) return;

    activa.classList.remove("hidden");

    if(vistaId==="inicio"){

        activa.classList.add("grid");

    }else{

        activa.classList.add("block");

    }

    controlarFooter(vistaId);

}


/* ==========================================================
   FOOTER
========================================================== */

function controlarFooter(vista){

    const footer=document.getElementById("seccion-membresias-footer");

    if(!footer) return;

    if(vista==="inicio"){

        footer.classList.remove("hidden");

    }else{

        footer.classList.add("hidden");

    }

}


/* ==========================================================
   ACORDEÓN MÓVIL
========================================================== */

function toggleAcordion(tipo){

    const acordeones=[
        "membresia",
        "comprar",
        "codigo"
    ];

    acordeones.forEach(nombre=>{

        const contenido=document.getElementById("content-acordion-"+nombre);

        const icono=document.getElementById("icon-acordion-"+nombre);

        if(!contenido) return;

        if(nombre===tipo){

            const abierto=contenido.classList.contains("expanded");

            if(abierto){

                contenido.classList.remove("expanded");

                if(icono) icono.style.transform="rotate(0deg)";

            }else{

                contenido.classList.add("expanded");

                if(icono) icono.style.transform="rotate(90deg)";

            }

        }else{

            contenido.classList.remove("expanded");

            if(icono) icono.style.transform="rotate(0deg)";

        }

    });

}


/* ==========================================================
   UTILIDADES
========================================================== */

function mostrar(id){

    const el=document.getElementById(id);

    if(el){

        el.classList.remove("hidden");

    }

}

function ocultar(id){

    const el=document.getElementById(id);

    if(el){

        el.classList.add("hidden");

    }

}

function togglePasswordDesktop(){

    const input=document.getElementById("membresia-clave-desktop");
    const icono=document.getElementById("eyeDesktop");

    if(!input) return;

    const mostrar=input.type==="password";

    input.type=mostrar ? "text" : "password";

    if(icono){

        icono.setAttribute("data-lucide", mostrar ? "eye-off" : "eye");
        crearIconosLucide();

    }

}

function enlazarControlesApp(){

    document.querySelectorAll("[data-accordion-toggle]").forEach(control=>{

        control.addEventListener("click", ()=>{

            const tipo=control.dataset.accordionToggle || null;
            toggleAcordion(tipo);

        });

    });

    document.querySelectorAll("[data-desktop-view]").forEach(control=>{

        control.addEventListener("click", ()=>{

            cambiarVistaDesktop(control.dataset.desktopView);

        });

    });

    document.querySelectorAll("[data-password-toggle='desktop']").forEach(control=>{

        control.addEventListener("click", ()=>{

            togglePasswordDesktop();

        });

    });

}
