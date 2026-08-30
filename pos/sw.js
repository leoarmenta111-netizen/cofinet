const CACHE_NAME = "cofi-pos-shell-v9";

const APP_SHELL = [
    "./index.html",
    "./css/pos.css?v=8",
    "./js/uuid.js?v=8",
    "./js/db.js?v=8",
    "./js/api.js?v=8",
    "./js/catalog.js?v=8",
    "./js/sync.js?v=8",
    "./js/app.js?v=8",
    "./js/orders-local.js?v=1",
    "./js/orders.js?v=11",
    "./manifest.webmanifest"
];


/* =========================================================
   INSTALL
   ========================================================= */

self.addEventListener("install", event => {
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
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
                            key.startsWith("cofi-pos-shell-") &&
                            key !== CACHE_NAME
                        )
                        .map(key => caches.delete(key))
                )
            )
            .then(() => self.clients.claim())
    );
});


/* =========================================================
   FETCH
   ========================================================= */

self.addEventListener("fetch", event => {
    const request = event.request;
    const url = new URL(request.url);

    // API must never be fulfilled by application-shell cache.
    if (url.pathname.startsWith("/api/")) {
        return;
    }

    // Navigation:
    // network first, cached POS shell when offline.
    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request)
                .catch(() =>
                    caches.match("./index.html")
                )
        );

        return;
    }

    // POS static assets.
    if (
        url.origin === self.location.origin &&
        url.pathname.startsWith("/pos/")
    ) {
        event.respondWith(
            caches.match(request)
                .then(cached => {
                    if (cached) {
                        return cached;
                    }

                    // Defensive fallback for query-string
                    // differences between versioned shell URLs.
                    return caches.match(
                        request,
                        { ignoreSearch: true }
                    );
                })
                .then(cached => {
                    if (cached) {
                        return cached;
                    }

                    return fetch(request)
                        .then(response => {
                            if (
                                !response ||
                                response.status !== 200
                            ) {
                                return response;
                            }

                            const copy =
                                response.clone();

                            caches
                                .open(CACHE_NAME)
                                .then(cache =>
                                    cache.put(
                                        request,
                                        copy
                                    )
                                );

                            return response;
                        });
                })
        );
    }
});
