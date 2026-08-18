"""NOAA CPC — índice ONI (Oceanic Niño Index).

El índice operativo con el que la NOAA declara oficialmente El Niño y La Niña:
anomalía de temperatura del mar en la región Niño 3.4 del Pacífico ecuatorial,
en medias móviles de tres meses. Desde 1950, sin API key, un fichero de texto.

Es la fuente más pequeña del proyecto y probablemente la más útil, porque es
**el único predictor estacional de verdad** que vamos a tener: ENSO modula la
actividad ciclónica de cada cuenca y las anomalías de temperatura globales, y su
estado se conoce con meses de antelación.

Formato del fichero, en columnas fijas:

    SEAS  YR   TOTAL   ANOM
     DJF 1950  25.01  -1.32

`SEAS` son trimestres solapados: DJF es dic-ene-feb, JFM es ene-feb-mar, y así.
Cada mes aparece en tres estaciones distintas, lo cual es correcto — es una media
móvil, no una partición. Tratarlas como periodos independientes al agregar por
año triplicaría el peso de cada mes.

Docs: https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php
"""

from __future__ import annotations

import logging

import httpx

from appclima.config import settings
from appclima.schemas.population import OniValue

log = logging.getLogger(__name__)

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

# Orden de los trimestres solapados dentro del año, para poder ordenar la serie.
SEASON_ORDER: dict[str, int] = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def fetch_oni() -> list[OniValue]:
    """Descarga y parsea la serie ONI completa desde 1950."""
    response = httpx.get(
        ONI_URL,
        timeout=60.0,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    )
    response.raise_for_status()

    values: list[OniValue] = []
    skipped = 0

    for line in response.text.splitlines():
        parts = line.split()
        # La cabecera y las líneas en blanco no tienen 4 campos numéricos.
        if len(parts) != 4 or parts[0] not in SEASON_ORDER:
            skipped += 1
            continue

        season, year, sst, anomaly = parts
        try:
            values.append(
                OniValue(
                    year=int(year),
                    season=season,
                    season_index=SEASON_ORDER[season],
                    sst_c=float(sst),
                    anomaly_c=float(anomaly),
                )
            )
        except ValueError:
            skipped += 1

    log.info("ONI: %d trimestres desde %d, %d líneas ignoradas",
             len(values), min(v.year for v in values), skipped)
    return values
