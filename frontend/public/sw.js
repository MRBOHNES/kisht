// Keeps the officer app openable without network. Network first, so a working connection
// always gets fresh pages; the cached copy is only used offline. API data is never cached here.
const CACHE = "kisht-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request, { ignoreVary: true });
        if (cached) return cached;
        if (request.mode === "navigate") return offlinePage();
        return Response.error();
      }),
  );
});

function offlinePage() {
  const html = `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<body style="font-family:sans-serif;padding:24px;background:#F5F6F8;color:#101828">
<p>ऑफ़लाइन — यह पेज अभी फ़ोन पर नहीं है।</p><p>Offline: this page is not saved on the phone yet.</p>
<p><a href="/today" style="color:#1F5FD6">आज की सूची / Today's list</a></p></body>`;
  return new Response(html, { headers: { "content-type": "text/html; charset=utf-8" } });
}
