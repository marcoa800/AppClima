"""USGS Earthquake Catalog — el estándar mundial de datos sísmicos.

Gratis, sin key, sin registro. Cobertura global, actualización en minutos, y
catálogo histórico que llega a 1900. La API implementa el estándar FDSN, el
mismo que usan los observatorios sismológicos de todo el mundo.

Dos límites reales que hay que respetar:

  - **20.000 eventos por consulta.** Pasado eso devuelve 400. Por eso troceamos
    por ventanas de tiempo en lugar de pedir décadas de golpe.
  - Los eventos recientes se **revisan durante días**: una magnitud puede
    cambiar de 6.1 a 6.3 al día siguiente. El campo `updated` es lo que permite
    quedarnos con la última versión al deduplicar en silver.

Docs: https://earthquake.usgs.gov/fdsnws/event/1/
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from appclima.http import get_json
from appclima.schemas.quakes import Earthquake

log = logging.getLogger(__name__)

# Id en el catálogo de atribución. Lo lee `test_atribucion` recorriendo
# el paquete: así, añadir un conector sin su entrada de licencia rompe
# los tests en vez de publicarse sin atribuir.
SOURCE_ID = "usgs"

QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Límite duro de la API. Nos quedamos por debajo para tener margen.
MAX_EVENTS_PER_QUERY = 20_000


def _epoch_ms_to_dt(value: int | float | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _parse_feature(feature: dict) -> Earthquake | None:
    """Convierte un Feature GeoJSON en un Earthquake validado."""
    props = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or []

    # Sin geometría no hay evento utilizable. Pasa muy rara vez, pero pasa.
    if len(coords) < 2 or coords[0] is None or coords[1] is None:
        log.warning("Evento %s sin coordenadas válidas — descartado", feature.get("id"))
        return None

    origin_time = _epoch_ms_to_dt(props.get("time"))
    if origin_time is None:
        log.warning("Evento %s sin timestamp — descartado", feature.get("id"))
        return None

    return Earthquake(
        event_id=feature["id"],
        time=origin_time,
        updated=_epoch_ms_to_dt(props.get("updated")),
        magnitude=props.get("mag"),
        magnitude_type=props.get("magType"),
        lon=coords[0],
        lat=coords[1],
        depth_km=coords[2] if len(coords) > 2 else None,
        place=props.get("place"),
        event_type=props.get("type"),
        # USGS usa 0/1 en lugar de booleano.
        tsunami=bool(props.get("tsunami")),
        significance=props.get("sig"),
        alert=props.get("alert"),
        status=props.get("status"),
        felt=props.get("felt"),
        cdi=props.get("cdi"),
        mmi=props.get("mmi"),
        network=props.get("net"),
        url=props.get("url"),
    )


def _fetch_window(
    start: datetime,
    end: datetime,
    min_magnitude: float | None,
) -> list[Earthquake]:
    params: dict[str, object] = {
        "format": "geojson",
        "starttime": start.isoformat(),
        "endtime": end.isoformat(),
        "orderby": "time",
        "limit": MAX_EVENTS_PER_QUERY,
    }
    if min_magnitude is not None:
        params["minmagnitude"] = min_magnitude

    payload = get_json(QUERY_URL, params=params)
    features = payload.get("features", [])

    if len(features) >= MAX_EVENTS_PER_QUERY:
        # Silencio aquí sería mentir: habría eventos perdidos sin avisar.
        log.warning(
            "La ventana %s→%s alcanzó el límite de %d eventos. Hay datos "
            "truncados: usa una ventana más corta o una magnitud mínima mayor.",
            start.date(), end.date(), MAX_EVENTS_PER_QUERY,
        )

    quakes = [q for f in features if (q := _parse_feature(f)) is not None]
    log.info("USGS %s→%s: %d eventos", start.date(), end.date(), len(quakes))
    return quakes


def fetch_recent(
    days_back: int = 7,
    min_magnitude: float | None = 2.5,
) -> list[Earthquake]:
    """Eventos de los últimos N días.

    Con magnitud mínima 2.5 salen unos 55-60 eventos al día en todo el planeta
    (medido: 395 en 7 días), un volumen muy cómodo. La cifra sube bastante
    durante secuencias de réplicas de un sismo grande, así que no conviene
    dimensionar nada asumiendo que es constante.

    Bajar a 1.0 multiplica por diez y añade sobre
    todo ruido de redes densas de EEUU, California y Japón, que detectan
    micro-sismos que en el resto del mundo pasarían desapercibidos. Ese sesgo
    de detección hay que tenerlo presente en cualquier comparación regional.
    """
    end = datetime.now(UTC)
    start = end - timedelta(days=days_back)
    return _fetch_window(start, end, min_magnitude)


def fetch_range(
    start: date,
    end: date,
    min_magnitude: float | None = 4.5,
    window_days: int = 90,
) -> list[Earthquake]:
    """Rango histórico, troceado automáticamente para no chocar con el límite.

    Con magnitud mínima 4.5 el planeta produce unos 7.500 eventos al año
    (medido: 79.106 entre 2016 y mediados de 2026), así que ventanas de 90 días
    van muy holgadas frente al tope de 20.000.
    """
    if start > end:
        raise ValueError(f"start ({start}) es posterior a end ({end})")

    quakes: list[Earthquake] = []
    cursor = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    final = datetime.combine(end, datetime.max.time(), tzinfo=UTC)

    while cursor < final:
        window_end = min(cursor + timedelta(days=window_days), final)
        quakes.extend(_fetch_window(cursor, window_end, min_magnitude))
        cursor = window_end

    return quakes
