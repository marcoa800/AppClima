"""Esquema de observaciones de aves, modelado sobre eBird API 2.0.

Dos avisos sobre la naturaleza de este dato, porque condicionan todo análisis
que se haga con él:

1. **Es ciencia ciudadana, no una red de sensores.** El número de observaciones
   depende de cuánta gente estaba mirando. Un pico en abril puede significar
   "llegaron las aves" o "empezó la temporada y salió más gente al campo". Para
   detectar migración de verdad hay que normalizar por esfuerzo de observación,
   no contar observaciones en bruto.

2. **`how_many` puede ser null** aunque la observación sea válida: el
   observador vio la especie pero no contó individuos. Tratarlo como 0 sesga
   los recuentos a la baja.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BirdObservation(BaseModel):
    """Una observación de una especie en un punto y momento."""

    model_config = ConfigDict(extra="forbid")

    # Ubicación ancla desde la que se hizo la búsqueda, para poder unir con el
    # clima. No es la coordenada de la observación: esa es lat/lon.
    location_id: str
    search_radius_km: int

    species_code: str = Field(description="Código eBird, ej. 'houspa'")
    common_name: str | None = None
    scientific_name: str | None = None

    obs_datetime: datetime = Field(
        description="Hora LOCAL del observador. eBird no da zona horaria."
    )
    obs_date_only: bool = Field(
        default=False,
        description="True si el observador no anotó la hora (medianoche implícita)",
    )

    how_many: int | None = Field(
        default=None, description="Nº de individuos. None = presencia sin recuento."
    )

    lat: float
    lon: float
    loc_id: str | None = None
    loc_name: str | None = None

    obs_valid: bool = True
    obs_reviewed: bool = False
    checklist_id: str | None = Field(default=None, description="subId de eBird")
