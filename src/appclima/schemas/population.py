"""Esquemas de población y del índice ENSO.

La población no es "otra fuente más": es **el denominador que hace comparable
todo lo demás**.

Todas las cifras de muertes que hay en el proyecto son absolutas, y eso engaña
sistemáticamente. El terremoto de Shaanxi de 1556 mató a 830.000 personas y el
de Tangshan de 1976 a 242.769, así que Shaanxi parece 3,4 veces peor. Pero en
1556 la humanidad eran unos 500 millones de personas y en 1976 unos 4.100
millones: en proporción, Shaanxi fue casi 28 veces más letal.

Sin denominador, cualquier serie histórica de víctimas mide sobre todo cuánta
gente había disponible para morir.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PopulationYear(BaseModel):
    """Población de un país (o agregado) en un año, del Banco Mundial."""

    model_config = ConfigDict(extra="forbid")

    country_id: str = Field(description="Código ISO3, o código de agregado")
    country_name: str
    iso2: str | None = None
    year: int
    population: int | None = None

    # Los agregados (WLD, regiones, grupos de renta) vienen mezclados con los
    # países en la misma respuesta. Sumar sin filtrar cuenta a cada persona
    # varias veces: una como país, otra como región, otra como grupo de renta.
    is_aggregate: bool = Field(
        description="True para World, regiones y grupos de renta"
    )
    region: str | None = None
    income_level: str | None = None


class WorldPopulationEstimate(BaseModel):
    """Población mundial en un año anterior a las estadísticas modernas.

    El Banco Mundial arranca en 1960. Para normalizar la peste negra o el
    terremoto de Shaanxi hace falta llegar mucho más atrás, y ahí solo hay
    estimaciones demográficas con incertidumbre grande — la misma lógica que el
    catálogo de epidemias: rango, nunca cifra única.
    """

    model_config = ConfigDict(extra="forbid")

    year: int = Field(description="Negativo para años a.C.")
    population_low: int
    population_high: int
    confidence: Literal["alta", "media", "baja"]
    source: str
    note: str | None = None


class OniValue(BaseModel):
    """Índice ONI: el estado de El Niño / La Niña en una estación trimestral.

    Es la anomalía de temperatura superficial del mar en la región Niño 3.4 del
    Pacífico ecuatorial, promediada en ventanas de tres meses. Es el índice
    operativo que usa la NOAA para declarar oficialmente si hay El Niño o
    La Niña.

    Importa aquí porque es **el mejor predictor estacional que existe** para
    actividad ciclónica y anomalías de temperatura globales, y porque se conoce
    con meses de antelación. Ver `gold_enso_cyclones`.
    """

    model_config = ConfigDict(extra="forbid")

    year: int
    season: str = Field(description="Trimestre solapado: DJF, JFM, FMA…")
    season_index: int = Field(ge=1, le=12, description="1 = DJF, para poder ordenar")
    sst_c: float = Field(description="Temperatura absoluta de la región Niño 3.4")
    anomaly_c: float = Field(description="El valor ONI propiamente dicho")

    @property
    def phase(self) -> str:
        """Umbrales oficiales de la NOAA: ±0,5 °C."""
        if self.anomaly_c >= 0.5:
            return "El Niño"
        if self.anomaly_c <= -0.5:
            return "La Niña"
        return "Neutral"
