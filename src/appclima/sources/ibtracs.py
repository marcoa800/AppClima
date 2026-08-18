"""IBTrACS — International Best Track Archive for Climate Stewardship.

El archivo global de referencia de ciclones tropicales, mantenido por NOAA NCEI.
Reúne en un formato único las trayectorias de todos los centros meteorológicos
del mundo, desde 1842 hasta hoy. Dominio público, sin API key.

**No es una API sino un CSV grande**, así que la ingesta funciona distinto al
resto de fuentes: se descarga en streaming y se parsea fila a fila, sin cargar
el fichero entero en memoria. El completo son 316 MB.

Aviso central sobre estos datos, y es el que decide el valor por defecto:

    Antes de la era de los satélites, los ciclones que nunca tocaron tierra ni
    cruzaron una ruta marítima simplemente NO SE OBSERVARON.

Un gráfico de "ciclones por año desde 1842" muestra una tendencia creciente
espectacular que es casi enteramente artefacto: mide cobertura de observación,
no actividad ciclónica. Por eso el fichero `since1980` existe y por eso es
nuestro valor por defecto — 1980 marca la cobertura satelital global fiable.
Es exactamente el mismo sesgo que ya medimos en los desastres históricos.

Docs: https://www.ncei.noaa.gov/products/international-best-track-archive
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx

from appclima.config import settings
from appclima.schemas.cyclones import CycloneTrackPoint

log = logging.getLogger(__name__)

BASE_URL = (
    "https://www.ncei.noaa.gov/data/"
    "international-best-track-archive-for-climate-stewardship-ibtracs/"
    "v04r01/access/csv"
)

# Conjuntos disponibles, con su tamaño real medido.
DATASETS: dict[str, str] = {
    "since1980": "ibtracs.since1980.list.v04r01.csv",   # 137 MB — el recomendado
    "all": "ibtracs.ALL.list.v04r01.csv",               # 316 MB — desde 1842
    "last3years": "ibtracs.last3years.list.v04r01.csv",  # 9 MB — para probar
}

# Índices de columna. IBTrACS trae 174, la mayoría duplicados por agencia; fijar
# los índices evita cargar 174 campos por fila para tirar 150.
COLS: dict[str, int] = {
    "sid": 0, "season": 1, "number": 2, "basin": 3, "subbasin": 4, "name": 5,
    "time": 6, "nature": 7, "lat": 8, "lon": 9,
    "wmo_wind": 10, "wmo_pres": 11, "wmo_agency": 12, "track_type": 13,
    "dist2land": 14, "landfall": 15,
    "usa_wind": 23, "usa_pres": 24, "usa_sshs": 25,
    "storm_speed": 172, "storm_dir": 173,
}


def _num(row: list[str], key: str) -> float | None:
    """Lee un campo numérico. IBTrACS marca los ausentes con blancos o espacios."""
    raw = row[COLS[key]].strip() if COLS[key] < len(row) else ""
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _text(row: list[str], key: str) -> str | None:
    raw = row[COLS[key]].strip() if COLS[key] < len(row) else ""
    return raw or None


def _parse_row(row: list[str]) -> CycloneTrackPoint | None:
    """Convierte una fila del CSV en un punto de trayectoria validado."""
    if len(row) <= COLS["lon"]:
        return None

    sid = row[COLS["sid"]].strip()
    raw_time = row[COLS["time"]].strip()
    if not sid or not raw_time:
        return None

    try:
        # IBTrACS da "YYYY-MM-DD HH:MM:SS" sin zona; es UTC por definición.
        time = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None

    lat, lon = _num(row, "lat"), _num(row, "lon")
    if lat is None or lon is None:
        return None

    # Algunas cuencas del Pacífico se publican con longitudes por encima de 180.
    # Sin normalizar, el Pacífico occidental aparecería fuera del mapa y el
    # cálculo de distancias a las ciudades ancla daría resultados absurdos.
    if lon > 180:
        lon -= 360
    elif lon < -180:
        lon += 360

    season_raw = _num(row, "season")
    if season_raw is None:
        return None

    sshs = _num(row, "usa_sshs")
    number = _num(row, "number")

    return CycloneTrackPoint(
        sid=sid,
        season=int(season_raw),
        number=int(number) if number is not None else None,
        basin=_text(row, "basin"),
        subbasin=_text(row, "subbasin"),
        name=_text(row, "name"),
        time=time,
        nature=_text(row, "nature"),
        track_type=_text(row, "track_type"),
        lat=lat,
        lon=lon,
        wmo_wind_kt=_num(row, "wmo_wind"),
        wmo_pressure_mb=_num(row, "wmo_pres"),
        wmo_agency=_text(row, "wmo_agency"),
        usa_wind_kt=_num(row, "usa_wind"),
        usa_pressure_mb=_num(row, "usa_pres"),
        usa_sshs=int(sshs) if sshs is not None and -5 <= sshs <= 5 else None,
        dist2land_km=_num(row, "dist2land"),
        landfall_km=_num(row, "landfall"),
        storm_speed_kt=_num(row, "storm_speed"),
        storm_dir_deg=_num(row, "storm_dir"),
    )


def fetch_tracks(
    dataset: str = "since1980",
    batch_size: int = 100_000,
) -> Iterator[list[CycloneTrackPoint]]:
    """Descarga y parsea IBTrACS en streaming, devolviendo lotes de puntos.

    Es un iterador de lotes y no una lista por la misma razón que en el archivo
    de Open-Meteo: el fichero completo son cientos de miles de filas, y
    materializarlas todas como objetos Pydantic antes de escribir nada se come
    varios GB de RAM sin necesidad.
    """
    if dataset not in DATASETS:
        raise ValueError(f"Dataset desconocido: {dataset}. Opciones: {list(DATASETS)}")

    url = f"{BASE_URL}/{DATASETS[dataset]}"
    log.info("Descargando IBTrACS %s desde %s", dataset, url)

    batch: list[CycloneTrackPoint] = []
    total = skipped = 0

    with httpx.stream(
        "GET",
        url,
        timeout=httpx.Timeout(60.0, read=300.0),
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    ) as response:
        response.raise_for_status()

        # iter_lines evita cargar 137 MB de golpe; el csv.reader consume el
        # generador línea a línea.
        reader = csv.reader(response.iter_lines())

        next(reader, None)  # cabecera
        next(reader, None)  # fila de UNIDADES, no de datos: sin esto entra una
                            # tormenta fantasma llamada "Year"

        for row in reader:
            point = _parse_row(row)
            if point is None:
                skipped += 1
                continue

            batch.append(point)
            total += 1

            if len(batch) >= batch_size:
                log.info("IBTrACS: %d puntos parseados", total)
                yield batch
                batch = []

    if batch:
        yield batch

    log.info("IBTrACS %s: %d puntos válidos, %d descartados", dataset, total, skipped)
