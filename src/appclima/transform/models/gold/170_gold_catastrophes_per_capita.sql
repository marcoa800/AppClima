-- Catástrofes normalizadas por la población mundial de su época.
--
-- Grano: una fila por evento (epidemia o desastre natural).
--
-- **Este modelo cambia las conclusiones del proyecto, no solo las adorna.**
--
-- En cifras absolutas, el terremoto de Shaanxi de 1556 (830.000 muertes) parece
-- 3,4 veces peor que el de Tangshan de 1976 (242.769). Pero en 1556 la humanidad
-- eran ~480 millones de personas y en 1976 ~4.100 millones. En proporción,
-- Shaanxi mató a 1 de cada 578 personas vivas y Tangshan a 1 de cada 16.900:
-- Shaanxi fue casi treinta veces más letal.
--
-- Lo mismo, y más extremo, con las pandemias: la peste negra se llevó en torno
-- a una cuarta parte de la especie humana. Ninguna catástrofe posterior se
-- acerca ni de lejos, por muchos millones absolutos que acumule.
--
-- Sin denominador, cualquier serie histórica de víctimas mide sobre todo cuánta
-- gente había disponible para morir. Con él, se puede comparar de verdad.
--
-- Limitación declarada: `deaths_per_million` usa población MUNDIAL, no la de la
-- región afectada. Es la métrica correcta para responder "¿qué fracción de la
-- humanidad se llevó?", que es la pregunta comparable entre épocas. NO responde
-- "¿qué fracción de los afectados murió?" — para eso haría falta población
-- regional histórica, que para el siglo XVI no existe con esa granularidad.

CREATE OR REPLACE TABLE gold_catastrophes_per_capita AS
WITH events AS (
    SELECT
        family,
        event_key,
        event_name,
        subtype,
        year,
        duration_years,
        location,
        deaths_low,
        deaths_high,
        deaths_representative,
        estimate_kind,
        estimate_confidence
    FROM gold_epidemics_vs_disasters
    WHERE deaths_representative IS NOT NULL
),
joined AS (
    SELECT
        e.*,
        p.population_mid AS world_population,
        p.population_low AS world_population_low,
        p.population_high AS world_population_high,
        p.source_kind AS population_source,
        p.uncertainty_ratio AS population_uncertainty
    FROM events e
    LEFT JOIN gold_world_population p ON p.year = e.year
)
SELECT
    *,
    round(1e6 * deaths_representative / nullif(world_population, 0), 2)
        AS deaths_per_million,

    -- "1 de cada N personas vivas en el mundo". Es la forma más intuitiva de
    -- leer esto: mucho más legible que un 0,00024.
    round(world_population / nullif(deaths_representative, 0))::BIGINT
        AS one_in_every,

    round(100.0 * deaths_representative / nullif(world_population, 0), 4)
        AS pct_of_humanity,

    -- Rango de la proporción, combinando las DOS incertidumbres: la del número
    -- de muertes y la de la población de la época. Para eventos antiguos ambas
    -- son grandes, y multiplicarlas es lo honesto — el peor caso usa el máximo
    -- de muertes sobre la población mínima.
    round(1e6 * deaths_low / nullif(world_population_high, 0), 2)
        AS deaths_per_million_low,
    round(1e6 * deaths_high / nullif(world_population_low, 0), 2)
        AS deaths_per_million_high
FROM joined
WHERE world_population IS NOT NULL
ORDER BY deaths_per_million DESC;
