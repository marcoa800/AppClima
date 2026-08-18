-- Anomalías térmicas: cada día comparado con su propia normal.
--
-- Grano: (location_id, local_date, kind).
--
-- Esta es la tabla que responde a la pregunta que la gente hace de verdad: "¿es
-- normal el calor que está haciendo?". Y lo hace de forma comparable entre
-- climas: +5°C sobre la media es mucho en Singapur, donde la temperatura apenas
-- varía, y poco en Yakutsk, donde el rango anual supera los 60°C. Por eso el
-- z-score importa tanto como la anomalía en grados.
--
-- Incluye tanto observado como pronóstico. Eso permite algo bonito en la app:
-- "los próximos 7 días estarán 3°C por encima de lo normal", que es mucho más
-- informativo que un número de temperatura suelto.
--
-- Nota sobre `extreme_heat`: el umbral es el percentil 95 de la máxima para ese
-- día del año. Es un umbral relativo al clima local y a la época, no absoluto —
-- 25°C es extremo en Reikiavik en junio y trivial en Bangkok en cualquier mes.
--
-- Nota sobre `record_heat` y `in_baseline`: la línea base va de 2006 a 2020, y
-- los días de ese periodo forman parte de su propia referencia. Para ellos, un
-- récord es imposible por construcción. La columna `in_baseline` marca cuáles
-- son, y **los flags de récord solo deben interpretarse cuando in_baseline es
-- falso**. Exponerlo así es más honesto que ocultar la limitación.

CREATE OR REPLACE TABLE gold_temperature_anomaly AS
SELECT
    d.location_id,
    d.local_date,
    d.kind,
    dayofyear(d.local_date) AS doy,

    d.temp_mean,
    c.temp_mean_avg AS clim_mean,
    round(d.temp_mean - c.temp_mean_avg, 2) AS anomaly_c,

    -- Cuántas desviaciones típicas por encima o por debajo de lo normal. Es lo
    -- que hace comparable un día de Singapur con uno de Yakutsk.
    CASE
        WHEN c.temp_mean_sd > 0
        THEN round((d.temp_mean - c.temp_mean_avg) / c.temp_mean_sd, 2)
    END AS z_score,

    d.temp_max,
    c.temp_max_p95 AS clim_max_p95,
    c.temp_max_record AS clim_max_record,
    d.temp_max > c.temp_max_p95 AS extreme_heat,
    d.temp_max > c.temp_max_record AS record_heat,

    d.temp_min,
    c.temp_min_p05 AS clim_min_p05,
    c.temp_min_record AS clim_min_record,
    d.temp_min < c.temp_min_p05 AS extreme_cold,
    d.temp_min < c.temp_min_record AS record_cold,

    d.precip_sum,
    c.precip_avg AS clim_precip_avg,

    -- Expuesto a propósito: una anomalía calculada con 40 muestras no merece la
    -- misma confianza que una con 300. Que el consumidor pueda decidir.
    c.n_samples AS clim_n_samples,

    -- ¿Este día formó parte del cálculo de su propia referencia? Si sí, los
    -- flags de récord no son interpretables.
    d.local_date BETWEEN DATE '2006-01-01' AND DATE '2020-12-31' AS in_baseline
FROM gold_weather_daily d
JOIN gold_climatology c
  ON c.location_id = d.location_id
 AND c.doy = dayofyear(d.local_date);
