-- Conjunto de entrenamiento para predecir calor extremo a 7 días.
--
-- Grano: (location_id, local_date).
--
-- Pregunta: ¿superará el día D la máxima del percentil 95 para esa fecha del
-- año, sabiendo solo lo que se conoce el día D-7?
--
-- **La regla que hace válido todo esto: ninguna característica puede usar
-- información posterior a D-7.** Es la única forma de que el backtest signifique
-- algo. Una variable que se cuele desde el futuro produce una precisión
-- espectacular y completamente falsa, y es el error más común en series
-- temporales.
--
-- Por eso el periodo base del objetivo también se recorta. La climatología
-- general del proyecto usa 2006-2020, pero el modelo se entrena con 2006-2018 y
-- se evalúa en 2019-2025. Si el umbral p95 se calculase con los 2006-2020
-- habituales, dos años del conjunto de prueba estarían contribuyendo a definir
-- su propio objetivo: una fuga pequeña (unas 30 de 225 muestras, un 13%) pero
-- real. Aquí se calcula un p95 SOLO con 2006-2018.
--
-- Predictores, todos conocidos en D-7:
--   anomaly_lag7      anomalía del día D-7
--   anomaly_mean_14d  media de anomalías de D-7 a D-20 (persistencia)
--   oni_anomaly       estado de ENSO, conocido con meses de antelación
--   doy               día del año, para la estacionalidad

CREATE OR REPLACE TABLE gold_heatwave_features AS
WITH train_climatology AS (
    -- Percentil 95 de la máxima por día del año, SOLO con 2006-2018.
    SELECT
        o.location_id,
        c.doy,
        quantile_cont(o.temp_max, 0.95) AS temp_max_p95_train,
        avg(o.temp_mean) AS temp_mean_avg_train,
        stddev_samp(o.temp_mean) AS temp_mean_sd_train,
        count(*) AS n_train
    FROM (SELECT * FROM range(1, 367) AS t(doy)) c
    JOIN (
        SELECT location_id, local_date, dayofyear(local_date) AS doy,
               temp_max, temp_mean
        FROM gold_weather_daily
        WHERE kind = 'observed'
          AND local_date BETWEEN DATE '2006-01-01' AND DATE '2018-12-31'
    ) o ON doy_distance(o.doy, c.doy) <= 7
    GROUP BY 1, 2
),
daily AS (
    SELECT location_id, local_date, temp_max, temp_mean,
           dayofyear(local_date) AS doy
    FROM gold_weather_daily
    WHERE kind = 'observed'
),
-- Anomalía diaria respecto de la referencia de entrenamiento.
anomalies AS (
    SELECT
        d.location_id,
        d.local_date,
        d.doy,
        d.temp_max,
        d.temp_mean,
        c.temp_max_p95_train,
        c.temp_mean_avg_train,
        c.temp_mean_sd_train,
        d.temp_mean - c.temp_mean_avg_train AS anomaly_c
    FROM daily d
    JOIN train_climatology c
      ON c.location_id = d.location_id AND c.doy = d.doy
),
lagged AS (
    SELECT
        *,
        -- Desfase de 7 días: lo último que se sabe al hacer la predicción.
        lag(anomaly_c, 7) OVER w AS anomaly_lag7,
        -- Media de las dos semanas anteriores a D-7. Captura persistencia:
        -- los periodos cálidos tienden a encadenarse.
        avg(anomaly_c) OVER (
            PARTITION BY location_id ORDER BY local_date
            ROWS BETWEEN 20 PRECEDING AND 7 PRECEDING
        ) AS anomaly_mean_14d,
        lag(temp_max, 7) OVER w AS temp_max_lag7
    FROM anomalies
    WINDOW w AS (PARTITION BY location_id ORDER BY local_date)
)
SELECT
    l.location_id,
    l.local_date,
    l.doy,
    year(l.local_date) AS year,

    -- Objetivo: ¿supera el p95 de entrenamiento para ese día del año?
    l.temp_max > l.temp_max_p95_train AS is_extreme,
    l.temp_max,
    l.temp_max_p95_train,

    -- Predictores, todos disponibles en D-7.
    round(l.anomaly_lag7, 2) AS anomaly_lag7,
    round(l.anomaly_mean_14d, 2) AS anomaly_mean_14d,
    round(l.temp_max_lag7, 2) AS temp_max_lag7,
    round(o.anomaly_c, 2) AS oni_anomaly,
    o.phase AS enso_phase,

    l.local_date <= DATE '2018-12-31' AS in_train
FROM lagged l
LEFT JOIN silver_oni o
  ON o.year = year(l.local_date)
 -- Estación ONI del trimestre centrado en el mes del día. Se conoce con
 -- antelación, así que es un predictor legítimo.
 AND o.season_index = month(l.local_date)
WHERE l.anomaly_lag7 IS NOT NULL
  AND l.anomaly_mean_14d IS NOT NULL
  AND l.temp_max_p95_train IS NOT NULL;
