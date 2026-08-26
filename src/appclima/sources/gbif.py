"""GBIF — Global Biodiversity Information Facility.

El mayor agregador de datos de biodiversidad del mundo: más de 3.000 millones de
registros de miles de instituciones, museos y programas de ciencia ciudadana.
Gratis, sin API key, sin registro.

Se usa exclusivamente para fenología, con la API de facetas. Ver el módulo de
esquemas para el razonamiento completo; en resumen:

  - Paginar es imposible (17,5 M de registros para una sola especie, y el
    buscador corta en 100.000 de desplazamiento).
  - Una petición con `facet=month` y `limit=0` devuelve los doce recuentos
    mensuales sin transferir un solo registro.

Docs: https://techdocs.gbif.org/en/openapi/v1/occurrence
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator

from appclima.config import settings
from appclima.http import get_json
from appclima.locations import BY_ID
from appclima.schemas.phenology import PhenologyYear

log = logging.getLogger(__name__)

# Id en el catálogo de atribución. Lo lee `test_atribucion` recorriendo
# el paquete: así, añadir un conector sin su entrada de licencia rompe
# los tests en vez de publicarse sin atribuir.
SOURCE_ID = "gbif"

BASE_URL = "https://api.gbif.org/v1"

# Migradoras de larga distancia bien cubiertas en GBIF. Se eligen especies
# cuya llegada primaveral es un evento marcado y popularmente reconocido, que
# es justo lo que garantiza que haya registros suficientes.
#
# Los taxonKey van fijados y NO resueltos en tiempo de ejecución, para que la
# ingesta sea reproducible. Un test comprueba que siguen resolviendo a la
# especie correcta: dos de estas claves las puse de memoria al escribir el
# módulo y estaban equivocadas, lo que habría descargado en silencio la especie
# equivocada durante 800 peticiones.
SPECIES: dict[int, tuple[str, str]] = {
    9515886: ("Hirundo rustica", "Golondrina común"),
    5228676: ("Apus apus", "Vencejo común"),
    5231918: ("Cuculus canorus", "Cuco común"),
    2481912: ("Ciconia ciconia", "Cigüeña blanca"),
}

# Residentes que NO migran, usadas como control del sesgo de observación.
# Su percentil de "llegada" debería ser plano en el tiempo; lo que se mueva en
# ellas mide el cambio del comportamiento del observador, no de las aves.
CONTROL_SPECIES: dict[int, tuple[str, str]] = {
    5231190: ("Passer domesticus", "Gorrión común"),
    9705453: ("Parus major", "Carbonero común"),
}

# Ciudades con cobertura densa de GBIF y dentro del área de estas especies.
TARGET_CITIES: tuple[str, ...] = (
    "madrid", "barcelona", "london", "berlin", "moscow", "athens", "istanbul",
)

# Semilado de la caja de búsqueda, en grados. Un grado son ~111 km, así que 1.0
# da una ventana de ~220 km de lado. Suficiente para acumular registros y lo
# bastante pequeña para que la fecha de llegada tenga sentido local: una caja
# de escala continental mezclaría latitudes con calendarios distintos.
BBOX_DEGREES = 1.0


def resolve_species(name: str) -> int | None:
    """Busca el taxonKey de una especie por nombre científico."""
    payload = get_json(f"{BASE_URL}/species/match", params={"name": name})
    return payload.get("usageKey")


def fetch_phenology(
    years: range,
    species: dict[int, tuple[str, str]] | None = None,
    cities: tuple[str, ...] = TARGET_CITIES,
    bbox: float = BBOX_DEGREES,
    is_control: bool = False,
) -> Iterator[list[PhenologyYear]]:
    """Recuentos mensuales por especie, ciudad y año.

    Devuelve un lote por especie, para poder escribir a bronze de forma
    incremental: si la ingesta se corta a mitad, lo ya descargado se conserva.
    """
    species = species or SPECIES

    for species_key, (scientific, common) in species.items():
        rows: list[PhenologyYear] = []

        for city_id in cities:
            location = BY_ID[city_id]
            lat_range = f"{location.lat - bbox},{location.lat + bbox}"
            lon_range = f"{location.lon - bbox},{location.lon + bbox}"

            for year in years:
                payload = get_json(
                    f"{BASE_URL}/occurrence/search",
                    params={
                        "taxonKey": species_key,
                        "decimalLatitude": lat_range,
                        "decimalLongitude": lon_range,
                        "year": year,
                        # Sin coordenadas no se puede acotar geográficamente, y
                        # los registros con problemas geoespaciales conocidos
                        # aparecen en el océano o en el país equivocado.
                        "hasCoordinate": "true",
                        "hasGeospatialIssue": "false",
                        "limit": 0,
                        "facet": "month",
                        "facetLimit": 12,
                    },
                )

                total = payload.get("count", 0)
                facets = payload.get("facets") or []
                counts = {
                    int(c["name"]): c["count"]
                    for c in (facets[0]["counts"] if facets else [])
                }

                rows.append(
                    PhenologyYear(
                        species_key=species_key,
                        species_name=scientific,
                        common_name=common,
                        location_id=city_id,
                        bbox_degrees=bbox,
                        is_control=is_control,
                        year=year,
                        total_records=total,
                        **{f"m{m:02d}": counts.get(m, 0) for m in range(1, 13)},
                    )
                )

                time.sleep(settings.rate_limit_sleep)

            log.info("GBIF %s en %s: %d años", common, city_id, len(years))

        yield rows
