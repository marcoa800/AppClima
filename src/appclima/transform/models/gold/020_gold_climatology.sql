-- Climatología: qué es "normal" en cada ubicación para cada día del año.
--
-- Grano: (location_id, doy).
--
-- Esta tabla es la que da sentido a la palabra "anomalía". Sin una referencia
-- de qué es normal, decir que hoy hace 33°C en Madrid no informa de nada: puede
-- ser un día de agosto perfectamente corriente o un récord histórico.
--
-- Dos decisiones metodológicas:
--
-- 1. **Ventana de ±7 días.** La climatología de un día concreto se calcula con
--    los datos de los 15 días centrados en él, a lo largo de todos los años
--    disponibles. Un solo día del año tendría 20 muestras (una por año), que es
--    demasiado ruidoso; con la ventana son ~300. Es el enfoque estándar en
--    climatología, y `doy_distance` se encarga de que el 1 de enero también use
--    la última semana de diciembre.
--
-- 2. **Periodo base FIJO de 2006 a 2020.** Esto es más importante de lo que
--    parece, y lo aprendí viendo que `record_heat` salía siempre False.
--
--    Si la climatología se calcula con TODOS los años disponibles, cada día
--    entra en su propia línea base. Consecuencias: las anomalías quedan
--    amortiguadas, y sobre todo los récords se vuelven imposibles por
--    construcción — un día nunca puede superar un máximo que lo incluye a él
--    mismo. La columna era matemáticamente siempre falsa.
--
--    Con un periodo base cerrado en 2020, los años 2021+ se evalúan contra una
--    referencia independiente y los récords significan algo. Es además la
--    práctica estándar en climatología: la norma WMO 1991-2020 es fija por este
--    mismo motivo.
--
-- 3. **15 años, no los 30 de la norma WMO.** Descargar 1991-2020 completo para
--    las 49 ciudades no cabe en la cuota gratuita de Open-Meteo (ver
--    locations.FLAGSHIP_IDS). La referencia es sólida pero NO es la normal
--    climática oficial y no debe presentarse como tal. `n_samples` queda
--    expuesto para que cualquiera juzgue la solidez de cada celda.
--
-- Solo usa datos observados (reanálisis). Calcular la normal con pronósticos
-- sería circular.

CREATE OR REPLACE TABLE gold_climatology AS
WITH observed AS (
    SELECT
        location_id,
        local_date,
        dayofyear(local_date) AS doy,
        temp_mean,
        temp_min,
        temp_max,
        precip_sum
    FROM gold_weather_daily
    WHERE kind = 'observed'
      -- Periodo base cerrado. Ver el punto 2 de la cabecera: sin este filtro,
      -- los récords son imposibles por construcción.
      AND local_date BETWEEN DATE '2006-01-01' AND DATE '2020-12-31'
),
calendar AS (
    SELECT * FROM range(1, 367) AS t(doy)
),
windowed AS (
    SELECT
        c.doy,
        o.location_id,
        o.temp_mean,
        o.temp_min,
        o.temp_max,
        o.precip_sum
    FROM calendar c
    JOIN observed o ON doy_distance(o.doy, c.doy) <= 7
)
SELECT
    location_id,
    doy,
    count(*) AS n_samples,

    round(avg(temp_mean), 2) AS temp_mean_avg,
    round(stddev_samp(temp_mean), 2) AS temp_mean_sd,
    round(quantile_cont(temp_mean, 0.05), 2) AS temp_mean_p05,
    round(quantile_cont(temp_mean, 0.95), 2) AS temp_mean_p95,

    round(avg(temp_max), 2) AS temp_max_avg,
    round(quantile_cont(temp_max, 0.95), 2) AS temp_max_p95,
    round(max(temp_max), 2) AS temp_max_record,

    round(avg(temp_min), 2) AS temp_min_avg,
    round(quantile_cont(temp_min, 0.05), 2) AS temp_min_p05,
    round(min(temp_min), 2) AS temp_min_record,

    round(avg(precip_sum), 2) AS precip_avg
FROM windowed
GROUP BY 1, 2;
