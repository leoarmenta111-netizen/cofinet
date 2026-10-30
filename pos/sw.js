const SHELL_CACHE = "cofi-pos-shell-v26";
const IMAGE_CACHE = "cofi-pos-images-v1";

const APP_SHELL = [
    "./index.html",
    "./css/pos.css?v=28",
    "./css/receipt.css",
    "./js/uuid.js",
    "./js/db.js",
    "./js/api.js",
    "./js/staff-session.js",
    "./js/cash-shift.js?v=2",
    "./js/catalog.js",
    "./js/sync.js",
    "./js/folio.js",
    "./js/receipt-core.js?v=2",
    "./js/receipt-renderer.js?v=2",
    "./js/app.js?v=26",
    "./js/orders-local.js",
    "./js/sound-alerts.js",
    "./js/orders.js?v=18",
    "./assets/coficenter-logo.png",
    "./assets/pwa/icon-192.png",
    "./assets/pwa/icon-512.png",
    "./assets/pwa/icon-maskable-512.png",
    "./manifest.webmanifest",
    "./manifest-nuevo-vallarta.webmanifest",
    "./manifest-bucerias.webmanifest",
    "./manifest-ixtapa.webmanifest"
];


/* =========================================================
   INSTALL
   ========================================================= */

self.addEventListener("install", event => {
    event.waitUntil(
        caches
            .open(SHELL_CACHE)
            .then(cache =>
                Promise.all(
                    APP_SHELL.map(async url => {
                        try {
                            await cache.add(url);
                        } catch (error) {
                            console.warn(
                                "No se pudo precachear:",
                                url
                            );
                        }
                    })
                )
            )
            .then(() => self.skipWaiting())
    );
});


/* =========================================================
   ACTIVATE
   ========================================================= */

self.addEventListener("activate", event => {
    event.waitUntil(
        caches
            .keys()
            .then(keys =>
                Promise.all(
                    keys
                        .filter(key =>
                            (
                                key.startsWith(
                                    "cofi-pos-shell-"
                                ) &&
                                key !== SHELL_CACHE
                            )
                        )
                        .map(key =>
                            caches.delete(key)
                        )
                )
            )
            .then(() =>
                self.clients.claim()
            )
    );
});


/* =========================================================
   NAVIGATION
   ========================================================= */

async function navigationResponse(request) {
    const controller =
        new AbortController();

    const timeout =
        setTimeout(
            () => controller.abort(),
            4000
        );

    try {
        const response =
            await fetch(
                request,
                {
                    signal:
                        controller.signal
                }
            );

        clearTimeout(timeout);

        if (
            response &&
            response.ok
        ) {
            const cache =
                await caches.open(
                    SHELL_CACHE
                );

            await cache.put(
                "./index.html",
                response.clone()
            );
        }

        return response;

    } catch (error) {
        clearTimeout(timeout);

        const cached =
            await caches.match(
                "./index.html",
                {
                    ignoreSearch: true
                }
            );

        if (cached) {
            return cached;
        }

        return new Response(
            `
            <!doctype html>
            <html lang="es">
            <head>
                <meta charset="utf-8">
                <meta
                    name="viewport"
                    content="width=device-width,initial-scale=1"
                >
                <title>Cofi POS</title>
            </head>
            <body>
                <h1>Cofi POS</h1>
                <p>
                    No hay conexión y todavía no existe
                    una copia local del sistema.
                </p>
            </body>
            </html>
            `,
            {
                status: 503,
                headers: {
                    "Content-Type":
                        "text/html; charset=utf-8"
                }
            }
        );
    }
}


/* =========================================================
   STATIC POS ASSETS
   ========================================================= */

async function staticAssetResponse(request) {
    const exact =
        await caches.match(request);

    if (exact) {
        return exact;
    }

    try {
        const response =
            await fetch(request);

        if (
            response &&
            response.status === 200
        ) {
            const cache =
                await caches.open(
                    SHELL_CACHE
                );

            await cache.put(
                request,
                response.clone()
            );
        }

        return response;

    } catch (error) {
        return (
            await caches.match(
                request,
                {
                    ignoreSearch: true
                }
            )
        ) || Response.error();
    }
}


/* =========================================================
   PRODUCT IMAGES
   ========================================================= */

async function productImageResponse(request) {
    const cache =
        await caches.open(
            IMAGE_CACHE
        );

    const cached =
        await cache.match(request);

    if (cached) {
        return cached;
    }

    try {
        const response =
            await fetch(request);

        if (
            response &&
            response.ok
        ) {
            await cache.put(
                request,
                response.clone()
            );
        }

        return response;

    } catch (error) {
        return (
            await cache.match(
                request,
                {
                    ignoreSearch: true
                }
            )
        ) || Response.error();
    }
}


/* =========================================================
   FETCH
   ========================================================= */

self.addEventListener("fetch", event => {
    const request =
        event.request;

    if (
        request.method !== "GET"
    ) {
        return;
    }

    const url =
        new URL(
            request.url
        );

    /*
     * API:
     * nunca usar cache del Service Worker.
     * IndexedDB maneja catálogo y ventas offline.
     */
    if (
        url.pathname.startsWith(
            "/api/"
        )
    ) {
        return;
    }

    /*
     * Navegación:
     * red primero; shell local si no hay Internet.
     */
    if (
        request.mode === "navigate"
    ) {
        event.respondWith(
            navigationResponse(request)
        );

        return;
    }

    /*
     * Fotos de productos.
     */
    if (
        url.origin ===
            self.location.origin &&
        url.pathname.startsWith(
            "/media/pos-products/"
        )
    ) {
        event.respondWith(
            productImageResponse(
                request
            )
        );

        return;
    }

    /*
     * Archivos propios del POS.
     */
    if (
        url.origin ===
            self.location.origin &&
        url.pathname.startsWith(
            "/pos/"
        )
    ) {
        event.respondWith(
            staticAssetResponse(
                request
            )
        );
    }
});


/* =========================================================
   CACHE PRODUCT IMAGES ON DEMAND
   ========================================================= */

self.addEventListener(
    "message",
    event => {
        if (
            event.data?.type !==
            "CACHE_PRODUCT_IMAGES"
        ) {
            return;
        }

        const urls =
            Array.isArray(
                event.data.urls
            )
                ? event.data.urls
                : [];

        event.waitUntil(
            caches
                .open(IMAGE_CACHE)
                .then(async cache => {
                    for (
                        const url
                        of urls
                    ) {
                        try {
                            const request =
                                new Request(
                                    url,
                                    {
                                        mode:
                                            "same-origin"
                                    }
                                );

                            const existing =
                                await cache.match(
                                    request
                                );

                            if (existing) {
                                continue;
                            }

                            const response =
                                await fetch(
                                    request
                                );

                            if (
                                response.ok
                            ) {
                                await cache.put(
                                    request,
                                    response.clone()
                                );
                            }

                        } catch (error) {
                            console.warn(
                                "No se pudo cachear imagen:",
                                url
                            );
                        }
                    }
                })
        );
    }
);
