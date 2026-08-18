-- Modelo de probabilidad de calor extremo, como tabla de contingencia.
--
-- Grano: (anomaly_bucket, enso_bucket).
--
-- No hay ninguna librería de machine learning aquí, y es deliberado: el modelo
-- es una **tabla de frecuencias condicionadas** calculada solo sobre 2006-2018.
-- Para cada combinación de "cuán cálidas venían las dos semanas previas" y
-- "estado de ENSO", cuenta qué fracción de días acabó siendo extremo.
--
-- Es un clasificador naive, pero tiene tres ventajas sobre una regresión
-- logística en este contexto: es completamente auditable (se puede leer la
-- tabla y entender la predicción), no puede sobreajustar de formas raras, y su
-- salida es directamente una probabilidad calibrada por construcción.
--
-- La tasa base es ~5% por definición del p95. Cualquier celda muy por encima de
-- ese 5% es señal real.
--
-- `n_train` va expuesto porque una celda con 12 observaciones no merece la
-- misma confianza que una con 4.000, y el suavizado de Laplace evita que una
-- celda con 3 casos y 3 aciertos prediga el 100%.

CREATE OR REPLACE TABLE gold_heatwave_model AS
WITH bucketed AS (
    SELECT
        -- Discretización de la anomalía previa. Los cortes son redondos a
        -- propósito: buscados a mano invitarían a sobreajustar.
        CASE
            WHEN anomaly_mean_14d < -1 THEN '1. muy fría (<-1)'
            WHEN anomaly_mean_14d < 0 THEN '2. fría (-1 a 0)'
            WHEN anomaly_mean_14d < 1 THEN '3. normal (0 a 1)'
            WHEN anomaly_mean_14d < 2 THEN '4. cálida (1 a 2)'
            ELSE '5. muy cálida (>2)'
        END AS anomaly_bucket,
        coalesce(enso_phase, 'Neutral') AS enso_bucket,
        is_extreme
    FROM gold_heatwave_features
    WHERE in_train
),
base AS (
    SELECT avg(CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END) AS base_rate
    FROM bucketed
)
SELECT
    b.anomaly_bucket,
    b.enso_bucket,
    count(*) AS n_train,
    sum(CASE WHEN b.is_extreme THEN 1 ELSE 0 END) AS n_extreme,

    -- Suavizado de Laplace: sin él, una celda con 3 casos y 3 extremos
    -- predeciría probabilidad 1,0 y arruinaría el Brier score en la prueba.
    round(
        (sum(CASE WHEN b.is_extreme THEN 1.0 ELSE 0.0 END) + 1)
        / (count(*) + 2), 4
    ) AS p_extreme,

    round((SELECT base_rate FROM base), 4) AS base_rate,
    round(
        ((sum(CASE WHEN b.is_extreme THEN 1.0 ELSE 0.0 END) + 1) / (count(*) + 2))
        / (SELECT base_rate FROM base), 2
    ) AS lift
FROM bucketed b
GROUP BY 1, 2
ORDER BY 1, 2;
