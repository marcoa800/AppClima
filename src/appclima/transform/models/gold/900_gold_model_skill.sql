-- Habilidad de cada modelo, evaluada con walk-forward y varios cortes.
--
-- Grano: (model_id, scope, cut_year).
--
-- **Esta tabla es la que decide qué se enseña en la interfaz.** Existe por el
-- fallo de raíz que la verificación adversarial encontró en las tres hipótesis
-- que parecían tener señal: todas se midieron en UN SOLO corte temporal, y
-- todas habían elegido —sin mala fe— el corte donde mejor se veían.
--
-- El caso más claro fue el riesgo climatológico: +16,9% con el corte
-- 2018/2019, pero −0,9% con el corte 2012/2013. La diferencia no está en el
-- modelo, está en lo caliente que salió el periodo de prueba.
--
-- Por eso aquí se evalúa sobre VARIOS cortes y se guarda la **mediana**, no el
-- máximo. Un modelo que solo funciona en un corte concreto no funciona.
--
-- `should_display` es el criterio de producto, y vive en los datos a propósito:
-- si viviera en un `if` del frontend, la tentación de enseñar el número bonito
-- acabaría ganando.
--
-- Numerado 900 para que se ejecute el último. Antes era el 230 y no podía
-- juzgar a los modelos 280-300, que corren después: una tabla que decide qué
-- se publica no puede ir a mitad de la lista.

CREATE OR REPLACE TABLE gold_model_skill AS

-- ══ MODELO 1: pronóstico de réplicas ═══════════════════════════════════════
WITH cuts_quake AS (SELECT unnest([2019, 2020, 2021, 2022, 2023]) AS cut_year),
quake_fit AS (
    -- alpha = razón agregada, más robusta que la media de razones cuando la
    -- distribución tiene cola pesada, que es exactamente el caso.
    SELECT
        c.cut_year,
        sum(f.y_days_2_8)::DOUBLE / nullif(sum(f.n1), 0) AS alpha
    FROM cuts_quake c
    JOIN gold_aftershock_forecast f
      ON f.year <= c.cut_year AND f.is_predictable
    GROUP BY 1
),
quake_baseline AS (
    -- Línea base: media histórica de réplicas por banda de magnitud.
    SELECT c.cut_year, f.mag_band, avg(f.y_days_2_8) AS y_mean
    FROM cuts_quake c
    JOIN gold_aftershock_forecast f
      ON f.year <= c.cut_year AND f.is_predictable
    GROUP BY 1, 2
),
quake_skill AS (
    SELECT
        'pronostico_replicas' AS model_family,
        'pronostico_replicas' AS model_id,
        'GLOBAL' AS scope,
        c.cut_year,
        'RMSE replicas dias 2-8' AS metric,
        count(*) AS n_test,
        sqrt(avg(pow(t.y_days_2_8 - fit.alpha * t.n1, 2))) AS value_model,
        sqrt(avg(pow(t.y_days_2_8 - b.y_mean, 2))) AS value_baseline
    FROM cuts_quake c
    JOIN quake_fit fit ON fit.cut_year = c.cut_year
    JOIN gold_aftershock_forecast t
      ON t.year > c.cut_year AND t.is_predictable
    JOIN quake_baseline b
      ON b.cut_year = c.cut_year AND b.mag_band = t.mag_band
    GROUP BY 1, 2, 3, 4
    HAVING count(*) >= 20
),

