-- Catálogo curado de epidemias y pandemias.
--
-- Grano: id.
--
-- A diferencia del resto de silver, esta fuente no viene de una API sino de
-- src/appclima/epidemics.py. No existe base de datos abierta con pandemias
-- históricas: la peste negra vive en historiografía, no en un endpoint.
--
-- Aquí se calculan dos cosas que la fuente no trae y que son el núcleo de cómo
-- hay que leer estos datos:
--
--   `deaths_uncertainty_ratio` — cuántas veces mayor es la estimación alta que
--   la baja. Para la peste negra vale 2,7; para la plaga de Justiniano, 6,7.
--   Un ratio alto significa "nadie lo sabe realmente", y eso debe verse.
--
--   `deaths_mid` — punto medio, expuesto SOLO para poder ordenar y graficar.
--   Nunca debe presentarse como una cifra: es un artefacto de conveniencia,
--   y por eso viaja siempre junto a low, high y el ratio.

CREATE OR REPLACE VIEW silver_epidemics AS
WITH ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (PARTITION BY id ORDER BY _ingested_at DESC) AS _rn
    FROM {{bronze_epidemics}}
)
SELECT
    * EXCLUDE (_rn),

    end_year IS NULL AS ongoing,
    coalesce(end_year, year(current_date)) - start_year + 1 AS duration_years,

    (deaths_low + deaths_high) / 2 AS deaths_mid,

    CASE
        WHEN deaths_low > 0 THEN round(deaths_high::DOUBLE / deaths_low, 2)
    END AS deaths_uncertainty_ratio,

    CASE
        WHEN start_year > 0 THEN ((start_year - 1) // 100) + 1
        ELSE -(((-start_year - 1) // 100) + 1)
    END AS century
FROM ranked
WHERE _rn = 1;
