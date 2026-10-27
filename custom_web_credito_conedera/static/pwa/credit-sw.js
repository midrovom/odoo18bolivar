/* Portal de crédito - service worker sin cache de expedientes ni adjuntos.
   Se utiliza solo en /my/credito y nunca se almacena información del usuario. */
'use strict';
const OFFLINE_PAGE = `<!doctype html><html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sin conexión · Crédito</title><style>
body{margin:0;background:#f8eded;color:#472525;font:16px system-ui,sans-serif}
main{max-width:420px;margin:15vh auto;padding:28px;background:white;border-radius:16px}
a{color:#8f2f2f;font-weight:700}</style></head><body><main>
<h1>Sin conexión</h1><p>Para consultar o enviar solicitudes se necesita internet. Revisa tu conexión e inténtalo de nuevo.</p>
<a href="/my/credito/historial">Volver a intentar</a></main></body></html>`;
self.addEventListener('install', function () { self.skipWaiting(); });
self.addEventListener('activate', function (event) { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', function (event) {
    // Únicamente navegación del portal: no cachear páginas privadas ni documentos.
    if (event.request.mode !== 'navigate' || event.request.method !== 'GET') { return; }
    const address = new URL(event.request.url);
    if (address.origin !== self.location.origin || !address.pathname.startsWith('/my/credito/')) { return; }
    event.respondWith(fetch(event.request).catch(function () {
        return new Response(OFFLINE_PAGE, {status: 503, statusText: 'Offline',
            headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}});
    }));
});
