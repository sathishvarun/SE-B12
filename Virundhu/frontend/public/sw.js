// Minimal service worker so owners can install Virundhu on their phone's home screen.
// It never caches API answers or reviews: everything still comes fresh from the server.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
