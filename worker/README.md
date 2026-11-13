# Backend del tauler veïnal (Cloudflare Worker)

## Arquitectura

- Un **Cloudflare Worker** (`src/index.js`) en `*.workers.dev` sirve la API JSON que usa `static/board.js` y las páginas mínimas de confirmar/gestionar/moderar. No toca el DNS del sitio.
- **D1** (SQLite, `schema.sql`) guarda anuncios, denuncias, cubos de límite y baneos. Nunca se publica el email ni la IP: solo hashes con sal.
- **Turnstile** protege crear, responder y denunciar. **Gmail API** (OAuth2, `src/mail.js`) envía los correos: confirmación con doble opt-in, relevo de respuestas (el email del lector va solo en `Reply-To`), avisos de caducidad y de ocultación.
- Un **cron** diario (03:17 UTC) caduca anuncios a los 45 días, purga pendientes/borrados y avisa 5 días antes de caducar.
- Moderación: filtro de palabras y estafas (`src/filter.js`), límites por IP/email, ocultación automática con 3 denuncias de IPs distintas y página `/admin?key=`.
- Todo cabe en los planes gratuitos (Workers 100 000 peticiones/día, D1 5 GB, Gmail ≈ 500 correos/día; el worker se autolimita a 300).

## Instalación (una sola vez)

Requisitos: Node ≥ 20 (`npx`), Python ≥ 3.12, una cuenta de Cloudflare y una cuenta de Gmail para enviar.

1. **Cloudflare**: crea la cuenta gratuita y, desde `worker/`, inicia sesión:
   ```bash
   npx wrangler login
   ```
2. **Base de datos D1**:
   ```bash
   npx wrangler d1 create cerdanyola-board
   ```
   Copia el `database_id` que imprime en `wrangler.toml` (sustituye `PON_AQUI_EL_ID`) y crea las tablas:
   ```bash
   npx wrangler d1 execute cerdanyola-board --remote --file=schema.sql
   ```
3. **Turnstile**: en el panel de Cloudflare → Turnstile → *Add widget*. Modo *Managed*, hostnames `cerdanyola.horaverda.es` y `localhost`. Apunta la *site key* (va al cliente) y la *secret key* (va al worker).
4. **Gmail API** (Google Cloud Console, gratis):
   1. Crea un proyecto y activa *Gmail API* (APIs y servicios → Biblioteca).
   2. *Pantalla de consentimiento OAuth*: tipo **Externo**, rellena nombre y correo, añade el scope `https://www.googleapis.com/auth/gmail.send` y **publica la app** (*Publishing status: In production*; no hace falta verificación para uso propio, aunque Google avise). Si la dejas en *Testing* el refresh token caduca a los 7 días.
   3. *Credenciales* → *Crear credenciales* → *ID de cliente OAuth* → tipo **Aplicación de escritorio**. Copia el client id y el client secret.
   4. Obtén el refresh token (abre el navegador; autoriza con la cuenta Gmail que enviará):
      ```bash
      python tools/gmail_token.py CLIENT_ID CLIENT_SECRET
      ```
5. **Secretos** del worker (cada comando pide el valor por teclado):
   ```bash
   npx wrangler secret put TURNSTILE_SECRET
   ```
   ```bash
   npx wrangler secret put GMAIL_CLIENT_ID
   ```
   ```bash
   npx wrangler secret put GMAIL_CLIENT_SECRET
   ```
   ```bash
   npx wrangler secret put GMAIL_REFRESH_TOKEN
   ```
   ```bash
   npx wrangler secret put GMAIL_FROM
   ```
   ```bash
   npx wrangler secret put ADMIN_KEY
   ```
   ```bash
   npx wrangler secret put ADMIN_EMAIL
   ```
   ```bash
   npx wrangler secret put IP_SALT
   ```
   `ADMIN_KEY` e `IP_SALT`: cadenas aleatorias largas (p. ej. `python -c "import secrets;print(secrets.token_urlsafe(32))"`). `IP_SALT` no debe cambiar después: de ella dependen los baneos y los enlaces de gestión de los correos.
