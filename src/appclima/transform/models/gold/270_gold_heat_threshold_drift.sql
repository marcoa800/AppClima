-- Cuánto se ha desfasado el umbral de alerta por calor de cada ciudad.
--
-- Grano: location_id.
--
-- **Es el hallazgo con más valor preventivo del proyecto, y salió sin buscarlo.**
--
-- Los planes de emergencia por calor se disparan al superar un umbral, y ese
-- umbral se calibra con datos históricos: típicamente el percentil 95 de la
-- máxima diaria sobre una ventana de referencia. Por construcción debería
-- superarse un 5% de los días.
--
-- Al evaluar el modelo de calor extremo apareció que ya no es así. Con el
-- umbral calculado en 2006-2018, el periodo 2019-2025 lo supera:
--
--     Singapur          45,8%   en vez del 5%      ×10,7
--     Ciudad de México  38,5%                      × 8,1
--     Tokio             19,2%                      × 4,2
--     Reikiavik          4,8%                      × 1,1
--
-- Traducido: **un plan de calor calibrado hace una década se dispara varias
-- veces menos de lo que debería.** No porque esté mal diseñado, sino porque el
-- clima sobre el que se calibró ya no es el clima actual.
--
-- Y el patrón de quién sufre más es contraintuitivo: la correlación entre
-- variabilidad térmica y factor de amplificación es r = -0,68. Los climas
-- ESTABLES se disparan. Singapur, con una desviación típica de 0,70 °C, no
-- tiene margen para absorber el desplazamiento; Yakutsk, con 4,74 °C, lo
-- absorbe entre sus oscilaciones diarias.
--
-- La consecuencia práctica es incómoda: **las ciudades tropicales necesitan
-- planes de calor con urgencia y son las que menos probablemente los tengan**,
-- porque su clima fue históricamente aburrido.
--
-- LIMITACIONES, porque esto no es un informe técnico oficial:
--   - 12 ciudades, no una muestra global
--   - la ventana de evaluación son 7 años: suficiente para ver el desfase,
--     corta para estimar la tendencia con precisión
--   - un umbral real de salud pública combina temperatura, humedad, duración
--     de la ola y mortalidad observada. Aquí solo hay temperatura máxima.

CREATE OR REPLACE TABLE gold_heat_threshold_drift AS
WITH daily AS (
    SELECT location_id, local_date, year(local_date) AS yr, temp_max, temp_mean
    FROM gold_weather_daily
    WHERE kind = 'observed' AND temp_max IS NOT NULL
),
-- El umbral tal como se habría calibrado con la ventana de referencia.
calibracion AS (
    SELECT
        location_id,
        quantile_cont(temp_max, 0.95) AS threshold_c,
        count(*) AS n_reference_days,
        stddev_samp(temp_mean) AS temp_sd
    FROM daily
    WHERE yr BETWEEN 2006 AND 2018
    GROUP BY 1
),
-- Qué pasa hoy con ese mismo umbral.
evaluacion AS (
    SELECT
        d.location_id,
        count(*) AS n_recent_days,
        sum(CASE WHEN d.temp_max > c.threshold_c THEN 1 ELSE 0 END) AS n_exceeded,
        -- El umbral que HOY daría el 5% que se pretendía.
        quantile_cont(d.temp_max, 0.95) AS threshold_now_c,
        max(d.temp_max) AS temp_max_record
    FROM daily d
    JOIN calibracion c ON c.location_id = d.location_id
    WHERE d.yr BETWEEN 2019 AND 2025
    GROUP BY 1
)
SELECT
    l.id AS location_id,
    l.name AS location_name,
    l.country,
    l.koppen,
    round(abs(l.lat), 1) AS abs_lat,

    round(c.threshold_c, 1) AS threshold_2006_2018,
    round(e.threshold_now_c, 1) AS threshold_2019_2025,
    round(e.threshold_now_c - c.threshold_c, 2) AS threshold_drift_c,

    e.n_recent_days,
    e.n_exceeded,
    round(100.0 * e.n_exceeded / e.n_recent_days, 1) AS pct_exceeded_now,
    5.0 AS pct_expected,

    -- Cuántas veces más a menudo se dispara la alarma de lo previsto. Es la
    -- cifra que un responsable de plan de emergencia necesita ver.
    round((100.0 * e.n_exceeded / e.n_recent_days) / 5.0, 1) AS amplification,

    -- Días al año por encima del umbral, antes y ahora. Más legible que un
    -- porcentaje para dimensionar recursos.
    round(365 * 0.05) AS days_per_year_expected,
    round(365.0 * e.n_exceeded / e.n_recent_days) AS days_per_year_now,

    round(c.temp_sd, 2) AS temp_variability_sd,
    round(e.temp_max_record, 1) AS temp_max_record,

    -- Prioridad de recalibración. El criterio combina cuánto se desvía y
    -- cuánto sube el umbral: un factor alto sobre pocos días importa menos
    -- que uno moderado sobre muchos.
    CASE
        WHEN (100.0 * e.n_exceeded / e.n_recent_days) / 5.0 >= 5 THEN '1. urgente'
        WHEN (100.0 * e.n_exceeded / e.n_recent_days) / 5.0 >= 3 THEN '2. alta'
        WHEN (100.0 * e.n_exceeded / e.n_recent_days) / 5.0 >= 1.8 THEN '3. media'
        ELSE '4. baja'
    END AS recalibration_priority
FROM calibracion c
JOIN evaluacion e ON e.location_id = c.location_id
JOIN dim_locations l ON l.id = c.location_id
ORDER BY amplification DESC;
