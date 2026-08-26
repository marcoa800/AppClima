"""NOAA NCEI — archivo de peligros naturales (HazEl).

Tres bases de datos que cubren los desastres naturales más grandes de los que
existe registro: sismos significativos, tsunamis y erupciones volcánicas. El
evento más antiguo es del año -4360. Dominio público, sin API key, sin
registro.

Es lo que le faltaba al catálogo moderno de USGS: profundidad histórica y, sobre
todo, **impacto humano**. USGS dice que hubo un M7.5 en Tangshan en 1976; NOAA
añade que murieron 242.769 personas.

Y lo más interesante para modelar: los tres datasets están **enlazados por id**.
Un tsunami apunta al sismo que lo causó; una erupción apunta al tsunami que
generó. Eso permite reconstruir cascadas de desastres, que es donde vive el
patrón que casi nadie mira.

Docs: https://www.ngdc.noaa.gov/hazel/view/swagger
"""

from __future__ import annotations

import logging
import time

from appclima.config import settings
from appclima.http import get_json
from appclima.schemas.disasters import HistoricalDisaster

log = logging.getLogger(__name__)

# Id en el catálogo de atribución. Lo lee `test_atribucion` recorriendo
# el paquete: así, añadir un conector sin su entrada de licencia rompe
# los tests en vez de publicarse sin atribuir.
SOURCE_ID = "noaa-ncei"

BASE_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1"

ENDPOINTS: dict[str, str] = {
    "earthquake": "earthquakes",
    "tsunami": "tsunamis/events",
    "volcano": "volcanoes",
}

# La API rechaza itemsPerPage > 200 con un 400. Comprobado, no supuesto.
PAGE_SIZE = 200

# El año del evento más antiguo del archivo (una erupción). Se usa como suelo
# por defecto para pedir "todo" sin tener que adivinar.
EARLIEST_YEAR = -4400


def _to_int(value: object) -> int | None:
    """NOAA mezcla enteros y flotantes en campos que son conteos."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_item(item: dict, hazard_type: str) -> HistoricalDisaster | None:
    """Convierte un registro de NOAA al esquema unificado."""
    if item.get("year") is None:
        # Sin año no hay nada que situar en el tiempo.
        log.warning("Evento %s sin año — descartado", item.get("id"))
        return None

    return HistoricalDisaster(
        source_id=item["id"],
        hazard_type=hazard_type,  # type: ignore[arg-type]
        year=item["year"],
        month=item.get("month"),
        day=item.get("day"),
        hour=item.get("hour"),
        minute=item.get("minute"),
        latitude=item.get("latitude"),
        longitude=item.get("longitude"),
        country=item.get("country"),
        # En el dataset de volcanes el topónimo va en 'location'; en los otros
        # dos en 'locationName'.
        location_name=item.get("locationName") or item.get("location"),
        region_code=item.get("regionCode"),
        deaths=_to_int(item.get("deaths")),
        deaths_order=item.get("deathsAmountOrder"),
        injuries=_to_int(item.get("injuries")),
        injuries_order=item.get("injuriesAmountOrder"),
        damage_musd=item.get("damageMillionsDollars"),
        damage_order=item.get("damageAmountOrder"),
        houses_destroyed=_to_int(item.get("housesDestroyed")),
        deaths_total=_to_int(item.get("deathsTotal")),
        deaths_order_total=item.get("deathsAmountOrderTotal"),
        injuries_total=_to_int(item.get("injuriesTotal")),
        damage_musd_total=item.get("damageMillionsDollarsTotal"),
        eq_magnitude=item.get("eqMagnitude"),
        eq_depth_km=item.get("eqDepth"),
        eq_intensity=item.get("intensity"),
        tsunami_max_water_height_m=item.get("maxWaterHeight"),
        tsunami_num_runups=_to_int(item.get("numRunups")),
        volcano_vei=item.get("vei"),
        volcano_name=item.get("name") if hazard_type == "volcano" else None,
        volcano_elevation_m=item.get("elevation"),
        volcano_morphology=item.get("morphology"),
        caused_earthquake_id=item.get("earthquakeEventId"),
        caused_tsunami_id=item.get("tsunamiEventId"),
        published=bool(item.get("publish", True)),
    )


def fetch_hazard(
    hazard_type: str,
    min_year: int = EARLIEST_YEAR,
    max_year: int = 2030,
) -> list[HistoricalDisaster]:
    """Descarga un dataset completo, recorriendo todas sus páginas."""
    if hazard_type not in ENDPOINTS:
        raise ValueError(
            f"Peligro desconocido: {hazard_type}. Opciones: {list(ENDPOINTS)}"
        )

    url = f"{BASE_URL}/{ENDPOINTS[hazard_type]}"
    events: list[HistoricalDisaster] = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        payload = get_json(
            url,
            params={
                "minYear": min_year,
                "maxYear": max_year,
                "itemsPerPage": PAGE_SIZE,
                "page": page,
            },
        )

        # La respuesta trae la paginación en la raíz; la leemos en la primera
        # vuelta en lugar de adivinar cuántas páginas hay.
        total_pages = payload.get("totalPages", 1)
        items = payload.get("items", [])

        events.extend(
            event
            for item in items
            if (event := _parse_item(item, hazard_type)) is not None
        )

        log.info(
            "NOAA %s: página %d/%d, %d eventos acumulados",
            hazard_type, page, total_pages, len(events),
        )
        page += 1

        # Cortesía con un servicio público y gratuito.
        if page <= total_pages:
            time.sleep(settings.rate_limit_sleep)

    return events


def fetch_all(
    min_year: int = EARLIEST_YEAR,
    max_year: int = 2030,
) -> dict[str, list[HistoricalDisaster]]:
    """Los tres datasets, devueltos por tipo de peligro."""
    return {
        hazard: fetch_hazard(hazard, min_year=min_year, max_year=max_year)
        for hazard in ENDPOINTS
    }
