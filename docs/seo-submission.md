# SEO — submitir SkilTak a buscadores

Guía operativa para que el sitio aparezca en Google y Bing/DuckDuckGo
después del deploy a producción. Es proceso de una sola vez por dominio.

Pre-requisitos:

- El dominio `skiltak.com` resuelve a tu VPS y `https://skiltak.com`
  responde 200 con el landing.
- `https://skiltak.com/robots.txt` se sirve y muestra el contenido del
  archivo (no un 404 ni el index.html del SPA).
- `https://skiltak.com/sitemap.xml` se sirve y devuelve el XML válido.
- Acceso al panel DNS del dominio (Hostinger en nuestro caso) para
  poder crear registros TXT.

Si alguno de esos no responde, frená acá y arreglá nginx/DNS primero.

---

## Google Search Console (GSC)

1. Entrá a https://search.google.com/search-console con la cuenta de
   Google del proyecto.

2. Click en "Add property" → elegí "**Domain**" (no "URL prefix").
   - Property: `skiltak.com`
   - Cubre `http`, `https`, `www.` y subdominios de un solo plumazo. Es
     mejor que la opción "URL prefix" si querés ambos `skiltak.com` y
     `www.skiltak.com` bajo la misma vista.

3. Google te muestra un **DNS TXT record** del tipo
   `google-site-verification=XXXXXXXXXX`. Copialo.

4. Andá al panel DNS de Hostinger → DNS → agregar registro:
   - Type: `TXT`
   - Name: `@` (raíz del dominio)
   - Value: `google-site-verification=XXXXXXXXXX` (pegá literal)
   - TTL: 3600 (default está bien)

5. Esperá entre 5 y 30 minutos para que propague. Después en GSC click
   "Verify". Si tira error de "Record not found" después de 30 min,
   chequeá con `nslookup -type=TXT skiltak.com` que el TXT esté.

6. Una vez verificado, en GSC menú izquierdo → **Sitemaps** → "Add a
   new sitemap" → escribí `sitemap.xml` (Google la prefijea sola con
   el dominio). Submit.

7. GSC va a leer el sitemap en ~24h y empezar a crawlear las URLs.
   Volvé al día siguiente a "Pages" para ver qué indexó y qué no.

### Cosas a watchear en GSC

- **Pages → "Why pages aren't indexed"**: errores comunes:
  - "Soft 404" — Google llegó a la URL pero recibió contenido vacío
    (típico de SPA sin SSR cuando crawler no ejecuta JS). En nuestro
    caso el landing tiene meta tags + JSON-LD en `index.html`
    directo, así que debería indexar bien.
  - "Page with redirect" — alguna URL del sitemap redirige. Si Google
    se queja, revisá la URL.
  - "Discovered, not indexed" — Google la ve pero todavía no la
    crawleó. Normal en sitios nuevos, pasa a indexada en días.

- **URL Inspection** (lupa arriba): pegá una URL y "Test live URL"
  para ver qué renderiza Google. Útil para diagnosticar SEO de
  páginas individuales.

---

## Bing Webmaster Tools

Bing y DuckDuckGo comparten índice — verificar acá cubre los dos.

1. Entrá a https://www.bing.com/webmasters con cuenta Microsoft.

2. "Add a site" → ingresá `https://skiltak.com`.

3. Bing tiene atajo: si ya verificaste en GSC, click "**Import from
   Google Search Console**" — se conecta vía OAuth y trae todo
   automático. Es la ruta más rápida.

4. Si preferís verificar manual:
   - Opción A: HTML file. Bing te da un `BingSiteAuth.xml`. Tirá ese
     archivo en `public/` (queda accesible en
     `https://skiltak.com/BingSiteAuth.xml`) y click verify.
   - Opción B: DNS TXT. Misma idea que Google pero con valor
     `MS=XXXXXXXX`.

5. Una vez verificado, en el panel → **Sitemaps** → "Submit sitemap" →
   pegá `https://skiltak.com/sitemap.xml`.

---

## Otros buscadores (opcional)

- **DuckDuckGo**: no tiene panel propio. Usa el índice de Bing más
  fuentes propias. Con Bing verified ya estás cubierto.

- **Yandex** (relevante si apuntás a tráfico ruso/europa este):
  https://webmaster.yandex.com/sites/add/ — mismo flujo de verificación
  TXT + sitemap.

- **Baidu** (China): https://ziyuan.baidu.com — requiere ID chino para
  registrarse, normalmente no vale la pena para LatAm.

---

## Después de submitir

### Día 1-3
Google va a empezar a aparecer en logs de nginx con
`User-Agent: Googlebot`. Si nginx no loggea accesos, podés correr
`tail -f /var/log/nginx/access.log | grep -i googlebot` durante un rato.

### Semana 1
- En GSC → Performance: empezás a ver clicks/impresiones reales.
- En GSC → Pages: ver el conteo de páginas indexadas. Esperable 4-5
  inicialmente (las del sitemap).

### Mes 1
- Si después de 4 semanas no hay indexación de páginas obvias,
  posibles causas:
  1. `robots.txt` está bloqueando sin querer — verificá en GSC →
     Settings → "robots.txt Tester" qué interpreta Google.
  2. El SPA no muestra contenido a Googlebot — usá "URL Inspection"
     → "Test live URL" para ver qué HTML recibe Google. Si está
     vacío excepto por `<app-root></app-root>`, hay que migrar a SSR
     (Angular Universal).

---

## SEO contenido futuro

Cuando tengamos secciones públicas adicionales (`/blog`, `/recursos`),
hay que:

1. Agregar las URLs al `public/sitemap.xml` con la prioridad
   correspondiente.
2. Si el contenido es renderizado client-side y necesita ranqueo en
   Google → considerar SSR con `ng add @angular/ssr`.
3. Para páginas de detalle de oferta (`/jobs/:id`), no son URLs
   estables (la oferta caduca) — mejor NO indexarlas. Ya están en
   `Disallow` del robots.txt.

---

## Referencia rápida de archivos relevantes

| Archivo | Para qué |
|---|---|
| `frontend/src/index.html` | Meta tags, Open Graph, JSON-LD |
| `frontend/public/robots.txt` | Reglas para crawlers |
| `frontend/public/sitemap.xml` | Lista de URLs públicas para indexar |
| `deploy/nginx/skiltak.com.conf` | Sirve los 3 archivos anteriores en `/` |

Para regenerar el sitemap programáticamente más adelante (cuando el
contenido sea dinámico) lo más simple es un management command Django
que escupa el XML a `public/` antes del build de frontend.
