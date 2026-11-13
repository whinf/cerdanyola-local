# Cerdanyola Avui

Web local de Cerdanyola del Vallès y Bellaterra, en catalán, castellano e inglés. Reúne:
- la previsión del tiempo;
- las horas más baratas de la luz;
- los avisos de Rodalies R7 y R8;
- la agenda (Ajuntament, Agenda cultural de Catalunya, agenda de la UAB y calendarios de entidades como el Festival de Blues y AFOCER), con las fiestas y conciertos marcados con el icono de fiesta y los actos infantiles con el suyo;
- recomendaciones de la semana: restaurantes y experiencias elegidos a mano (`curated/picks.json`), que rotan cada semana;
- una página «Ahorra»: horas baratas de la luz, gasolinera más barata, actos gratuitos, ayudas para particulares y tarifas sociales;
- una guía de ocio: plan para hoy según el tiempo, próximas fiestas, rutas, fuentes, miradores, patrimonio, restaurantes, bares y pubs;
- las ayudas, becas y subvenciones que se pueden pedir ahora (Ajuntament, comarca, AMB, Generalitat y Estado), con su plazo;
- empleo: ofertas de Feina Activa (SOC) en Cerdanyola y municipios vecinos, y oposiciones y bolsas públicas del CIDO;
- los precios de hoy de las gasolineras de Cerdanyola y alrededores;
- inversiones y empresas: grandes contratos públicos (1 M€ o más), licitaciones abiertas, contratos anunciados y altas, traslados y cambios de capital de empresas de Cerdanyola según el BORME, con un canal Atom por idioma (`/ca/inversions/feed.xml`...) para recibir avisos. Es información, no consejo de inversión;
- la calidad del aire;
- un directorio de equipamientos públicos y puntos de recarga;
- una página de emergencias con los teléfonos útiles;
- `agenda.ics`, la agenda como calendario para suscribirse desde el móvil;
- un tablón vecinal («Tauler veïnal»): los vecinos piden ayuda, regalan lo que ya no usan o publican chollos y segunda mano, y se responden por email sin que se publique ninguna dirección. Es la única parte con backend: un worker de Cloudflare (`worker/`, gratis) con base de datos D1, Turnstile contra robots y envío de correos por la API de Gmail; moderación automática (filtro, límites, caducidad a 45 días, denuncias) y página de administración. La web estática muestra la lista de la última build (`data/board.json`, no se guarda en git) y `static/board.js` la sustituye por la lista en vivo. Instalación en `worker/README.md`.

Se actualiza sola cuatro veces al día con GitHub Actions y se publica en GitHub Pages. Funciona sin dependencias y sin cookies.

## Fuentes

| Dato | Fuente | Licencia |
|---|---|---|
| Tiempo | MET Norway `locationforecast` | CC BY 4.0 |
| Agenda | Ajuntament (`cerdanyola.cat/agenda`) y Generalitat (`rhpv-yr4f`) | Llicència oberta Catalunya; del Ajuntament solo se usa el título, la fecha y el enlace |
| Equipamientos, recarga, aire | Generalitat (`8gmd-gz7i`, `tb2m-m33b`, `tasf-thgu`) | Llicència oberta Catalunya |
| Avisos de trenes | Renfe GTFS-RT `alerts.json` | CC BY 4.0 |
| Luz | web hermana Hora Verda (`light_api_url` en `config.json`: `https://horaverda.es/api/v1/latest.json`) | Red Eléctrica, uso informativo |
| Agenda UAB y entidades | `uab.cat` (HTML) y calendarios WordPress/The Events Calendar (`TRIBE_FEEDS` en `sources.py`) | UAB: CC BY-NC (otra razón para no monetizar). Si una web cae, se conservan sus actos guardados |
| Empleo | CIDO de la Diputació (`api.diba.cat`) y XML de Feina Activa (SOC) | CC BY 4.0 y Llicència oberta Catalunya |
| Carburantes | API del Ministerio para la Transición Ecológica (`FiltroMunicipio`) | Reutilización libre citando fuente y fecha |
| Tablón vecinal | Anuncios de los propios vecinos, vía el worker de Cloudflare (`board_api_url` en `config.json`; `turnstile_site_key` es la clave pública de Turnstile) | Contenido de los usuarios; solo se publican nombre o alias, texto y el contacto que el autor decide mostrar |
| Recomendaciones | `curated/picks.json`, escrito a mano | Propio; `--check` avisa si una ficha lleva más de un año sin revisar (`checked`) |
| Guía de ocio | OpenStreetMap vía Overpass API (una consulta al día) | ODbL: `data/leisure.json`, `tests/fixtures/osm.json` y `geo/cerdanyola.json` (término municipal) son © colaboradores de OpenStreetMap, bajo ODbL |
| Más locales nocturnos | Overture Maps, PMTiles de lugares de la última versión (`stac.overturemaps.org`), leído por rangos HTTP: solo las ~25 teselas de Cerdanyola | CDLA Permissive 2.0 (Meta, BrightQuery...); se descartan los registros con otras licencias. Solo se añaden los que no están ya en OpenStreetMap; `_NIGHT_SKIP` en `sources.py` excluye por nombre los clubs de alterne (y se omite la categoría adult_entertainment de Overture) |
| Ayudas | Base de Datos Nacional de Subvenciones (`infosubvenciones.es/bdnstrans/api`) | Reutilización libre (Ministerio de Hacienda); `data/aids.json` guarda las convocatorias abiertas y las ya descartadas para no repetir consultas |
| Inversiones y licitaciones | Plataforma de serveis de contractació pública (`ybgg-dgi6`), contratos del Ajuntament o con lugar de ejecución en Cerdanyola o Bellaterra | Llicència oberta Catalunya. Los nombres de adjudicatarios particulares no se publican (`companies_only`). No incluye la plataforma del Estado (ALBA, Adif) |
| Empresas | BORME sección A de Barcelona (API de datos abiertos del BOE + página HTML del día) | Reutilización libre citando la fuente. Solo nombre, acto, capital y actividad: ni administradores ni direcciones. `data/companies.json` guarda las hojas registrales de las empresas de Cerdanyola vistas desde el primer año leído, para reconocer después sus ampliaciones, traslados y cierres |

