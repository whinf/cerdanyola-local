"""Textos y formatos en ca, es y en (el catalán va primero: es una web local)."""
import re

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

AGENDA_CATS = {  # categorías de la agenda (en catalán, como las publica el Ajuntament)
    "Festes populars": ("Fiestas populares", "Local festivals"), "Música": ("Música", "Music"),
    "Teatre i dansa": ("Teatro y danza", "Theatre and dance"), "Cinema": ("Cine", "Cinema"),
    "Hostalaria": ("Gastronomía", "Food and drink"), "Esports": ("Deportes", "Sport"),
    "Infància": ("Infancia", "Children"), "Exposicions": ("Exposiciones", "Exhibitions"),
    "Conferències": ("Conferencias", "Talks"), "Actes literaris": ("Actos literarios", "Literary events"),
    "Cursos i tallers": ("Cursos y talleres", "Courses and workshops"),
    "Jornades i seminaris": ("Jornadas y seminarios", "Conferences"), "Altres activitats": ("Otras actividades", "Other"),
    "Rutes i visites": ("Rutas y visitas", "Walks and tours"), "Festivals": ("Festivales", "Festivals"),
    "Fires i mercats": ("Ferias y mercados", "Fairs and markets"), "Nadal": ("Navidad", "Christmas"),
    "Joventut": ("Juventud", "Youth"), "Gent gran": ("Gente mayor", "Older people"),
}

# grupos de la guía de ocio: icono, ca, es, en (en el orden en que salen en la página)
LEISURE_GROUPS = {
    "nature": ("🌳", "Natura, parcs i fonts", "Naturaleza, parques y fuentes", "Nature, parks and springs"),
    "routes": ("🥾", "Rutes a peu i en bici", "Rutas a pie y en bici", "Walking and cycling routes"),
    "heritage": ("🏛️", "Patrimoni", "Patrimonio", "Heritage"),
    "culture": ("🎭", "Cultura i lleure", "Cultura y ocio", "Culture and entertainment"),
    "eat": ("🍽️", "Restaurants", "Restaurantes", "Restaurants"),
    "drink": ("☕", "Bars i cafeteries", "Bares y cafeterías", "Bars and cafés"),
    "night": ("🌙", "Nit: pubs, discoteques i música", "Noche: pubs, discotecas y música", "Nightlife: pubs, clubs and live music"),
    "sport": ("⚽", "Esport", "Deporte", "Sport"),
    "community": ("🤝", "Centres cívics i entitats", "Centros cívicos y entidades", "Community centres and associations"),
}

PLACE_TYPES = {  # valor de OSM -> ca, es, en
    "park": ("Parc", "Parque", "Park"), "nature_reserve": ("Espai natural", "Espacio natural", "Nature reserve"),
    "playground": ("Parc infantil", "Parque infantil", "Playground"), "water_park": ("Parc aquàtic", "Parque acuático", "Water park"),
    "viewpoint": ("Mirador", "Mirador", "Viewpoint"), "picnic_site": ("Àrea de pícnic", "Área de pícnic", "Picnic area"),
    "spring": ("Font", "Fuente", "Spring"), "peak": ("Turó", "Cima", "Hill"), "cave_entrance": ("Cova", "Cueva", "Cave"),
    "hiking": ("A peu", "A pie", "On foot"), "foot": ("A peu", "A pie", "On foot"),
    "bicycle": ("En bici", "En bici", "By bike"), "mtb": ("BTT", "BTT", "Mountain bike"),
    "castle": ("Castell", "Castillo", "Castle"), "manor": ("Casa senyorial", "Casa señorial", "Manor house"),
    "ruins": ("Ruïnes", "Ruinas", "Ruins"), "archaeological_site": ("Jaciment arqueològic", "Yacimiento arqueológico", "Archaeological site"),
    "monument": ("Monument", "Monumento", "Monument"), "memorial": ("Memorial", "Memorial", "Memorial"),
    "fort": ("Fortificació", "Fortificación", "Fortification"), "tower": ("Torre", "Torre", "Tower"), "farm": ("Masia", "Masía", "Farmhouse"),
    "museum": ("Museu", "Museo", "Museum"), "gallery": ("Galeria d'art", "Galería de arte", "Art gallery"),
    "attraction": ("Atracció", "Atracción", "Attraction"), "cinema": ("Cinema", "Cine", "Cinema"),
    "theatre": ("Teatre", "Teatro", "Theatre"), "arts_centre": ("Centre d'art", "Centro de arte", "Arts centre"),
    "escape_game": ("Escape room", "Escape room", "Escape room"), "bowling_alley": ("Bitlles", "Bolera", "Bowling"),
    "community_centre": ("Centre cívic o entitat", "Centro cívico o entidad", "Community centre"),
    "restaurant": ("Restaurant", "Restaurante", "Restaurant"), "fast_food": ("Menjar ràpid", "Comida rápida", "Fast food"),
    "bar": ("Bar", "Bar", "Bar"), "cafe": ("Cafeteria", "Cafetería", "Café"), "ice_cream": ("Gelateria", "Heladería", "Ice cream"),
    "biergarten": ("Terrassa", "Terraza", "Beer garden"), "pub": ("Pub", "Pub", "Pub"),
    "nightclub": ("Discoteca", "Discoteca", "Nightclub"), "dance": ("Sala de ball", "Sala de baile", "Dance hall"),
    "music_venue": ("Música en directe", "Música en directo", "Live music"), "karaoke_box": ("Karaoke", "Karaoke", "Karaoke"),
    "cocktail_bar": ("Bar de copes", "Bar de copas", "Cocktail bar"), "piano_bar": ("Piano bar", "Piano bar", "Piano bar"),
    "hookah_lounge": ("Bar de xixa", "Bar de shisha", "Shisha lounge"), "night_venue": ("Local nocturn", "Local nocturno", "Night venue"),
    "sports_centre": ("Centre esportiu", "Centro deportivo", "Sports centre"), "swimming_pool": ("Piscina", "Piscina", "Swimming pool"),
    "stadium": ("Estadi", "Estadio", "Stadium"), "fitness_centre": ("Gimnàs", "Gimnasio", "Gym"),
}

