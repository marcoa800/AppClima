-- Cuánto cambia el catálogo sísmico después de publicarse.
--
-- Grano: (mag_band).
--
-- ══ Por qué existe ══════════════════════════════════════════════════════════
--
-- El pronóstico de réplicas es el modelo con más habilidad del proyecto:
-- +56,6% sobre su línea base. Ese número está medido contra el catálogo
-- **final**, con las magnitudes ya revisadas y los eventos pequeños ya
-- añadidos por los analistas.
--
-- En producción no se tiene eso. Veinticuatro horas después de un terremoto
-- principal, el catálogo tiene magnitudes preliminares y le faltan réplicas
-- que aún no se han procesado. El modelo real trabajaría con menos y peor
-- información que el modelo evaluado.
--
-- Así que **+56,6% es un techo, no una cifra de producción**. Esta tabla
-- mide la distancia entre ambos.
--
-- ══ Cómo se mide ════════════════════════════════════════════════════════════
--
-- Bronze es append-only y el cron diario deja una foto del catálogo cada vez
-- que se ejecuta. Comparando la primera versión de cada evento con la última
-- se obtienen las dos correcciones que importan:
--
--   · revisión de magnitud → cuánto se mueve el valor
--   · adición tardía       → cuántos eventos no estaban el primer día
--
-- La segunda pesa más para este modelo, porque cuenta réplicas: si al día
-- siguiente falta un tercio de ellas, la señal disponible es menor.
--
-- ══ Aviso sobre la serie ════════════════════════════════════════════════════
--
-- Esta tabla nace casi vacía: mide días de ingesta acumulados, y el proyecto
-- lleva pocos. `dias_de_historia` dice cuánto se puede creer. Por debajo de
-- unos 30 días, los números son indicativos y no deben publicarse como
-- corrección del modelo — solo como recordatorio de que la corrección existe.

CREATE OR REPLACE TABLE gold_catalog_revision AS
WITH versiones AS (
    SELECT
        event_id,
        time,
        arg_min(magnitude, _ingested_at) AS magnitud_primera,
        arg_max(magnitude, _ingested_at) AS magnitud_ultima,
        min(_ingested_at)                AS visto_primera_vez,
        max(_ingested_at)                AS visto_ultima_vez,
        count(DISTINCT visto_el)         AS dias_visto
    FROM silver_quake_revisions
    GROUP BY 1, 2
),

-- El instante desde el que hay vigilancia continua. Antes de esta fecha los
-- eventos entraron de golpe con el backfill histórico, así que su "primera
-- aparición" es la fecha del backfill y no dice nada sobre la latencia del
-- catálogo. Medir la adición tardía sobre ellos daba un 100% que no
-- significaba nada — y era plausible, que es lo peligroso.
inicio_vigilancia AS (
    SELECT min(_ingested_at) AS desde FROM silver_quake_revisions
),

etiquetado AS (
    SELECT
        v.*,
        CASE
            WHEN v.magnitud_ultima >= 6.0 THEN 'M6+'
            WHEN v.magnitud_ultima >= 5.0 THEN 'M5-6'
            WHEN v.magnitud_ultima >= 4.5 THEN 'M4.5-5'
            ELSE 'M<4.5'
        END AS mag_band,
        v.magnitud_ultima - v.magnitud_primera AS revision,
        v.time >= iv.desde AS bajo_vigilancia,
        -- Solo tiene sentido para los eventos ocurridos con la vigilancia ya
        -- en marcha. El umbral son 24 h, que es el horizonte del pronóstico
        -- de réplicas.
        v.time >= iv.desde
            AND date_diff('hour', v.time, v.visto_primera_vez) > 24 AS adicion_tardia
    FROM versiones v CROSS JOIN inicio_vigilancia iv
)

SELECT
    mag_band,
    count(*)                                            AS eventos,
    count(*) FILTER (WHERE dias_visto > 1)              AS vistos_varios_dias,
    count(*) FILTER (WHERE revision <> 0)               AS con_magnitud_revisada,
    round(avg(abs(revision)) FILTER (WHERE revision <> 0), 3) AS revision_media_abs,
    round(max(abs(revision)), 2)                        AS revision_maxima,
    count(*) FILTER (WHERE bajo_vigilancia)             AS eventos_bajo_vigilancia,
    count(*) FILTER (WHERE adicion_tardia)              AS adiciones_tardias,
    round(100.0 * count(*) FILTER (WHERE adicion_tardia)
          / nullif(count(*) FILTER (WHERE bajo_vigilancia), 0), 1)
        AS pct_adicion_tardia,

    -- Cuánta historia respalda cada cifra. Sin esto, un 0% de revisiones
    -- parecería una buena noticia cuando solo significa "aún no ha dado tiempo".
    (SELECT count(DISTINCT visto_el) FROM silver_quake_revisions)
        AS dias_de_historia,

    (SELECT count(DISTINCT visto_el) FROM silver_quake_revisions) >= 30
        AS historia_suficiente

FROM etiquetado
GROUP BY 1
ORDER BY CASE mag_band
    WHEN 'M6+' THEN 1 WHEN 'M5-6' THEN 2 WHEN 'M4.5-5' THEN 3 ELSE 4 END;
