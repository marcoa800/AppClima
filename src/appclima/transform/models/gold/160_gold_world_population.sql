-- Población mundial año a año, uniendo estimación histórica y estadística.
--
-- Grano: year.
--
-- Dos regímenes de dato bien distintos, unidos en una sola serie continua:
--
--   año -10000 → 1950   estimación demográfica, interpolada entre años ancla
--   año  1960  → hoy    Banco Mundial, agregado 'WLD'
--
-- La interpolación lineal entre anclas es una aproximación con un límite que
-- hay que declarar: la población NO creció linealmente entre ellas. El tramo
-- 1300→1400 suaviza justo la caída de la peste negra, así que el valor
-- interpolado para 1350 no refleja la mortandad en curso. Para órdenes de
-- magnitud sirve; para el año exacto de una catástrofe, hay que mirar el ancla
-- más cercana y su rango.
--
-- `source_kind` marca de qué régimen viene cada fila. Sin esa columna, una
-- gráfica de población desde el año -10000 mezclaría conjeturas arqueológicas
-- con censos sin avisar.

CREATE OR REPLACE TABLE gold_world_population AS
WITH curated_anchors AS (
    SELECT year, population_low, population_high, confidence, source
    FROM (
        SELECT *, row_number() OVER (PARTITION BY year ORDER BY _ingested_at DESC) AS _rn
        FROM {{bronze_world_pop}}
    ) WHERE _rn = 1
),
-- El primer año del Banco Mundial entra como ANCLA, no solo como serie.
--
-- Sin esto quedaba un agujero de nueve años: las anclas curadas terminan en
-- 1950 y el Banco Mundial arranca en 1960, así que 1951-1959 no tenía dato
-- ninguno. Cualquier análisis que normalizara por población en esa década
-- —y ahí caen la gripe asiática de 1957 y buena parte de la posguerra— se
-- quedaba sin denominador y perdía las filas en silencio.
first_wb AS (
    SELECT min(year) AS year FROM silver_population WHERE country_id = 'WLD'
),
anchors AS (
    SELECT * FROM curated_anchors
    UNION ALL
    SELECT p.year, p.population AS population_low, p.population AS population_high,
           'alta' AS confidence, 'Banco Mundial' AS source
    FROM silver_population p
    JOIN first_wb f ON f.year = p.year
    WHERE p.country_id = 'WLD'
),
-- Todos los años entre el ancla más antigua y la primera del Banco Mundial.
years AS (
    SELECT unnest(generate_series(
        (SELECT min(year) FROM anchors),
        (SELECT year FROM first_wb) - 1,
        1
    )) AS year
),
-- Para cada año, el ancla inmediatamente anterior y la posterior.
bracketed AS (
    SELECT
        y.year,
        (SELECT max(a.year) FROM anchors a WHERE a.year <= y.year) AS lo_year,
        (SELECT min(a.year) FROM anchors a WHERE a.year >= y.year) AS hi_year
    FROM years y
),
interpolated AS (
    SELECT
        b.year,
        CASE
            WHEN b.lo_year = b.hi_year THEN lo.population_low
            ELSE lo.population_low
                 + (hi.population_low - lo.population_low)
                   * (b.year - b.lo_year)::DOUBLE / (b.hi_year - b.lo_year)
        END AS population_low,
        CASE
            WHEN b.lo_year = b.hi_year THEN lo.population_high
            ELSE lo.population_high
                 + (hi.population_high - lo.population_high)
                   * (b.year - b.lo_year)::DOUBLE / (b.hi_year - b.lo_year)
        END AS population_high,
        b.year IN (SELECT year FROM anchors) AS is_anchor,
        lo.confidence
    FROM bracketed b
    JOIN anchors lo ON lo.year = b.lo_year
    JOIN anchors hi ON hi.year = b.hi_year
)
SELECT
    year,
    population_low::BIGINT AS population_low,
    population_high::BIGINT AS population_high,
    -- round() explícito, no un casteo implícito. Aquí redondear SÍ es lo
    -- correcto (es un punto medio, no una división en cubos), pero escrito
    -- como '(a+b)/2)::BIGINT' era imposible saber si la intención era
    -- redondear o truncar. El test de higiene de SQL lo marcó justamente por
    -- esa ambigüedad, y tenía razón: el mismo patrón ya fue un bug real dos
    -- veces en este repositorio.
    round((population_low + population_high) / 2.0)::BIGINT AS population_mid,
    round(population_high::DOUBLE / nullif(population_low, 0), 3) AS uncertainty_ratio,
    is_anchor,
    confidence,
    'estimación histórica' AS source_kind
FROM interpolated

UNION ALL BY NAME

SELECT
    year,
    population AS population_low,
    population AS population_high,
    population AS population_mid,
    1.0 AS uncertainty_ratio,
    TRUE AS is_anchor,
    'alta' AS confidence,
    'Banco Mundial' AS source_kind
FROM silver_population
WHERE country_id = 'WLD'

ORDER BY year;
