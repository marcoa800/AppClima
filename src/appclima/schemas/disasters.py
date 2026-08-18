"""Esquemas de desastres naturales históricos.

Tres problemas de modelado que este dominio impone y que no aparecen en el
clima ni en el catálogo sísmico moderno:

1. **Fechas incompletas y anteriores a Cristo.** El evento más antiguo es del
   año -4360. Muchos registros tienen año pero no mes ni día. Por eso el año se
   guarda como entero con signo y la fecha completa es opcional: forzar un DATE
   obligaría a inventar un 1 de enero que no está en la fuente.

2. **Muertes directas frente a muertes totales.** Krakatoa 1883 registra 2.000
   muertes por la erupción y 36.417 en total, porque el tsunami que provocó mató
   al resto. Elegir la columna equivocada cambia la cifra por un factor de 18.
   Se guardan las dos, siempre.

3. **Cifras exactas frente a órdenes de magnitud.** Para eventos antiguos a
   menudo solo se sabe la escala, no el número. NOAA usa un ordinal 0-4 que
   existe incluso cuando la cifra exacta es nula. Tratar ese ordinal como si
   fuera un recuento sería un error grave, así que va en un campo aparte.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Escala ordinal de NOAA, usada cuando no hay cifra exacta.
#   0 = ninguno · 1 = pocos (~1-50) · 2 = algunos (~51-100)
#   3 = muchos (~101-1000) · 4 = muchísimos (>1000)
AMOUNT_ORDER_LABELS: dict[int, str] = {
    0: "ninguno",
    1: "pocos (~1-50)",
    2: "algunos (~51-100)",
    3: "muchos (~101-1000)",
    4: "muchísimos (>1000)",
}

HazardType = Literal["earthquake", "tsunami", "volcano"]


class HistoricalDisaster(BaseModel):
    """Un evento del archivo de peligros naturales de NOAA NCEI."""

    model_config = ConfigDict(extra="forbid")

    source_id: int = Field(description="id de NOAA, único dentro de su dataset")
    hazard_type: HazardType = Field(
        description="Necesario en la clave: los ids se repiten entre datasets"
    )

    # Fecha desmontada. El año puede ser negativo (a.C.) y mes/día faltar.
    year: int
    month: int | None = None
    day: int | None = None
    hour: int | None = None
    minute: int | None = None

    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    location_name: str | None = None
    region_code: int | None = None

    # Impacto DIRECTO del evento.
    deaths: int | None = None
    deaths_order: int | None = Field(default=None, ge=0, le=4)
    injuries: int | None = None
    injuries_order: int | None = Field(default=None, ge=0, le=4)
    damage_musd: float | None = Field(
        default=None, description="Daños en millones de USD del año del evento"
    )
    damage_order: int | None = Field(default=None, ge=0, le=4)
    houses_destroyed: int | None = None

    # Impacto TOTAL, incluyendo los peligros secundarios que desencadenó.
    deaths_total: int | None = None
    deaths_order_total: int | None = Field(default=None, ge=0, le=4)
    injuries_total: int | None = None
    damage_musd_total: float | None = None

    # Intensidad, con el campo que corresponda a cada tipo de peligro.
    eq_magnitude: float | None = None
    eq_depth_km: float | None = None
    eq_intensity: float | None = Field(
        default=None, description="Intensidad Mercalli modificada, I-XII"
    )
    tsunami_max_water_height_m: float | None = None
    tsunami_num_runups: int | None = None
    volcano_vei: int | None = Field(
        default=None, ge=0, le=8, description="Índice de explosividad volcánica"
    )
    volcano_name: str | None = None
    volcano_elevation_m: float | None = None
    volcano_morphology: str | None = None

    # Enlaces causales entre datasets. Son la materia prima del modelo de
    # cascadas: un sismo genera un tsunami, un volcán genera un tsunami.
    caused_earthquake_id: int | None = None
    caused_tsunami_id: int | None = None

    published: bool = Field(
        default=True,
        description="Marca editorial de NOAA. False no significa dudoso.",
    )


class HistoricalEpidemic(BaseModel):
    """Una epidemia o pandemia del catálogo curado.

    A diferencia del resto del proyecto, esto NO viene de una API: no existe
    ninguna abierta con datos históricos de pandemias. Es un catálogo curado a
    mano, y por eso cada registro lleva rango de incertidumbre y fuente.

    El rango no es un adorno. Las estimaciones de muertes de la peste negra van
    de 75 a 200 millones, y las de la gripe de 1918 de 17 a 100 millones.
    Publicar un solo número como si fuera un hecho sería deshonesto; el ancho
    del rango ES el dato.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Slug estable")
    name: str
    pathogen: str | None = Field(default=None, description="Agente causante")
    disease: str | None = None

    start_year: int
    end_year: int | None = Field(default=None, description="None = todavía en curso")

    # Siempre un rango. Un punto medio sin rango miente sobre la certeza.
    deaths_low: int | None = None
    deaths_high: int | None = None

    regions: str = Field(description="Zonas afectadas, texto libre")

    estimate_confidence: Literal["alta", "media", "baja"] = Field(
        description=(
            "alta = registro moderno fiable · media = estimación histórica "
            "consensuada · baja = muy disputada entre historiadores"
        )
    )
    source: str = Field(description="De dónde sale la estimación")
    note: str | None = None
