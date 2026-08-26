"""Catálogo de ciudades ancla.

Aquí está la decisión de diseño más importante del proyecto: **"global" no
significa el planeta entero en resolución horaria**. Eso son terabytes y una
factura de nube. Significa una muestra deliberada.

Estas ubicaciones están elegidas para cubrir:

  - Todo el rango de latitud, de 71°N (Utqiagvik) a 54°S (Ushuaia)
  - Los grandes grupos climáticos de Köppen, incluidos extremos: desierto
    cálido (Kuwait), continental subárctico (Yakutsk), tropical húmedo (Manaos)
  - Zonas sísmicas de riesgo alto y de riesgo nulo, para poder contrastar
  - Las principales rutas migratorias de aves del mundo

Los eventos globales y en vivo (sismos, incendios) NO se limitan a esta lista:
son ligeros y se ingieren para todo el planeta. Esta muestra existe solo para
el análisis climático profundo, que es el caro.

Cada campo de aquí es una dimensión con la que después se puede agrupar. El
`flyway` es el que hace posible la pregunta interesante: ¿se comporta igual la
migración en la ruta del Atlántico Este que en la de Asia Oriental?
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Rutas migratorias principales reconocidas internacionalmente.
Flyway = Literal[
    "atlantico-este",
    "mediterraneo-mar-negro",
    "africa-oriental-asia-occidental",
    "asia-central",
    "asia-oriental-australasia",
    "americas-pacifico",
    "americas-central",
    "americas-misisipi",
    "americas-atlantico",
    "ninguna",
]


class Location(BaseModel):
    """Una ubicación ancla del catálogo."""

    id: str = Field(description="Slug estable. Nunca cambiar: es clave de join.")
    name: str
    country: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: str = Field(
        description="Zona IANA. Imprescindible para agregar por día LOCAL: "
                    "agrupar Tokio (UTC+9) por día UTC parte su jornada en dos."
    )
    koppen: str = Field(description="Clasificación climática de Köppen-Geiger")
    seismic_level: int = Field(
        ge=0, le=3, description="0 nulo · 1 bajo · 2 alto · 3 muy alto (orientativo)"
    )
    flyway: Flyway


# Coordenadas redondeadas a 2 decimales (~1 km), suficiente para la celda de
# malla meteorológica. El nivel sísmico es orientativo, basado en proximidad a
# límites de placa: sirve para agrupar, no para evaluar riesgo real.
LOCATIONS: list[Location] = [
    # ── Ártico y subártico ────────────────────────────────────────────────
    Location(id="utqiagvik", name="Utqiagvik", country="US", lat=71.29, lon=-156.79,
             timezone="America/Anchorage",
             koppen="ET", seismic_level=1, flyway="americas-pacifico"),
    Location(id="tromso", name="Tromsø", country="NO", lat=69.65, lon=18.96,
             timezone="Europe/Oslo",
             koppen="Dfc", seismic_level=1, flyway="atlantico-este"),
    Location(id="yakutsk", name="Yakutsk", country="RU", lat=62.03, lon=129.73,
             timezone="Asia/Yakutsk",
             koppen="Dfd", seismic_level=1, flyway="asia-oriental-australasia"),
    Location(id="reykjavik", name="Reikiavik", country="IS", lat=64.15, lon=-21.94,
             timezone="Atlantic/Reykjavik",
             koppen="Cfc", seismic_level=3, flyway="atlantico-este"),
    Location(id="anchorage", name="Anchorage", country="US", lat=61.22, lon=-149.90,
             timezone="America/Anchorage",
             koppen="Dfc", seismic_level=3, flyway="americas-pacifico"),

    # ── Europa ────────────────────────────────────────────────────────────
    Location(id="london", name="Londres", country="GB", lat=51.51, lon=-0.13,
             timezone="Europe/London",
             koppen="Cfb", seismic_level=0, flyway="atlantico-este"),
    Location(id="berlin", name="Berlín", country="DE", lat=52.52, lon=13.40,
             timezone="Europe/Berlin",
             koppen="Cfb", seismic_level=0, flyway="atlantico-este"),
    Location(id="moscow", name="Moscú", country="RU", lat=55.76, lon=37.62,
             timezone="Europe/Moscow",
             koppen="Dfb", seismic_level=0, flyway="mediterraneo-mar-negro"),
    Location(id="madrid", name="Madrid", country="ES", lat=40.42, lon=-3.70,
             timezone="Europe/Madrid",
             koppen="Csa", seismic_level=1, flyway="atlantico-este"),
    Location(id="barcelona", name="Barcelona", country="ES", lat=41.39, lon=2.17,
             timezone="Europe/Madrid",
             koppen="Csa", seismic_level=1, flyway="mediterraneo-mar-negro"),
    Location(id="athens", name="Atenas", country="GR", lat=37.98, lon=23.73,
             timezone="Europe/Athens",
             koppen="Csa", seismic_level=3, flyway="mediterraneo-mar-negro"),
    Location(id="istanbul", name="Estambul", country="TR", lat=41.01, lon=28.98,
             timezone="Europe/Istanbul",
             koppen="Csa", seismic_level=3, flyway="mediterraneo-mar-negro"),

    # ── Norteamérica ──────────────────────────────────────────────────────
    Location(id="vancouver", name="Vancouver", country="CA", lat=49.28, lon=-123.12,
             timezone="America/Vancouver",
             koppen="Csb", seismic_level=3, flyway="americas-pacifico"),
    Location(id="san-francisco", name="San Francisco", country="US", lat=37.77, lon=-122.42,
             timezone="America/Los_Angeles",
             koppen="Csb", seismic_level=3, flyway="americas-pacifico"),
    Location(id="denver", name="Denver", country="US", lat=39.74, lon=-104.99,
             timezone="America/Denver",
             koppen="BSk", seismic_level=1, flyway="americas-central"),
    Location(id="phoenix", name="Phoenix", country="US", lat=33.45, lon=-112.07,
             timezone="America/Phoenix",
             koppen="BWh", seismic_level=1, flyway="americas-pacifico"),
    Location(id="chicago", name="Chicago", country="US", lat=41.88, lon=-87.63,
             timezone="America/Chicago",
             koppen="Dfa", seismic_level=0, flyway="americas-misisipi"),
    Location(id="new-york", name="Nueva York", country="US", lat=40.71, lon=-74.01,
             timezone="America/New_York",
             koppen="Cfa", seismic_level=0, flyway="americas-atlantico"),
    Location(id="mexico-city", name="Ciudad de México", country="MX", lat=19.43, lon=-99.13,
             timezone="America/Mexico_City",
             koppen="Cwb", seismic_level=3, flyway="americas-central"),

    # ── Centroamérica, Caribe y Andes ─────────────────────────────────────
    Location(id="san-jose-cr", name="San José", country="CR", lat=9.93, lon=-84.08,
             timezone="America/Costa_Rica",
             koppen="Aw", seismic_level=3, flyway="americas-central"),
    Location(id="bogota", name="Bogotá", country="CO", lat=4.71, lon=-74.07,
             timezone="America/Bogota",
             koppen="Cfb", seismic_level=2, flyway="americas-central"),
    Location(id="quito", name="Quito", country="EC", lat=-0.18, lon=-78.47,
             timezone="America/Guayaquil",
             koppen="Cfb", seismic_level=3, flyway="americas-pacifico"),
    Location(id="lima", name="Lima", country="PE", lat=-12.05, lon=-77.04,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="la-paz", name="La Paz", country="BO", lat=-16.50, lon=-68.15,
             timezone="America/La_Paz",
             koppen="Cwc", seismic_level=2, flyway="americas-pacifico"),


    # ── Perú ──────────────────────────────────────────────────────────────
    # Se amplía a once ciudades por tres razones que no son de cercanía:
    #
    # 1. **El Niño tiene aquí su señal terrestre más fuerte del planeta.** El
    #    fenómeno se llama así porque lo nombraron pescadores peruanos al ver
    #    que el mar se calentaba por Navidad. La costa norte —Piura, Chiclayo,
    #    Tumbes— pasa de desierto a inundaciones en un evento fuerte.
    # 2. **Gradiente de altitud de 0 a 3.800 m** en menos de 300 km. Puno está
    #    a más altura que muchas cumbres europeas.
    # 3. **Tres zonas climáticas** en un país: desierto costero (BWh), Andes
    #    (Cwb/ETH) y Amazonía (Af). Es un laboratorio natural para contrastar
    #    si un patrón depende del clima o de la latitud.
    Location(id="piura", name="Piura", country="PE", lat=-5.19, lon=-80.63,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="chiclayo", name="Chiclayo", country="PE", lat=-6.77, lon=-79.84,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="trujillo", name="Trujillo", country="PE", lat=-8.11, lon=-79.03,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="iquitos", name="Iquitos", country="PE", lat=-3.75, lon=-73.25,
             timezone="America/Lima",
             koppen="Af", seismic_level=1, flyway="americas-atlantico"),
    Location(id="pucallpa", name="Pucallpa", country="PE", lat=-8.38, lon=-74.55,
             timezone="America/Lima",
             koppen="Af", seismic_level=1, flyway="americas-atlantico"),
    Location(id="huaraz", name="Huaraz", country="PE", lat=-9.53, lon=-77.53,
             timezone="America/Lima",
             koppen="Cwb", seismic_level=3, flyway="americas-pacifico"),
    Location(id="huancayo", name="Huancayo", country="PE", lat=-12.07, lon=-75.21,
             timezone="America/Lima",
             koppen="Cwb", seismic_level=2, flyway="americas-pacifico"),
    Location(id="cusco", name="Cusco", country="PE", lat=-13.53, lon=-71.97,
             timezone="America/Lima",
             koppen="Cwb", seismic_level=2, flyway="americas-pacifico"),
    Location(id="puno", name="Puno", country="PE", lat=-15.84, lon=-70.03,
             timezone="America/Lima",
             koppen="ETH", seismic_level=2, flyway="americas-pacifico"),
    Location(id="arequipa", name="Arequipa", country="PE", lat=-16.41, lon=-71.54,
             timezone="America/Lima",
             koppen="BWk", seismic_level=3, flyway="americas-pacifico"),
    Location(id="tacna", name="Tacna", country="PE", lat=-18.01, lon=-70.25,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    # ── Seis provincias añadidas por el dengue ─────────────────────────────
    #
    # No están aquí por su clima sino por su epidemiología: son las provincias
    # con más casos notificados de Perú que no tenían ninguna ciudad cerca. Con
    # ellas el panel pasa de 6 a 12 series y la carga cubierta del 38% al 59%.
    #
    # La razón no es de cobertura sino estadística. Con seis series solo dos
    # mostraban señal, y dos no bastan para distinguir habilidad de suerte —
    # que es la trampa en la que ya cayó el umbral térmico.
    #
    # Y son además un test falsable de lo que salió del análisis: si la
    # temperatura solo manda en el BORDE de la transmisión, Tumbes y Sullana
    # —calientes y saturadas como Piura— deberían fallar, mientras que Jaén y
    # Puerto Maldonado deberían parecerse a Trujillo. Predicción hecha antes de
    # mirar el dato.
    Location(id="sullana", name="Sullana", country="PE", lat=-4.90, lon=-80.69,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="tumbes", name="Tumbes", country="PE", lat=-3.57, lon=-80.46,
             timezone="America/Lima",
             koppen="BSh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="talara", name="Talara", country="PE", lat=-4.58, lon=-81.27,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    # Capital de la provincia de Morropón. El nombre de la provincia y el de su
    # capital no coinciden, y confundirlos rompería el emparejamiento.
    Location(id="chulucanas", name="Chulucanas", country="PE", lat=-5.09, lon=-80.16,
             timezone="America/Lima",
             koppen="BSh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="jaen", name="Jaén", country="PE", lat=-5.71, lon=-78.81,
             timezone="America/Lima",
             koppen="Aw", seismic_level=2, flyway="americas-pacifico"),
    Location(id="puerto-maldonado", name="Puerto Maldonado", country="PE",
             lat=-12.60, lon=-69.19, timezone="America/Lima",
             koppen="Am", seismic_level=1, flyway="americas-atlantico"),
    # ── Segunda tanda por epidemiología ───────────────────────────────────
    #
    # Diez provincias más con carga alta de dengue y sin ciudad cercana. Suben
    # la cobertura del panel del 59% al ~75% de los casos notificados del país.
    #
    # Como en la tanda anterior, el nombre de la ciudad y el de la provincia no
    # siempre coinciden, y confundirlos rompe el emparejamiento en silencio:
    # Yurimaguas es capital de Alto Amazonas, La Merced de Chanchamayo,
    # Chimbote de Santa, Tarapoto de San Martín, Quillabamba de La Convención y
    # Lambayeque es a la vez departamento y provincia.
    Location(id="ica", name="Ica", country="PE", lat=-14.07, lon=-75.73,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="yurimaguas", name="Yurimaguas", country="PE", lat=-5.90, lon=-76.10,
             timezone="America/Lima",
             koppen="Af", seismic_level=1, flyway="americas-atlantico"),
    Location(id="la-merced", name="La Merced", country="PE", lat=-11.06, lon=-75.34,
             timezone="America/Lima",
             koppen="Am", seismic_level=2, flyway="americas-atlantico"),
    Location(id="chimbote", name="Chimbote", country="PE", lat=-9.09, lon=-78.58,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="lambayeque", name="Lambayeque", country="PE", lat=-6.70, lon=-79.91,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="quillabamba", name="Quillabamba", country="PE", lat=-12.87, lon=-72.69,
             timezone="America/Lima",
             koppen="Am", seismic_level=2, flyway="americas-atlantico"),
    Location(id="tarapoto", name="Tarapoto", country="PE", lat=-6.49, lon=-76.37,
             timezone="America/Lima",
             koppen="Am", seismic_level=2, flyway="americas-atlantico"),
    Location(id="chincha", name="Chincha Alta", country="PE", lat=-13.42, lon=-76.13,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="paita", name="Paita", country="PE", lat=-5.09, lon=-81.11,
             timezone="America/Lima",
             koppen="BWh", seismic_level=3, flyway="americas-pacifico"),
    Location(id="satipo", name="Satipo", country="PE", lat=-11.25, lon=-74.64,
             timezone="America/Lima",
             koppen="Af", seismic_level=2, flyway="americas-atlantico"),

    # ── Sudamérica ────────────────────────────────────────────────────────
    Location(id="manaus", name="Manaos", country="BR", lat=-3.12, lon=-60.02,
             timezone="America/Manaus",
             koppen="Af", seismic_level=0, flyway="americas-atlantico"),
    Location(id="sao-paulo", name="São Paulo", country="BR", lat=-23.55, lon=-46.63,
             timezone="America/Sao_Paulo",
             koppen="Cfa", seismic_level=0, flyway="americas-atlantico"),
    Location(id="buenos-aires", name="Buenos Aires", country="AR", lat=-34.60, lon=-58.38,
             timezone="America/Argentina/Buenos_Aires",
             koppen="Cfa", seismic_level=0, flyway="americas-atlantico"),
    Location(id="santiago", name="Santiago", country="CL", lat=-33.45, lon=-70.67,
             timezone="America/Santiago",
             koppen="Csb", seismic_level=3, flyway="americas-pacifico"),
    Location(id="ushuaia", name="Ushuaia", country="AR", lat=-54.80, lon=-68.30,
             timezone="America/Argentina/Ushuaia",
             koppen="Cfc", seismic_level=2, flyway="americas-pacifico"),

    # ── África y Oriente Medio ────────────────────────────────────────────
    Location(id="marrakech", name="Marrakech", country="MA", lat=31.63, lon=-7.99,
             timezone="Africa/Casablanca",
             koppen="BSh", seismic_level=2, flyway="atlantico-este"),
    Location(id="cairo", name="El Cairo", country="EG", lat=30.04, lon=31.24,
             timezone="Africa/Cairo",
             koppen="BWh", seismic_level=2, flyway="africa-oriental-asia-occidental"),
    Location(id="lagos", name="Lagos", country="NG", lat=6.52, lon=3.38,
             timezone="Africa/Lagos",
             koppen="Aw", seismic_level=0, flyway="atlantico-este"),
    Location(id="nairobi", name="Nairobi", country="KE", lat=-1.29, lon=36.82,
             timezone="Africa/Nairobi",
             koppen="Cwb", seismic_level=2, flyway="africa-oriental-asia-occidental"),
    Location(id="cape-town", name="Ciudad del Cabo", country="ZA", lat=-33.92, lon=18.42,
             timezone="Africa/Johannesburg",
             koppen="Csb", seismic_level=0, flyway="africa-oriental-asia-occidental"),
    Location(id="kuwait-city", name="Kuwait", country="KW", lat=29.38, lon=47.99,
             timezone="Asia/Kuwait",
             koppen="BWh", seismic_level=1, flyway="africa-oriental-asia-occidental"),
    Location(id="tehran", name="Teherán", country="IR", lat=35.69, lon=51.39,
             timezone="Asia/Tehran",
             koppen="BSk", seismic_level=3, flyway="asia-central"),

    # ── Asia ──────────────────────────────────────────────────────────────
    Location(id="kathmandu", name="Katmandú", country="NP", lat=27.72, lon=85.32,
             timezone="Asia/Kathmandu",
             koppen="Cwb", seismic_level=3, flyway="asia-central"),
    Location(id="mumbai", name="Bombay", country="IN", lat=19.08, lon=72.88,
             timezone="Asia/Kolkata",
             koppen="Aw", seismic_level=1, flyway="asia-central"),
    Location(id="bangkok", name="Bangkok", country="TH", lat=13.76, lon=100.50,
             timezone="Asia/Bangkok",
             koppen="Aw", seismic_level=1, flyway="asia-oriental-australasia"),
    Location(id="singapore", name="Singapur", country="SG", lat=1.35, lon=103.82,
             timezone="Asia/Singapore",
             koppen="Af", seismic_level=0, flyway="asia-oriental-australasia"),
    Location(id="jakarta", name="Yakarta", country="ID", lat=-6.21, lon=106.85,
             timezone="Asia/Jakarta",
             koppen="Am", seismic_level=3, flyway="asia-oriental-australasia"),
    Location(id="manila", name="Manila", country="PH", lat=14.60, lon=120.98,
             timezone="Asia/Manila",
             koppen="Aw", seismic_level=3, flyway="asia-oriental-australasia"),
    Location(id="beijing", name="Pekín", country="CN", lat=39.90, lon=116.41,
             timezone="Asia/Shanghai",
             koppen="Dwa", seismic_level=2, flyway="asia-oriental-australasia"),
    Location(id="seoul", name="Seúl", country="KR", lat=37.57, lon=126.98,
             timezone="Asia/Seoul",
             koppen="Dwa", seismic_level=1, flyway="asia-oriental-australasia"),
    Location(id="tokyo", name="Tokio", country="JP", lat=35.68, lon=139.65,
             timezone="Asia/Tokyo",
             koppen="Cfa", seismic_level=3, flyway="asia-oriental-australasia"),

    # ── Oceanía ───────────────────────────────────────────────────────────
    Location(id="perth", name="Perth", country="AU", lat=-31.95, lon=115.86,
             timezone="Australia/Perth",
             koppen="Csa", seismic_level=1, flyway="asia-oriental-australasia"),
    Location(id="alice-springs", name="Alice Springs", country="AU", lat=-23.70, lon=133.88,
             timezone="Australia/Darwin",
             koppen="BWh", seismic_level=1, flyway="asia-oriental-australasia"),
    Location(id="sydney", name="Sídney", country="AU", lat=-33.87, lon=151.21,
             timezone="Australia/Sydney",
             koppen="Cfa", seismic_level=0, flyway="asia-oriental-australasia"),
    Location(id="wellington", name="Wellington", country="NZ", lat=-41.29, lon=174.78,
             timezone="Pacific/Auckland",
             koppen="Cfb", seismic_level=3, flyway="asia-oriental-australasia"),
]

BY_ID: dict[str, Location] = {loc.id: loc for loc in LOCATIONS}

# Subconjunto para historia profunda (décadas). Existe por una razón muy
# concreta: el límite gratuito de Open-Meteo se cuenta por PESO
# (ubicaciones × variables × días), no por número de peticiones. Un backfill de
# 10 años sobre las 49 ciudades con las 14 variables equivale a ~38.000
# llamadas ponderadas y no cabe en la cuota diaria de 10.000.
#
# Estas cubren el espectro climático completo con una fracción del coste, y son
# las que permiten calcular una climatología de verdad para medir anomalías.
#
# **Ojo con lo que esta lista significa hoy.** Dice qué ciudades TOCA
# descargar, no cuáles están descargadas, y las dos cifras ya no coinciden: el
# archivo cubre 47 ciudades y esta lista tiene 30. Lo que decide si una ciudad
# tiene anomalía es el DATO —`gold_climatology`, y de ahí `has_climatology`—,
# nunca esta constante.
#
# La distinción importa porque `opendengue.flagship_countries()` sigue usándola
# para decidir de qué países se ingiere dengue subnacional, y su regla dice
# "países con 20 años de ERA5". Desde que Manaos, São Paulo y Bogotá tienen
# archivo, esas dos cosas dejaron de ser lo mismo: Brasil y Colombia cumplen la
# regla escrita pero no entran, porque la lista no se ha ampliado. Ampliarla
# traería 2,1 millones de filas de dengue subnacional (~7 MB en bronze), que es
# una decisión y no un efecto secundario.
FLAGSHIP_IDS: tuple[str, ...] = (
    "utqiagvik",      # ET   — tundra ártica
    "yakutsk",        # Dfd  — continental extremo
    "reykjavik",      # Cfc  — oceánico subpolar
    "london",         # Cfb  — oceánico templado
    "madrid",         # Csa  — mediterráneo continentalizado
    "phoenix",        # BWh  — desierto cálido
    "mexico-city",    # Cwb  — subtropical de altura
    "singapore",      # Af   — ecuatorial húmedo
    "nairobi",        # Cwb  — tropical de altura
    "tokyo",          # Cfa  — subtropical húmedo
    "santiago",       # Csb  — mediterráneo austral
    "ushuaia",        # Cfc  — subantártico

    # Perú entero, porque es donde El Niño tiene su señal terrestre más fuerte
    # y porque su gradiente de altitud y sus tres zonas climáticas permiten
    # contrastar si un patrón depende del clima o de la latitud.
    "piura",          # BWh  — costa norte, epicentro de El Niño
    "chiclayo",       # BWh  — costa norte
    "trujillo",       # BWh  — costa norte
    "lima",           # BWh  — desierto costero templado por la corriente fría
    "tacna",          # BWh  — costa sur
    "sullana",        # BWh  — valle del Chira, hiperendémica de dengue
    "tumbes",         # BSh  — frontera con Ecuador
    "talara",         # BWh  — costa desértica extrema
    "chulucanas",     # BSh  — transición costa-sierra
    "jaen",           # Aw   — selva alta, 730 m
    "puerto-maldonado",  # Am — selva sur
    "ica",            # BWh  — costa sur
    "yurimaguas",     # Af   — selva baja
    "la-merced",      # Am   — selva central
    "chimbote",       # BWh  — costa de Áncash
    "lambayeque",     # BWh  — costa norte
    "quillabamba",    # Am   — selva de Cusco
    "tarapoto",       # Am   — selva alta
    "chincha",        # BWh  — costa sur
    "paita",          # BWh  — costa de Piura
    "satipo",         # Af   — selva central
    "iquitos",        # Af   — Amazonía
    "pucallpa",       # Af   — Amazonía
    "huaraz",         # Cwb  — Cordillera Blanca
    "huancayo",       # Cwb  — Andes centrales
    "cusco",          # Cwb  — Andes del sur
    "puno",           # ETH  — altiplano, 3.800 m
    "arequipa",       # BWk  — desierto de altura
)

FLAGSHIPS: list[Location] = [BY_ID[i] for i in FLAGSHIP_IDS]


def get(location_id: str) -> Location:
    if location_id not in BY_ID:
        raise KeyError(f"Ubicación desconocida: {location_id}")
    return BY_ID[location_id]


def resolve(ids: list[str] | None) -> list[Location]:
    """Resuelve una lista de ids a objetos Location. None o vacío = todas."""
    if not ids:
        return LOCATIONS
    return [get(i) for i in ids]
