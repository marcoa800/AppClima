"""Esquema sísmico, modelado sobre el catálogo GeoJSON de USGS.

USGS es generoso con los nulls: `mag` puede faltar en eventos muy pequeños,
`alert` solo existe en eventos significativos, y `felt`/`cdi`/`mmi` dependen de
que haya habido reportes ciudadanos. Todo eso es opcional a propósito.

`event_type` importa más de lo que parece: el catálogo incluye explosiones
mineras, deslizamientos y ensayos nucleares junto a los terremotos. Filtrar por
`event_type = 'earthquake'` en silver evita que un análisis de sismicidad
natural quede contaminado por actividad humana.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Earthquake(BaseModel):
    """Un evento sísmico del catálogo USGS."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(description="id de USGS, clave natural para deduplicar")
    time: datetime = Field(description="Origen del evento, en UTC")
    updated: datetime | None = Field(
        default=None,
        description="Última revisión. USGS recalcula magnitudes durante días.",
    )

    magnitude: float | None = None
    magnitude_type: str | None = Field(
        default=None,
        description="mww, mb, ml… No son intercambiables entre sí.",
    )

    lat: float
    lon: float
    depth_km: float | None = Field(
        default=None,
        description="Profundidad. Negativa = por encima del nivel del mar.",
    )

    place: str | None = None
    event_type: str | None = Field(
        default=None, description="earthquake, quarry blast, explosion…"
    )

    tsunami: bool = False
    significance: int | None = Field(
        default=None, description="Índice sig de USGS: magnitud + impacto + reportes"
    )
    alert: str | None = Field(default=None, description="green | yellow | orange | red")
    status: str | None = Field(default=None, description="automatic | reviewed | deleted")

    felt: int | None = Field(default=None, description="Nº de reportes ciudadanos")
    cdi: float | None = Field(default=None, description="Intensidad máxima reportada")
    mmi: float | None = Field(default=None, description="Intensidad instrumental estimada")

    network: str | None = None
    url: str | None = None
