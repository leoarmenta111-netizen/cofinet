(() => {
    if (!("serviceWorker" in navigator)) {
        return;
    }

    window.addEventListener("load", () => {
        navigator.serviceWorker
            .register("./sw.js", {
                scope: "./"
            })
            .then(registration => {
                console.log(
                    "CofiCenter Kiosk PWA activa:",
                    registration.scope
                );
            })
            .catch(error => {
                console.error(
                    "No se pudo registrar la PWA:",
                    error
                );
            });
    });
})();
