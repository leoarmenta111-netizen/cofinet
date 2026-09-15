const CACHE_PREFIX =
    "cofi-kds-kitchen-shell-";

const SHELL_CACHE =
    "cofi-kds-kitchen-shell-v3";

const STATION_PATH =
    "/pos/kitchen/";

const APP_SHELL = [
    "./",
    "./index.html",
    "./manifest.webmanifest?v=1",
    "./manifest-nuevo-vallarta.webmanifest?v=1",
    "./manifest-bucerias.webmanifest?v=1",
    "./manifest-ixtapa.webmanifest?v=1",
    "../css/station.css?v=2",
    "../js/api.js?v=11",
    "../js/sound-alerts.js?v=1",
    "../js/station.js?v=3",
    "../assets/coficenter-logo.png",
    "../assets/pwa/icon-192.png",
    "../assets/pwa/icon-512.png",
    "../assets/pwa/icon-maskable-512.png",
];

const STATIC_PATHS = new Set([
    "/pos/css/station.css",
    "/pos/js/api.js",
    "/pos/js/sound-alerts.js",
    "/pos/js/station.js",
    "/pos/assets/coficenter-logo.png",
    "/pos/assets/pwa/icon-192.png",
    "/pos/assets/pwa/icon-512.png",
    "/pos/assets/pwa/icon-maskable-512.png",
    `${STATION_PATH}manifest.webmanifest`,
    `${STATION_PATH}manifest-nuevo-vallarta.webmanifest`,
    `${STATION_PATH}manifest-bucerias.webmanifest`,
    `${STATION_PATH}manifest-ixtapa.webmanifest`,
]);

self.addEventListener(
    "install",
    event => {
        event.waitUntil(
            caches
                .open(SHELL_CACHE)
                .then(
                    cache =>
                        cache.addAll(APP_SHELL)
                )
                .then(
                    () => self.skipWaiting()
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
                .then(
                    keys =>
                        Promise.all(
                            keys
                                .filter(
                                    key =>
                                        key.startsWith(
                                            CACHE_PREFIX
                                        )
                                        && key !==
                                            SHELL_CACHE
                                )
                                .map(
                                    key =>
                                        caches.delete(
                                            key
                                        )
                                )
                        )
                )
                .then(
                    () => self.clients.claim()
                )
        );
    }
);

self.addEventListener(
    "fetch",
    event => {
        const request =
            event.request;

        if (
            request.method !== "GET"
        ) {
            return;
        }

        const url =
            new URL(request.url);

        if (
            url.origin !==
            self.location.origin
        ) {
            return;
        }

        const isStationNavigation =
            request.mode === "navigate"
            && (
                url.pathname ===
                    STATION_PATH
                || url.pathname ===
                    `${STATION_PATH}index.html`
            );

        const isStaticAsset =
            STATIC_PATHS.has(
                url.pathname
            );

        /*
         * Important:
         * API/order traffic falls through untouched.
         */
        if (
            !isStationNavigation
            && !isStaticAsset
        ) {
            return;
        }

        if (
            isStationNavigation
        ) {
            event.respondWith(
                fetch(request)
                    .then(
                        async response => {
                            if (
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
                        }
                    )
                    .catch(
                        async () =>
                            (
                                await caches.match(
                                    "./index.html"
                                )
                            )
                            || Response.error()
                    )
            );

            return;
        }

        event.respondWith(
            caches
                .match(
                    request,
                    {
                        ignoreSearch: true,
                    }
                )
                .then(
                    cached => {
                        if (cached) {
                            return cached;
                        }

                        return fetch(request)
                            .then(
                                async response => {
                                    if (
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
                                }
                            );
                    }
                )
        );
    }
);