-- ══ MODELO 2: riesgo de calor extremo corregido por tendencia ══════════════
cuts_heat AS (SELECT unnest([2012, 2014, 2016, 2018, 2020]) AS cut_year),
daily AS (
    SELECT location_id, local_date, year(local_date) AS yr,
           dayofyear(local_date) AS doy, temp_max
    FROM gold_weather_daily
    WHERE kind = 'observed' AND temp_max IS NOT NULL
),
-- Umbral por ciudad, recalculado en CADA corte solo con su entrenamiento.
heat_thr AS (
    SELECT c.cut_year, d.location_id,
           quantile_cont(d.temp_max, 0.95) AS thr
    FROM cuts_heat c JOIN daily d ON d.yr <= c.cut_year AND d.yr >= 2006
    GROUP BY 1, 2
),
heat_slope AS (
    SELECT c.cut_year, d.location_id,
           regr_slope(d.temp_max, d.yr) AS b_year
    FROM cuts_heat c JOIN daily d ON d.yr <= c.cut_year AND d.yr >= 2006
    GROUP BY 1, 2
),
-- Probabilidad climatológica por ventana de ±7 días del día del año.
heat_prob AS (
    SELECT c.cut_year, d.location_id, cal.doy,
           avg(CASE WHEN d.temp_max > t.thr THEN 1.0 ELSE 0.0 END) AS p_base,
           avg(d.temp_max) AS tmax_mean_train,
           avg(d.yr) AS yr_mean_train
    FROM cuts_heat c
    CROSS JOIN (SELECT * FROM range(1, 367) AS r(doy)) cal
    JOIN daily d ON d.yr <= c.cut_year AND d.yr >= 2006
                AND doy_distance(d.doy, cal.doy) <= 7
    JOIN heat_thr t ON t.cut_year = c.cut_year AND t.location_id = d.location_id
    GROUP BY 1, 2, 3
),
heat_eval AS (
    SELECT
        c.cut_year,
        d.location_id,
        CASE WHEN d.temp_max > t.thr THEN 1.0 ELSE 0.0 END AS y,
        p.p_base,
        -- Corrección por tendencia: desplaza la probabilidad hacia arriba en
        -- proporción al calentamiento acumulado desde el centro del
        -- entrenamiento. Acotada a [0,1].
        least(1.0, greatest(0.0,
            p.p_base + s.b_year * (d.yr - p.yr_mean_train) * 0.05
        )) AS p_trend
    FROM cuts_heat c
    JOIN daily d ON d.yr > c.cut_year
    JOIN heat_thr t ON t.cut_year = c.cut_year AND t.location_id = d.location_id
    JOIN heat_slope s ON s.cut_year = c.cut_year AND s.location_id = d.location_id
    JOIN heat_prob p ON p.cut_year = c.cut_year AND p.location_id = d.location_id
                    AND p.doy = d.doy
),
heat_skill AS (
    SELECT
        'riesgo_calor_corregido' AS model_family,
        'riesgo_calor_corregido' AS model_id,
        'GLOBAL' AS scope,
        cut_year,
        'Brier score' AS metric,
        count(*) AS n_test,
        avg(pow(p_trend - y, 2)) AS value_model,
        avg(pow(p_base - y, 2)) AS value_baseline
    FROM heat_eval
    GROUP BY 1, 2, 3, 4
),

-- ══ MODELO 3: persistencia amortiguada a 1 y 7 días ════════════════════════
cuts_pers AS (SELECT unnest([2014, 2016, 2018, 2020]) AS cut_year),
anom AS (
    SELECT location_id, local_date, year(local_date) AS yr, anomaly_c,
           lag(anomaly_c, 1) OVER w AS lag1,
           lag(anomaly_c, 7) OVER w AS lag7
    FROM gold_temperature_anomaly
    WHERE kind = 'observed' AND anomaly_c IS NOT NULL
    WINDOW w AS (PARTITION BY location_id ORDER BY local_date)
),
pers_fit AS (
    -- alpha amortiguado, ajustado solo con entrenamiento.
    SELECT c.cut_year,
           regr_slope(a.anomaly_c, a.lag1) AS a1,
           regr_slope(a.anomaly_c, a.lag7) AS a7
    FROM cuts_pers c JOIN anom a ON a.yr <= c.cut_year AND a.yr >= 2006
    WHERE a.lag1 IS NOT NULL AND a.lag7 IS NOT NULL
    GROUP BY 1
),
pers_skill AS (
    SELECT
        'persistencia_' || h.horizon AS model_family,
        'persistencia_' || h.horizon AS model_id,
        'GLOBAL' AS scope,
        c.cut_year,
        'RMSE anomalia C' AS metric,
        count(*) AS n_test,
        sqrt(avg(pow(
            a.anomaly_c - CASE WHEN h.horizon = '1d' THEN f.a1 * a.lag1
                               ELSE f.a7 * a.lag7 END, 2))) AS value_model,
        -- Línea base: la climatología, o sea anomalía cero.
        sqrt(avg(pow(a.anomaly_c, 2))) AS value_baseline
    FROM cuts_pers c
    JOIN pers_fit f ON f.cut_year = c.cut_year
    JOIN anom a ON a.yr > c.cut_year
    CROSS JOIN (SELECT unnest(['1d', '7d']) AS horizon) h
    WHERE a.lag1 IS NOT NULL AND a.lag7 IS NOT NULL
    GROUP BY 1, 2, 3, 4
),

