-- Historia de versiones del catálogo sísmico.
--
-- Grano: (event_id, _ingested_at).
--
-- `silver_earthquakes` deduplica a la versión más reciente, que es lo correcto
-- para analizar sismos — pero borra justo la información que hace falta para
-- responder a otra pregunta: **¿qué sabíamos el día después?**
--
-- El USGS revisa magnitudes durante días o semanas y añade eventos pequeños
-- conforme los analistas los procesan. Un modelo evaluado contra el catálogo
-- final se está evaluando con información que en producción no habría tenido.
--
-- Esta tabla conserva todas las versiones, sin deduplicar, porque bronze es
-- append-only y cada ejecución del cron deja una foto del catálogo tal como
-- estaba ese día. La serie es corta al principio y se llena sola.

CREATE OR REPLACE TABLE silver_quake_revisions AS
SELECT
    event_id,
    time,
    magnitude,
    magnitude_type,
    depth_km,
    _ingested_at,
    _ingested_at::DATE AS visto_el
FROM {{bronze_quakes}}
WHERE magnitude IS NOT NULL;
