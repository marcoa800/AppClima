"""Hitos históricos y de disponibilidad de datos.

Este catálogo tiene un propósito analítico concreto, no decorativo: **anota la
línea temporal con los momentos en que cambió el mundo Y con los momentos en que
cambió nuestra capacidad de medirlo**.

La segunda parte es la que resuelve un problema real del proyecto. Casi todas
las series largas de este warehouse tienen saltos que parecen tendencias y son
artefactos:

  - Los "desastres por siglo" se disparan en el XX. No hubo más terremotos:
    hubo sismógrafos, prensa y censos.
  - Los ciclones "aumentan" desde 1842. No se formaron más: empezaron a verse
    desde el espacio en 1979.
  - El catálogo sísmico moderno arranca en 2016 con M≥2.5 y el histórico con
    M≥4.5, lo que ya nos costó un sesgo en las secuencias de réplicas.

Con la categoría `observacion`, esos saltos dejan de ser trampas invisibles y
pasan a ser líneas verticales dibujables en cualquier gráfica temporal.

Los eventos de guerra, economía y salud sirven para lo contrario: dar contexto
humano a las series. La caída de emisiones de 1929-1939 o de 2020 no se entiende
sin saber qué pasaba.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EventCategory = Literal[
    "guerra",
    "economia",
    "tecnologia",
    "salud",
    "clima",
    "observacion",
]


class HistoricalEvent(BaseModel):
    """Un hito con fecha, para anotar series temporales."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: EventCategory
    start_year: int
    end_year: int | None = Field(
        default=None, description="None si es puntual o sigue vigente"
    )
    description: str
    relevance: str = Field(
        description="Por qué importa PARA ESTE PROYECTO, no en general"
    )