6. **Desplegar**:
   ```bash
   npx wrangler deploy
   ```
   Copia la URL `https://cerdanyola-board.<subdominio>.workers.dev` que imprime en `API_URL` de `wrangler.toml` (vuelve a desplegar) y en `board_api_url` de `config.json`; pon la *site key* de Turnstile en `turnstile_site_key` de `config.json`.
7. Comprueba `https://…workers.dev/health` → `{"ok":true}` y `/posts` → `{"posts":[],…}`.

## Probar en local

```bash
npx wrangler d1 execute cerdanyola-board --local --file=schema.sql
```
Copia `.dev.vars.example` a `.dev.vars` (ya está en `.gitignore`): lleva las claves de prueba de Turnstile y `MAIL_DRY_RUN=1`, con lo que los correos no se envían sino que se imprimen en la consola de `wrangler dev` (el cuerpo va en base64; el enlace de confirmación está dentro). Si quieres correos reales, pon las credenciales de Gmail y quita `MAIL_DRY_RUN`. Luego:
```bash
npx wrangler dev
```
La API queda en `http://localhost:8787`; el sitio estático en `http://localhost:8001` está en `ALLOWED_ORIGINS`. Para probar la página con el worker local, pon en `config.json` `board_api_url` = `http://localhost:8787` y `turnstile_site_key` = `1x00000000000000000000AA` (sin commitear) y regenera con `python src/build.py --offline`. Para ejecutar el cron a mano:
```bash
curl "http://127.0.0.1:8787/cdn-cgi/local/scheduled"
```
Tests sin red (desde la raíz del repo):
```bash
node --test worker/test
```

## API (resumen)

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /posts` | – | `{posts:[…], generated}`; caché 5 min; CORS `*` |
| `POST /posts` | `{cat,lang,title,body,name,email,contact?,price?,consent:true,turnstile}` | `201 {ok:true}` y correo de confirmación |
| `GET /confirm?id&t` | – | HTML; publica el anuncio y redirige al tablón |
| `GET /manage?id&t` | – | HTML con botones renovar (`POST /renew`) y borrar (`POST /delete`) |
| `POST /reply` | `{id,email,message,turnstile}` | `200 {ok:true}`; correo al autor con `Reply-To` del lector |
| `POST /report` | `{id,reason,turnstile}` | `200 {ok:true}`; 3 denuncias de IPs distintas ocultan el anuncio |
| `GET /health` | – | `{ok:true}` |

Errores: `400 invalid` (con `field`), `400 filtered`, `403 turnstile`, `403 invalid` (origen no permitido), `404 notfound`, `429 rate`, `503 full` (500 anuncios vivos), `503 mail_quota` (300 correos/día), `502 mail` (Gmail falló), `500 server`.

Límites: crear 3/día por IP y 2/día por email; responder 5/día por IP y 10/día por anuncio; denunciar 10/día por IP; confirmar/gestionar 30/h por IP; admin 5/h por IP. Los anuncios caducan a los 45 días y se pueden renovar 3 veces desde el enlace del correo.

## Moderar

Abre `https://…workers.dev/admin?key=ADMIN_KEY` (en castellano). Muestra los anuncios ocultos o denunciados con sus motivos y los últimos 50 vivos. Acciones por anuncio: **Borrar**, **Restaurar** (vuelve a publicar y limpia denuncias), **Banear IP** y **Banear email** (borran el anuncio y bloquean futuras publicaciones; solo se guardan hashes). Cuando un anuncio recibe 3 denuncias se oculta solo y llega un correo a `ADMIN_EMAIL` con el enlace de esta página.

Los baneos se levantan a mano:
```bash
npx wrangler d1 execute cerdanyola-board --remote --command "DELETE FROM bans WHERE note='ID_DEL_ANUNCIO'"
```
