"""Textos y formatos en ca, es y en (el catalán va primero: es una web local)."""

LANGS = ("ca", "es", "en")

MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "ca": ["gener", "febrer", "març", "abril", "maig", "juny", "juliol",
           "agost", "setembre", "octubre", "novembre", "desembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}
WEEKDAYS = {
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
    "ca": ["dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}

# Tiempo: palabra clave del código de MET Norway -> (icono, es, ca, en)
SKY = [
    ("thunder", "⛈️", "Tormenta", "Tempesta", "Thunderstorm"),
    ("snow", "🌨️", "Nieve", "Neu", "Snow"),
    ("sleet", "🌨️", "Aguanieve", "Aiguaneu", "Sleet"),
    ("heavyrain", "🌧️", "Lluvia fuerte", "Pluja forta", "Heavy rain"),
    ("showers", "🌦️", "Chubascos", "Ruixats", "Showers"),
    ("lightrain", "🌦️", "Lluvia débil", "Pluja feble", "Light rain"),
    ("rain", "🌧️", "Lluvia", "Pluja", "Rain"),
    ("fog", "🌫️", "Niebla", "Boira", "Fog"),
    ("partlycloudy", "⛅", "Parcialmente nublado", "Parcialment ennuvolat", "Partly cloudy"),
    ("cloudy", "☁️", "Nublado", "Ennuvolat", "Cloudy"),
    ("fair", "🌤️", "Poco nuboso", "Poc ennuvolat", "Mostly clear"),
    ("clearsky", "☀️", "Despejado", "Serè", "Clear sky"),
]
SKY_COL = {"es": 2, "ca": 3, "en": 4}

# Índice europeo de calidad del aire (EEA): límites superiores de cada categoría.
AQ_BANDS = {"NO2": (40, 90, 120, 230, 340), "O3": (50, 100, 130, 240, 380),
            "PM10": (20, 40, 50, 100, 150), "PM2.5": (10, 20, 25, 50, 75)}

CATEGORIES = {  # categorías de equipamientos de la Generalitat (vienen en catalán)
    "Educació. Formació": ("Educación y formación", "Education and training"),
    "Recerca": ("Investigación", "Research"),
    "Serveis socials especialitzats": ("Servicios sociales especializados", "Specialised social services"),
    "Serveis socials bàsics": ("Servicios sociales básicos", "Basic social services"),
    "Cultura": ("Cultura", "Culture"),
    "Justícia": ("Justicia", "Justice"),
    "Universitats": ("Universidades", "Universities"),
    "Esports. Lleure": ("Deportes y ocio", "Sport and leisure"),
    "Societat. Ciutadania. Famílies": ("Sociedad, ciudadanía y familias", "Community and families"),
    "Emergències. Seguretat": ("Emergencias y seguridad", "Emergencies and safety"),
    "Tecnologia. Innovació": ("Tecnología e innovación", "Technology and innovation"),
    "Llengua. Comunicació": ("Lengua y comunicación", "Language and communication"),
    "Administració pública": ("Administración pública", "Public administration"),
    "Medi ambient": ("Medio ambiente", "Environment"),
    "Treball": ("Trabajo", "Employment"),
    "Comerç. Consum": ("Comercio y consumo", "Shopping and consumer affairs"),
    "Habitatge": ("Vivienda", "Housing"),
    "": ("Otros", "Other"),
}

STRINGS = {
    "ca": {
        "lang_name": "Català", "locale": "ca_ES",
        "slug_agenda": "agenda", "slug_directory": "equipaments", "slug_about": "sobre-el-web",
        "slug_legal": "avis-legal", "slug_privacy": "privacitat",
        "home_title": "Cerdanyola del Vallès avui: temps, agenda, llum i transport",
        "home_desc": "El que passa avui a Cerdanyola del Vallès i Bellaterra: previsió del temps, agenda d'activitats, hores més barates de la llum, qualitat de l'aire i avisos de Rodalies R7 i R8.",
        "tagline": "Dades obertes útils per a la gent de Cerdanyola i Bellaterra, actualitzades soles cada dia.",
        "home": "Inici", "now": "Ara",
        "weather_title": "El temps", "forecast": "Previsió",
        "th_day": "Dia", "th_sky": "Cel", "th_min": "Mín.", "th_max": "Màx.", "th_rain": "Pluja", "th_wind": "Vent",
        "wind": "vent", "weather_note": "Previsió de MET Norway per a Cerdanyola, actualitzada cada poques hores.",
        "light_title": "Hores més barates de la llum avui",
        "light_text": "Les 3 hores seguides més barates: <strong>{w}</strong>. L'hora més barata: <strong>{h}</strong> ({p} €/kWh).",
        "light_tip": "Posar la rentadora o carregar el cotxe en aquestes hores estalvia diners i sol coincidir amb més energia solar.",
        "light_more": "Veure el preu de la llum hora a hora",
        "air_title": "Qualitat de l'aire",
        "air_note": "Darrera mesura de les estacions de la Generalitat més properes (a Cerdanyola no n'hi ha cap). La categoria és aproximada, segons els llindars de l'Índex Europeu de Qualitat de l'Aire.",
        "air_at": "{date}, {h}:00 h", "station": "Estació",
        "aq_0": "Bona", "aq_1": "Raonable", "aq_2": "Moderada", "aq_3": "Dolenta", "aq_4": "Molt dolenta", "aq_5": "Extremadament dolenta",
        "transport_title": "Rodalies R7 i R8",
        "transport_none": "Ara mateix no hi ha avisos actius per a les línies R7 i R8.",
        "transport_more": "Estat del servei a Rodalies de Catalunya",
        "agenda_title": "Agenda de Cerdanyola", "agenda_next": "Properes activitats", "agenda_all": "Veure tota l'agenda",
        "agenda_permanent": "Sempre obert", "agenda_empty": "Ara mateix no hi ha activitats publicades.",
        "agenda_desc": "Agenda d'activitats de Cerdanyola del Vallès i Bellaterra: actes de l'Ajuntament i de l'Agenda cultural de Catalunya.",
        "free": "Gratuït", "src_ajuntament": "Ajuntament", "src_gencat": "Agenda cultural",
        "directory_title": "Equipaments públics de Cerdanyola",
        "directory_desc": "Directori d'equipaments públics de Cerdanyola del Vallès: escoles, biblioteques, instal·lacions esportives, serveis socials i més, amb adreça i telèfon.",
        "chargers_title": "Punts de recàrrega de vehicles elèctrics", "map": "Mapa", "phone": "Tel.",
        "quick_title": "Més informació",
        "source_line": "Fonts: MET Norway (temps), Generalitat de Catalunya (agenda, equipaments i aire), Ajuntament de Cerdanyola (agenda), Renfe (avisos) i Red Eléctrica (llum). Actualitzat: {t}.",
        "about": "Sobre el web", "legal": "Avís legal", "privacy": "Privacitat",
        "skip": "Salta al contingut", "language": "Idioma", "choose": "Tria l'idioma",
        "notfound_title": "Pàgina no trobada", "notfound_text": "Aquesta pàgina no existeix. Torna a l'inici.",
        "about_body": """
<p>{site} reuneix en una sola pàgina dades obertes útils per a la gent de Cerdanyola del Vallès i Bellaterra: el temps, l'agenda, les hores més barates de la llum, la qualitat de l'aire i els avisos de Rodalies.</p>
<p>El web s'actualitza sol diverses vegades al dia a partir de fonts públiques. Les dades poden tenir retards o errors: per a qualsevol tràmit, consulta sempre la font oficial enllaçada.</p>
<h2>Fonts</h2>
<ul>
<li>Temps: previsió de MET Norway (Institut Meteorològic de Noruega), llicència CC BY 4.0.</li>
<li>Agenda: Ajuntament de Cerdanyola del Vallès i Agenda cultural de Catalunya (dades obertes de la Generalitat).</li>
<li>Equipaments, punts de recàrrega i qualitat de l'aire: dades obertes de la Generalitat de Catalunya.</li>
<li>Avisos de trens: Renfe Rodalies (GTFS-RT), llicència CC BY 4.0.</li>
<li>Preu de la llum: Red Eléctrica, a través del web germà <a href="{light}">{light}</a>.</li>
</ul>
<p>El codi és obert i és a <a href="{repo}">GitHub</a>, on pots avisar d'errors o proposar millores.</p>
""",
        "legal_body": """
<p>{site} és un projecte gratuït i informatiu, sense relació amb l'Ajuntament de Cerdanyola del Vallès ni amb cap altra administració.</p>
<h2>Titular</h2><p>{owner}</p>
<h2>Responsabilitat</h2><p>La informació prové de fonts públiques citades a cada apartat i s'ofereix tal com és, sense garantia. Consulta sempre la font oficial abans de prendre decisions.</p>
""",
        "privacy_body": """
<p>Aquest web no fa servir galetes, no té analítica ni publicitat i no recull dades personals.</p>
<p>Està allotjat a GitHub Pages. Com qualsevol servidor web, GitHub registra l'adreça IP de les visites per motius de seguretat. Més informació a la <a href="https://docs.github.com/es/site-policy/privacy-policies/github-general-privacy-statement">declaració de privacitat de GitHub</a>.</p>
""",
        "owner_missing": "Projecte personal sense ànim de lucre. Contacte: a través del <a href=\"{repo}\">repositori a GitHub</a>.",
    },
    "es": {
        "lang_name": "Español", "locale": "es_ES",
        "slug_agenda": "agenda", "slug_directory": "equipamientos", "slug_about": "sobre-la-web",
        "slug_legal": "aviso-legal", "slug_privacy": "privacidad",
        "home_title": "Cerdanyola del Vallès hoy: tiempo, agenda, luz y transporte",
        "home_desc": "Lo que pasa hoy en Cerdanyola del Vallès y Bellaterra: previsión del tiempo, agenda de actividades, horas más baratas de la luz, calidad del aire y avisos de Rodalies R7 y R8.",
        "tagline": "Datos abiertos útiles para la gente de Cerdanyola y Bellaterra, actualizados solos cada día.",
        "home": "Inicio", "now": "Ahora",
        "weather_title": "El tiempo", "forecast": "Previsión",
        "th_day": "Día", "th_sky": "Cielo", "th_min": "Mín.", "th_max": "Máx.", "th_rain": "Lluvia", "th_wind": "Viento",
        "wind": "viento", "weather_note": "Previsión de MET Norway para Cerdanyola, actualizada cada pocas horas.",
        "light_title": "Horas más baratas de la luz hoy",
        "light_text": "Las 3 horas seguidas más baratas: <strong>{w}</strong>. La hora más barata: <strong>{h}</strong> ({p} €/kWh).",
        "light_tip": "Poner la lavadora o cargar el coche en estas horas ahorra dinero y suele coincidir con más energía solar.",
        "light_more": "Ver el precio de la luz hora a hora",
        "air_title": "Calidad del aire",
        "air_note": "Última medición de las estaciones de la Generalitat más cercanas (en Cerdanyola no hay ninguna). La categoría es aproximada, según los umbrales del Índice Europeo de Calidad del Aire.",
        "air_at": "{date}, {h}:00 h", "station": "Estación",
        "aq_0": "Buena", "aq_1": "Razonable", "aq_2": "Regular", "aq_3": "Mala", "aq_4": "Muy mala", "aq_5": "Extremadamente mala",
        "transport_title": "Rodalies R7 y R8",
        "transport_none": "Ahora mismo no hay avisos activos para las líneas R7 y R8.",
        "transport_more": "Estado del servicio en Rodalies de Catalunya",
        "agenda_title": "Agenda de Cerdanyola", "agenda_next": "Próximas actividades", "agenda_all": "Ver toda la agenda",
        "agenda_permanent": "Siempre abierto", "agenda_empty": "Ahora mismo no hay actividades publicadas.",
        "agenda_desc": "Agenda de actividades de Cerdanyola del Vallès y Bellaterra: actos del Ajuntament y de la Agenda cultural de Catalunya.",
        "free": "Gratis", "src_ajuntament": "Ajuntament", "src_gencat": "Agenda cultural",
        "directory_title": "Equipamientos públicos de Cerdanyola",
        "directory_desc": "Directorio de equipamientos públicos de Cerdanyola del Vallès: escuelas, bibliotecas, instalaciones deportivas, servicios sociales y más, con dirección y teléfono.",
        "chargers_title": "Puntos de recarga de coches eléctricos", "map": "Mapa", "phone": "Tel.",
        "quick_title": "Más información",
        "source_line": "Fuentes: MET Norway (tiempo), Generalitat de Catalunya (agenda, equipamientos y aire), Ajuntament de Cerdanyola (agenda), Renfe (avisos) y Red Eléctrica (luz). Actualizado: {t}.",
        "about": "Sobre la web", "legal": "Aviso legal", "privacy": "Privacidad",
        "skip": "Saltar al contenido", "language": "Idioma", "choose": "Elige idioma",
        "notfound_title": "Página no encontrada", "notfound_text": "Esta página no existe. Vuelve al inicio.",
        "about_body": """
<p>{site} reúne en una sola página datos abiertos útiles para la gente de Cerdanyola del Vallès y Bellaterra: el tiempo, la agenda, las horas más baratas de la luz, la calidad del aire y los avisos de Rodalies.</p>
<p>La web se actualiza sola varias veces al día a partir de fuentes públicas. Los datos pueden tener retrasos o errores: para cualquier trámite, consulta siempre la fuente oficial enlazada.</p>
<h2>Fuentes</h2>
<ul>
<li>Tiempo: previsión de MET Norway (Instituto Meteorológico de Noruega), licencia CC BY 4.0.</li>
<li>Agenda: Ajuntament de Cerdanyola del Vallès y Agenda cultural de Catalunya (datos abiertos de la Generalitat).</li>
<li>Equipamientos, puntos de recarga y calidad del aire: datos abiertos de la Generalitat de Catalunya.</li>
<li>Avisos de trenes: Renfe Rodalies (GTFS-RT), licencia CC BY 4.0.</li>
<li>Precio de la luz: Red Eléctrica, a través de la web hermana <a href="{light}">{light}</a>.</li>
</ul>
<p>El código es abierto y está en <a href="{repo}">GitHub</a>, donde puedes avisar de errores o proponer mejoras.</p>
""",
        "legal_body": """
<p>{site} es un proyecto gratuito e informativo, sin relación con el Ajuntament de Cerdanyola del Vallès ni con ninguna otra administración.</p>
<h2>Titular</h2><p>{owner}</p>
<h2>Responsabilidad</h2><p>La información procede de fuentes públicas citadas en cada apartado y se ofrece tal cual, sin garantía. Consulta siempre la fuente oficial antes de tomar decisiones.</p>
""",
        "privacy_body": """
<p>Esta web no usa cookies, no tiene analítica ni publicidad y no recoge datos personales.</p>
<p>Está alojada en GitHub Pages. Como cualquier servidor web, GitHub registra la dirección IP de las visitas por motivos de seguridad. Más información en la <a href="https://docs.github.com/es/site-policy/privacy-policies/github-general-privacy-statement">declaración de privacidad de GitHub</a>.</p>
""",
        "owner_missing": "Proyecto personal sin ánimo de lucro. Contacto: a través del <a href=\"{repo}\">repositorio en GitHub</a>.",
    },
    "en": {
        "lang_name": "English", "locale": "en_GB",
        "slug_agenda": "events", "slug_directory": "facilities", "slug_about": "about",
        "slug_legal": "legal-notice", "slug_privacy": "privacy",
        "home_title": "Cerdanyola del Vallès today: weather, events, electricity and trains",
        "home_desc": "What's on today in Cerdanyola del Vallès and Bellaterra (UAB): weather forecast, events, cheapest electricity hours, air quality and Rodalies R7 and R8 train alerts.",
        "tagline": "Useful open data for people in Cerdanyola and Bellaterra, updated automatically every day.",
        "home": "Home", "now": "Now",
        "weather_title": "Weather", "forecast": "Forecast",
        "th_day": "Day", "th_sky": "Sky", "th_min": "Min", "th_max": "Max", "th_rain": "Rain", "th_wind": "Wind",
        "wind": "wind", "weather_note": "MET Norway forecast for Cerdanyola, updated every few hours.",
        "light_title": "Cheapest electricity hours today",
        "light_text": "The cheapest 3 consecutive hours: <strong>{w}</strong>. The cheapest hour: <strong>{h}</strong> ({p} €/kWh).",
        "light_tip": "Running the washing machine or charging your car in these hours saves money and usually coincides with more solar power.",
        "light_more": "See the electricity price hour by hour",
        "air_title": "Air quality",
        "air_note": "Latest measurement from the nearest Generalitat stations (there is none in Cerdanyola itself). The category is approximate, based on the European Air Quality Index thresholds.",
        "air_at": "{date}, {h}:00", "station": "Station",
        "aq_0": "Good", "aq_1": "Fair", "aq_2": "Moderate", "aq_3": "Poor", "aq_4": "Very poor", "aq_5": "Extremely poor",
        "transport_title": "Rodalies R7 and R8 trains",
        "transport_none": "There are no active alerts for the R7 and R8 lines right now.",
        "transport_more": "Service status on Rodalies de Catalunya",
        "agenda_title": "What's on in Cerdanyola", "agenda_next": "Upcoming events", "agenda_all": "See all events",
        "agenda_permanent": "Always open", "agenda_empty": "There are no published events right now.",
        "agenda_desc": "Events in Cerdanyola del Vallès and Bellaterra, from the town council and the Catalan culture agenda.",
        "free": "Free", "src_ajuntament": "Town council", "src_gencat": "Culture agenda",
        "directory_title": "Public facilities in Cerdanyola",
        "directory_desc": "Directory of public facilities in Cerdanyola del Vallès: schools, libraries, sports centres, social services and more, with address and phone number.",
        "chargers_title": "Electric vehicle charging points", "map": "Map", "phone": "Tel.",
        "quick_title": "More information",
        "source_line": "Sources: MET Norway (weather), Generalitat de Catalunya (events, facilities and air), Cerdanyola town council (events), Renfe (alerts) and Red Eléctrica (electricity). Updated: {t}.",
        "about": "About", "legal": "Legal notice", "privacy": "Privacy",
        "skip": "Skip to content", "language": "Language", "choose": "Choose your language",
        "notfound_title": "Page not found", "notfound_text": "This page does not exist. Go back to the home page.",
        "about_body": """
<p>{site} brings together useful open data for people in Cerdanyola del Vallès and Bellaterra on a single page: weather, events, the cheapest electricity hours, air quality and Rodalies train alerts.</p>
<p>The site updates itself several times a day from public sources. Data may be delayed or contain errors: always check the linked official source before acting on it.</p>
<h2>Sources</h2>
<ul>
<li>Weather: MET Norway (Norwegian Meteorological Institute) forecast, CC BY 4.0 licence.</li>
<li>Events: Cerdanyola del Vallès town council and the Catalan culture agenda (Generalitat open data).</li>
<li>Facilities, charging points and air quality: Generalitat de Catalunya open data.</li>
<li>Train alerts: Renfe Rodalies (GTFS-RT), CC BY 4.0 licence.</li>
<li>Electricity price: Red Eléctrica, via the sister site <a href="{light}">{light}</a>.</li>
</ul>
<p>The code is open source and lives on <a href="{repo}">GitHub</a>, where you can report bugs or suggest improvements.</p>
""",
        "legal_body": """
<p>{site} is a free, informational project with no connection to Cerdanyola del Vallès town council or any other public body.</p>
<h2>Owner</h2><p>{owner}</p>
<h2>Liability</h2><p>The information comes from the public sources cited in each section and is provided as is, without warranty. Always check the official source before making decisions.</p>
""",
        "privacy_body": """
<p>This website uses no cookies, has no analytics or advertising, and collects no personal data.</p>
<p>It is hosted on GitHub Pages. Like any web server, GitHub logs visitors' IP addresses for security reasons. See the <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub privacy statement</a>.</p>
""",
        "owner_missing": "Personal non-profit project. Contact: through the <a href=\"{repo}\">GitHub repository</a>.",
    },
}


def t(lang, key, **kw):
    text = STRINGS[lang][key]
    return text.format(**kw) if kw else text


def fmt_num(lang, x, decimals):
    s = f"{x:.{decimals}f}"
    return s if lang == "en" else s.replace(".", ",")


def fmt_date(lang, d, weekday=True):
    if lang == "en":
        s = f"{d.day} {MONTHS['en'][d.month - 1]}"
        return f"{WEEKDAYS['en'][d.weekday()]}, {s}" if weekday else s
    name = MONTHS[lang][d.month - 1]
    of = ("d'" if lang == "ca" and name[0] in "aeiou" else "de ") + name
    s = f"{d.day} {of}"
    return f"{WEEKDAYS[lang][d.weekday()]}, {s}" if weekday else s


def sky(lang, code):
    for key, icon, *names in SKY:
        if code and key in code.split("_")[0]:
            return icon, names[SKY_COL[lang] - 2]
    return "", ""


def aq_level(pollutant, value):
    for i, limit in enumerate(AQ_BANDS[pollutant]):
        if value <= limit:
            return i
    return 5


def category(lang, cat):
    if lang == "ca":
        return cat or "Altres"
    es, en = CATEGORIES.get(cat, (cat, cat))
    return es if lang == "es" else en
