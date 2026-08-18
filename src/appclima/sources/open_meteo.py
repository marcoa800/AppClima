"""Open-Meteo: pronóstico y archivo histórico (ERA5).

Sin API key, sin registro. Gratis para uso no comercial hasta ~10.000 llamadas
al día. Es la mejor fuente meteorológica abierta que existe hoy.

Truco de eficiencia que usamos aquí: Open-Meteo acepta **varias coordenadas en
una sola petición** (`latitude=40.4,51.5&longitude=-3.7,-0.1`) y devuelve un
array de resultados. Nuestras 49 ciudades caben en 2 llamadas en vez de 49.
Cuando se piden varias, la respuesta es una lista; cuando se pide una sola, es
un objeto — hay que normalizar ese detalle, y es una fuente clásica de bugs.

Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from itertools import batched
from zoneinfo import ZoneInfo

from appclima.http import get_json
from appclima.locations import Location
from appclima.schemas.weather import CORE_VARIABLES, HOURLY_VARIABLES, WeatherHour

log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# El límite gratuito de Open-Meteo se cuenta por PESO, no por peticiones:
#
#     peso ≈ ubicaciones × (variables / 10) × (días / 7)
#
# Con topes aproximados de 600/minuto, 5.000/hora y 10.000/día. Esto explica
# por qué el pronóstico y el archivo necesitan lotes de tamaño distinto:
#
#   - Pronóstico: 9 días. 25 ubicaciones × 1,4 × 1,3 ≈ 45 de peso. Barato.
#   - Archivo: 90 días. 6 ubicaciones × 0,5 × 12,9 ≈ 39 de peso. También
#     barato, pero solo gracias a mantener el lote pequeño. Con 25 ubicaciones
#     y un año entero se dispara a ~1.800 y la API responde 429 al instante.
#
# Aprendido a base de un 429 real, no de leer la documentación.
BATCH_SIZE = 25
ARCHIVE_BATCH_SIZE = 6

UTC = ZoneInfo("UTC")


def _as_list(payload: object) -> list[dict]:
    """Normaliza la respuesta: siempre una lista, aunque venga un solo objeto."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise TypeError(f"Respuesta inesperada de Open-Meteo: {type(payload)}")


def _parse_block(block: dict, location: Location, kind: str) -> list[WeatherHour]:
    """Convierte el bloque `hourly` (arrays paralelos) en filas."""
    hourly = block.get("hourly")
    if not hourly:
        log.warning("Sin bloque hourly para %s", location.id)
        return []

    times = hourly.get("time", [])
    # Open-Meteo devuelve arrays paralelos: una lista por variable, todas de la
    # misma longitud que `time`. Los recorremos por índice.
    #
    # Recorremos SIEMPRE las 14 variables del esquema, no solo las pedidas: las
    # que no se pidieron quedan a NULL y el Parquet mantiene el mismo esquema
    # sea cual sea la llamada. Sin esto, bronze acabaría con ficheros de
    # columnas distintas y DuckDB tendría que reconciliarlos al leer.
    columns = {var: hourly.get(var) or [None] * len(times) for var in HOURLY_VARIABLES}

    rows: list[WeatherHour] = []
    for i, raw_time in enumerate(times):
        # Con timezone=UTC la API devuelve "2026-08-17T14:00" sin offset.
        parsed = datetime.fromisoformat(raw_time)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        rows.append(
            WeatherHour(
                location_id=location.id,
                lat=location.lat,
                lon=location.lon,
                time=parsed,
                kind=kind,
                **{var: columns[var][i] for var in HOURLY_VARIABLES},
            )
        )
    return rows


def _fetch(
    url: str,
    locations: list[Location],
    extra_params: dict[str, object],
    kind: str,
    variables: tuple[str, ...] = HOURLY_VARIABLES,
    batch_size: int = BATCH_SIZE,
    pace: float = 0.0,
) -> list[WeatherHour]:
    rows: list[WeatherHour] = []

    for index, chunk in enumerate(batched(locations, batch_size)):
        # Pausa entre lotes para no acercarnos al límite por minuto. En el
        # pronóstico sobra; en el archivo es lo que evita el 429.
        if index > 0 and pace:
            time.sleep(pace)

        params: dict[str, object] = {
            "latitude": ",".join(str(loc.lat) for loc in chunk),
            "longitude": ",".join(str(loc.lon) for loc in chunk),
            "hourly": ",".join(variables),
            # UTC en el origen. Convertir a hora local es problema de la UI,
            # nunca del almacén: mezclar zonas en el warehouse es irreversible.
            "timezone": "UTC",
            **extra_params,
        }

        payload = _as_list(get_json(url, params=params))

        if len(payload) != len(chunk):
            raise ValueError(
                f"Open-Meteo devolvió {len(payload)} bloques para {len(chunk)} "
                "ubicaciones. El orden ya no es fiable: abortando."
            )

        for block, location in zip(payload, chunk, strict=True):
            rows.extend(_parse_block(block, location, kind))

    return rows


def fetch_forecast(
    locations: list[Location],
    forecast_days: int = 7,
    past_days: int = 2,
) -> list[WeatherHour]:
    """Pronóstico horario, con unos días de pasado reciente para solapar.

    El solape con `past_days` no es un capricho: garantiza que no queden huecos
    si un job programado falla y se salta una ejecución.
    """
    return _fetch(
        FORECAST_URL,
        locations,
        {"forecast_days": forecast_days, "past_days": past_days},
        kind="forecast",
    )


def fetch_archive(
    locations: list[Location],
    start: date,
    end: date,
    chunk_days: int = 90,
    variables: tuple[str, ...] = CORE_VARIABLES,
    pace: float = 1.0,
) -> Iterator[list[WeatherHour]]:
    """Archivo histórico (reanálisis ERA5). Datos desde 1940.

    Devuelve un **iterador de tramos**, no una lista. El motivo es de memoria:
    10 años × 49 ubicaciones son 4,3 millones de filas, y materializarlas todas
    como objetos Pydantic antes de escribir nada se come varios GB de RAM. Con
    un iterador, quien llama escribe cada tramo a Parquet y libera.

    El troceado también respeta el límite por peso de la API: tramos de 90 días
    con lotes de 6 ubicaciones dan ~39 de peso por petición, muy por debajo del
    tope de 600/minuto. Ver el comentario de ARCHIVE_BATCH_SIZE arriba.

    Por defecto pide solo CORE_VARIABLES (5 en vez de 14), lo que reduce el
    coste a un tercio. Las demás columnas quedan a NULL, que es lo honesto:
    significan "no se pidió", no "no había dato".

    Además ERA5 tiene ~5 días de latencia: los datos de ayer no están todavía.
    """
    if start > end:
        raise ValueError(f"start ({start}) es posterior a end ({end})")

    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=chunk_days - 1), end)
        rows = _fetch(
            ARCHIVE_URL,
            locations,
            {"start_date": cursor.isoformat(), "end_date": chunk_end.isoformat()},
            kind="observed",
            variables=variables,
            batch_size=ARCHIVE_BATCH_SIZE,
            pace=pace,
        )
        log.info("Archivo %s→%s: %d filas", cursor, chunk_end, len(rows))
        yield rows

        cursor = chunk_end + timedelta(days=1)
        if pace:
            time.sleep(pace)
