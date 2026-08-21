const CACHE_NAME =
    "cofi-pos-shell-v4";

const APP_SHELL = [
    "./",
    "./index.html",
    "./css/pos.css",
    "./js/uuid.js",
    "./js/db.js",
    "./js/api.js",
    "./js/catalog.js",
    "./js/sync.js",
    "./js/app.js",
    "./manifest.webmanifest"
];

self.addEventListener(
    "install",
    event => {
        event.waitUntil(
            caches
                .open(CACHE_NAME)
                .then(cache =>
                    cache.addAll(APP_SHELL)
                )
                .then(() =>
                    self.skipWaiting()
                )
        );
    }
);

self.addEventListener(
    "activate",
    event => {
        event.waitUntil(
            caches
                .keys()
                .then(keys =>
                    Promise.all(
                        keys
                            .filter(
                                key =>
                                    key !== CACHE_NAME
                            )
                            .map(
                                key =>
                                    caches.delete(key)
                            )
                    )
                )
                .then(() =>
                    self.clients.claim()
                )
        );
    }
);

self.addEventListener(
    "fetch",
    event => {
        const request =
            event.request;

        const url =
            new URL(request.url);

        if (
            url.pathname.startsWith(
                "/api/"
            )
        ) {
            return;
        }

        if (
            request.mode ===
            "navigate"
        ) {
            event.respondWith(
                fetch(request)
                    .catch(() =>
                        caches.match(
                            "./index.html"
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
                        .then(response => {
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
);