-- ══ MODELO 4: dengue a cuatro semanas vista ════════════════════════════════
--
-- La pregunta operativa, no la estadística: **estando en la semana t-4, ¿saber
-- la temperatura ayuda a anticipar los casos de la semana t?**
--
-- Se compara contra dos líneas base, y la diferencia entre ellas es el punto:
--
--   · climatología  → predecir "lo normal para esa semana del año". Fácil de
--     batir, y batirla sola no demuestra nada operativo.
--   · persistencia  → predecir "lo mismo que hace cuatro semanas". Con una
--     autocorrelación de 0,90-0,96, esta es durísima y es la que de verdad
--     decide si el modelo aporta algo.
--
-- Un modelo que bate a la climatología pero no a la persistencia es un modelo
-- que ha aprendido que el dengue tiene estaciones. Eso ya lo sabíamos.
--
-- ── La fuga que hay que evitar ──────────────────────────────────────────────
--
-- La climatología se calcula SOLO con años de entrenamiento. Si se calculara
-- con la serie entera, las semanas de prueba habrían contribuido a la media
-- estacional que luego se les resta: el futuro se colaría en su propia
-- referencia y el error de prueba saldría artificialmente bajo.
cuts_dengue AS (SELECT unnest([2012, 2014, 2016, 2018]) AS cut_year),

dengue_base AS (
    SELECT
        location_id, provincia, period_start, year, semana_iso,
        ln(1 + casos)  AS lc,
        temp_media_c   AS tm,
        row_number() OVER (PARTITION BY location_id ORDER BY period_start) AS t
    FROM gold_dengue_peru
    WHERE clima_completo
      AND location_id IN (
          SELECT location_id FROM gold_dengue_peru GROUP BY 1
          HAVING sum(casos) >= 100
             AND sum(CASE WHEN casos > 0 THEN 1 ELSE 0 END) >= 50
      )
),
dengue_clim AS (
    SELECT c.cut_year, b.location_id, b.semana_iso,
           avg(b.lc) AS lc_norm, avg(b.tm) AS tm_norm
    FROM cuts_dengue c
    JOIN dengue_base b ON b.year <= c.cut_year
    GROUP BY 1, 2, 3
),
dengue_anom AS (
    SELECT c.cut_year, b.location_id, b.provincia, b.year, b.t,
           b.lc - cl.lc_norm AS a_casos,
           b.tm - cl.tm_norm AS a_temp
    FROM cuts_dengue c
    CROSS JOIN dengue_base b
    JOIN dengue_clim cl
      ON cl.cut_year = c.cut_year
     AND cl.location_id = b.location_id
     AND cl.semana_iso = b.semana_iso
),
-- Alineación al horizonte real: la fila lleva el objetivo de la semana t y los
-- predictores de la t-4, que es todo lo que se conoce al hacer el pronóstico.
dengue_pairs AS (
    SELECT a.cut_year, a.location_id, a.provincia, a.year,
           a.a_casos AS y, p.a_temp AS x, p.a_casos AS y_persistencia
    FROM dengue_anom a
    JOIN dengue_anom p
      ON p.cut_year = a.cut_year
     AND p.location_id = a.location_id
     AND p.t = a.t - 4
),
dengue_fit AS (
    SELECT cut_year, location_id,
           regr_slope(y, x)     AS beta,
           regr_intercept(y, x) AS alpha
    FROM dengue_pairs
    WHERE year <= cut_year
    GROUP BY 1, 2
),
dengue_skill AS (
    SELECT
        'dengue_clima_4sem' AS model_family,
        'dengue_clima_4sem' AS model_family,
        'dengue_clima_4sem_vs_persistencia' AS model_id,
        any_value(p.provincia)              AS scope,
        p.cut_year,
        'RMSE anomalia log-casos'           AS metric,
        count(*)                            AS n_test,
        sqrt(avg(pow(p.y - (f.alpha + f.beta * p.x), 2))) AS value_model,
        sqrt(avg(pow(p.y - p.y_persistencia, 2)))         AS value_baseline
    FROM dengue_pairs p
    JOIN dengue_fit f USING (cut_year, location_id)
    WHERE p.year > p.cut_year
    GROUP BY p.location_id, p.cut_year

    UNION ALL

    SELECT
        'dengue_clima_4sem' AS model_family,
        'dengue_clima_4sem' AS model_family,
        'dengue_clima_4sem_vs_climatologia' AS model_id,
        any_value(p.provincia)              AS scope,
        p.cut_year,
        'RMSE anomalia log-casos'           AS metric,
        count(*)                            AS n_test,
        sqrt(avg(pow(p.y - (f.alpha + f.beta * p.x), 2))) AS value_model,
        -- Predecir la anomalía como cero ES predecir la climatología, porque
        -- la anomalía ya está definida contra ella.
        sqrt(avg(pow(p.y, 2)))                            AS value_baseline
    FROM dengue_pairs p
    JOIN dengue_fit f USING (cut_year, location_id)
    WHERE p.year > p.cut_year
    GROUP BY p.location_id, p.cut_year
),

