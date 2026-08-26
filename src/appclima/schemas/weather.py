"""Esquema del clima horario.

Decisión clave: el conjunto de variables está limitado a las que existen **a la
vez** en la API de pronóstico y en la de archivo (ERA5) de Open-Meteo. Así una
sola tabla cubre 1940→futuro sin columnas huérfanas, y el análisis de anomalías
puede comparar el presente contra la climatología sin hacer malabares.

Por eso no está aquí `uv_index` (solo pronóstico) ni `soil_temperature`
(solo archivo), aunque sean tentadores. Si algún día se necesitan, van en una
tabla aparte.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WeatherHour(BaseModel):
    """Una hora de observación o pronóstico en una ubicación."""

    model_config = ConfigDict(extra="forbid")

    location_id: str
    lat: float
    lon: float
    time: datetime = Field(description="Inicio de la hora, siempre en UTC")

    # `observed` = archivo/reanálisis (pasado). `forecast` = modelo (futuro).
    # Mezclarlos sin distinguir es la forma más rápida de invalidar un análisis.
    kind: str = Field(description="observed | forecast")

    # Qué modelo produjo la fila. Sin esta columna, una serie larga puede estar
    # cosida a partir de dos reanálisis distintos sin que nada lo delate: el
    # dato es plausible, la ingesta no falla y el salto se lee como clima.
    # Aquí pasó exactamente eso — ver el comentario de ARCHIVE_MODEL en
    # sources/open_meteo.py.
    model: str | None = Field(
        default=None, description="Modelo de la fuente: era5_seamless, best_match…"
    )

    temperature_2m: float | None = None
    apparent_temperature: float | None = None
    relative_humidity_2m: float | None = None
    dew_point_2m: float | None = None
    precipitation: float | None = None
    rain: float | None = None
    snowfall: float | None = None
    pressure_msl: float | None = None
    surface_pressure: float | None = None
    cloud_cover: float | None = None
    wind_speed_10m: float | None = None
    wind_direction_10m: float | None = None
    wind_gusts_10m: float | None = None
    shortwave_radiation: float | None = None


# Nombres exactos que pide la API, en el orden en que los pedimos.
HOURLY_VARIABLES: tuple[str, ...] = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "rain",
    "snowfall",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
)

# Subconjunto para el histórico profundo.
#
# El límite gratuito de Open-Meteo se cuenta por PESO: ubicaciones × variables
# × días. Pedir 14 variables en un backfill de décadas triplica el coste sin
# aportar nada al análisis, porque la climatología y las anomalías solo
# necesitan temperatura y precipitación.
#
# La presión está aquí por un motivo específico: es la variable necesaria para
# contrastar el mito del "clima sísmico" (spoiler: no existe correlación, y
# demostrarlo con datos propios es más honesto que fingir un hallazgo).
#
# Las columnas no pedidas quedan como NULL en bronze. Eso es correcto y
# deliberado: NULL significa "no se pidió", no "no había dato".
CORE_VARIABLES: tuple[str, ...] = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "pressure_msl",
    "surface_pressure",
)
