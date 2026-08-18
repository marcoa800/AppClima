"""Población mundial antes de las estadísticas modernas.

El Banco Mundial arranca en 1960. Para poner en contexto la peste negra (1346) o
el terremoto de Shaanxi (1556) hace falta saber cuánta gente había entonces, y
ahí no hay censos: hay demografía histórica.

Mismo criterio que el catálogo de epidemias — **rango, nunca cifra única**. Las
estimaciones de la población mundial en el año 1 van de 170 a 400 millones según
el autor, un factor de 2,4. Publicar "300 millones" como si fuera un dato sería
inventarse una precisión que no existe.

Estos años ancla se interpolan linealmente en `gold_world_population`, y eso
tiene un límite honesto que conviene tener presente: la población no creció de
forma lineal entre ellos. La interpolación entre 1300 y 1400, por ejemplo,
suaviza justo la caída brutal de la peste negra. Para cualquier año concreto el
valor interpolado es orientativo; lo que sí es sólido es el orden de magnitud.

Fuentes: síntesis de McEvedy & Jones (1978), base HYDE 3.2 y las estimaciones
retrospectivas de Naciones Unidas.
"""

from __future__ import annotations

from appclima.schemas.population import WorldPopulationEstimate

M = 1_000_000

WORLD_POPULATION: list[WorldPopulationEstimate] = [
    WorldPopulationEstimate(
        year=-10000, population_low=1 * M, population_high=10 * M,
        confidence="baja", source="HYDE 3.2 / síntesis arqueológica",
        note="Final del Paleolítico. El rango abarca un factor de diez.",
    ),
    WorldPopulationEstimate(
        year=-5000, population_low=5 * M, population_high=20 * M,
        confidence="baja", source="HYDE 3.2",
    ),
    WorldPopulationEstimate(
        year=-3000, population_low=14 * M, population_high=27 * M,
        confidence="baja", source="McEvedy & Jones / HYDE",
    ),
    WorldPopulationEstimate(
        year=-1000, population_low=50 * M, population_high=100 * M,
        confidence="baja", source="McEvedy & Jones / HYDE",
    ),
    WorldPopulationEstimate(
        year=-500, population_low=100 * M, population_high=150 * M,
        confidence="baja", source="McEvedy & Jones",
        note="Contemporáneo de la plaga de Atenas.",
    ),
    WorldPopulationEstimate(
        year=1, population_low=170 * M, population_high=400 * M,
        confidence="baja", source="Rango entre autores; factor 2,4",
        note="El desacuerdo más grande de toda la serie.",
    ),
    WorldPopulationEstimate(
        year=500, population_low=190 * M, population_high=260 * M,
        confidence="baja", source="McEvedy & Jones",
        note="Vísperas de la plaga de Justiniano.",
    ),
    WorldPopulationEstimate(
        year=1000, population_low=250 * M, population_high=350 * M,
        confidence="baja", source="McEvedy & Jones / HYDE",
    ),
    WorldPopulationEstimate(
        year=1300, population_low=360 * M, population_high=432 * M,
        confidence="media", source="McEvedy & Jones / Biraben",
        note="Máximo medieval, justo antes de la peste negra.",
    ),
    WorldPopulationEstimate(
        year=1400, population_low=350 * M, population_high=374 * M,
        confidence="media", source="McEvedy & Jones / Biraben",
        note=(
            "La única caída de la serie. Medio siglo después de la peste negra "
            "la humanidad seguía por debajo de su nivel de 1300."
        ),
    ),
    WorldPopulationEstimate(
        year=1500, population_low=425 * M, population_high=540 * M,
        confidence="media", source="McEvedy & Jones / Biraben",
    ),
    WorldPopulationEstimate(
        year=1600, population_low=545 * M, population_high=579 * M,
        confidence="media", source="McEvedy & Jones / Biraben",
    ),
    WorldPopulationEstimate(
        year=1700, population_low=600 * M, population_high=679 * M,
        confidence="media", source="McEvedy & Jones / Biraben",
    ),
    WorldPopulationEstimate(
        year=1800, population_low=890 * M, population_high=980 * M,
        confidence="media", source="Estimaciones demográficas históricas",
    ),
    WorldPopulationEstimate(
        year=1850, population_low=1_200 * M, population_high=1_300 * M,
        confidence="media", source="Estimaciones demográficas históricas",
    ),
    WorldPopulationEstimate(
        year=1900, population_low=1_550 * M, population_high=1_760 * M,
        confidence="alta", source="Censos nacionales y reconstrucciones de la ONU",
    ),
    WorldPopulationEstimate(
        year=1950, population_low=2_499 * M, population_high=2_536 * M,
        confidence="alta", source="ONU, World Population Prospects",
        note="Desde aquí el dato es estadística, no estimación.",
    ),
]

BY_YEAR: dict[int, WorldPopulationEstimate] = {
    e.year: e for e in WORLD_POPULATION
}
