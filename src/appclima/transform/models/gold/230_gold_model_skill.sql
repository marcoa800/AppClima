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

all_cuts AS (
    SELECT * FROM quake_skill
    UNION ALL BY NAME SELECT * FROM heat_skill
    UNION ALL BY NAME SELECT * FROM pers_skill
),
scored AS (
    SELECT
        *,
        -- Mejora porcentual. Ambas métricas son "menor es mejor", así que el
        -- signo es el mismo para RMSE y para Brier.
        round(100 * (1 - value_model / nullif(value_baseline, 0)), 2) AS improvement_pct
    FROM all_cuts
)
SELECT
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

    -- EL CRITERIO DE PRODUCTO. Dos condiciones, ambas necesarias:
    --   1. la mediana bate a la línea base con margen (>=5%)
    --   2. NINGÚN corte es negativo — un modelo que a veces estorba, no sale
    (median(improvement_pct) OVER (PARTITION BY model_id, scope) >= 5.0
     AND min(improvement_pct) OVER (PARTITION BY model_id, scope) > 0)
        AS should_display
FROM scored
ORDER BY improvement_median DESC, model_id, cut_year;
