-- Población por país y año (Banco Mundial).
--
-- Grano: (country_id, year).
--
-- El filtro que evita el error más caro de este dataset: **países y agregados
-- vienen mezclados**. "Mundo", "América Latina y el Caribe" e "Ingreso alto"
-- llegan como filas hermanas de España o Japón. Un `SELECT sum(population)`
-- sin filtrar cuenta a cada persona del planeta tres o cuatro veces.
--
-- Aquí NO se descartan los agregados: se marcan. El agregado 'WLD' es
-- exactamente la población mundial que necesitamos como denominador, así que
-- tirarlo sería absurdo. Lo que hay que hacer es no mezclarlos nunca en la
-- misma suma, y para eso está `is_aggregate`.

CREATE OR REPLACE TABLE silver_population AS
WITH ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (
            PARTITION BY country_id, year ORDER BY _ingested_at DESC
        ) AS _rn
    FROM {{bronze_population}}
)
SELECT * EXCLUDE (_rn)
FROM ranked
WHERE _rn = 1
  AND population IS NOT NULL;
