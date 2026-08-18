"""Esquema de ciclones tropicales, modelado sobre IBTrACS v04.

IBTrACS no es un catálogo de tormentas: es un catálogo de **puntos de
trayectoria**. Cada huracán aparece como decenas de filas, una cada 3 o 6 horas,
con su posición e intensidad en ese instante. Agregar a "una fila por tormenta"
es trabajo de la capa gold, no de la ingesta.

Tres particularidades de la fuente que condicionan el modelado:

1. **174 columnas, y la mayoría son duplicados por agencia.** El mismo ciclón lo
   siguen a la vez el JTWC, el JMA, el centro de Nueva Delhi, Météo-France... y
   cada uno aporta su propia estimación de viento y presión. Nos quedamos con la
   columna WMO (la agencia oficial responsable de cada cuenca) y con la de
   Estados Unidos, que es la única que cubre todas las cuencas de forma
   homogénea y trae la escala Saffir-Simpson.

2. **La segunda fila del CSV son las unidades, no datos.** Parsearla como fila
   mete una tormenta fantasma llamada "Year" en el dataset.

3. **`track_type` distingue la trayectoria principal de las secundarias.** Un
   mismo sistema puede tener trayectorias 'spur' que son fragmentos alternativos
   de un centro de análisis distinto. Contarlas como tormentas propias duplica
   los recuentos por temporada.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CycloneTrackPoint(BaseModel):
    """Una observación de un ciclón tropical en un instante concreto."""

    model_config = ConfigDict(extra="forbid")

    sid: str = Field(description="Identificador de la tormenta en IBTrACS")
    season: int = Field(description="Temporada. En el hemisferio sur cruza el año")
    number: int | None = Field(default=None, description="Nº dentro de la temporada")

    basin: str | None = Field(
        default=None, description="NA, EP, WP, NI, SI, SP, SA"
    )
    subbasin: str | None = None
    name: str | None = Field(default=None, description="UNNAMED si no recibió nombre")

    time: datetime = Field(description="Instante de la observación, en UTC")

    nature: str | None = Field(
        default=None,
        description="TS tropical · ET extratropical · SS subtropical · DS disturbio",
    )
    track_type: str | None = Field(
        default=None, description="main = trayectoria principal; el resto son spurs"
    )

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

    # Intensidad según la agencia WMO responsable de la cuenca.
    wmo_wind_kt: float | None = None
    wmo_pressure_mb: float | None = None
    wmo_agency: str | None = None

    # Intensidad según EE. UU. Cubre todas las cuencas de forma homogénea, así
    # que es la única base válida para comparar entre océanos.
    usa_wind_kt: float | None = None
    usa_pressure_mb: float | None = None
    usa_sshs: int | None = Field(
        default=None,
        ge=-5,
        le=5,
        description="Saffir-Simpson: 1-5 huracán; ≤0 aún no lo es",
    )

    dist2land_km: float | None = Field(
        default=None, description="Distancia a tierra desde este punto"
    )
    landfall_km: float | None = Field(
        default=None, description="Distancia al siguiente toque de tierra"
    )

    storm_speed_kt: float | None = Field(
        default=None, description="Velocidad de traslación del sistema"
    )
    storm_dir_deg: float | None = None