EVENTS: list[HistoricalEvent] = [
    # ── Disponibilidad de datos ───────────────────────────────────────────
    # La categoría más útil: explica los saltos de las series largas.
    HistoricalEvent(
        id="ibtracs-inicio", name="Primer registro de IBTrACS",
        category="observacion", start_year=1842,
        description="Arranca el archivo global de trayectorias de ciclones.",
        relevance=(
            "Todo lo anterior a 1979 subestima gravemente: los ciclones que no "
            "tocaron tierra ni cruzaron una ruta marítima no se observaron."
        ),
    ),
    HistoricalEvent(
        id="era5-inicio", name="Inicio del reanálisis ERA5",
        category="observacion", start_year=1940,
        description="Copernicus reconstruye el clima horario global desde 1940.",
        relevance="Es el suelo temporal de toda la parte climática del proyecto.",
    ),
    HistoricalEvent(
        id="oni-inicio", name="Inicio del índice ONI",
        category="observacion", start_year=1950,
        description="La NOAA empieza la serie de El Niño en la región Niño 3.4.",
        relevance="Suelo temporal del único predictor estacional que tenemos.",
    ),
    HistoricalEvent(
        id="banco-mundial-inicio", name="Inicio de las series del Banco Mundial",
        category="observacion", start_year=1960,
        description="Estadísticas nacionales sistemáticas de población y economía.",
        relevance=(
            "Antes de esta fecha la población mundial es estimación demográfica "
            "con rango, no censo. Marca el cambio de régimen de dato."
        ),
    ),
    HistoricalEvent(
        id="satelite-meteorologico", name="Primer satélite meteorológico (TIROS-1)",
        category="observacion", start_year=1960,
        description="Primera imagen de la Tierra desde órbita con fines meteorológicos.",
        relevance="Empieza el camino hacia la cobertura ciclónica global de 1979.",
    ),
    HistoricalEvent(
        id="cobertura-satelital-global", name="Cobertura satelital global fiable",
        category="observacion", start_year=1979,
        description="Los satélites geoestacionarios cubren ya todas las cuencas.",
        relevance=(
            "**La línea más importante del catálogo.** Es la razón de que el "
            "análisis de ciclones arranque en 1980 y no en 1842. Cualquier "
            "tendencia que cruce esta fecha mezcla dos mundos distintos."
        ),
    ),
    HistoricalEvent(
        id="ingesta-usgs-appclima", name="Inicio de nuestra ingesta USGS",
        category="observacion", start_year=2016,
        description="Backfill del catálogo sísmico moderno con M≥4.5.",
        relevance=(
            "La ingesta diaria usa M≥2.5 y el histórico M≥4.5: dos magnitudes "
            "de completitud en el mismo catálogo. Ya causó un sesgo real en las "
            "secuencias de réplicas."
        ),
    ),

    # ── Guerras ──────────────────────────────────────────────────────────
    HistoricalEvent(
        id="primera-guerra-mundial", name="Primera Guerra Mundial",
        category="guerra", start_year=1914, end_year=1918,
        description="Unos 20 millones de muertos entre militares y civiles.",
        relevance=(
            "Se solapa con la gripe de 1918 y con la epidemia de tifus en Rusia. "
            "Separar mortalidad bélica de epidémica en ese periodo es imposible "
            "con nuestros datos, y conviene decirlo."
        ),
    ),
    HistoricalEvent(
        id="segunda-guerra-mundial", name="Segunda Guerra Mundial",
        category="guerra", start_year=1939, end_year=1945,
        description="Entre 70 y 85 millones de muertos, el conflicto más letal.",
        relevance=(
            "Supera en cifras absolutas a cualquier desastre natural del "
            "archivo. Queda fuera del catálogo de catástrofes porque no es un "
            "peligro natural, pero ignorarlo distorsiona la escala."
        ),
    ),
    HistoricalEvent(
        id="bombas-atomicas", name="Hiroshima y Nagasaki",
        category="guerra", start_year=1945,
        description="Primeras y únicas armas nucleares usadas en guerra.",
        relevance=(
            "Los ensayos nucleares posteriores aparecen en el catálogo sísmico "
            "de USGS como event_type distinto de 'earthquake'. Por eso silver "
            "los filtra."
        ),
    ),

    # ── Economía y tecnología ────────────────────────────────────────────
    HistoricalEvent(
        id="revolucion-industrial", name="Revolución Industrial",
        category="tecnologia", start_year=1760, end_year=1840,
        description="Mecanización, carbón y el inicio de las emisiones masivas.",
        relevance=(
            "El punto cero del cambio climático antropogénico. Los periodos "
            "base preindustriales que usa el IPCC se sitúan antes de esto."
        ),
    ),
    HistoricalEvent(
        id="gran-depresion", name="Gran Depresión",
        category="economia", start_year=1929, end_year=1939,
        description="Colapso económico global tras el crack del 29.",
        relevance="Primera caída significativa de emisiones de la era industrial.",
    ),
    HistoricalEvent(
        id="revolucion-verde", name="Revolución Verde",
        category="tecnologia", start_year=1950, end_year=1970,
        description="Variedades de alto rendimiento, fertilizantes y riego.",
        relevance=(
            "Explica buena parte de la aceleración demográfica visible en la "
            "serie del Banco Mundial: de 2.500 a 3.700 millones en 20 años."
        ),
    ),
    HistoricalEvent(
        id="crisis-petroleo-1973", name="Crisis del petróleo",
        category="economia", start_year=1973, end_year=1974,
        description="El embargo de la OPEP cuadruplica el precio del crudo.",
        relevance="Segunda gran inflexión en la curva de emisiones.",
    ),

    # ── Salud ────────────────────────────────────────────────────────────
    HistoricalEvent(
        id="penicilina", name="Descubrimiento de la penicilina",
        category="salud", start_year=1928,
        description="Fleming identifica el primer antibiótico de uso general.",
        relevance=(
            "Marca la frontera del catálogo de epidemias: casi todas las "
            "pandemias bacterianas masivas quedan antes de la producción "
            "industrial de antibióticos, en 1942."
        ),
    ),
    HistoricalEvent(
        id="erradicacion-viruela", name="Erradicación de la viruela",
        category="salud", start_year=1980,
        description="La OMS declara erradicada la primera enfermedad humana.",
        relevance=(
            "Cierra el registro de la enfermedad que causó dos entradas del "
            "catálogo de epidemias, una con hasta 56 millones de muertes."
        ),
    ),

    # ── Política climática ───────────────────────────────────────────────
    HistoricalEvent(
        id="curva-keeling", name="Inicio de la curva de Keeling",
        category="clima", start_year=1958,
        description="Primera medición continua de CO₂ atmosférico, en Mauna Loa.",
        relevance=(
            "La serie instrumental de CO₂ más importante que existe. Sería la "
            "siguiente fuente natural a integrar en este proyecto."
        ),
    ),
    HistoricalEvent(
        id="protocolo-montreal", name="Protocolo de Montreal",
        category="clima", start_year=1987,
        description="Acuerdo para eliminar los CFC que destruían la capa de ozono.",
        relevance=(
            "El caso de éxito: un problema atmosférico global detectado, "
            "regulado y revertido. Sirve de contraste con el CO₂."
        ),
    ),
    HistoricalEvent(
        id="primer-informe-ipcc", name="Primer informe del IPCC",
        category="clima", start_year=1990,
        description="Primera evaluación científica coordinada del cambio climático.",
        relevance="Origen del marco de anomalías y periodos base que usamos.",
    ),
    HistoricalEvent(
        id="acuerdo-paris", name="Acuerdo de París",
        category="clima", start_year=2015,
        description="Compromiso de limitar el calentamiento muy por debajo de 2 °C.",
        relevance=(
            "Cae dentro de nuestro periodo de evaluación (2021-2025), donde la "
            "anomalía medida sube de +0,14 a +0,86 °C."
        ),
    ),
]

BY_ID: dict[str, HistoricalEvent] = {e.id: e for e in EVENTS}
BY_CATEGORY: dict[str, list[HistoricalEvent]] = {}
for _event in EVENTS:
    BY_CATEGORY.setdefault(_event.category, []).append(_event)
