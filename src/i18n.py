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

# Tiempo: palabra clave del código de MET Norway -> (es, ca, en); el icono es static/wx/<clave>.svg
SKY = [
    ("thunder", "Tormenta", "Tempesta", "Thunderstorm"),
    ("snow", "Nieve", "Neu", "Snow"),
    ("sleet", "Aguanieve", "Aiguaneu", "Sleet"),
    ("heavyrain", "Lluvia fuerte", "Pluja forta", "Heavy rain"),
    ("showers", "Chubascos", "Ruixats", "Showers"),
    ("lightrain", "Lluvia débil", "Pluja feble", "Light rain"),
    ("rain", "Lluvia", "Pluja", "Rain"),
    ("fog", "Niebla", "Boira", "Fog"),
    ("partlycloudy", "Parcialmente nublado", "Parcialment ennuvolat", "Partly cloudy"),
    ("cloudy", "Nublado", "Ennuvolat", "Cloudy"),
    ("fair", "Poco nuboso", "Poc ennuvolat", "Mostly clear"),
    ("clearsky", "Despejado", "Serè", "Clear sky"),
]
SKY_COL = {"es": 1, "ca": 2, "en": 3}

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

# grupos de la guía de ocio: icono (Lucide), ca, es, en (en el orden en que salen en la página)
LEISURE_GROUPS = {
    "nature": ("trees", "Natura, parcs i fonts", "Naturaleza, parques y fuentes", "Nature, parks and springs"),
    "routes": ("footprints", "Rutes a peu i en bici", "Rutas a pie y en bici", "Walking and cycling routes"),
    "heritage": ("landmark", "Patrimoni", "Patrimonio", "Heritage"),
    "culture": ("drama", "Cultura i lleure", "Cultura y ocio", "Culture and entertainment"),
    "eat": ("utensils", "Restaurants", "Restaurantes", "Restaurants"),
    "drink": ("coffee", "Bars i cafeteries", "Bares y cafeterías", "Bars and cafés"),
    "night": ("moon", "Nit: pubs, discoteques i música", "Noche: pubs, discotecas y música", "Nightlife: pubs, clubs and live music"),
    "sport": ("trophy", "Esport", "Deporte", "Sport"),
    "community": ("handshake", "Centres cívics i entitats", "Centros cívicos y entidades", "Community centres and associations"),
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

CONTRACT_PHASES = {  # fase de la Plataforma de contractació pública -> ca, es, en
    "Alerta futura": ("Previst", "Previsto", "Planned"),
    "Consulta preliminar del mercat": ("Consulta al mercat", "Consulta al mercado", "Market consultation"),
    "Anunci previ": ("Anunci previ", "Anuncio previo", "Prior notice"),
    "Anunci de licitació": ("En licitació", "En licitación", "Open for bids"),
    "closed_bids": ("Ofertes tancades", "Ofertas cerradas", "Bidding closed"),
    "Expedient en avaluació": ("En avaluació", "En evaluación", "Under evaluation"),
    "Adjudicació": ("Adjudicat", "Adjudicado", "Awarded"),
    "Formalització": ("Contracte signat", "Contrato firmado", "Contract signed"),
    "Execució": ("En execució", "En ejecución", "Under way"),
    "Anul·lació": ("Anul·lat", "Anulado", "Cancelled"),
}

CONTRACT_TYPES = {  # tipo de contrato (viene en catalán) -> es, en
    "Obres": ("Obras", "Works"), "Serveis": ("Servicios", "Services"), "Subministraments": ("Suministros", "Supplies"),
    "Concessió de serveis": ("Concesión de servicios", "Service concession"),
    "Concessió d'obres": ("Concesión de obras", "Works concession"),
    "Administratiu especial": ("Administrativo especial", "Special administrative contract"),
    "Privat d'Administració Pública": ("Privado de la Administración", "Private contract"),
    "Contracte de serveis especials (annex IV)": ("Servicios especiales", "Special services"),
    "Concessió de serveis especials (annex IV)": ("Concesión de servicios especiales", "Special service concession"),
    "Altra legislació sectorial": ("Otra legislación sectorial", "Other"),
    "Col·laboració Públic-Privat": ("Colaboración público-privada", "Public-private partnership"),
}

# actos del BORME, en el orden en que salen en la página: ca, es, en
COMPANY_KINDS = {
    "capital": ("Ampliacions de capital", "Ampliaciones de capital", "Capital increases"),
    "new": ("Empreses noves", "Empresas nuevas", "New companies"),
    "moved_in": ("Arriben a Cerdanyola", "Llegan a Cerdanyola", "Moved to Cerdanyola"),
    "moved_out": ("Se'n van de Cerdanyola", "Se van de Cerdanyola", "Left Cerdanyola"),
    "capital_down": ("Reduccions de capital", "Reducciones de capital", "Capital reductions"),
    "closed": ("Dissolucions i tancaments", "Disoluciones y cierres", "Wound up or closed"),
}

STRINGS = {
    "ca": {
        "lang_name": "Català", "locale": "ca_ES",
        "slug_agenda": "agenda", "slug_directory": "equipaments", "slug_about": "sobre-el-web",
        "slug_legal": "avis-legal", "slug_privacy": "privacitat",
        "home_title": "Cerdanyola del Vallès avui: temps, agenda, llum i transport",
        "home_desc": "El que passa avui a Cerdanyola del Vallès i Bellaterra: previsió del temps, agenda d'activitats, hores més barates de la llum, avisos de Rodalies R7 i R8, qualitat de l'aire, guia d'oci, ajudes, feina, inversions i maneres d'estalviar.",
        "tagline": "Dades obertes útils per a la gent de Cerdanyola i Bellaterra, actualitzades soles cada dia.",
        "now": "Ara",
        "weather_title": "El temps",
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
        "slug_picks": "recomanacions", "picks_title": "Recomanacions de la setmana a Cerdanyola",
        "picks_desc": "Restaurants, bars i experiències especials de Cerdanyola del Vallès i Bellaterra triats a mà. Cada setmana en surten uns altres.",
        "picks_home": "Recomanat aquesta setmana", "picks_more": "Més detalls de les recomanacions",
        "picks_week": "Selecció de la setmana del {d}. Dilluns que ve en canvien.",
        "picks_food": "On menjar", "picks_experience": "Què fer",
        "picks_note": "Llista feta a mà ({n} llocs) a partir de la reputació pública de cada local, sense cap pagament ni acord comercial. Abans d'anar-hi, comprova horaris i obertura al seu web. Trobes a faltar un lloc o n'ha tancat algun? <a href=\"{repo}/issues\">Digues-nos-ho a GitHub</a>.",
        "slug_save": "estalvia", "save_title": "Estalvia a Cerdanyola",
        "save_desc": "Maneres reals d'estalviar a Cerdanyola del Vallès i Bellaterra, actualitzades cada dia: les hores més barates de la llum, la benzinera més barata, activitats gratuïtes, ajudes per a particulars i descomptes oficials.",
        "save_home": "Estalvia a Cerdanyola", "save_all": "Totes les maneres d'estalviar",
        "save_home_text": "Llum, carburant, activitats gratuïtes, ajudes i descomptes oficials, en una sola pàgina.",
        "save_home_fuel": "Avui, omplir {l} L de gasolina a la benzinera més barata de Cerdanyola estalvia <strong>{e} €</strong> respecte a la més cara.",
        "save_home_free": "Activitats gratuïtes el pròxim mes: <strong>{n}</strong>.",
        "save_fuel": "La benzinera més barata",
        "save_fuel_text": "Gasolina 95 avui: la més barata és {c} a <strong>{cp} €/l</strong> i la més cara, {d} a {dp} €/l. En un dipòsit de {l} L hi ha <strong>{e} €</strong> de diferència.",
        "save_free": "Activitats gratuïtes el pròxim mes",
        "save_free_empty": "Ara mateix no hi ha cap activitat marcada com a gratuïta a l'agenda. Moltes activitats municipals ho són: mira l'agenda completa.",
        "save_free_note": "Només hi surten les activitats que la font marca com a gratuïtes o que ho diuen al títol.",
        "save_aids": "Ajudes que pots demanar com a particular",
        "save_aids_text": "Ajudes amb termini obert per a particulars i famílies: {n}. Aquestes són les més properes:",
        "save_links": "Descomptes i tarifes socials que val la pena conèixer",
        "save_links_body": """<ul class="months">
<li><a href="https://www.miteco.gob.es/es/energia/pobreza-energetica/pe-001.html">Bo social elèctric i tèrmic</a>: descompte a la factura de la llum per a llars amb pocs ingressos, famílies nombroses i alguns pensionistes.</li>
<li><a href="https://www.aiguesdebarcelona.cat/ca/el-teu-servei-daigua/bonificacions">Tarifa social de l'aigua</a> d'Aigües de Barcelona, que dona servei a Cerdanyola, i bonificacions per a famílies nombroses i monoparentals.</li>
<li><a href="https://www.atm.cat/titols-i-tarifes">T-Jove, T-Usual i altres títols de transport</a> de l'ATM: per a qui agafa Rodalies, FGC o bus sovint, solen sortir molt més a compte que els bitllets senzills.</li>
<li><a href="https://bibliotecavirtual.diba.cat/">Biblioteques de la Diputació</a>: llibres, pel·lícules, revistes i cursos gratis amb el carnet.</li>
<li><a href="https://www.amb.cat/s/web/medi-ambient/residus.html">Deixalleria</a>: fer-la servir amb el carnet d'usuari pot donar descompte a la taxa de residus; pregunta-ho a l'Ajuntament.</li>
<li><a href="https://subastas.boe.es/">Portal de Subhastes del BOE</a>: subhastes judicials, d'Hisenda i de la Seguretat Social de pisos, vehicles i altres béns; s'hi pot buscar per municipi.</li>
</ul>""",
        "save_note": "Informació orientativa: comprova sempre les condicions a la font oficial. Aquest web no cobra comissions ni té acords amb cap comerç. Si saps d'una campanya de descomptes del comerç local o de l'Ajuntament, <a href=\"{repo}/issues\">explica-ho a GitHub</a>.",
        "slug_leisure": "oci", "leisure_title": "Guia d'oci de Cerdanyola",
        "leisure_desc": "Què fer a Cerdanyola del Vallès i Bellaterra: festes i concerts, rutes per Collserola, fonts, miradors, patrimoni, museus, restaurants, bars i pubs.",
        "festive_title": "Properes festes, concerts i nit", "festive_empty": "Ara mateix no hi ha festes ni concerts anunciats.",
        "plan_title": "Pla per avui", "plan_out": "Avui: {sky}, fins a {tmax}°. Bon dia per sortir; algunes idees:",
        "plan_in": "Avui es preveu pluja ({mm} mm). Idees a cobert:", "plan_events": "Activitats d'avui a l'agenda: {n}",
        "osm_note": "Llocs d'<a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> (© col·laboradors d'OpenStreetMap, llicència ODbL), en ordre alfabètic i sense enllaços patrocinats. Hi falta un lloc o hi ha una dada malament? Qualsevol persona el pot afegir o corregir gratis a <a href=\"https://www.openstreetmap.org/#map=15/41.4913/2.1408\">OpenStreetMap</a> i es veurà aquí l'endemà.",
        "overture_note": "Alguns locals nocturns que encara no són a OpenStreetMap venen d'<a href=\"https://overturemaps.org\">Overture Maps Foundation</a> (dades de {src}, llicència <a href=\"https://cdla.dev/permissive-2-0/\">CDLA Permissive 2.0</a>). Surten de registres d'empreses i de les pàgines dels mateixos locals, i algun pot haver tancat o canviat de nom.",
        "directory_title": "Equipaments públics de Cerdanyola",
        "directory_desc": "Directori d'equipaments públics de Cerdanyola del Vallès: escoles, biblioteques, instal·lacions esportives, serveis socials i més, amb adreça i telèfon, i els preus d'avui de les benzineres.",
        "chargers_title": "Punts de recàrrega de vehicles elèctrics", "map": "Mapa", "phone": "Tel.",
        "quick_title": "Més informació",
        "slug_jobs": "feina",
        "jobs_title": "Feina a Cerdanyola i rodalia",
        "jobs_desc": "Ofertes de feina a Cerdanyola del Vallès i als municipis veïns, i oposicions i borses de treball públiques obertes al Vallès Occidental i a la UAB, actualitzades cada dia.",
        "jobs_offers": "Ofertes de feina",
        "jobs_public": "Oposicions i borses de treball públiques",
        "jobs_near": "A menys de 5 km",
        "jobs_far": "Resta del Vallès Occidental",
        "jobs_pool": "Borsa de treball",
        "jobs_places": "{n} places",
        "jobs_place": "1 plaça",
        "jobs_posted": "Publicada el {d}",
        "jobs_empty": "Ara mateix no n'hi ha cap.",
        "jobs_note": "Ofertes del Servei Públic d'Ocupació de Catalunya (<a href='https://feinaactiva.gencat.cat/'>Feina Activa</a>) i convocatòries públiques del <a href='https://cido.diba.cat/'>CIDO</a> de la Diputació de Barcelona (CC BY 4.0). Només es mostren les ofertes publicades els darrers 60 dies: algunes ja poden estar cobertes. <a href='https://www.cerdanyolactiva.cat/'>Cerdanyola Activa</a> també té una borsa de treball i orientació laboral gratuïta.",
        "jobs_home": "Feina a prop",
        "jobs_home_text": "{o} ofertes de feina a Cerdanyola i rodalia i {p} oposicions i borses públiques obertes.",
        "jobs_all": "Veure les ofertes",
        "fuel_title": "Benzineres: preus d'avui",
        "fuel_station": "Benzinera",
        "fuel_g95": "Gasolina 95",
        "fuel_diesel": "Gasoil",
        "fuel_town": "A Cerdanyola",
        "fuel_near": "Les més barates dels municipis veïns",
        "fuel_home": "Carburant més barat avui a Cerdanyola",
        "fuel_home_text": "Gasolina 95: <strong>{g} €/l</strong> a {gs}. Gasoil: <strong>{d} €/l</strong> a {ds}.",
        "fuel_more": "Veure totes les benzineres",
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
        "ics_link": "Vols l'agenda al mòbil? Afegeix <a href=\"{url}\">aquest calendari</a> al teu (a Google Calendar: «Altres calendaris» → «Des de l'URL») i s'actualitzarà sol.",
        "slug_invest": "inversions", "invest_title": "Inversions i empreses a Cerdanyola",
        "invest_desc": "Grans inversions públiques a Cerdanyola del Vallès i Bellaterra, licitacions obertes per a empreses i autònoms, contractes anunciats, i empreses noves, trasllats i ampliacions de capital del Registre Mercantil.",
        "invest_big": "Grans inversions públiques",
        "invest_big_text": "Contractes públics d'1 milió d'euros o més a Cerdanyola i al campus de la UAB amb novetats l'últim any, del més gran al més petit.",
        "invest_open": "Licitacions obertes",
        "invest_open_text": "Contractes públics a Cerdanyola que ara accepten ofertes d'empreses i autònoms, per data de tancament.",
        "invest_soon": "Properament",
        "invest_soon_text": "Contractes que l'administració ha anunciat que traurà a licitació.",
        "invest_companies": "Empreses: altes, trasllats i capital",
        "invest_companies_text": "Els darrers {d} dies, al Registre Mercantil: {n} empreses noves amb domicili a Cerdanyola o Bellaterra (capital inicial total: {c}), {m} trasllats a Cerdanyola i {u} ampliacions de capital.",
        "invest_empty": "Ara mateix no n'hi ha cap.",
        "invest_until": "ofertes fins al {d}", "invest_lots": "{n} lots", "invest_winners": "Adjudicat a: {w}",
        "invest_capital": "Capital: {c}", "invest_capital_change": "{c} (capital resultant: {t})",
        "invest_feed": "Vols que t'avisin? Afegeix <a href=\"{url}\">aquest canal</a> a un lector de notícies (Feedly, Inoreader, Thunderbird...) i rebràs cada licitació, gran inversió o moviment d'empreses nou.",
        "invest_note": "Contractes: <a href=\"https://contractaciopublica.cat/\">Plataforma de serveis de contractació pública</a> (dades obertes de la Generalitat). Hi publiquen l'Ajuntament, la Generalitat, l'AMB, la UAB i els centres de recerca del campus; les inversions de l'Estat (sincrotró ALBA, Adif...) no hi surten. Imports sense IVA: el pressupost de licitació o, si ja s'ha adjudicat, l'import adjudicat. Empreses: <a href=\"https://www.boe.es/diario_borme/\">BORME</a> (Agència Estatal Butlletí Oficial de l'Estat), llegit fins al {t}; només hi surten empreses, sense dades de persones. Els trasllats, els canvis de capital i els tancaments només es detecten d'empreses que s'han constituït o traslladat a Cerdanyola des del {since}. Aquesta pàgina és informativa: no és cap recomanació ni assessorament d'inversió.",
        "invest_home": "Inversions i empreses",
        "invest_home_text": "{o} licitacions públiques obertes, {b} grans inversions (d'1 milió d'euros o més) amb novetats l'últim any i {n} empreses noves o arribades a Cerdanyola els darrers {d} dies. Les darreres grans inversions:",
        "invest_all": "Veure inversions, licitacions i empreses",
        "source_line": "Fonts: MET Norway (temps), Generalitat de Catalunya (agenda, equipaments, aire i contractes públics), Ajuntament de Cerdanyola, UAB i entitats locals (agenda), Renfe (avisos), OpenStreetMap i Overture Maps (guia d'oci), BDNS (ajudes), SOC i Diputació de Barcelona (feina), BORME (empreses), Ministeri per a la Transició Ecològica (carburants) i Red Eléctrica (llum). Actualitzat: {t}.",
        "about": "Sobre el web", "legal": "Avís legal", "privacy": "Privacitat",
        "studio": "L'autor",
        "donate": "Dona suport al projecte",
        "skip": "Salta al contingut", "language": "Idioma", "choose": "Tria l'idioma",
        "sections": "Seccions", "nav_home": "Inici", "nav_agenda": "Agenda", "nav_leisure": "Oci",
        "nav_picks": "Recomanacions", "nav_save": "Estalvia", "nav_aids": "Ajudes", "nav_jobs": "Feina",
        "nav_invest": "Inversions", "nav_directory": "Equipaments", "nav_emergency": "112",
        "theme_auto": "Tema: automàtic", "theme_light": "Tema: clar", "theme_dark": "Tema: fosc",
        "install_title": "Porta Cerdanyola Avui al mòbil.", "install_text": "Instal·la-la com una app: icona a la pantalla d'inici, pantalla completa i les últimes dades encara que caigui la connexió. Sense botigues ni comptes.",
        "install_button": "Instal·la l'app", "install_ios_q": "Tens un iPhone o un iPad?",
        "install_ios": "Obre aquesta web amb el Safari, toca el botó Compartir (el quadrat amb la fletxa) i tria «Afegeix a la pantalla d'inici».",
        "offline_title": "Sense connexió", "offline_text": "No s'ha pogut carregar aquesta pàgina. Torna-ho a provar quan tinguis connexió o ves a l'inici.",
        "notfound_title": "Pàgina no trobada", "notfound_text": "Aquesta pàgina no existeix. Torna a l'inici.",
        "about_body": """
<p>{site} reuneix en una sola pàgina dades obertes útils per a la gent de Cerdanyola del Vallès i Bellaterra: el temps, l'agenda, les hores més barates de la llum, els avisos de Rodalies, la qualitat de l'aire, una guia d'oci, les ajudes obertes, la feina, les inversions públiques i maneres d'estalviar.</p>
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
<li>Inversions i licitacions: Plataforma de serveis de contractació pública (dades obertes de la Generalitat). Empreses: BORME, de l'Agència Estatal Butlletí Oficial de l'Estat, de reutilització lliure citant-ne la font.</li>
<li>Preus dels carburants: Ministeri per a la Transició Ecològica i el Repte Demogràfic.</li>
<li>Recomanacions de restaurants i experiències: llista feta a mà, sense pagaments ni acords comercials; no reproduïm valoracions ni ressenyes de cap plataforma.</li>
<li>Preu de la llum: Red Eléctrica, a través del web germà <a href="{light}">{light}</a>.</li>
</ul>
<p>El codi és obert i és a <a href="{repo}">GitHub</a>, on pots avisar d'errors o proposar millores.</p>
""",
        "legal_body": """
<p>{site} és un projecte gratuït i informatiu, sense relació amb l'Ajuntament de Cerdanyola del Vallès ni amb cap altra administració.</p>
<h2>Titular</h2><p>{owner}</p>
<h2>Responsabilitat</h2><p>La informació prové de fonts públiques citades a cada apartat i s'ofereix tal com és, sense garantia. Consulta sempre la font oficial abans de prendre decisions.</p>
<h2>Continguts dels usuaris</h2><p>Els anuncis del <a href="{board}">tauler veïnal</a> els publiquen els mateixos veïns i no es revisen abans de publicar-se. {site} no participa en cap tracte ni garanteix el que s'hi anuncia. Si veus un anunci il·lícit o ofensiu, fes servir el botó «Denuncia» o escriu al titular: es retirarà tan aviat com se'n tingui coneixement (article 16 de la LSSI).</p>
""",
        "privacy_body": """
<p>Aquest web no fa servir galetes i no té analítica ni publicitat. L'única part que tracta dades personals és el <a href="{board}">tauler veïnal</a>, explicat més avall.</p>
<p>Si tries el tema clar o fosc, la preferència es desa només al teu navegador (localStorage) i no s'envia enlloc.</p>
<p>Està allotjat a GitHub Pages. Com qualsevol servidor web, GitHub registra l'adreça IP de les visites per motius de seguretat. Més informació a la <a href="https://docs.github.com/es/site-policy/privacy-policies/github-general-privacy-statement">declaració de privacitat de GitHub</a>.</p>
<h2>Tauler veïnal</h2>
<p>Responsable del tractament: {owner}</p>
<p>Quan publiques un anunci es guarden el text, el nom o àlies, el contacte que vulguis mostrar i el teu correu electrònic. El correu no es publica mai: només serveix per confirmar l'anunci, enviar-te les respostes dels veïns i avisar-te abans que caduqui. Quan respons a un anunci, el teu missatge i el teu correu s'envien a l'autor i no es guarden. Base jurídica: el teu consentiment (article 6.1.a del RGPD).</p>
<p>Per evitar abusos es guarda un resum (hash amb sal) de l'adreça IP, del qual no es pot recuperar l'adreça. Els anuncis caduquen als 45 dies i s'esborren del tot set dies després; pots esborrar-los abans amb l'enllaç del correu de confirmació o escrivint al responsable. També pots demanar accés, rectificació o supressió per correu, i reclamar davant l'<a href="https://www.aepd.es">Agència Espanyola de Protecció de Dades</a>.</p>
<p>Les dades es guarden als servidors de Cloudflare i els correus s'envien amb Gmail (Google). A la pàgina del tauler s'executa <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare Turnstile</a> per distingir persones de robots; no fa servir galetes de seguiment.</p>
""",
        "slug_board": "tauler",
        "nav_board": "Tauler",
        "board_title": "Tauler veïnal de Cerdanyola",
        "board_desc": "Tauler d'anuncis entre veïns de Cerdanyola del Vallès i Bellaterra: demana ajuda, regala el que ja no fas servir i troba gangues de comerços i particulars.",
        "board_intro": "Un espai perquè els veïns s'ajudin: demana un cop de mà o suport per a un projecte, regala el que ja no necessites o publica gangues i segona mà. Sense registre: només un nom i un correu, que no es mostra mai.",
        "board_cat_help": "Ajuda'm",
        "board_cat_give": "Ho regalo",
        "board_cat_deal": "Gangues",
        "board_cat_all": "Tot",
        "board_cat_help_desc": "Demana un cop de mà amb una tasca o suport per a un projecte.",
        "board_cat_give_desc": "Regala el que ja no fas servir.",
        "board_cat_deal_desc": "Segona mà i ofertes de comerços locals i particulars.",
        "board_new": "Publica un anunci",
        "board_empty": "Encara no hi ha cap anunci aquí. Sigues el primer!",
        "board_loading": "Carregant els anuncis…",
        "board_nojs": "Per publicar, respondre o denunciar cal JavaScript.",
        "board_static_note": "Llista actualitzada quatre vegades al dia; amb JavaScript es mostra al moment.",
        "board_offline": "El tauler encara no està en marxa. Torna-hi aviat.",
        "board_reply": "Respon",
        "board_report": "Denuncia",
        "board_rules": "<ul><li>Només per a veïns de Cerdanyola i Bellaterra: particulars i comerços locals.</li><li>Els anuncis caduquen als 45 dies; es poden renovar o esborrar des del correu de confirmació.</li><li>No publiquis dades de tercers ni dades bancàries. No enviïs mai diners per avançat: el web no fa d'intermediari ni garanteix res.</li><li>Els anuncis denunciats per diversos veïns s'amaguen automàticament.</li></ul>",
        "board_privacy": "El correu només serveix per confirmar l'anunci i rebre'n les respostes; no es publica mai. Més detalls a la <a href=\"{privacy}\">política de privacitat</a>.",
        "board_f_cat": "Categoria",
        "board_f_title": "Títol",
        "board_f_body": "Text",
        "board_f_name": "Nom o àlies",
        "board_f_email": "Correu electrònic (no es mostra)",
        "board_f_contact": "Telèfon, WhatsApp o Telegram (opcional; es mostrarà)",
        "board_f_price": "Preu (opcional)",
        "board_f_consent": "Accepto les normes i que es publiqui l'anunci amb el nom i el contacte que he indicat.",
        "board_f_message": "Missatge",
        "board_f_reply_email": "El teu correu (perquè et puguin respondre)",
        "board_f_reason": "Motiu (opcional)",
        "board_submit": "Envia",
        "board_cancel": "Cancel·la",
        "board_sent": "T'hem enviat un correu. Fes clic a l'enllaç per publicar l'anunci (mira també la carpeta de correu brossa).",
        "board_reply_sent": "Missatge enviat. Si l'autor et respon, ho rebràs al teu correu.",
        "board_report_sent": "Gràcies per l'avís. Ho revisarem.",
        "board_err_rate": "Has fet massa enviaments avui. Torna-ho a provar demà.",
        "board_err_filtered": "El text conté paraules o dades no permeses (insults, dades bancàries…). Revisa'l.",
        "board_err_turnstile": "No hem pogut comprovar que no ets un robot. Torna-ho a provar.",
        "board_err_full": "El tauler és ple. Torna-ho a provar d'aquí a uns dies.",
        "board_err_mail_quota": "Avui ja no podem enviar més correus. Torna-ho a provar demà.",
        "board_err_invalid": "Revisa els camps: falta alguna dada o és massa llarga.",
        "board_err_notfound": "Aquest anunci ja no existeix.",
        "board_err_network": "No s'ha pogut connectar amb el tauler. Torna-ho a provar.",
        "board_err_generic": "S'ha produït un error. Torna-ho a provar més tard.",
        "board_expires": "caduca el {d}",
        "board_posted": "publicat el {d}",
        "board_contact_show": "Mostra el contacte",
        "board_reply_title": "Respon a l'anunci",
        "board_report_title": "Denuncia l'anunci",
        "board_report_hint": "Denuncia només anuncis amb estafes, insults, dades de tercers o que no tinguin res a veure amb Cerdanyola.",
        "board_home": "Tauler veïnal",
        "board_home_text": "Demana ajuda, regala el que ja no fas servir o troba gangues entre veïns.",
        "board_home_n": "{n} anuncis actius.",
        "board_all": "Veure el tauler",
        "owner_missing": "Projecte personal sense ànim de lucre. Contacte: a través del <a href=\"{repo}\">repositori a GitHub</a>.",
    },
    "es": {
        "lang_name": "Español", "locale": "es_ES",
        "slug_agenda": "agenda", "slug_directory": "equipamientos", "slug_about": "sobre-la-web",
        "slug_legal": "aviso-legal", "slug_privacy": "privacidad",
        "home_title": "Cerdanyola del Vallès hoy: tiempo, agenda, luz y transporte",
        "home_desc": "Lo que pasa hoy en Cerdanyola del Vallès y Bellaterra: previsión del tiempo, agenda de actividades, horas más baratas de la luz, avisos de Rodalies R7 y R8, calidad del aire, guía de ocio, ayudas, empleo, inversiones y formas de ahorrar.",
        "tagline": "Datos abiertos útiles para la gente de Cerdanyola y Bellaterra, actualizados solos cada día.",
        "now": "Ahora",
        "weather_title": "El tiempo",
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
        "agenda_desc": "Agenda de actividades de Cerdanyola del Vallès y Bellaterra: fiestas, conciertos, teatro y actos del Ayuntamiento, las entidades y los locales, y de la Agenda cultural de Catalunya.",
        "free": "Gratis", "src_ajuntament": "Ajuntament", "src_gencat": "Agenda cultural",
        "src_uab": "UAB", "src_blues": "Festival de Blues", "src_afocer": "AFOCER",
        "ongoing_title": "En curso", "festive": "Fiesta",
        "add_event": "¿Organizas una fiesta, un concierto o una actividad abierta al público en Cerdanyola? Si tu local o entidad tiene un calendario web (por ejemplo, WordPress con The Events Calendar), <a href=\"{repo}/issues\">cuéntalo en GitHub</a> y lo añadiremos a la agenda.",
        "slug_picks": "recomendaciones", "picks_title": "Recomendaciones de la semana en Cerdanyola",
        "picks_desc": "Restaurantes, bares y experiencias especiales de Cerdanyola del Vallès y Bellaterra elegidos a mano. Cada semana salen otros.",
        "picks_home": "Recomendado esta semana", "picks_more": "Más detalles de las recomendaciones",
        "picks_week": "Selección de la semana del {d}. El lunes que viene cambian.",
        "picks_food": "Dónde comer", "picks_experience": "Qué hacer",
        "picks_note": "Lista hecha a mano ({n} sitios) a partir de la reputación pública de cada local, sin ningún pago ni acuerdo comercial. Antes de ir, comprueba horarios y apertura en su web. ¿Echas de menos un sitio o ha cerrado alguno? <a href=\"{repo}/issues\">Dínoslo en GitHub</a>.",
        "slug_save": "ahorra", "save_title": "Ahorra en Cerdanyola",
        "save_desc": "Formas reales de ahorrar en Cerdanyola del Vallès y Bellaterra, actualizadas cada día: las horas más baratas de la luz, la gasolinera más barata, actividades gratuitas, ayudas para particulares y descuentos oficiales.",
        "save_home": "Ahorra en Cerdanyola", "save_all": "Todas las formas de ahorrar",
        "save_home_text": "Luz, carburante, actividades gratuitas, ayudas y descuentos oficiales, en una sola página.",
        "save_home_fuel": "Hoy, llenar {l} L de gasolina en la gasolinera más barata de Cerdanyola ahorra <strong>{e} €</strong> respecto a la más cara.",
        "save_home_free": "Actividades gratuitas en el próximo mes: <strong>{n}</strong>.",
        "save_fuel": "La gasolinera más barata",
        "save_fuel_text": "Gasolina 95 hoy: la más barata es {c} a <strong>{cp} €/l</strong> y la más cara, {d} a {dp} €/l. En un depósito de {l} L hay <strong>{e} €</strong> de diferencia.",
        "save_free": "Actividades gratuitas en el próximo mes",
        "save_free_empty": "Ahora mismo no hay ninguna actividad marcada como gratuita en la agenda. Muchas actividades municipales lo son: mira la agenda completa.",
        "save_free_note": "Solo salen las actividades que la fuente marca como gratuitas o que lo dicen en el título.",
        "save_aids": "Ayudas que puedes pedir como particular",
        "save_aids_text": "Ayudas con plazo abierto para particulares y familias: {n}. Estas son las más cercanas:",
        "save_links": "Descuentos y tarifas sociales que vale la pena conocer",
        "save_links_body": """<ul class="months">
<li><a href="https://www.miteco.gob.es/es/energia/pobreza-energetica/pe-001.html">Bono social eléctrico y térmico</a>: descuento en la factura de la luz para hogares con pocos ingresos, familias numerosas y algunos pensionistas.</li>
<li><a href="https://www.aiguesdebarcelona.cat/ca/el-teu-servei-daigua/bonificacions">Tarifa social del agua</a> de Aigües de Barcelona, que da servicio a Cerdanyola, y bonificaciones para familias numerosas y monoparentales.</li>
<li><a href="https://www.atm.cat/titols-i-tarifes">T-Jove, T-Usual y otros títulos de transporte</a> de la ATM: si coges Rodalies, FGC o bus a menudo, suelen salir mucho más a cuenta que los billetes sencillos.</li>
<li><a href="https://bibliotecavirtual.diba.cat/">Bibliotecas de la Diputació</a>: libros, películas, revistas y cursos gratis con el carnet.</li>
<li><a href="https://www.amb.cat/s/web/medi-ambient/residus.html">Deixalleria (punto limpio)</a>: usarla con el carnet de usuario puede dar descuento en la tasa de residuos; pregúntalo en el Ayuntamiento.</li>
<li><a href="https://subastas.boe.es/">Portal de Subastas del BOE</a>: subastas judiciales, de Hacienda y de la Seguridad Social de pisos, vehículos y otros bienes; se puede buscar por municipio.</li>
</ul>""",
        "save_note": "Información orientativa: comprueba siempre las condiciones en la fuente oficial. Esta web no cobra comisiones ni tiene acuerdos con ningún comercio. Si sabes de una campaña de descuentos del comercio local o del Ayuntamiento, <a href=\"{repo}/issues\">cuéntalo en GitHub</a>.",
        "slug_leisure": "ocio", "leisure_title": "Guía de ocio de Cerdanyola",
        "leisure_desc": "Qué hacer en Cerdanyola del Vallès y Bellaterra: fiestas y conciertos, rutas por Collserola, fuentes, miradores, patrimonio, museos, restaurantes, bares y pubs.",
        "festive_title": "Próximas fiestas, conciertos y noche", "festive_empty": "Ahora mismo no hay fiestas ni conciertos anunciados.",
        "plan_title": "Plan para hoy", "plan_out": "Hoy: {sky}, hasta {tmax}°. Buen día para salir; algunas ideas:",
        "plan_in": "Hoy se prevé lluvia ({mm} mm). Ideas a cubierto:", "plan_events": "Actividades de hoy en la agenda: {n}",
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
        "jobs_near": "A menos de 5 km",
        "jobs_far": "Resto del Vallès Occidental",
        "jobs_pool": "Bolsa de trabajo",
        "jobs_places": "{n} plazas",
        "jobs_place": "1 plaza",
        "jobs_posted": "Publicada el {d}",
        "jobs_empty": "Ahora mismo no hay ninguna.",
        "jobs_note": "Ofertas del Servei Públic d'Ocupació de Catalunya (<a href='https://feinaactiva.gencat.cat/'>Feina Activa</a>) y convocatorias públicas del <a href='https://cido.diba.cat/'>CIDO</a> de la Diputació de Barcelona (CC BY 4.0). Solo se muestran las ofertas publicadas en los últimos 60 días: algunas pueden estar ya cubiertas. <a href='https://www.cerdanyolactiva.cat/'>Cerdanyola Activa</a> también tiene una bolsa de trabajo y orientación laboral gratuita.",
        "jobs_home": "Empleo cerca",
        "jobs_home_text": "{o} ofertas de trabajo en Cerdanyola y alrededores y {p} oposiciones y bolsas públicas abiertas.",
        "jobs_all": "Ver las ofertas",
        "fuel_title": "Gasolineras: precios de hoy",
        "fuel_station": "Gasolinera",
        "fuel_g95": "Gasolina 95",
        "fuel_diesel": "Gasóleo",
        "fuel_town": "En Cerdanyola",
        "fuel_near": "Las más baratas de los municipios vecinos",
        "fuel_home": "Carburante más barato hoy en Cerdanyola",
        "fuel_home_text": "Gasolina 95: <strong>{g} €/l</strong> en {gs}. Gasóleo: <strong>{d} €/l</strong> en {ds}.",
        "fuel_more": "Ver todas las gasolineras",
        "fuel_note": "Precios en €/litro. Origen de los datos: Ministerio para la Transición Ecológica y el Reto Demográfico. Última actualización: {t}.",
        "slug_emergency": "emergencias", "emergency_title": "Emergencias en Cerdanyola: teléfonos y consejos",
        "emergency_desc": "Teléfonos de emergencia y de ayuda, Policía Local, Mossos y Bomberos de Cerdanyola del Vallès, y cómo prepararse para un apagón, una ola de calor o una inundación.",
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
<p class="note">Teléfonos comprobados en las webs oficiales. Los de la Policía Local, los Mossos y los Bomberos salen de los datos abiertos de la Generalitat y se actualizan solos.</p>
""",
        "emergency_local": "En Cerdanyola",
        "slug_aids": "ayudas", "aids_title": "Ayudas y subvenciones abiertas en Cerdanyola",
        "aids_desc": "Ayudas, becas y subvenciones que puedes pedir ahora si vives en Cerdanyola del Vallès: del Ayuntamiento, la comarca, el AMB, la Generalitat y el Estado, con el plazo de cada una.",
        "aids_people": "Para personas y familias", "aids_business": "Para autónomos y empresas", "aids_entities": "Para entidades y asociaciones",
        "aids_lvl_LOCAL": "Cerdanyola, comarca y área metropolitana", "aids_lvl_AUTONOMICA": "Generalitat de Catalunya", "aids_lvl_ESTADO": "Estado",
        "aids_until": "Hasta el {d}", "aids_approx": "Hasta el {d} (aprox.)", "aids_opens": "Abre el {d}",
        "aids_check": "Plazo: {t}", "aids_check_none": "Plazo: consulta la convocatoria", "aids_budget": "Presupuesto: {b}",
        "aids_soon": "Acaba pronto", "aids_empty": "Ahora mismo no hay ninguna convocatoria abierta en este apartado.",
        "aids_home_title": "Ayudas que puedes pedir ahora",
        "aids_home_text": "{p} para personas y familias, {b} para autónomos y empresas y {e} para entidades. Las que cierran antes:",
        "aids_all": "Ver todas las ayudas abiertas",
        "aids_note": "Datos de la <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/index\">Base de Datos Nacional de Subvenciones</a> (Ministerio de Hacienda), actualizados cada día. Cuando el plazo se cuenta desde la publicación oficial, la fecha es aproximada. Antes de pedir nada, lee las bases en la convocatoria oficial: es la única que vale. Hay ayudas municipales, como las bonificaciones de impuestos, que no aparecen aquí: consúltalas en el Ayuntamiento. ¿Quieres que te avisen? La BDNS envía <a href=\"https://www.infosubvenciones.es/bdnstrans/GE/es/alertas\">alertas gratuitas por correo</a>.",
        "weekend_title": "Este fin de semana", "weekend_empty": "Todavía no hay actividades anunciadas para el fin de semana.",
        "kids": "Infantil",
        "ics_link": "¿Quieres la agenda en el móvil? Añade <a href=\"{url}\">este calendario</a> al tuyo (en Google Calendar: «Otros calendarios» → «Desde URL») y se actualizará solo.",
        "slug_invest": "inversiones", "invest_title": "Inversiones y empresas en Cerdanyola",
        "invest_desc": "Grandes inversiones públicas en Cerdanyola del Vallès y Bellaterra, licitaciones abiertas para empresas y autónomos, contratos anunciados, y empresas nuevas, traslados y ampliaciones de capital del Registro Mercantil.",
        "invest_big": "Grandes inversiones públicas",
        "invest_big_text": "Contratos públicos de 1 millón de euros o más en Cerdanyola y el campus de la UAB con novedades en el último año, de mayor a menor.",
        "invest_open": "Licitaciones abiertas",
        "invest_open_text": "Contratos públicos en Cerdanyola que ahora aceptan ofertas de empresas y autónomos, por fecha de cierre.",
        "invest_soon": "Próximamente",
        "invest_soon_text": "Contratos que la administración ha anunciado que sacará a licitación.",
        "invest_companies": "Empresas: altas, traslados y capital",
        "invest_companies_text": "En los últimos {d} días, en el Registro Mercantil: {n} empresas nuevas con domicilio en Cerdanyola o Bellaterra (capital inicial total: {c}), {m} traslados a Cerdanyola y {u} ampliaciones de capital.",
        "invest_empty": "Ahora mismo no hay ninguno.",
        "invest_until": "ofertas hasta el {d}", "invest_lots": "{n} lotes", "invest_winners": "Adjudicado a: {w}",
        "invest_capital": "Capital: {c}", "invest_capital_change": "{c} (capital resultante: {t})",
        "invest_feed": "¿Quieres que te avisen? Añade <a href=\"{url}\">este canal</a> a un lector de noticias (Feedly, Inoreader, Thunderbird...) y recibirás cada nueva licitación, gran inversión o movimiento de empresas.",
        "invest_note": "Contratos: <a href=\"https://contractaciopublica.cat/\">Plataforma de serveis de contractació pública</a> (datos abiertos de la Generalitat). Publican en ella el Ayuntamiento, la Generalitat, el AMB, la UAB y los centros de investigación del campus; las inversiones del Estado (sincrotrón ALBA, Adif...) no aparecen. Importes sin IVA: el presupuesto de licitación o, si ya se ha adjudicado, el importe adjudicado. Empresas: <a href=\"https://www.boe.es/diario_borme/\">BORME</a> (Agencia Estatal Boletín Oficial del Estado), leído hasta el {t}; solo aparecen empresas, sin datos de personas. Los traslados, los cambios de capital y los cierres solo se detectan en empresas que se han constituido o trasladado a Cerdanyola desde el {since}. Esta página es informativa: no es ninguna recomendación ni asesoramiento de inversión.",
        "invest_home": "Inversiones y empresas",
        "invest_home_text": "{o} licitaciones públicas abiertas, {b} grandes inversiones (de 1 millón de euros o más) con novedades en el último año y {n} empresas nuevas o llegadas a Cerdanyola en los últimos {d} días. Las últimas grandes inversiones:",
        "invest_all": "Ver inversiones, licitaciones y empresas",
        "source_line": "Fuentes: MET Norway (tiempo), Generalitat de Catalunya (agenda, equipamientos, aire y contratos públicos), Ajuntament de Cerdanyola, UAB y entidades locales (agenda), Renfe (avisos), OpenStreetMap y Overture Maps (guía de ocio), BDNS (ayudas), SOC y Diputació de Barcelona (empleo), BORME (empresas), Ministerio para la Transición Ecológica (carburantes) y Red Eléctrica (luz). Actualizado: {t}.",
        "about": "Sobre la web", "legal": "Aviso legal", "privacy": "Privacidad",
        "studio": "El autor",
        "donate": "Apoya el proyecto",
        "skip": "Saltar al contenido", "language": "Idioma", "choose": "Elige idioma",
        "sections": "Secciones", "nav_home": "Inicio", "nav_agenda": "Agenda", "nav_leisure": "Ocio",
        "nav_picks": "Recomendaciones", "nav_save": "Ahorra", "nav_aids": "Ayudas", "nav_jobs": "Empleo",
        "nav_invest": "Inversiones", "nav_directory": "Equipamientos", "nav_emergency": "112",
        "theme_auto": "Tema: automático", "theme_light": "Tema: claro", "theme_dark": "Tema: oscuro",
        "install_title": "Lleva Cerdanyola Avui en el móvil.", "install_text": "Instálala como una app: icono en la pantalla de inicio, pantalla completa y los últimos datos aunque falle la conexión. Sin tiendas ni cuentas.",
        "install_button": "Instalar la app", "install_ios_q": "¿Tienes iPhone o iPad?",
        "install_ios": "Abre esta web con Safari, toca el botón Compartir (el cuadrado con la flecha) y elige «Añadir a pantalla de inicio».",
        "offline_title": "Sin conexión", "offline_text": "No se ha podido cargar esta página. Vuelve a intentarlo cuando tengas conexión o ve al inicio.",
        "notfound_title": "Página no encontrada", "notfound_text": "Esta página no existe. Vuelve al inicio.",
        "about_body": """
<p>{site} reúne en una sola página datos abiertos útiles para la gente de Cerdanyola del Vallès y Bellaterra: el tiempo, la agenda, las horas más baratas de la luz, los avisos de Rodalies, la calidad del aire, una guía de ocio, las ayudas abiertas, el empleo, las inversiones públicas y formas de ahorrar.</p>
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
<li>Inversiones y licitaciones: Plataforma de serveis de contractació pública (datos abiertos de la Generalitat). Empresas: BORME, de la Agencia Estatal Boletín Oficial del Estado, de reutilización libre citando la fuente.</li>
<li>Precios de los carburantes: Ministerio para la Transición Ecológica y el Reto Demográfico.</li>
<li>Recomendaciones de restaurantes y experiencias: lista hecha a mano, sin pagos ni acuerdos comerciales; no reproducimos valoraciones ni reseñas de ninguna plataforma.</li>
<li>Precio de la luz: Red Eléctrica, a través de la web hermana <a href="{light}">{light}</a>.</li>
</ul>
<p>El código es abierto y está en <a href="{repo}">GitHub</a>, donde puedes avisar de errores o proponer mejoras.</p>
""",
        "legal_body": """
<p>{site} es un proyecto gratuito e informativo, sin relación con el Ajuntament de Cerdanyola del Vallès ni con ninguna otra administración.</p>
<h2>Titular</h2><p>{owner}</p>
<h2>Responsabilidad</h2><p>La información procede de fuentes públicas citadas en cada apartado y se ofrece tal cual, sin garantía. Consulta siempre la fuente oficial antes de tomar decisiones.</p>
<h2>Contenidos de los usuarios</h2><p>Los anuncios del <a href="{board}">tablón vecinal</a> los publican los propios vecinos y no se revisan antes de publicarse. {site} no participa en ningún trato ni garantiza lo que se anuncia. Si ves un anuncio ilícito u ofensivo, usa el botón «Denunciar» o escribe al titular: se retirará en cuanto se tenga conocimiento (artículo 16 de la LSSI).</p>
""",
        "privacy_body": """
<p>Esta web no usa cookies y no tiene analítica ni publicidad. La única parte que trata datos personales es el <a href="{board}">tablón vecinal</a>, explicado más abajo.</p>
<p>Si eliges el tema claro u oscuro, la preferencia se guarda solo en tu navegador (localStorage) y no se envía a ningún sitio.</p>
<p>Está alojada en GitHub Pages. Como cualquier servidor web, GitHub registra la dirección IP de las visitas por motivos de seguridad. Más información en la <a href="https://docs.github.com/es/site-policy/privacy-policies/github-general-privacy-statement">declaración de privacidad de GitHub</a>.</p>
<h2>Tablón vecinal</h2>
<p>Responsable del tratamiento: {owner}</p>
<p>Cuando publicas un anuncio se guardan el texto, el nombre o alias, el contacto que quieras mostrar y tu correo electrónico. El correo nunca se publica: solo sirve para confirmar el anuncio, enviarte las respuestas de los vecinos y avisarte antes de que caduque. Cuando respondes a un anuncio, tu mensaje y tu correo se envían al autor y no se guardan. Base jurídica: tu consentimiento (artículo 6.1.a del RGPD).</p>
<p>Para evitar abusos se guarda un resumen (hash con sal) de la dirección IP, del que no se puede recuperar la dirección. Los anuncios caducan a los 45 días y se borran del todo siete días después; puedes borrarlos antes con el enlace del correo de confirmación o escribiendo al responsable. También puedes pedir acceso, rectificación o supresión por correo, y reclamar ante la <a href="https://www.aepd.es">Agencia Española de Protección de Datos</a>.</p>
<p>Los datos se guardan en los servidores de Cloudflare y los correos se envían con Gmail (Google). En la página del tablón se ejecuta <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare Turnstile</a> para distinguir personas de robots; no usa cookies de seguimiento.</p>
""",
        "slug_board": "tablon",
        "nav_board": "Tablón",
        "board_title": "Tablón vecinal de Cerdanyola",
        "board_desc": "Tablón de anuncios entre vecinos de Cerdanyola del Vallès y Bellaterra: pide ayuda, regala lo que ya no uses y encuentra chollos de comercios y particulares.",
        "board_intro": "Un espacio para que los vecinos se ayuden: pide una mano o apoyo para un proyecto, regala lo que ya no necesites o publica chollos y segunda mano. Sin registro: solo un nombre y un correo, que nunca se muestra.",
        "board_cat_help": "Ayúdame",
        "board_cat_give": "Lo regalo",
        "board_cat_deal": "Chollos",
        "board_cat_all": "Todo",
        "board_cat_help_desc": "Pide una mano con una tarea o apoyo para un proyecto.",
        "board_cat_give_desc": "Regala lo que ya no uses.",
        "board_cat_deal_desc": "Segunda mano y ofertas de comercios locales y particulares.",
        "board_new": "Publicar un anuncio",
        "board_empty": "Aún no hay ningún anuncio aquí. ¡Sé el primero!",
        "board_loading": "Cargando los anuncios…",
        "board_nojs": "Para publicar, responder o denunciar hace falta JavaScript.",
        "board_static_note": "Lista actualizada cuatro veces al día; con JavaScript se muestra al momento.",
        "board_offline": "El tablón todavía no está en marcha. Vuelve pronto.",
        "board_reply": "Responder",
        "board_report": "Denunciar",
        "board_rules": "<ul><li>Solo para vecinos de Cerdanyola y Bellaterra: particulares y comercios locales.</li><li>Los anuncios caducan a los 45 días; se pueden renovar o borrar desde el correo de confirmación.</li><li>No publiques datos de terceros ni datos bancarios. No envíes nunca dinero por adelantado: la web no hace de intermediaria ni garantiza nada.</li><li>Los anuncios denunciados por varios vecinos se ocultan automáticamente.</li></ul>",
        "board_privacy": "El correo solo sirve para confirmar el anuncio y recibir las respuestas; nunca se publica. Más detalles en la <a href=\"{privacy}\">política de privacidad</a>.",
        "board_f_cat": "Categoría",
        "board_f_title": "Título",
        "board_f_body": "Texto",
        "board_f_name": "Nombre o alias",
        "board_f_email": "Correo electrónico (no se muestra)",
        "board_f_contact": "Teléfono, WhatsApp o Telegram (opcional; se mostrará)",
        "board_f_price": "Precio (opcional)",
        "board_f_consent": "Acepto las normas y que se publique el anuncio con el nombre y el contacto que he indicado.",
        "board_f_message": "Mensaje",
        "board_f_reply_email": "Tu correo (para que puedan responderte)",
        "board_f_reason": "Motivo (opcional)",
        "board_submit": "Enviar",
        "board_cancel": "Cancelar",
        "board_sent": "Te hemos enviado un correo. Haz clic en el enlace para publicar el anuncio (mira también la carpeta de spam).",
        "board_reply_sent": "Mensaje enviado. Si el autor te responde, lo recibirás en tu correo.",
        "board_report_sent": "Gracias por el aviso. Lo revisaremos.",
        "board_err_rate": "Has hecho demasiados envíos hoy. Vuelve a intentarlo mañana.",
        "board_err_filtered": "El texto contiene palabras o datos no permitidos (insultos, datos bancarios…). Revísalo.",
        "board_err_turnstile": "No hemos podido comprobar que no eres un robot. Vuelve a intentarlo.",
        "board_err_full": "El tablón está lleno. Vuelve a intentarlo dentro de unos días.",
        "board_err_mail_quota": "Hoy ya no podemos enviar más correos. Vuelve a intentarlo mañana.",
        "board_err_invalid": "Revisa los campos: falta algún dato o es demasiado largo.",
        "board_err_notfound": "Este anuncio ya no existe.",
        "board_err_network": "No se ha podido conectar con el tablón. Vuelve a intentarlo.",
        "board_err_generic": "Se ha producido un error. Vuelve a intentarlo más tarde.",
        "board_expires": "caduca el {d}",
        "board_posted": "publicado el {d}",
        "board_contact_show": "Mostrar el contacto",
        "board_reply_title": "Responder al anuncio",
        "board_report_title": "Denunciar el anuncio",
        "board_report_hint": "Denuncia solo anuncios con estafas, insultos, datos de terceros o que no tengan nada que ver con Cerdanyola.",
        "board_home": "Tablón vecinal",
        "board_home_text": "Pide ayuda, regala lo que ya no uses o encuentra chollos entre vecinos.",
        "board_home_n": "{n} anuncios activos.",
        "board_all": "Ver el tablón",
        "owner_missing": "Proyecto personal sin ánimo de lucro. Contacto: a través del <a href=\"{repo}\">repositorio en GitHub</a>.",
    },
    "en": {
        "lang_name": "English", "locale": "en_GB",
        "slug_agenda": "events", "slug_directory": "facilities", "slug_about": "about",
        "slug_legal": "legal-notice", "slug_privacy": "privacy",
        "home_title": "Cerdanyola del Vallès today: weather, events, electricity and trains",
        "home_desc": "What's on today in Cerdanyola del Vallès and Bellaterra (UAB): weather forecast, events, cheapest electricity hours, Rodalies R7 and R8 train alerts, air quality, leisure guide, grants, jobs, public investment and ways to save money.",
        "tagline": "Useful open data for people in Cerdanyola and Bellaterra, updated automatically every day.",
        "now": "Now",
        "weather_title": "Weather",
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
        "slug_picks": "recommendations", "picks_title": "This week's picks in Cerdanyola",
        "picks_desc": "Hand-picked restaurants, bars and special experiences in Cerdanyola del Vallès and Bellaterra. A different selection every week.",
        "picks_home": "Picks of the week", "picks_more": "More about this week's picks",
        "picks_week": "Selection for the week of {d}. It changes next Monday.",
        "picks_food": "Where to eat", "picks_experience": "Things to do",
        "picks_note": "Hand-picked list ({n} places) based on each venue's public reputation, with no payments or commercial agreements. Check opening hours on their website before going. Missing a place, or has one closed? <a href=\"{repo}/issues\">Tell us on GitHub</a>.",
        "slug_save": "save", "save_title": "Save money in Cerdanyola",
        "save_desc": "Real ways to save money in Cerdanyola del Vallès and Bellaterra, updated daily: the cheapest electricity hours, the cheapest petrol station, free activities, grants for individuals and official discounts.",
        "save_home": "Save money in Cerdanyola", "save_all": "All the ways to save",
        "save_home_text": "Electricity, fuel, free activities, grants and official discounts, on one page.",
        "save_home_fuel": "Today, filling {l} L of petrol at the cheapest station in Cerdanyola saves <strong>€{e}</strong> compared with the most expensive one.",
        "save_home_free": "Free activities in the coming month: <strong>{n}</strong>.",
        "save_fuel": "The cheapest petrol station",
        "save_fuel_text": "Unleaded 95 today: the cheapest is {c} at <strong>€{cp}/l</strong> and the most expensive, {d} at €{dp}/l. On a {l} L tank that is a <strong>€{e}</strong> difference.",
        "save_free": "Free activities in the coming month",
        "save_free_empty": "No activity in the listings is marked as free right now. Many council events are: see the full listings.",
        "save_free_note": "Only activities the source marks as free, or that say so in their title, are shown.",
        "save_aids": "Grants you can apply for as an individual",
        "save_aids_text": "Grants currently open to individuals and families: {n}. These close soonest:",
        "save_links": "Discounts and social tariffs worth knowing",
        "save_links_body": """<ul class="months">
<li><a href="https://www.miteco.gob.es/es/energia/pobreza-energetica/pe-001.html">Bono social (electricity and heating)</a>: a discount on the electricity bill for low-income households, large families and some pensioners.</li>
<li><a href="https://www.aiguesdebarcelona.cat/ca/el-teu-servei-daigua/bonificacions">Social water tariff</a> from Aigües de Barcelona, which supplies Cerdanyola, plus discounts for large and single-parent families.</li>
<li><a href="https://www.atm.cat/titols-i-tarifes">T-Jove, T-Usual and other travel cards</a> from ATM: if you use Rodalies, FGC or buses often, they usually work out much cheaper than single tickets.</li>
<li><a href="https://bibliotecavirtual.diba.cat/">Diputació libraries</a>: free books, films, magazines and courses with a library card.</li>
<li><a href="https://www.amb.cat/s/web/medi-ambient/residus.html">Recycling centre (deixalleria)</a>: using it with a user card may reduce your waste tax; ask the town council.</li>
<li><a href="https://subastas.boe.es/">BOE auction portal</a>: court, tax-office and Social Security auctions of flats, vehicles and other goods; you can search by town.</li>
</ul>""",
        "save_note": "For guidance only: always check the conditions with the official source. This website takes no commissions and has no deals with any business. If you know of a discount campaign by local shops or the town council, <a href=\"{repo}/issues\">tell us on GitHub</a>.",
        "slug_leisure": "leisure", "leisure_title": "Leisure guide to Cerdanyola",
        "leisure_desc": "Things to do in Cerdanyola del Vallès and Bellaterra: festivals and concerts, walks in Collserola, springs, viewpoints, heritage, museums, restaurants, bars and pubs.",
        "festive_title": "Upcoming festivals, concerts and nights out", "festive_empty": "There are no festivals or concerts announced right now.",
        "plan_title": "Plan for today", "plan_out": "Today: {sky}, up to {tmax}°. A good day to get out; some ideas:",
        "plan_in": "Rain is forecast today ({mm} mm). Indoor ideas:", "plan_events": "Events on today: {n}",
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
        "jobs_near": "Within 5 km",
        "jobs_far": "Rest of the Vallès Occidental",
        "jobs_pool": "Job pool",
        "jobs_places": "{n} posts",
        "jobs_place": "1 post",
        "jobs_posted": "Posted {d}",
        "jobs_empty": "There are none right now.",
        "jobs_note": "Offers from the Catalan public employment service (<a href='https://feinaactiva.gencat.cat/'>Feina Activa</a>) and public calls from the Diputació de Barcelona's <a href='https://cido.diba.cat/'>CIDO</a> (CC BY 4.0). Offers are in Catalan or Spanish, as published. Only offers posted in the last 60 days are shown: some may already be filled. <a href='https://www.cerdanyolactiva.cat/'>Cerdanyola Activa</a> also runs a job board and free career guidance.",
        "jobs_home": "Jobs nearby",
        "jobs_home_text": "{o} job offers in and around Cerdanyola and {p} open public-sector posts and job pools.",
        "jobs_all": "See the offers",
        "fuel_title": "Petrol stations: today's prices",
        "fuel_station": "Station",
        "fuel_g95": "Unleaded 95",
        "fuel_diesel": "Diesel",
        "fuel_town": "In Cerdanyola",
        "fuel_near": "Cheapest in neighbouring towns",
        "fuel_home": "Cheapest fuel in Cerdanyola today",
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
        "ics_link": "Want the events on your phone? Add <a href=\"{url}\">this calendar</a> to yours (in Google Calendar: “Other calendars” → “From URL”) and it will update itself.",
        "slug_invest": "investment", "invest_title": "Investment and business in Cerdanyola",
        "invest_desc": "Major public investment in Cerdanyola del Vallès and Bellaterra, open public tenders for businesses and the self-employed, announced contracts, and new companies, relocations and capital increases from the Companies Register.",
        "invest_big": "Major public investment",
        "invest_big_text": "Public contracts worth €1 million or more in Cerdanyola and on the UAB campus with news in the last year, largest first.",
        "invest_open": "Open tenders",
        "invest_open_text": "Public contracts in Cerdanyola now accepting bids from businesses and the self-employed, by closing date.",
        "invest_soon": "Coming up",
        "invest_soon_text": "Contracts that public bodies have announced they will put out to tender.",
        "invest_companies": "Companies: new, relocations and capital",
        "invest_companies_text": "In the last {d} days, in the Companies Register: {n} new companies based in Cerdanyola or Bellaterra (total initial capital: {c}), {m} relocations to Cerdanyola and {u} capital increases.",
        "invest_empty": "There are none right now.",
        "invest_until": "bids until {d}", "invest_lots": "{n} lots", "invest_winners": "Awarded to: {w}",
        "invest_capital": "Capital: {c}", "invest_capital_change": "{c} (new total: {t})",
        "invest_feed": "Want alerts? Add <a href=\"{url}\">this feed</a> to a news reader (Feedly, Inoreader, Thunderbird...) and you'll get every new tender, major investment or company move.",
        "invest_note": "Contracts: the Catalan <a href=\"https://contractaciopublica.cat/\">public procurement platform</a> (Generalitat open data), where the town council, the Catalan government, the metropolitan area (AMB), the UAB and the campus research centres publish; Spanish state investment (ALBA synchrotron, Adif...) is not included. Titles are in Catalan or Spanish, as published. Amounts exclude VAT: the tender budget or, once awarded, the awarded amount. Companies: the <a href=\"https://www.boe.es/diario_borme/\">BORME</a> (Spain's official Companies Register gazette, Agencia Estatal Boletín Oficial del Estado), read up to {t}; only companies are shown, never personal data. Relocations, capital changes and closures are only detected for companies set up in or moved to Cerdanyola since {since}. This page is for information only: it is not investment advice or a recommendation.",
        "invest_home": "Investment and business",
        "invest_home_text": "{o} open public tenders, {b} major investments (€1 million or more) with news in the last year and {n} new or newly arrived companies in Cerdanyola in the last {d} days. Latest major investments:",
        "invest_all": "See investment, tenders and companies",
        "source_line": "Sources: MET Norway (weather), Generalitat de Catalunya (events, facilities, air and public contracts), Cerdanyola town council, UAB and local associations (events), Renfe (alerts), OpenStreetMap and Overture Maps (leisure guide), BDNS (grants), SOC and Diputació de Barcelona (jobs), BORME (companies), Ministry for the Ecological Transition (fuel) and Red Eléctrica (electricity). Updated: {t}.",
        "about": "About", "legal": "Legal notice", "privacy": "Privacy",
        "studio": "About the author",
        "donate": "Support the project",
        "skip": "Skip to content", "language": "Language", "choose": "Choose your language",
        "sections": "Sections", "nav_home": "Home", "nav_agenda": "What's on", "nav_leisure": "Leisure",
        "nav_picks": "Picks", "nav_save": "Save", "nav_aids": "Grants", "nav_jobs": "Jobs",
        "nav_invest": "Investment", "nav_directory": "Facilities", "nav_emergency": "112",
        "theme_auto": "Theme: auto", "theme_light": "Theme: light", "theme_dark": "Theme: dark",
        "install_title": "Take Cerdanyola Avui with you.", "install_text": "Install it as an app: an icon on your home screen, full screen and the latest data even when you are offline. No app store, no account.",
        "install_button": "Install the app", "install_ios_q": "On an iPhone or iPad?",
        "install_ios": "Open this site in Safari, tap the Share button (the square with the arrow) and choose “Add to Home Screen”.",
        "offline_title": "No connection", "offline_text": "This page could not be loaded. Try again when you are back online, or go to the home page.",
        "notfound_title": "Page not found", "notfound_text": "This page does not exist. Go back to the home page.",
        "about_body": """
<p>{site} brings together useful open data for people in Cerdanyola del Vallès and Bellaterra on a single page: weather, events, the cheapest electricity hours, Rodalies train alerts, air quality, a leisure guide, open grants, jobs, public investment and ways to save money.</p>
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
<li>Investment and tenders: the Catalan public procurement platform (Generalitat open data). Companies: the BORME, published by the Agencia Estatal Boletín Oficial del Estado, free to reuse with attribution.</li>
<li>Fuel prices: Spanish Ministry for the Ecological Transition.</li>
<li>Restaurant and experience picks: a hand-made list with no payments or commercial agreements; we do not reproduce ratings or reviews from any platform.</li>
<li>Electricity price: Red Eléctrica, via the sister site <a href="{light}">{light}</a>.</li>
</ul>
<p>The code is open source and lives on <a href="{repo}">GitHub</a>, where you can report bugs or suggest improvements.</p>
""",
        "legal_body": """
<p>{site} is a free, informational project with no connection to Cerdanyola del Vallès town council or any other public body.</p>
<h2>Owner</h2><p>{owner}</p>
<h2>Liability</h2><p>The information comes from the public sources cited in each section and is provided as is, without warranty. Always check the official source before making decisions.</p>
<h2>User content</h2><p>Notices on the <a href="{board}">community board</a> are posted by neighbours themselves and are not reviewed before publication. {site} takes no part in any deal and guarantees nothing that is advertised. If you see an unlawful or offensive notice, use the "Report" button or write to the owner: it will be removed as soon as we become aware of it (article 16 of Spain's LSSI).</p>
""",
        "privacy_body": """
<p>This website uses no cookies and has no analytics or advertising. The only part that processes personal data is the <a href="{board}">community board</a>, explained below.</p>
<p>If you pick the light or dark theme, the preference is stored only in your browser (localStorage) and never sent anywhere.</p>
<p>It is hosted on GitHub Pages. Like any web server, GitHub logs visitors' IP addresses for security reasons. See the <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub privacy statement</a>.</p>
<h2>Community board</h2>
<p>Data controller: {owner}</p>
<p>When you post a notice we store its text, your name or alias, the contact you choose to show and your email address. The email is never published: it is only used to confirm the notice, forward replies from neighbours and warn you before it expires. When you reply to a notice, your message and email are sent to the author and not stored. Legal basis: your consent (article 6.1.a GDPR).</p>
<p>To prevent abuse we store a salted hash of your IP address, from which the address cannot be recovered. Notices expire after 45 days and are fully deleted seven days later; you can delete them earlier with the link in the confirmation email or by writing to the controller. You can also request access, rectification or erasure by email, and lodge a complaint with the <a href="https://www.aepd.es">Spanish Data Protection Agency</a>.</p>
<p>Data is stored on Cloudflare servers and emails are sent with Gmail (Google). The board page runs <a href="https://www.cloudflare.com/privacypolicy/">Cloudflare Turnstile</a> to tell people from robots; it uses no tracking cookies.</p>
""",
        "slug_board": "board",
        "nav_board": "Board",
        "board_title": "Cerdanyola community board",
        "board_desc": "Notice board for neighbours in Cerdanyola del Vallès and Bellaterra: ask for help, give away what you no longer use and find bargains from local shops and individuals.",
        "board_intro": "A place for neighbours to help each other: ask for a hand or support for a project, give away what you no longer need, or post bargains and second-hand items. No sign-up: just a name and an email address, which is never shown.",
        "board_cat_help": "Help me",
        "board_cat_give": "Giving away",
        "board_cat_deal": "Bargains",
        "board_cat_all": "All",
        "board_cat_help_desc": "Ask for a hand with a task or support for a project.",
        "board_cat_give_desc": "Give away what you no longer use.",
        "board_cat_deal_desc": "Second-hand items and offers from local shops and individuals.",
        "board_new": "Post a notice",
        "board_empty": "No notices here yet. Be the first!",
        "board_loading": "Loading notices…",
        "board_nojs": "JavaScript is needed to post, reply or report.",
        "board_static_note": "List updated four times a day; with JavaScript it shows live.",
        "board_offline": "The board is not running yet. Come back soon.",
        "board_reply": "Reply",
        "board_report": "Report",
        "board_rules": "<ul><li>Only for neighbours in Cerdanyola and Bellaterra: individuals and local shops.</li><li>Notices expire after 45 days; renew or delete them from the confirmation email.</li><li>Do not post other people's data or bank details. Never send money in advance: this site is not an intermediary and guarantees nothing.</li><li>Notices reported by several neighbours are hidden automatically.</li></ul>",
        "board_privacy": "Your email is only used to confirm the notice and receive replies; it is never published. See the <a href=\"{privacy}\">privacy policy</a>.",
        "board_f_cat": "Category",
        "board_f_title": "Title",
        "board_f_body": "Text",
        "board_f_name": "Name or alias",
        "board_f_email": "Email (not shown)",
        "board_f_contact": "Phone, WhatsApp or Telegram (optional; will be shown)",
        "board_f_price": "Price (optional)",
        "board_f_consent": "I accept the rules and agree to publish the notice with the name and contact I have given.",
        "board_f_message": "Message",
        "board_f_reply_email": "Your email (so they can answer you)",
        "board_f_reason": "Reason (optional)",
        "board_submit": "Send",
        "board_cancel": "Cancel",
        "board_sent": "We have sent you an email. Click the link to publish the notice (check your spam folder too).",
        "board_reply_sent": "Message sent. If the author replies, you will get it by email.",
        "board_report_sent": "Thanks for letting us know. We will review it.",
        "board_err_rate": "Too many submissions today. Try again tomorrow.",
        "board_err_filtered": "The text contains words or data that are not allowed (insults, bank details…). Please revise it.",
        "board_err_turnstile": "We could not verify that you are not a robot. Please try again.",
        "board_err_full": "The board is full. Try again in a few days.",
        "board_err_mail_quota": "We cannot send more emails today. Try again tomorrow.",
        "board_err_invalid": "Check the fields: something is missing or too long.",
        "board_err_notfound": "This notice no longer exists.",
        "board_err_network": "Could not reach the board. Please try again.",
        "board_err_generic": "Something went wrong. Please try again later.",
        "board_expires": "expires {d}",
        "board_posted": "posted {d}",
        "board_contact_show": "Show contact",
        "board_reply_title": "Reply to the notice",
        "board_report_title": "Report the notice",
        "board_report_hint": "Report only notices with scams, insults, other people's data or nothing to do with Cerdanyola.",
        "board_home": "Community board",
        "board_home_text": "Ask for help, give away what you no longer use or find bargains among neighbours.",
        "board_home_n": "{n} active notices.",
        "board_all": "See the board",
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
    for key, *names in SKY:
        if code and key in code.split("_")[0]:
            return key, names[SKY_COL[lang] - 1]
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


def fmt_big(lang, x):
    """2.750.000 -> «2,8 M€» («€2.8m» en inglés); por debajo del millón, el importe entero."""
    if x < 1_000_000:
        return fmt_money(lang, x)
    n = fmt_num(lang, x / 1_000_000, 1)
    return f"€{n}m" if lang == "en" else f"{n} M€"


def phase(lang, key):
    return _pick(lang, CONTRACT_PHASES[key]) if key in CONTRACT_PHASES else key


def contract_type(lang, kind):
    if lang == "ca" or kind not in CONTRACT_TYPES:
        return kind
    es, en = CONTRACT_TYPES[kind]
    return es if lang == "es" else en


def company_kind(lang, kind):
    return _pick(lang, COMPANY_KINDS[kind])


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
