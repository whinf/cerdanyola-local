# Cerdanyola Avui

Web local de Cerdanyola del Vallès y Bellaterra, en catalán, castellano e inglés. Reúne:
- la previsión del tiempo;
- las horas más baratas de la luz;
- los avisos de Rodalies R7 y R8;
- la agenda (Ajuntament y Agenda cultural de Catalunya), con las fiestas, conciertos y actos de entidades y locales marcados con 🎉;
- una guía de ocio: plan para hoy según el tiempo, próximas fiestas, rutas, fuentes, miradores, patrimonio, restaurantes, bares y pubs;
- las ayudas, becas y subvenciones que se pueden pedir ahora (Ajuntament, comarca, AMB, Generalitat y Estado), con su plazo;
- inversiones y empresas: grandes contratos públicos (1 M€ o más), licitaciones abiertas, contratos anunciados y altas, traslados y cambios de capital de empresas de Cerdanyola según el BORME, con un canal Atom por idioma (`/ca/inversions/feed.xml`...) para recibir avisos. Es información, no consejo de inversión;
- la calidad del aire;
- un directorio de equipamientos públicos y puntos de recarga;
- una página de emergencias con los teléfonos útiles;
- `agenda.ics`, la agenda como calendario para suscribirse desde el móvil.

Se actualiza sola cuatro veces al día con GitHub Actions y se publica en GitHub Pages. Funciona sin dependencias y sin cookies.

## Fuentes

| Dato | Fuente | Licencia |
|---|---|---|
| Tiempo | MET Norway `locationforecast` | CC BY 4.0 |
| Agenda | Ajuntament (`cerdanyola.cat/agenda`) y Generalitat (`rhpv-yr4f`) | Llicència oberta Catalunya; del Ajuntament solo se usa el título, la fecha y el enlace |
| Equipamientos, recarga, aire | Generalitat (`8gmd-gz7i`, `tb2m-m33b`, `tasf-thgu`) | Llicència oberta Catalunya |
| Avisos de trenes | Renfe GTFS-RT `alerts.json` | CC BY 4.0 |
| Luz | web hermana `llum-hores` (`/api/v1/latest.json`) | Red Eléctrica, uso informativo |
| Guía de ocio | OpenStreetMap vía Overpass API (una consulta al día) | ODbL: `data/leisure.json`, `tests/fixtures/osm.json` y `geo/cerdanyola.json` (término municipal) son © colaboradores de OpenStreetMap, bajo ODbL |
| Más locales nocturnos | Overture Maps, PMTiles de lugares de la última versión (`stac.overturemaps.org`), leído por rangos HTTP: solo las ~25 teselas de Cerdanyola | CDLA Permissive 2.0 (Meta, BrightQuery...); se descartan los registros con otras licencias. Solo se añaden los que no están ya en OpenStreetMap; `_NIGHT_SKIP` en `sources.py` excluye clubs de alterne |
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

- La URL del JSON de la luz se deduce del usuario de GitHub. Para cambiarla, usa `light_api_url` en `config.json` o la variable `LIGHT_API_URL`.
- En Windows, si falla el certificado de MET Norway, ejecuta con `SSL_CERT_FILE` apuntando al `ca-bundle.crt` de Git.

`data/*.json` guarda la última versión buena de cada fuente. Si una fuente cae, la web sigue mostrando lo último que tenía, y el workflow solo falla (y te avisa por email) si lleva 3 días sin responder.