CUISINES = {  # cocina de OSM -> ca, es, en
    "regional": ("cuina tradicional", "cocina tradicional", "traditional"), "catalan": ("catalana", "catalana", "Catalan"),
    "spanish": ("espanyola", "española", "Spanish"), "mediterranean": ("mediterrània", "mediterránea", "Mediterranean"),
    "tapas": ("tapes", "tapas", "tapas"), "pizza": ("pizza", "pizza", "pizza"), "italian": ("italiana", "italiana", "Italian"),
    "pasta": ("pasta", "pasta", "pasta"), "burger": ("hamburgueses", "hamburguesas", "burgers"),
    "kebab": ("kebab", "kebab", "kebab"), "turkish": ("turca", "turca", "Turkish"), "chinese": ("xinesa", "china", "Chinese"),
    "japanese": ("japonesa", "japonesa", "Japanese"), "sushi": ("sushi", "sushi", "sushi"), "asian": ("asiàtica", "asiática", "Asian"),
    "international": ("internacional", "internacional", "international"), "sandwich": ("entrepans", "bocadillos", "sandwiches"),
    "breakfast": ("esmorzars", "desayunos", "breakfast"), "coffee_shop": ("cafè", "café", "coffee"),
    "grill": ("brasa", "brasa", "grill"), "seafood": ("peix i marisc", "pescado y marisco", "seafood"),
    "chicken": ("pollastre", "pollo", "chicken"), "mexican": ("mexicana", "mexicana", "Mexican"),
    "indian": ("índia", "india", "Indian"), "vegetarian": ("vegetariana", "vegetariana", "vegetarian"),
    "vegan": ("vegana", "vegana", "vegan"), "salad": ("amanides", "ensaladas", "salads"), "churro": ("xurros", "churros", "churros"),
    "noodle": ("fideus", "fideos", "noodles"), "hot_dog": ("frankfurts", "perritos", "hot dogs"),
    "bubble_tea": ("bubble tea", "bubble tea", "bubble tea"), "ice_cream": ("gelats", "helados", "ice cream"),
}

