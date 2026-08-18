-- Epidemias y desastres naturales en una sola escala comparable.
--
-- Grano: una fila por evento, de cualquiera de las dos familias.
--
-- La comparación produce el resultado más contundente de todo el proyecto: **la
-- peor pandemia mató entre 300 y 800 veces más que el peor desastre natural
-- registrado.** El terremoto de Tangshan de 1976, el más mortal con cifra
-- fiable, se lleva 242.769 vidas; la peste negra, entre 75 y 200 millones.
--
-- Para que la comparación sea legítima hay que ser explícito en tres cosas, y
-- por eso las tres van como columnas y no como nota al pie:
--
--   `estimate_kind` — un recuento no es una estimación. Tangshan tiene censo;
--   la peste negra tiene historiografía. Mezclarlos sin marcarlo sería
--   comparar peras con conjeturas.
--
--   `duration_years` — un terremoto dura segundos y una pandemia años o
--   décadas. Poner ambos en el mismo eje temporal sin decirlo es engañoso.
--
--   `deaths_low`/`deaths_high` — los desastres traen un número; las epidemias,
--   un rango que puede abarcar un factor de siete.

CREATE OR REPLACE TABLE gold_epidemics_vs_disasters AS
SELECT
    'epidemic' AS family,
    id AS event_key,
    name AS event_name,
    disease AS subtype,
    start_year AS year,
    end_year,
    duration_years,
    regions AS location,
    deaths_low,
    deaths_high,
    deaths_mid AS deaths_representative,
    deaths_uncertainty_ratio,
    estimate_confidence,
    'estimación' AS estimate_kind,
    source AS source_note
FROM silver_epidemics
WHERE deaths_low IS NOT NULL

UNION ALL BY NAME

SELECT
    'natural_disaster' AS family,
    hazard_type || ':' || source_id AS event_key,
    coalesce(volcano_name, location_name, country) AS event_name,
    hazard_type AS subtype,
    year,
    year AS end_year,
    -- Un desastre natural es puntual. Se marca 1 año para que el campo sea
    -- comparable, no porque durase un año.
    1 AS duration_years,
    coalesce(location_name, country) AS location,
    deaths AS deaths_low,
    deaths AS deaths_high,
    deaths AS deaths_representative,
    1.0 AS deaths_uncertainty_ratio,
    'alta' AS estimate_confidence,
    'recuento' AS estimate_kind,
    'NOAA NCEI' AS source_note
FROM gold_disasters_ranked
WHERE deaths >= 10000

ORDER BY deaths_representative DESC;
