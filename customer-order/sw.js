const SHELL_CACHE = "cofi-customer-kiosk-v3";

const APP_SHELL = [
    "./index.html",
    "./css/customer-order.css?v=5",
    "./js/api.js?v=1",
    "./js/cart.js?v=2",
    "./js/checkout.js?v=1",
    "./js/app.js?v=3",
    "./js/pwa.js?v=1",
    "./assets/coficenter-hero-combo.png",
    "./manifest-ixtapa.webmanifest",
    "/pos/assets/coficenter-logo.png",
    "/pos/assets/pwa/icon-192.png",
    "/pos/assets/pwa/icon-512.png",
    "/pos/assets/pwa/icon-maskable-512.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(SHELL_CACHE)
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

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys()
            .then(keys =>
                Promise.all(
                    keys
                        .filter(
                            key =>
                                key.startsWith(
                                    "cofi-customer-kiosk-"
                                ) &&
                                key !== SHELL_CACHE
                        )
                        .map(key => caches.delete(key))
                )
            )
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", event => {
    const request = event.request;

    if (request.method !== "GET") {
        return;
    }

    const url = new URL(request.url);

    if (url.origin !== self.location.origin) {
        return;
    }

    if (
        url.pathname.startsWith("/api/") ||
        url.pathname.startsWith("/media/pos-products/")
    ) {
        return;
    }

    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request)
                .then(async response => {
                    const cache =
                        await caches.open(SHELL_CACHE);

                    await cache.put(
                        "./index.html",
                        response.clone()
                    );

                    return response;
                })
                .catch(() =>
                    caches.match(
                        "./index.html",
                        {
                            ignoreSearch: true
                        }
                    )
                )
        );

        return;
    }

    event.respondWith(
        caches.match(request)
            .then(cached => {
                if (cached) {
                    return cached;
                }

                return fetch(request)
                    .then(async response => {
                        if (
                            response &&
                            response.ok
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
                    });
            })
    );
});