`certs/sectigo-ov-r36.pem` y `certs/letsencrypt-ye1.pem` son los certificados intermedios que `cerdanyola.cat` no envía (en octubre de 2026 pasó de Sectigo a Let's Encrypt). La verificación TLS sigue siendo completa. Si cae una de las webs de la agenda (Ajuntament, UAB o una entidad), la agenda sigue con las demás y conserva los actos de esa web que ya tenía guardados.

## Comandos locales (Python 3.12 o superior)

```bash
python -m unittest discover tests
```

```bash
python src/build.py
```

```bash
python src/build.py --offline
```

```bash
python -m http.server 8001 -d _site
```

- La URL del JSON de la luz es `light_api_url` en `config.json` (o la variable `LIGHT_API_URL`); si falta, se deduce del usuario de GitHub (`<usuario>.github.io/llum-hores`).
- En Windows, si falla el certificado de MET Norway, ejecuta con `SSL_CERT_FILE` apuntando al `ca-bundle.crt` de Git.

`data/*.json` guarda la última versión buena de cada fuente. Si una fuente cae, la web sigue mostrando lo último que tenía, y el workflow solo falla (y te avisa por email) si lleva 3 días sin responder.

## Diseño
- El marco común (`static/base.css`, `static/ui.js`, `static/fonts/`, `src/icons.py`) se sincroniza desde `llum-hores` con `python ..\tools\sync_base.py`; no se edita aquí. Las reglas propias están en `static/site.css`; el generador sirve un solo `static/style.css`.
- Iconos meteorológicos: `static/wx/*.svg`, de [MET Norway weathericons](https://github.com/metno/weathericons) (MIT). Resto de iconos: Lucide (ISC) vía `src/icons.py`.
- PNG (iconos PWA, `apple-touch-icon`, `og.png`): `py tools/make_assets.py` (Pillow, solo en local).

## App instalable (PWA)
La web se instala como app desde la propia web, sin tiendas: en Android/Chrome/Edge aparece el botón «Instala la app» (portada y pie); en iPhone/iPad, «Compartir → Añadir a pantalla de inicio». Piezas:
- `static/app.js`: registra el service worker y enseña el botón solo donde se puede instalar.
- `static/sw.js` → se sirve en `/sw.js` (controla toda la web): páginas red primero y, sin conexión, copia guardada u `offline.html`; `/static/` desde caché con actualización en segundo plano. Cada build estrena caché (`__BUILD__`). Las peticiones al worker del tablón no se tocan.
- Un manifest por idioma (`static/manifest.{ca,es,en}.webmanifest`, `display: standalone`, accesos directos a agenda, tablón y 112).
- Para probar en local: `python src/build.py --offline`, servir `_site` y abrir `http://localhost:8001/ca/` (localhost cuenta como contexto seguro; en las herramientas del navegador, Application → Service workers / Manifest).