# abreviaturas de opening_hours de OSM
HOURS = {
    "ca": {"Mo": "dl", "Tu": "dt", "We": "dc", "Th": "dj", "Fr": "dv", "Sa": "ds", "Su": "dg", "PH": "festius", "off": "tancat", "closed": "tancat"},
    "es": {"Mo": "lu", "Tu": "ma", "We": "mi", "Th": "ju", "Fr": "vi", "Sa": "sá", "Su": "do", "PH": "festivos", "off": "cerrado", "closed": "cerrado"},
    "en": {"PH": "holidays", "off": "closed"},
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
        "agenda_desc": "Agenda d'activitats de Cerdanyola del Vallès i Bellaterra: festes, concerts, teatre i actes de l'Ajuntament, les entitats i els locals, i de l'Agenda cultural de Catalunya.",
        "free": "Gratuït", "src_ajuntament": "Ajuntament", "src_gencat": "Agenda cultural",
        "src_uab": "UAB", "src_blues": "Festival de Blues", "src_afocer": "AFOCER",
        "ongoing_title": "Ara en marxa", "festive": "Festa",
        "add_event": "Organitzes una festa, un concert o una activitat oberta al públic a Cerdanyola? Si el teu local o entitat té un calendari web (per exemple, WordPress amb The Events Calendar), <a href=\"{repo}/issues\">explica-ho a GitHub</a> i l'afegirem a l'agenda.",
        "slug_leisure": "oci", "leisure_title": "Guia d'oci de Cerdanyola",
        "leisure_desc": "Què fer a Cerdanyola del Vallès i Bellaterra: festes i concerts, rutes per Collserola, fonts, miradors, patrimoni, museus, restaurants, bars i pubs.",
        "festive_title": "Properes festes, concerts i nit", "festive_empty": "Ara mateix no hi ha festes ni concerts anunciats.",
        "plan_title": "Pla per avui", "plan_out": "Avui: {sky}, fins a {tmax}°. Bon dia per sortir; algunes idees:",
        "plan_in": "Avui es preveu pluja ({mm} mm). Idees a cobert:", "plan_events": "Avui hi ha {n} activitats a l'agenda",
        "osm_note": "Llocs d'<a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> (© col·laboradors d'OpenStreetMap, llicència ODbL), en ordre alfabètic i sense enllaços patrocinats. Hi falta un lloc o hi ha una dada malament? Qualsevol persona el pot afegir o corregir gratis a <a href=\"https://www.openstreetmap.org/#map=15/41.4913/2.1408\">OpenStreetMap</a> i es veurà aquí l'endemà.",
        "overture_note": "Alguns locals nocturns que encara no són a OpenStreetMap vénen d'<a href=\"https://overturemaps.org\">Overture Maps Foundation</a> (dades de {src}, llicència <a href=\"https://cdla.dev/permissive-2-0/\">CDLA Permissive 2.0</a>). Surten de registres d'empreses i de les pàgines dels mateixos locals, i algun pot haver tancat o canviat de nom.",
        "directory_title": "Equipaments públics de Cerdanyola",
        "directory_desc": "Directori d'equipaments públics de Cerdanyola del Vallès: escoles, biblioteques, instal·lacions esportives, serveis socials i més, amb adreça i telèfon, i els preus d'avui de les gasolineres.",
        "chargers_title": "Punts de recàrrega de vehicles elèctrics", "map": "Mapa", "phone": "Tel.",
        "quick_title": "Més informació",
        "slug_jobs": "feina",
        "jobs_title": "Feina a Cerdanyola i rodalia",
        "jobs_desc": "Ofertes de feina a Cerdanyola del Vallès i als municipis veïns, i oposicions i borses de treball públiques obertes al Vallès Occidental i a la UAB, actualitzades cada dia.",
        "jobs_offers": "Ofertes de feina",
        "jobs_public": "Oposicions i borses de treball públiques",
        "jobs_near": "A Cerdanyola i al campus de la UAB",
        "jobs_far": "Resta del Vallès Occidental",
        "jobs_pool": "Borsa de treball",
        "jobs_places": "{n} places",
        "jobs_place": "1 plaça",
        "jobs_posted": "Publicada el {d}",
        "jobs_empty": "Ara mateix no n'hi ha cap.",
        "jobs_note": "Ofertes del Servei Públic d'Ocupació de Catalunya (<a href='https://feinaactiva.gencat.cat/'>Feina Activa</a>) i convocatòries públiques del <a href='https://cido.diba.cat/'>CIDO</a> de la Diputació de Barcelona (CC BY 4.0). Només es mostren les ofertes publicades els darrers 60 dies: algunes ja poden estar cobertes. <a href='https://www.cerdanyolactiva.cat/'>Cerdanyola Activa</a> també té una borsa de treball i orientació laboral gratuïta.",
        "jobs_home": "💼 Feina a prop",
        "jobs_home_text": "{o} ofertes de feina a Cerdanyola i rodalia i {p} oposicions i borses públiques obertes.",
        "jobs_all": "Veure les ofertes",
        "fuel_title": "Gasolineres: preus d'avui",
        "fuel_station": "Gasolinera",
        "fuel_g95": "Gasolina 95",
        "fuel_diesel": "Gasoil",
        "fuel_town": "A Cerdanyola",
        "fuel_near": "Les més barates dels municipis veïns",
        "fuel_home": "⛽ Carburant més barat avui a Cerdanyola",
        "fuel_home_text": "Gasolina 95: <strong>{g} €/l</strong> a {gs}. Gasoil: <strong>{d} €/l</strong> a {ds}.",
        "fuel_more": "Veure totes les gasolineres",
        "fuel_note": "Preus en €/litre. Origen de les dades: Ministeri per a la Transició Ecològica i el Repte Demogràfic. Última actualització: {t}.",
        "slug_emergency": "emergencies", "emergency_title": "Emergències a Cerdanyola: telèfons i consells",
        "emergency_desc": "Telèfons d'emergència i d'ajuda, Policia Local, Mossos i Bombers de Cerdanyola del Vallès, i com preparar-se per a una apagada, una onada de calor o una inundació.",
        "emergency_body": """
<p class="lede">Guarda aquesta pàgina. Si hi ha perill per a una persona, truca al <a href="tel:112"><strong>112</strong></a>.</p>
<h2>Telèfons</h2>
<ul class="dir">
<li><a href="tel:112"><strong>112</strong></a> — Emergències: ambulància, bombers i policia. Gratuït i 24 hores.</li>
<li><a href="tel:061"><strong>061</strong></a> — <a href="https://sem.gencat.cat/ca/061-salut-respon/">Salut Respon</a>: consultes de salut que no són una emergència.</li>
<li><a href="tel:024"><strong>024</strong></a> — <a href="https://www.sanidad.gob.es/linea024/home.htm">Atenció a la conducta suïcida</a>. Gratuït i 24 hores.</li>
<li><a href="tel:900900120"><strong>900 900 120</strong></a> — <a href="https://igualtat.gencat.cat/ca/ambits-dactuacio/violencies-masclistes/linia-datencio-contra-la-violencia-masclista-900-900-120-/">Violència masclista</a>. Gratuït, confidencial i 24 hores.</li>
<li><a href="tel:017"><strong>017</strong></a> — <a href="https://www.incibe.es/linea-de-ayuda-en-ciberseguridad">Ajuda en ciberseguretat</a> (INCIBE): estafes, suplantacions i comptes robats.</li>
<li><a href="tel:012"><strong>012</strong></a> — <a href="https://web.gencat.cat/ca/contacte/012/">Atenció ciutadana de la Generalitat</a>: informació i tràmits.</li>
</ul>
{local}
<h2>Prepara't</h2>
<p>Protecció Civil recomana tenir a casa un <a href="https://interior.gencat.cat/ca/actualitat/campanyes/equip-demergencia/">equip d'emergència</a>: aigua, menjar que no es faci malbé, llanterna, ràdio amb piles, bateria per al mòbil, farmaciola i medicaments, còpia dels documents i una mica de diners en efectiu.</p>
<p>Què fer en una onada de calor, una inundació, un incendi o una apagada: <a href="https://interior.gencat.cat/ca/arees_dactuacio/proteccio_civil/consells_autoproteccio_emergencia/">consells d'autoprotecció de Protecció Civil</a>.</p>
<p class="note">Telèfons comprovats a les webs oficials. Els de la Policia Local, els Mossos i els Bombers surten de les dades obertes de la Generalitat i s'actualitzen sols.</p>
""",
        "emergency_local": "A Cerdanyola",
        "slug_aids": "ajudes", "aids_title": "Ajudes i subvencions obertes a Cerdanyola",
        "aids_desc": "Ajudes, beques i subvencions que pots demanar ara si vius a Cerdanyola del Vallès: de l'Ajuntament, la comarca, l'AMB, la Generalitat i l'Estat, amb el termini de cada una.",
        "aids_people": "Per a persones i famílies", "aids_business": "Per a autònoms i empreses", "aids_entities": "Per a entitats i associacions",
        "aids_lvl_LOCAL": "Cerdanyola, comarca i àrea metropolitana", "aids_lvl_AUTONOMICA": "Generalitat de Catalunya", "aids_lvl_ESTADO": "Estat",
        "aids_until": "Fins al {d}", "aids_approx": "Fins al {d} (aprox.)", "aids_opens": "Obre el {d}",
        "aids_check": "Termini: {t}", "aids_check_none": "Termini: consulta la convocatòria", "aids_budget": "Pressupost: {b}",
        "aids_soon": "Acaba aviat", "aids_empty": "Ara mateix no hi ha cap convocatòria oberta en aquest apartat.",
        "aids_home_title": "Ajudes que pots demanar ara",
        "aids_home_text": "{p} per a persones i famílies, {b} per a autònoms i empreses i {e} per a entitats. Les que tanquen abans:",
        "aids_all": "Veure totes les ajudes obertes",
        "aids_note": "Dades de la <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/index\">Base de Dades Nacional de Subvencions</a> (Ministeri d'Hisenda), actualitzades cada dia. Quan el termini es compta des de la publicació oficial, la data és aproximada. Abans de demanar res, llegeix les bases a la convocatòria oficial: és l'única que val. Hi ha ajudes municipals, com les bonificacions d'impostos, que no hi surten: consulta-les a l'Ajuntament. Vols que t'avisin? La BDNS envia <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/alertas\">alertes gratuïtes per correu</a>.",
        "weekend_title": "Aquest cap de setmana", "weekend_empty": "Encara no hi ha activitats anunciades per al cap de setmana.",
        "kids": "Per a infants",
        "ics_link": "📅 Vols l'agenda al mòbil? Afegeix <a href=\"{url}\">aquest calendari</a> al teu (a Google Calendar: «Altres calendaris» → «Des de l'URL») i s'actualitzarà sol.",
        "source_line": "Fonts: MET Norway (temps), Generalitat de Catalunya (agenda, equipaments i aire), Ajuntament de Cerdanyola, UAB i entitats locals (agenda), Renfe (avisos), OpenStreetMap i Overture Maps (guia d'oci), BDNS (ajudes), SOC i Diputació de Barcelona (feina), Ministeri per a la Transició Ecològica (carburants) i Red Eléctrica (llum). Actualitzat: {t}.",
        "about": "Sobre el web", "legal": "Avís legal", "privacy": "Privacitat",
        "skip": "Salta al contingut", "language": "Idioma", "choose": "Tria l'idioma",
        "notfound_title": "Pàgina no trobada", "notfound_text": "Aquesta pàgina no existeix. Torna a l'inici.",
        "about_body": """
<p>{site} reuneix en una sola pàgina dades obertes útils per a la gent de Cerdanyola del Vallès i Bellaterra: el temps, l'agenda, les hores més barates de la llum, la qualitat de l'aire i els avisos de Rodalies.</p>
<p>El web s'actualitza sol diverses vegades al dia a partir de fonts públiques. Les dades poden tenir retards o errors: per a qualsevol tràmit, consulta sempre la font oficial enllaçada.</p>
<h2>Fonts</h2>
<ul>
<li>Temps: previsió de MET Norway (Institut Meteorològic de Noruega), llicència CC BY 4.0.</li>
<li>Agenda: Ajuntament de Cerdanyola del Vallès, Agenda cultural de Catalunya (dades obertes de la Generalitat), agenda de la UAB (llicència CC BY-NC) i calendaris del Festival de Blues de Cerdanyola i d'AFOCER.</li>
<li>Equipaments, punts de recàrrega i qualitat de l'aire: dades obertes de la Generalitat de Catalunya.</li>
<li>Avisos de trens: Renfe Rodalies (GTFS-RT), llicència CC BY 4.0.</li>
<li>Guia d'oci: © col·laboradors d'<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, llicència ODbL; més locals nocturns d'<a href="https://overturemaps.org">Overture Maps Foundation</a> (dades de Meta, BrightQuery i altres proveïdors), llicència <a href="https://cdla.dev/permissive-2-0/">CDLA Permissive 2.0</a>.</li>
<li>Ajudes i subvencions: Base de Dades Nacional de Subvencions (Ministeri d'Hisenda), de reutilització lliure.</li>
<li>Feina: Servei Públic d'Ocupació de Catalunya (Feina Activa, Llicència oberta de la Generalitat) i CIDO de la Diputació de Barcelona (CC BY 4.0).</li>
<li>Preus dels carburants: Ministeri per a la Transició Ecològica i el Repte Demogràfic.</li>
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
        "agenda_desc": "Agenda de actividades de Cerdanyola del Vallès y Bellaterra: fiestas, conciertos, teatro y actos del Ajuntament, las entidades y los locales, y de la Agenda cultural de Catalunya.",
        "free": "Gratis", "src_ajuntament": "Ajuntament", "src_gencat": "Agenda cultural",
        "src_uab": "UAB", "src_blues": "Festival de Blues", "src_afocer": "AFOCER",
        "ongoing_title": "En curso", "festive": "Fiesta",
        "add_event": "¿Organizas una fiesta, un concierto o una actividad abierta al público en Cerdanyola? Si tu local o entidad tiene un calendario web (por ejemplo, WordPress con The Events Calendar), <a href=\"{repo}/issues\">cuéntalo en GitHub</a> y lo añadiremos a la agenda.",
        "slug_leisure": "ocio", "leisure_title": "Guía de ocio de Cerdanyola",
        "leisure_desc": "Qué hacer en Cerdanyola del Vallès y Bellaterra: fiestas y conciertos, rutas por Collserola, fuentes, miradores, patrimonio, museos, restaurantes, bares y pubs.",
        "festive_title": "Próximas fiestas, conciertos y noche", "festive_empty": "Ahora mismo no hay fiestas ni conciertos anunciados.",
        "plan_title": "Plan para hoy", "plan_out": "Hoy: {sky}, hasta {tmax}°. Buen día para salir; algunas ideas:",
        "plan_in": "Hoy se prevé lluvia ({mm} mm). Ideas a cubierto:", "plan_events": "Hoy hay {n} actividades en la agenda",
        "osm_note": "Lugares de <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> (© colaboradores de OpenStreetMap, licencia ODbL), por orden alfabético y sin enlaces patrocinados. ¿Falta un sitio o hay un dato mal? Cualquiera puede añadirlo o corregirlo gratis en <a href=\"https://www.openstreetmap.org/#map=15/41.4913/2.1408\">OpenStreetMap</a> y se verá aquí al día siguiente.",
        "overture_note": "Algunos locales nocturnos que aún no están en OpenStreetMap vienen de <a href=\"https://overturemaps.org\">Overture Maps Foundation</a> (datos de {src}, licencia <a href=\"https://cdla.dev/permissive-2-0/\">CDLA Permissive 2.0</a>). Salen de registros de empresas y de las páginas de los propios locales, y alguno puede haber cerrado o cambiado de nombre.",
        "directory_title": "Equipamientos públicos de Cerdanyola",
        "directory_desc": "Directorio de equipamientos públicos de Cerdanyola del Vallès: escuelas, bibliotecas, instalaciones deportivas, servicios sociales y más, con dirección y teléfono, y los precios de hoy de las gasolineras.",
        "chargers_title": "Puntos de recarga de coches eléctricos", "map": "Mapa", "phone": "Tel.",
        "quick_title": "Más información",
        "slug_jobs": "empleo",
        "jobs_title": "Empleo en Cerdanyola y alrededores",
        "jobs_desc": "Ofertas de trabajo en Cerdanyola del Vallès y los municipios vecinos, y oposiciones y bolsas de trabajo públicas abiertas en el Vallès Occidental y la UAB, actualizadas cada día.",
        "jobs_offers": "Ofertas de trabajo",
        "jobs_public": "Oposiciones y bolsas de trabajo públicas",
        "jobs_near": "En Cerdanyola y el campus de la UAB",
        "jobs_far": "Resto del Vallès Occidental",
        "jobs_pool": "Bolsa de trabajo",
        "jobs_places": "{n} plazas",
        "jobs_place": "1 plaza",
        "jobs_posted": "Publicada el {d}",
        "jobs_empty": "Ahora mismo no hay ninguna.",
        "jobs_note": "Ofertas del Servei Públic d'Ocupació de Catalunya (<a href='https://feinaactiva.gencat.cat/'>Feina Activa</a>) y convocatorias públicas del <a href='https://cido.diba.cat/'>CIDO</a> de la Diputació de Barcelona (CC BY 4.0). Solo se muestran las ofertas publicadas en los últimos 60 días: algunas pueden estar ya cubiertas. <a href='https://www.cerdanyolactiva.cat/'>Cerdanyola Activa</a> también tiene una bolsa de trabajo y orientación laboral gratuita.",
        "jobs_home": "💼 Empleo cerca",
        "jobs_home_text": "{o} ofertas de trabajo en Cerdanyola y alrededores y {p} oposiciones y bolsas públicas abiertas.",
        "jobs_all": "Ver las ofertas",
        "fuel_title": "Gasolineras: precios de hoy",
        "fuel_station": "Gasolinera",
        "fuel_g95": "Gasolina 95",
        "fuel_diesel": "Gasóleo",
        "fuel_town": "En Cerdanyola",
        "fuel_near": "Las más baratas de los municipios vecinos",
        "fuel_home": "⛽ Carburante más barato hoy en Cerdanyola",
        "fuel_home_text": "Gasolina 95: <strong>{g} €/l</strong> en {gs}. Gasóleo: <strong>{d} €/l</strong> en {ds}.",
        "fuel_more": "Ver todas las gasolineras",
        "fuel_note": "Precios en €/litro. Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico. Última actualización: {t}.",
        "slug_emergency": "emergencias", "emergency_title": "Emergencias en Cerdanyola: teléfonos y consejos",
        "emergency_desc": "Teléfonos de emergencia y de ayuda, Policia Local, Mossos y Bomberos de Cerdanyola del Vallès, y cómo prepararse para un apagón, una ola de calor o una inundación.",
        "emergency_body": """
<p class="lede">Guarda esta página. Si hay peligro para una persona, llama al <a href="tel:112"><strong>112</strong></a>.</p>
<h2>Teléfonos</h2>
<ul class="dir">
<li><a href="tel:112"><strong>112</strong></a> — Emergencias: ambulancia, bomberos y policía. Gratuito y 24 horas.</li>
<li><a href="tel:061"><strong>061</strong></a> — <a href="https://sem.gencat.cat/ca/061-salut-respon/">Salut Respon</a>: consultas de salud que no son una emergencia.</li>
<li><a href="tel:024"><strong>024</strong></a> — <a href="https://www.sanidad.gob.es/linea024/home.htm">Atención a la conducta suicida</a>. Gratuito y 24 horas.</li>
<li><a href="tel:900900120"><strong>900 900 120</strong></a> — <a href="https://igualtat.gencat.cat/ca/ambits-dactuacio/violencies-masclistes/linia-datencio-contra-la-violencia-masclista-900-900-120-/">Violencia machista</a>. Gratuito, confidencial y 24 horas.</li>
<li><a href="tel:017"><strong>017</strong></a> — <a href="https://www.incibe.es/linea-de-ayuda-en-ciberseguridad">Ayuda en ciberseguridad</a> (INCIBE): estafas, suplantaciones y cuentas robadas.</li>
<li><a href="tel:012"><strong>012</strong></a> — <a href="https://web.gencat.cat/ca/contacte/012/">Atención ciudadana de la Generalitat</a>: información y trámites.</li>
</ul>
{local}
<h2>Prepárate</h2>
<p>Protección Civil recomienda tener en casa un <a href="https://interior.gencat.cat/ca/actualitat/campanyes/equip-demergencia/">equipo de emergencia</a>: agua, comida que no se estropee, linterna, radio a pilas, batería para el móvil, botiquín y medicamentos, copia de los documentos y algo de dinero en efectivo.</p>
<p>Qué hacer en una ola de calor, una inundación, un incendio o un apagón: <a href="https://interior.gencat.cat/es/arees_dactuacio/proteccio_civil/consells_autoproteccio_emergencia/">consejos de autoprotección de Protección Civil</a>.</p>
<p class="note">Teléfonos comprobados en las webs oficiales. Los de la Policia Local, los Mossos y los Bomberos salen de los datos abiertos de la Generalitat y se actualizan solos.</p>
""",
        "emergency_local": "En Cerdanyola",
        "slug_aids": "ayudas", "aids_title": "Ayudas y subvenciones abiertas en Cerdanyola",
        "aids_desc": "Ayudas, becas y subvenciones que puedes pedir ahora si vives en Cerdanyola del Vallès: del Ajuntament, la comarca, el AMB, la Generalitat y el Estado, con el plazo de cada una.",
        "aids_people": "Para personas y familias", "aids_business": "Para autónomos y empresas", "aids_entities": "Para entidades y asociaciones",
        "aids_lvl_LOCAL": "Cerdanyola, comarca y área metropolitana", "aids_lvl_AUTONOMICA": "Generalitat de Catalunya", "aids_lvl_ESTADO": "Estado",
        "aids_until": "Hasta el {d}", "aids_approx": "Hasta el {d} (aprox.)", "aids_opens": "Abre el {d}",
        "aids_check": "Plazo: {t}", "aids_check_none": "Plazo: consulta la convocatoria", "aids_budget": "Presupuesto: {b}",
        "aids_soon": "Acaba pronto", "aids_empty": "Ahora mismo no hay ninguna convocatoria abierta en este apartado.",
        "aids_home_title": "Ayudas que puedes pedir ahora",
        "aids_home_text": "{p} para personas y familias, {b} para autónomos y empresas y {e} para entidades. Las que cierran antes:",
        "aids_all": "Ver todas las ayudas abiertas",
        "aids_note": "Datos de la <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/index\">Base de Datos Nacional de Subvenciones</a> (Ministerio de Hacienda), actualizados cada día. Cuando el plazo se cuenta desde la publicación oficial, la fecha es aproximada. Antes de pedir nada, lee las bases en la convocatoria oficial: es la única que vale. Hay ayudas municipales, como las bonificaciones de impuestos, que no aparecen aquí: consúltalas en el Ajuntament. ¿Quieres que te avisen? La BDNS envía <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/alertas\">alertas gratuitas por correo</a>.",
        "weekend_title": "Este fin de semana", "weekend_empty": "Todavía no hay actividades anunciadas para el fin de semana.",
        "kids": "Para niños",
        "ics_link": "📅 ¿Quieres la agenda en el móvil? Añade <a href=\"{url}\">este calendario</a> al tuyo (en Google Calendar: «Otros calendarios» → «Desde URL») y se actualizará solo.",
        "source_line": "Fuentes: MET Norway (tiempo), Generalitat de Catalunya (agenda, equipamientos y aire), Ajuntament de Cerdanyola, UAB y entidades locales (agenda), Renfe (avisos), OpenStreetMap y Overture Maps (guía de ocio), BDNS (ayudas), SOC y Diputació de Barcelona (empleo), Ministerio para la Transición Ecológica (carburantes) y Red Eléctrica (luz). Actualizado: {t}.",
        "about": "Sobre la web", "legal": "Aviso legal", "privacy": "Privacidad",
        "skip": "Saltar al contenido", "language": "Idioma", "choose": "Elige idioma",
        "notfound_title": "Página no encontrada", "notfound_text": "Esta página no existe. Vuelve al inicio.",
        "about_body": """
<p>{site} reúne en una sola página datos abiertos útiles para la gente de Cerdanyola del Vallès y Bellaterra: el tiempo, la agenda, las horas más baratas de la luz, la calidad del aire y los avisos de Rodalies.</p>
<p>La web se actualiza sola varias veces al día a partir de fuentes públicas. Los datos pueden tener retrasos o errores: para cualquier trámite, consulta siempre la fuente oficial enlazada.</p>
<h2>Fuentes</h2>
<ul>
<li>Tiempo: previsión de MET Norway (Instituto Meteorológico de Noruega), licencia CC BY 4.0.</li>
<li>Agenda: Ajuntament de Cerdanyola del Vallès, Agenda cultural de Catalunya (datos abiertos de la Generalitat), agenda de la UAB (licencia CC BY-NC) y calendarios del Festival de Blues de Cerdanyola y de AFOCER.</li>
<li>Equipamientos, puntos de recarga y calidad del aire: datos abiertos de la Generalitat de Catalunya.</li>
<li>Avisos de trenes: Renfe Rodalies (GTFS-RT), licencia CC BY 4.0.</li>
<li>Guía de ocio: © colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, licencia ODbL; más locales nocturnos de <a href="https://overturemaps.org">Overture Maps Foundation</a> (datos de Meta, BrightQuery y otros proveedores), licencia <a href="https://cdla.dev/permissive-2-0/">CDLA Permissive 2.0</a>.</li>
<li>Ayudas y subvenciones: Base de Datos Nacional de Subvenciones (Ministerio de Hacienda), de reutilización libre.</li>
<li>Empleo: Servei Públic d'Ocupació de Catalunya (Feina Activa, Llicència oberta de la Generalitat) y CIDO de la Diputació de Barcelona (CC BY 4.0).</li>
<li>Precios de los carburantes: Ministerio para la Transición Ecológica y el Reto Demográfico.</li>
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
        "agenda_desc": "Events in Cerdanyola del Vallès and Bellaterra: festivals, concerts, theatre and activities by the town council, local associations and venues, and the Catalan culture agenda.",
        "free": "Free", "src_ajuntament": "Town council", "src_gencat": "Culture agenda",
        "src_uab": "UAB", "src_blues": "Blues Festival", "src_afocer": "AFOCER",
        "ongoing_title": "On now", "festive": "Party",
        "add_event": "Organising a party, concert or event open to the public in Cerdanyola? If your venue or association has a web calendar (for example WordPress with The Events Calendar), <a href=\"{repo}/issues\">tell us on GitHub</a> and we'll add it to the agenda.",
        "slug_leisure": "leisure", "leisure_title": "Leisure guide to Cerdanyola",
        "leisure_desc": "Things to do in Cerdanyola del Vallès and Bellaterra: festivals and concerts, walks in Collserola, springs, viewpoints, heritage, museums, restaurants, bars and pubs.",
        "festive_title": "Upcoming festivals, concerts and nights out", "festive_empty": "There are no festivals or concerts announced right now.",
        "plan_title": "Plan for today", "plan_out": "Today: {sky}, up to {tmax}°. A good day to get out; some ideas:",
        "plan_in": "Rain is forecast today ({mm} mm). Indoor ideas:", "plan_events": "There are {n} events on today",
        "osm_note": "Places from <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> (© OpenStreetMap contributors, ODbL licence), in alphabetical order with no sponsored links. Missing a place or spotted a mistake? Anyone can add or fix it for free on <a href=\"https://www.openstreetmap.org/#map=15/41.4913/2.1408\">OpenStreetMap</a> and it will show up here the next day.",
        "overture_note": "Some night venues that are not yet on OpenStreetMap come from the <a href=\"https://overturemaps.org\">Overture Maps Foundation</a> (data from {src}, <a href=\"https://cdla.dev/permissive-2-0/\">CDLA Permissive 2.0</a> licence). They come from business registers and the venues' own pages, so some may have closed or changed name.",
        "directory_title": "Public facilities in Cerdanyola",
        "directory_desc": "Directory of public facilities in Cerdanyola del Vallès: schools, libraries, sports centres, social services and more, with address and phone number, plus today's petrol prices.",
        "chargers_title": "Electric vehicle charging points", "map": "Map", "phone": "Tel.",
        "quick_title": "More information",
        "slug_jobs": "jobs",
        "jobs_title": "Jobs in and around Cerdanyola",
        "jobs_desc": "Job offers in Cerdanyola del Vallès and neighbouring towns, plus open public-sector posts and job pools in the Vallès Occidental and at the UAB, updated daily.",
        "jobs_offers": "Job offers",
        "jobs_public": "Public-sector posts and job pools",
        "jobs_near": "In Cerdanyola and on the UAB campus",
        "jobs_far": "Rest of the Vallès Occidental",
        "jobs_pool": "Job pool",
        "jobs_places": "{n} posts",
        "jobs_place": "1 post",
        "jobs_posted": "Posted {d}",
        "jobs_empty": "There are none right now.",
        "jobs_note": "Offers from the Catalan public employment service (<a href='https://feinaactiva.gencat.cat/'>Feina Activa</a>) and public calls from the Diputació de Barcelona's <a href='https://cido.diba.cat/'>CIDO</a> (CC BY 4.0). Offers are in Catalan or Spanish, as published. Only offers posted in the last 60 days are shown: some may already be filled. <a href='https://www.cerdanyolactiva.cat/'>Cerdanyola Activa</a> also runs a job board and free career guidance.",
        "jobs_home": "💼 Jobs nearby",
        "jobs_home_text": "{o} job offers in and around Cerdanyola and {p} open public-sector posts and job pools.",
        "jobs_all": "See the offers",
        "fuel_title": "Petrol stations: today's prices",
        "fuel_station": "Station",
        "fuel_g95": "Petrol 95",
        "fuel_diesel": "Diesel",
        "fuel_town": "In Cerdanyola",
        "fuel_near": "Cheapest in neighbouring towns",
        "fuel_home": "⛽ Cheapest fuel in Cerdanyola today",
        "fuel_home_text": "Petrol 95: <strong>€{g}/l</strong> at {gs}. Diesel: <strong>€{d}/l</strong> at {ds}.",
        "fuel_more": "See all petrol stations",
        "fuel_note": "Prices in €/litre. Data source: Spanish Ministry for the Ecological Transition. Last updated: {t}.",
        "slug_emergency": "emergencies", "emergency_title": "Emergencies in Cerdanyola: phone numbers and advice",
        "emergency_desc": "Emergency and help lines, local police, Mossos and fire brigade in Cerdanyola del Vallès, and how to prepare for a power cut, a heatwave or a flood.",
        "emergency_body": """
<p class="lede">Save this page. If someone is in danger, call <a href="tel:112"><strong>112</strong></a>.</p>
<h2>Phone numbers</h2>
<ul class="dir">
<li><a href="tel:112"><strong>112</strong></a> — Emergencies: ambulance, fire brigade and police. Free, 24 hours, in English too.</li>
<li><a href="tel:061"><strong>061</strong></a> — <a href="https://sem.gencat.cat/ca/061-salut-respon/">Salut Respon</a>: health questions that are not an emergency.</li>
<li><a href="tel:024"><strong>024</strong></a> — <a href="https://www.sanidad.gob.es/linea024/home.htm">Suicide prevention line</a>. Free, 24 hours.</li>
<li><a href="tel:900900120"><strong>900 900 120</strong></a> — <a href="https://igualtat.gencat.cat/ca/ambits-dactuacio/violencies-masclistes/linia-datencio-contra-la-violencia-masclista-900-900-120-/">Gender-based violence</a>. Free, confidential, 24 hours.</li>
<li><a href="tel:017"><strong>017</strong></a> — <a href="https://www.incibe.es/linea-de-ayuda-en-ciberseguridad">Cybersecurity help line</a> (INCIBE): scams, impersonation and hacked accounts.</li>
<li><a href="tel:012"><strong>012</strong></a> — <a href="https://web.gencat.cat/ca/contacte/012/">Catalan government information line</a>.</li>
</ul>
{local}
<h2>Be prepared</h2>
<p>Civil Protection recommends keeping an <a href="https://interior.gencat.cat/ca/actualitat/campanyes/equip-demergencia/">emergency kit</a> at home: water, food that keeps, a torch, a battery radio, a power bank, a first-aid kit and medicines, copies of your documents and some cash.</p>
<p>What to do in a heatwave, flood, fire or power cut: <a href="https://interior.gencat.cat/ca/arees_dactuacio/proteccio_civil/consells_autoproteccio_emergencia/">Civil Protection self-protection advice</a> (in Catalan).</p>
<p class="note">Numbers checked on the official websites. The local police, Mossos and fire station details come from Catalan government open data and update automatically.</p>
""",
        "emergency_local": "In Cerdanyola",
        "slug_aids": "grants", "aids_title": "Open grants and benefits for Cerdanyola residents",
        "aids_desc": "Grants, scholarships and benefits you can apply for now if you live in Cerdanyola del Vallès: from the town council, the county, the metropolitan area, the Catalan government and the Spanish state, with each deadline.",
        "aids_people": "For individuals and families", "aids_business": "For self-employed and businesses", "aids_entities": "For non-profits and associations",
        "aids_lvl_LOCAL": "Cerdanyola, county and metropolitan area", "aids_lvl_AUTONOMICA": "Catalan government", "aids_lvl_ESTADO": "Spanish state",
        "aids_until": "Until {d}", "aids_approx": "Until about {d}", "aids_opens": "Opens {d}",
        "aids_check": "Deadline: {t}", "aids_check_none": "Deadline: see the official call", "aids_budget": "Budget: {b}",
        "aids_soon": "Closing soon", "aids_empty": "There are no open calls in this section right now.",
        "aids_home_title": "Grants you can apply for now",
        "aids_home_text": "{p} for individuals and families, {b} for self-employed and businesses and {e} for non-profits. Closing soonest:",
        "aids_all": "See all open grants",
        "aids_note": "Data from Spain's <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/index\">National Grants Database</a> (BDNS, Ministry of Finance), updated daily. Titles are in Spanish or Catalan, as published. When the deadline counts from the official publication, the date is approximate. Before applying, read the rules in the official call: it is the only one that counts. Some local benefits, such as tax rebates, are not listed: ask the town council. Want alerts? The BDNS sends <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/alertas\">free email alerts</a>.",
        "weekend_title": "This weekend", "weekend_empty": "No events have been announced for the weekend yet.",
        "kids": "For children",
        "ics_link": "📅 Want the events on your phone? Add <a href=\"{url}\">this calendar</a> to yours (in Google Calendar: “Other calendars” → “From URL”) and it will update itself.",
        "source_line": "Sources: MET Norway (weather), Generalitat de Catalunya (events, facilities and air), Cerdanyola town council, UAB and local associations (events), Renfe (alerts), OpenStreetMap and Overture Maps (leisure guide), BDNS (grants), SOC and Diputació de Barcelona (jobs), Ministry for the Ecological Transition (fuel) and Red Eléctrica (electricity). Updated: {t}.",
        "about": "About", "legal": "Legal notice", "privacy": "Privacy",
        "skip": "Skip to content", "language": "Language", "choose": "Choose your language",
        "notfound_title": "Page not found", "notfound_text": "This page does not exist. Go back to the home page.",
        "about_body": """
<p>{site} brings together useful open data for people in Cerdanyola del Vallès and Bellaterra on a single page: weather, events, the cheapest electricity hours, air quality and Rodalies train alerts.</p>
<p>The site updates itself several times a day from public sources. Data may be delayed or contain errors: always check the linked official source before acting on it.</p>
<h2>Sources</h2>
<ul>
<li>Weather: MET Norway (Norwegian Meteorological Institute) forecast, CC BY 4.0 licence.</li>
<li>Events: Cerdanyola del Vallès town council, the Catalan culture agenda (Generalitat open data), the UAB events page (CC BY-NC licence) and the calendars of the Cerdanyola Blues Festival and AFOCER.</li>
<li>Facilities, charging points and air quality: Generalitat de Catalunya open data.</li>
<li>Train alerts: Renfe Rodalies (GTFS-RT), CC BY 4.0 licence.</li>
<li>Leisure guide: © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, ODbL licence; more night venues from the <a href="https://overturemaps.org">Overture Maps Foundation</a> (data from Meta, BrightQuery and other providers), <a href="https://cdla.dev/permissive-2-0/">CDLA Permissive 2.0</a> licence.</li>
<li>Grants: Spain's National Grants Database (BDNS, Ministry of Finance), free to reuse.</li>
<li>Jobs: Catalan public employment service (Feina Activa, Catalan open licence) and the Diputació de Barcelona's CIDO (CC BY 4.0).</li>
<li>Fuel prices: Spanish Ministry for the Ecological Transition.</li>
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


def agenda_cat(lang, cat):
    if lang == "ca" or not cat:
        return cat
    es, en = AGENDA_CATS.get(cat, (cat, cat))
    return es if lang == "es" else en


def _pick(lang, triple):
    return triple[("ca", "es", "en").index(lang)]


def place_type(lang, kind):
    return _pick(lang, PLACE_TYPES[kind]) if kind in PLACE_TYPES else kind.replace("_", " ")


def cuisine(lang, value):
    return ", ".join(_pick(lang, CUISINES[c]) if c in CUISINES else c.replace("_", " ")
                     for c in (x.strip() for x in value.split(";")) if c)


def group(lang, key):
    icon, *names = LEISURE_GROUPS[key]
    return icon, _pick(lang, names)


def hours(lang, value):
    words = HOURS[lang]
    return re.sub(r"\b(Mo|Tu|We|Th|Fr|Sa|Su|PH|off|closed)\b", lambda m: words.get(m.group(1), m.group(1)), value)


def fmt_money(lang, x):
    s = f"{round(x):,}"
    return f"€{s}" if lang == "en" else s.replace(",", ".") + " €"


def fmt_deadline(lang, d, today):
    s = fmt_date(lang, d, weekday=False)
    if d.year == today.year:
        return s
    return f"{s} {d.year}" if lang == "en" else f"{s} de {d.year}"


_SMALL_WORDS = {"de", "del", "dels", "la", "las", "los", "el", "els", "les", "i", "y", "d", "l", "a", "al", "en", "per", "para"}


def organ_name(name):
    """«AGÈNCIA DE GESTIÓ D'AJUTS (AGAUR)» -> «Agència de Gestió d'Ajuts (AGAUR)»: siglas entre paréntesis intactas."""
    out = []
    for i, part in enumerate(re.split(r"(\([^)]*\))", name or "")):
        if part.startswith("("):
            out.append(part)
            continue
        words = re.split(r"(\w+)", part.lower())
        out.append("".join(w if w in _SMALL_WORDS and (i or j > 1) else w.capitalize() for j, w in enumerate(words)))
    return "".join(out).strip()
