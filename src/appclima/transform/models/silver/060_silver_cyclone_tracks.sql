-- Puntos de trayectoria de ciclones tropicales, limpios y deduplicados.
--
-- Grano: (sid, time).
--
-- Dos filtros que cambian por completo los recuentos:
--
-- 1. `track_type = 'main'`. Un mismo sistema puede tener trayectorias 'spur',
--    que son fragmentos alternativos aportados por otro centro de análisis.
--    Contarlas como tormentas propias infla el número de ciclones por
--    temporada, y encima de forma desigual entre cuencas, porque no todos los
--    centros publican spurs.
--
-- 2. `is_synoptic`, la marca de hora sinóptica (00, 06, 12, 18 UTC). No filtra
--    filas pero es imprescindible aguas arriba: algunas cuencas reportan cada 3
--    horas y otras cada 6. El índice ACE está DEFINIDO sobre observaciones de 6
--    horas, así que calcularlo sobre todos los puntos duplicaría la energía de
--    las cuencas que reportan más a menudo — y haría que el Atlántico y el
--    Pacífico occidental dejaran de ser comparables.

CREATE OR REPLACE TABLE silver_cyclone_tracks AS
WITH ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (PARTITION BY sid, time ORDER BY _ingested_at DESC) AS _rn
    FROM {{bronze_cyclones}}
)
SELECT
    * EXCLUDE (_rn),

    -- Solo las horas sinópticas entran en el cálculo de ACE.
    hour(time) IN (0, 6, 12, 18) AND minute(time) = 0 AS is_synoptic,

    -- Viento de referencia. USA cubre todas las cuencas de forma homogénea, así
    -- que es la única base válida para comparar entre océanos; WMO entra solo
    -- como respaldo cuando falta.
    coalesce(usa_wind_kt, wmo_wind_kt) AS wind_kt,
    coalesce(usa_pressure_mb, wmo_pressure_mb) AS pressure_mb,

    -- Umbral de tormenta tropical: 34 nudos.
    coalesce(usa_wind_kt, wmo_wind_kt) >= 34 AS is_tropical_storm,
    -- Umbral de huracán: 64 nudos.
    coalesce(usa_wind_kt, wmo_wind_kt) >= 64 AS is_hurricane
FROM ranked
WHERE _rn = 1
  AND track_type = 'main';
