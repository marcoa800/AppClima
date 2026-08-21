-- Catálogo sísmico limpio y deduplicado.
--
-- Grano: event_id.
--
-- Dos filtros que cambian la validez de cualquier análisis posterior:
--
-- 1. `event_type = 'earthquake'`. El catálogo de USGS incluye explosiones de
--    cantera, deslizamientos, actividad volcánica y ensayos nucleares. Sin este
--    filtro, un estudio de sismicidad natural queda contaminado por actividad
--    humana — y las voladuras de cantera son numerosas y muy regulares en
--    horario laboral, lo que introduciría un patrón horario totalmente falso.
--
-- 2. `status <> 'deleted'`. USGS retira eventos que resultaron ser artefactos.
--    Bronze conserva la versión que vimos en su momento; silver no debe.
--
-- La deduplicación ordena por `updated` antes que por `_ingested_at`: USGS
-- revisa magnitudes durante días, y lo que queremos es la última revisión del
-- evento, no simplemente la última vez que nosotros lo descargamos.

CREATE OR REPLACE TABLE silver_earthquakes AS
WITH ranked AS (
    SELECT
        event_id,
        time,
        updated,
        magnitude,
        magnitude_type,
        lat,
        lon,
        depth_km,
        place,
        event_type,
        tsunami,
        significance,
        alert,
        status,
        felt,
        cdi,
        mmi,
        network,
        url,
        _ingested_at,
        row_number() OVER (
            PARTITION BY event_id
            ORDER BY updated DESC NULLS LAST, _ingested_at DESC
        ) AS _rn
    FROM {{bronze_quakes}}
    WHERE event_type = 'earthquake'
      AND (status IS NULL OR status <> 'deleted')
      AND magnitude IS NOT NULL
)
SELECT
    * EXCLUDE (_rn),
    -- Clasificación estándar por profundidad. La profundidad condiciona el daño
    -- en superficie tanto como la magnitud: un M6 a 10 km es mucho más
    -- destructivo que un M6 a 300 km.
    CASE
        WHEN depth_km < 70 THEN 'superficial'
        WHEN depth_km < 300 THEN 'intermedio'
        ELSE 'profundo'
    END AS depth_class
FROM ranked
WHERE _rn = 1;
