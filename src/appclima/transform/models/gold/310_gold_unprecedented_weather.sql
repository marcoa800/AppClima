-- Días sin precedente: cuántos y cuántos cabría esperar por puro azar.
--
-- Grano: (location_id).
--
-- ══ La pregunta ═════════════════════════════════════════════════════════════
--
-- No "¿hace más calor?" —eso ya lo dice la media— sino algo más concreto y más
-- útil para quien planifica: **¿cuántos días viven estas ciudades para los que
-- no tienen ningún referente en su propia historia reciente?**
--
-- Un día sin precedente es el que supera TODO lo registrado en su misma época
-- del año durante los trece años anteriores. Importa porque las
-- infraestructuras, los protocolos y las intuiciones se calibran con lo vivido:
-- un valor nunca visto es, por definición, uno para el que nadie se preparó.
--
-- ══ Por qué hace falta una expectativa, y no basta con contar ═══════════════
--
-- Contar récords y decir "van en aumento" es una trampa estadística clásica,
-- porque **los récords son cada vez más raros aunque el clima no cambie**. Con
-- n valores previos, la probabilidad de que el siguiente los supere todos es
-- 1/(n+1): frecuente al principio, rarísima después. Cualquier serie larga
-- produce esa desaceleración sin que nada esté pasando.
--
-- Así que la cifra publicada no es el recuento sino la **razón entre lo
-- observado y lo esperado bajo clima estacionario**. Un 1,0 significa "lo
-- normal". Un 3,0 significa el triple de días sin referente de los que
-- debería haber.
--
-- La ventana de referencia es fija (2006-2018) y la de evaluación también
-- (2019-2025), así que cada día evaluado se compara contra el MISMO número de
-- valores previos —15 días de calendario × 13 años = 195— y la esperanza es
-- limpia: días_evaluados / 196.
--
-- ══ El control que distingue tendencia de ruido ═════════════════════════════
--
-- Un clima simplemente más variable produciría más récords de calor **y más de
-- frío**. Uno que se calienta produce más de calor y MENOS de frío.
--
-- Por eso se cuentan las dos colas. La asimetría es la prueba, y es una prueba
-- interna: no depende de ninguna serie externa, ningún modelo, ninguna
-- atribución. Solo de que el frío y el calor no se comporten igual.
--
-- ══ Límites ════════════════════════════════════════════════════════════════
--
-- Los días consecutivos no son independientes: una ola de calor produce varios
-- días sin precedente seguidos, así que el RECUENTO es correcto en esperanza
-- pero su varianza es mayor de lo que sugiere una binomial. Eso significa que
-- la razón es fiable y que un intervalo de confianza ingenuo sería demasiado
-- estrecho. No se publica ninguno: haría falta un bootstrap por bloques.

CREATE OR REPLACE TABLE gold_unprecedented_weather AS
WITH base AS (
    SELECT
        location_id,
        local_date,
        dayofyear(local_date) AS doy,
        year(local_date)      AS yr,
        temp_max,
        temp_min,
        precip_sum
    FROM gold_weather_daily
    WHERE kind = 'observed'
      -- Un solo reanálisis, sin excepciones. Comparar un récord medido con
      -- ERA5 contra una referencia medida con el IFS sería medir el cambio de
      -- modelo, que en Tacna vale 2,44 °C — más que cualquier récord real.
      AND model = 'era5_seamless'
      AND NOT modelo_mixto
      AND temp_max IS NOT NULL
      AND temp_min IS NOT NULL
),

referencia AS (SELECT * FROM base WHERE yr BETWEEN 2006 AND 2018),
evaluacion AS (SELECT * FROM base WHERE yr BETWEEN 2019 AND 2025),

-- El récord de cada día en su propia ventana de calendario. ±7 días para que
-- la referencia sea de la misma estación sin diluirla con el resto del año.
limites AS (
    SELECT
        e.location_id,
        e.local_date,
        e.temp_max,
        e.temp_min,
        e.precip_sum,
        max(r.temp_max)   AS ref_temp_max,
        min(r.temp_min)   AS ref_temp_min,
        max(r.precip_sum) AS ref_precip,
        count(*)          AS n_ref
    FROM evaluacion e
    JOIN referencia r
      ON r.location_id = e.location_id
     AND doy_distance(r.doy, e.doy) <= 7
    GROUP BY 1, 2, 3, 4, 5
),

conteo AS (
    SELECT
        location_id,
        count(*)                                                  AS dias_evaluados,
        round(avg(n_ref))                                         AS n_referencia,
        sum(CASE WHEN temp_max > ref_temp_max THEN 1 ELSE 0 END)  AS dias_calor,
        sum(CASE WHEN temp_min < ref_temp_min THEN 1 ELSE 0 END)  AS dias_frio,
        sum(CASE WHEN precip_sum > ref_precip AND ref_precip > 0
                 THEN 1 ELSE 0 END)                               AS dias_lluvia,
        max(CASE WHEN temp_max > ref_temp_max
                 THEN temp_max - ref_temp_max END)                AS mayor_exceso_c
    FROM limites
    GROUP BY 1
)

SELECT
    c.location_id,
    l.name        AS location_name,
    l.country,
    l.koppen,
    abs(l.lat)    AS abs_lat,

    c.dias_evaluados,
    c.n_referencia::INTEGER AS n_referencia,

    -- Esperanza bajo clima estacionario: con n valores previos, la
    -- probabilidad de que el siguiente los supere todos es 1/(n+1).
    round(c.dias_evaluados / (c.n_referencia + 1), 1) AS dias_esperados,

    c.dias_calor,
    c.dias_frio,
    c.dias_lluvia,

    round(c.dias_calor  / nullif(c.dias_evaluados / (c.n_referencia + 1), 0), 2)
        AS razon_calor,
    round(c.dias_frio   / nullif(c.dias_evaluados / (c.n_referencia + 1), 0), 2)
        AS razon_frio,
    round(c.dias_lluvia / nullif(c.dias_evaluados / (c.n_referencia + 1), 0), 2)
        AS razon_lluvia,

    -- LA CIFRA. Cuántas veces más días sin precedente de calor que de frío.
    -- Bajo clima estacionario vale 1, suba o baje la variabilidad.
    round(c.dias_calor::DOUBLE / nullif(c.dias_frio, 0), 2) AS asimetria_calor_frio,

    round(c.mayor_exceso_c, 2) AS mayor_exceso_c,

    -- Cuántos días al año vive esta ciudad sin ningún referente propio.
    round(c.dias_calor / (c.dias_evaluados / 365.25), 1) AS dias_calor_por_anio,

    CASE
        WHEN c.dias_frio = 0 AND c.dias_calor > 0 THEN 'solo calor'
        WHEN c.dias_calor > 3 * c.dias_frio       THEN 'calor domina'
        WHEN c.dias_frio > 3 * c.dias_calor       THEN 'frío domina'
        ELSE 'simétrico'
    END AS patron

FROM conteo c
JOIN dim_locations l ON l.id = c.location_id
ORDER BY razon_calor DESC, c.location_id;
