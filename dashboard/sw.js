/**
 * SurakshaEdge Service Worker — v0.4.0
 * Provides offline splash, caches dashboard shell.
 * Network-first strategy: always tries live API, falls back to cache.
 */

const CACHE_NAME = 'surakshaedge-v0.4.0';

// Shell assets to pre-cache on install
const SHELL_ASSETS = ['/'];

// Offline fallback HTML
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SurakshaEdge — Offline</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0f1117;
      color: #e2e8f0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-family: 'Segoe UI', system-ui, sans-serif;
      text-align: center;
      gap: 20px;
    }
    .shield { font-size: 72px; }
    h1 { font-size: 1.8rem; color: #3b82f6; }
    p { color: #94a3b8; font-size: 1rem; max-width: 400px; line-height: 1.6; }
    .badge {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px 20px;
      font-size: 0.85rem;
      color: #64748b;
      margin-top: 10px;
    }
    .dot { width: 10px; height: 10px; background: #f59e0b; border-radius: 50%; display: inline-block; margin-right: 6px; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  </style>
</head>
<body>
  <div class="shield">🛡</div>
  <h1>SurakshaEdge</h1>
  <p>You are currently offline. The dashboard will reconnect automatically when your network is restored.</p>
  <div class="badge"><span class="dot"></span>Waiting for connection… | SEVA FIRST 2026 | REG-008-OP-024</div>
</body>
</html>`;

// ── Install: pre-cache shell ──────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(SHELL_ASSETS).catch(() => {
        // Non-fatal: might fail when offline during install
      });
    })
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch: network-first with offline fallback ────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip: non-GET, cross-origin tile requests (map tiles), WebSocket
  if (request.method !== 'GET') return;
  if (url.hostname.includes('openstreetmap') || url.hostname.includes('arcgisonline')) return;
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  // API calls: network only, no cache
  if (url.pathname.startsWith('/events') ||
      url.pathname.startsWith('/health') ||
      url.pathname.startsWith('/metrics') ||
      url.pathname.startsWith('/ws')) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful HTML/JS/CSS responses
        if (response.ok && ['text/html', 'text/javascript', 'text/css', 'application/javascript'].some(
          (t) => (response.headers.get('content-type') || '').includes(t)
        )) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(async () => {
        // Try cache
        const cached = await caches.match(request);
        if (cached) return cached;
        // Final fallback: offline page for navigation requests
        if (request.mode === 'navigate') {
          return new Response(OFFLINE_HTML, {
            headers: { 'Content-Type': 'text/html' },
          });
        }
      })
  );
});