all_cuts AS (
    SELECT * FROM quake_skill
    UNION ALL BY NAME SELECT * FROM heat_skill
    UNION ALL BY NAME SELECT * FROM pers_skill
    UNION ALL BY NAME SELECT * FROM dengue_skill
),
scored AS (
    SELECT
        *,
        -- Mejora porcentual. Ambas métricas son "menor es mejor", así que el
        -- signo es el mismo para RMSE y para Brier.
        round(100 * (1 - value_model / nullif(value_baseline, 0)), 2) AS improvement_pct
    FROM all_cuts
),
por_linea_base AS (
SELECT
    model_family,
    model_id,
    scope,
    cut_year,
    metric,
    n_test,
    round(value_model, 5) AS value_model,
    round(value_baseline, 5) AS value_baseline,
    improvement_pct,

    -- Agregados sobre TODOS los cortes. La mediana es la cifra que vale.
    round(median(improvement_pct) OVER (PARTITION BY model_id, scope), 2)
        AS improvement_median,
    round(min(improvement_pct) OVER (PARTITION BY model_id, scope), 2)
        AS improvement_min,
    round(max(improvement_pct) OVER (PARTITION BY model_id, scope), 2)
        AS improvement_max,
    count(*) OVER (PARTITION BY model_id, scope) AS n_cuts,

    -- Si este modelo bate a ESTA línea base concreta.
    (median(improvement_pct) OVER (PARTITION BY model_id, scope) >= 5.0
     AND min(improvement_pct) OVER (PARTITION BY model_id, scope) > 0)
        AS bate_esta_linea_base,

    -- EL CRITERIO DE PRODUCTO. Tres condiciones, todas necesarias:
    --   1. la mediana bate a la línea base con margen (>=5%)
    --   2. NINGÚN corte es negativo — un modelo que a veces estorba, no sale
    --   3. y las bate TODAS, no solo la más cómoda
    --
    -- La tercera se añadió por el dengue. Contra la climatología, Trujillo
    -- mejoraba un 22,9% y habría salido publicado; contra la persistencia
    -- —"lo mismo que hace cuatro semanas"— perdía un 98%. Un modelo peor que
    -- la regla más tonta posible no se puede enseñar por muy bien que quede
    -- frente a una línea base elegida con cariño.
    --
    -- Cuando una familia tiene una sola línea base, la condición no cambia
    -- nada: es la misma de siempre.
    NULL::BOOLEAN AS should_display        -- se calcula abajo
FROM scored
)
-- Un agregado no puede envolver a una función ventana, así que la condición de
-- familia se resuelve en un segundo paso sobre el resultado del primero.
SELECT
    * EXCLUDE (should_display),
    bool_and(bate_esta_linea_base) OVER (PARTITION BY model_family, scope)
        AS should_display
FROM por_linea_base
ORDER BY improvement_median DESC, model_id, scope, cut_year;
