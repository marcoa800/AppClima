"""Esquemas Pydantic: validación en el borde del sistema.

Cada fuente externa se valida aquí, en el momento de entrar. Si Open-Meteo
cambia un nombre de campo o USGS devuelve un null donde antes había un número,
queremos enterarnos en la ingesta con un error claro — no tres semanas después
al ver una gráfica rara.
"""

from appclima.schemas.birds import BirdObservation
from appclima.schemas.quakes import Earthquake
from appclima.schemas.weather import WeatherHour

__all__ = ["BirdObservation", "Earthquake", "WeatherHour"]
