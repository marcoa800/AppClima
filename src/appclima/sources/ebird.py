"""eBird API 2.0 (Cornell Lab of Ornithology).

La mejor fuente de observaciones de aves del mundo: cientos de millones de
registros de ciencia ciudadana, actualizados al minuto. Requiere un token
gratuito e instantáneo en https://ebird.org/api/keygen

Límites de la API que condicionan el diseño:

  - `dist` máximo **50 km** de radio
  - `back` máximo **30 días** hacia atrás
  - Devuelve solo la observación **más reciente por especie**, no todas. Es un
    endpoint de "qué hay ahora por aquí", no un histórico. Para series
    temporales largas hay que usar GBIF o las descargas masivas de eBird.

Y el aviso importante sobre `obsDt`: eBird devuelve la hora **local del
observador sin zona horaria**. No hay forma de convertirla a UTC de manera
fiable desde la respuesta. La guardamos tal cual y lo documentamos, porque
inventarse una zona es peor que admitir la ambigüedad.

Docs: https://documenter.getpostman.com/view/664302/S1ENwy59
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from appclima.config import settings
from appclima.http import get_json
from appclima.locations import Location
from appclima.schemas.birds import BirdObservation

log = logging.getLogger(__name__)

# Id en el catálogo de atribución. Lo lee `test_atribucion` recorriendo
# el paquete: así, añadir un conector sin su entrada de licencia rompe
# los tests en vez de publicarse sin atribuir.
SOURCE_ID = "ebird"

RECENT_GEO_URL = "https://api.ebird.org/v2/data/obs/geo/recent"

MAX_RADIUS_KM = 50
MAX_DAYS_BACK = 30


class MissingTokenError(RuntimeError):
    """No hay token de eBird configurado."""


def has_token() -> bool:
    return bool(settings.ebird_token.strip())


def _parse_obs_datetime(raw: str) -> tuple[datetime, bool]:
    """Parsea `obsDt`, que llega como 'YYYY-MM-DD HH:MM' o solo 'YYYY-MM-DD'.

    Devuelve (datetime, date_only). Cuando el observador no anotó la hora,
    marcamos date_only=True para que el análisis pueda excluir esos registros
    de cualquier cálculo que dependa de la hora del día.
    """
    raw = raw.strip()
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M"), False
    except ValueError:
        return datetime.strptime(raw, "%Y-%m-%d"), True


def _parse_observation(
    item: dict,
    location: Location,
    radius_km: int,
) -> BirdObservation | None:
    try:
        obs_dt, date_only = _parse_obs_datetime(item["obsDt"])
    except (KeyError, ValueError) as exc:
        log.warning("Observación con fecha ilegible (%s) — descartada: %s",
                    item.get("obsDt"), exc)
        return None

    return BirdObservation(
        location_id=location.id,
        search_radius_km=radius_km,
        species_code=item["speciesCode"],
        common_name=item.get("comName"),
        scientific_name=item.get("sciName"),
        obs_datetime=obs_dt,
        obs_date_only=date_only,
        # None a propósito si falta: el observador vio la especie pero no contó
        # individuos. Convertirlo en 0 sesgaría los recuentos a la baja.
        how_many=item.get("howMany"),
        lat=item["lat"],
        lon=item["lng"],
        loc_id=item.get("locId"),
        loc_name=item.get("locName"),
        obs_valid=bool(item.get("obsValid", True)),
        obs_reviewed=bool(item.get("obsReviewed", False)),
        checklist_id=item.get("subId"),
    )


def fetch_recent_observations(
    locations: list[Location],
    radius_km: int = 25,
    days_back: int = 7,
) -> list[BirdObservation]:
    """Observaciones recientes alrededor de cada ubicación ancla."""
    if not has_token():
        raise MissingTokenError(
            "Falta APPCLIMA_EBIRD_TOKEN. Consigue uno gratis en "
            "https://ebird.org/api/keygen y ponlo en el fichero .env"
        )

    radius_km = min(radius_km, MAX_RADIUS_KM)
    days_back = min(days_back, MAX_DAYS_BACK)

    headers = {"X-eBirdApiToken": settings.ebird_token.strip()}
    observations: list[BirdObservation] = []

    # Una llamada por ubicación: el endpoint geo no acepta lotes. Con 49
    # ubicaciones son 49 llamadas, así que espaciamos por cortesía.
    for location in locations:
        payload = get_json(
            RECENT_GEO_URL,
            params={
                "lat": location.lat,
                "lng": location.lon,
                "dist": radius_km,
                "back": days_back,
            },
            headers=headers,
        )

        parsed = [
            obs
            for item in payload
            if (obs := _parse_observation(item, location, radius_km)) is not None
        ]
        observations.extend(parsed)
        log.info("eBird %s: %d especies", location.id, len(parsed))

        time.sleep(settings.rate_limit_sleep)

    return observations
