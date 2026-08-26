-- Cascadas de desastres: cuando un peligro desencadena otro.
--
-- Grano: (trigger_type, trigger_id, tsunami_id).
--
-- Este es el modelo que justifica haber traído las tres bases de NOAA en lugar
-- de solo una. Los datasets están enlazados por id: un tsunami apunta al sismo
-- que lo generó, y una erupción apunta al tsunami que provocó. Con esos enlaces
-- se reconstruye la cadena causal completa.
--
-- Y ahí aparece el patrón que casi nadie modela: **en los desastres costeros,
-- el peligro primario rara vez es el que mata**. El terremoto de Sumatra de
-- 2004 derribó edificios; el tsunami que generó mató a 227.899 personas. Tratar
-- ambos como eventos independientes, que es lo que hace la mayoría de
-- catálogos, cuenta dos veces o pierde la relación por completo.
--
-- Limitación honesta: los enlaces son los que NOAA ha codificado. Una cascada
-- real sin id de enlace en la fuente no aparece aquí, y no hay forma de
-- distinguir "no hubo cascada" de "no se codificó".

CREATE OR REPLACE TABLE gold_disaster_cascades AS
WITH tsunamis AS (
    SELECT
        source_id AS tsunami_id,
        year, month, day, event_date, country, location_name,
        -- `deaths` y NO `deaths_best`. La distinción decide si esta tabla
        -- dice algo o miente.
        --
        -- `deaths_best` es coalesce(deaths_total, deaths), y está bien para lo
        -- que se creó: rankear desastres por impacto total, donde Krakatoa son
        -- 36.417 muertes y no 2.000. Pero en la ficha de un TSUNAMI, NOAA
        -- rellena `deaths_total` con las víctimas del evento entero —sismo
        -- incluido— así que usarlo aquí atribuye al tsunami lo que mató el
        -- terremoto.
        --
        -- El tsunami de Haití de 2010 mató a 7 personas y el terremoto a
        -- 316.000. Esta tabla decía que el tsunami mató a 316.000, y no era un
        -- caso aislado: 631 de 654 filas tenían tsunami_deaths idéntico a
        -- trigger_deaths_total, que es firma de error de columna y no una
        -- coincidencia.
        deaths AS tsunami_deaths,
        tsunami_max_water_height_m AS max_wave_m,
        tsunami_num_runups AS runups,
        caused_earthquake_id
    FROM silver_historical_disasters
    WHERE hazard_type = 'tsunami'
),
-- Sismos que generaron tsunami: el enlace vive en el lado del tsunami.
eq_triggers AS (
    SELECT
        'earthquake' AS trigger_type,
        e.source_id AS trigger_id,
        e.eq_magnitude AS trigger_magnitude,
        e.deaths AS trigger_deaths_direct,
        e.deaths_total AS trigger_deaths_total,
        t.*
    FROM tsunamis t
    JOIN silver_historical_disasters e
      ON e.hazard_type = 'earthquake'
     AND e.source_id = t.caused_earthquake_id
),
-- Volcanes que generaron tsunami: aquí el enlace vive en el lado del volcán.
volcano_triggers AS (
    SELECT
        'volcano' AS trigger_type,
        v.source_id AS trigger_id,
        v.volcano_vei::DOUBLE AS trigger_magnitude,
        v.deaths AS trigger_deaths_direct,
        v.deaths_total AS trigger_deaths_total,
        t.*
    FROM silver_historical_disasters v
    JOIN tsunamis t ON t.tsunami_id = v.caused_tsunami_id
    WHERE v.hazard_type = 'volcano'
)
SELECT
    trigger_type,
    trigger_id,
    trigger_magnitude,
    tsunami_id,
    year, month, day, event_date, country, location_name,
    trigger_deaths_direct,
    trigger_deaths_total,
    tsunami_deaths,
    max_wave_m,
    runups,

    -- Qué proporción de las muertes totales puso el peligro secundario.
    -- Cerca de 1 significa que el desencadenante fue casi inofensivo por sí
    -- mismo y lo devastador fue lo que vino después.
    --
    -- Se calcula restando las directas al total del desencadenante, y no
    -- dividiendo `tsunami_deaths` entre el total: las dos cifras vienen de
    -- fichas distintas de NOAA y no siempre suman: dividirlas daría cocientes
    -- mayores que uno sin que nada fallara.
    CASE
        WHEN trigger_deaths_total > 0
        THEN round(
            (trigger_deaths_total - coalesce(trigger_deaths_direct, 0))::DOUBLE
            / trigger_deaths_total, 4
        )
    END AS cascade_death_share
FROM (SELECT * FROM eq_triggers UNION ALL BY NAME SELECT * FROM volcano_triggers)
ORDER BY trigger_deaths_total DESC NULLS LAST;
