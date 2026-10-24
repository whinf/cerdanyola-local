# Cerdanyola Avui

Web local de Cerdanyola del Vallès y Bellaterra, en catalán, castellano e inglés. Reúne:
- la previsión del tiempo;
- las horas más baratas de la luz;
- los avisos de Rodalies R7 y R8;
- la agenda (Ajuntament y Agenda cultural de Catalunya), con las fiestas, conciertos y actos de entidades y locales marcados con 🎉;
- una guía de ocio: plan para hoy según el tiempo, próximas fiestas, rutas, fuentes, miradores, patrimonio, restaurantes, bares y pubs;
- las ayudas, becas y subvenciones que se pueden pedir ahora (Ajuntament, comarca, AMB, Generalitat y Estado), con su plazo;
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
| Guía de ocio | OpenStreetMap vía Overpass API (una consulta al día) | ODbL: `data/leisure.json` y `tests/fixtures/osm.json` son © colaboradores de OpenStreetMap, bajo ODbL |
| Ayudas | Base de Datos Nacional de Subvenciones (`infosubvenciones.es/bdnstrans/api`) | Reutilización libre (Ministerio de Hacienda); `data/aids.json` guarda las convocatorias abiertas y las ya descartadas para no repetir consultas |

`certs/sectigo-ov-r36.pem` es el certificado intermedio que `cerdanyola.cat` no envía. La verificación TLS sigue siendo completa.

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
