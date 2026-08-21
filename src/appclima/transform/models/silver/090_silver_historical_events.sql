-- Hitos históricos y de disponibilidad de datos.
--
-- Grano: id.
--
-- La categoría `observacion` es la que tiene uso analítico directo: cada uno de
-- esos años es una línea vertical que debería aparecer en cualquier gráfica
-- temporal larga de este warehouse, porque marca dónde la serie cambia de
-- régimen sin que el fenómeno subyacente cambie.

CREATE OR REPLACE TABLE silver_historical_events AS
WITH ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (PARTITION BY id ORDER BY _ingested_at DESC) AS _rn
    FROM {{bronze_events}}
)
SELECT
    * EXCLUDE (_rn),
    coalesce(end_year, start_year) - start_year AS duration_years,
    end_year IS NULL AS is_point_event
FROM ranked
WHERE _rn = 1;
