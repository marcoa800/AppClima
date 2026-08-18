-- Evaluación fuera de muestra del modelo de calor extremo.
--
-- Grano: (scope) — global y por ubicación.
--
-- **Este es el modelo más importante del proyecto, porque es el único que puede
-- decir "el modelo no sirve".** Todo lo demás describe; esto juzga.
--
-- Diseño del contraste:
--
--   Entrenamiento  2006-2018   solo aquí se calculan las probabilidades
--   Prueba         2019-2025   nunca vista durante el ajuste
--   Línea base     la tasa climatológica del entrenamiento
--
-- La partición es POR TIEMPO, no aleatoria. Un train_test_split al azar sobre
-- series temporales pone el día siguiente en el entrenamiento y el anterior en
-- la prueba: el modelo aprende a interpolar entre días que ya conoce, el
-- resultado sale espectacular y no significa nada.
--
-- Métrica: **Brier score**, la media de (probabilidad - resultado)². Es el error
-- cuadrático medio adaptado a predicciones probabilísticas, y penaliza tanto
-- equivocarse como estar seguro al equivocarse. Menor es mejor.
--
-- Y sobre todo el **Brier Skill Score**: 1 - BS_modelo/BS_base.
--
--     BSS > 0  el modelo aporta información sobre la climatología
--     BSS = 0  el modelo equivale a decir siempre "5% de probabilidad"
--     BSS < 0  el modelo es PEOR que no tener modelo
--
-- Ese último caso no es hipotético: ya pasó en este proyecto con el ACE del
-- Atlántico, donde un r de -0,50 en entrenamiento acabó siendo un 6,2% peor que
-- la climatología al evaluarlo fuera de muestra.

CREATE OR REPLACE TABLE gold_heatwave_backtest AS
WITH scored AS (
    SELECT
        f.location_id,
        f.local_date,
        f.is_extreme,
        m.p_extreme AS p_model,
        m.base_rate AS p_base
    FROM (
        SELECT
            *,
            CASE
                WHEN anomaly_mean_14d < -1 THEN '1. muy fría (<-1)'
                WHEN anomaly_mean_14d < 0 THEN '2. fría (-1 a 0)'
                WHEN anomaly_mean_14d < 1 THEN '3. normal (0 a 1)'
                WHEN anomaly_mean_14d < 2 THEN '4. cálida (1 a 2)'
                ELSE '5. muy cálida (>2)'
            END AS anomaly_bucket,
            coalesce(enso_phase, 'Neutral') AS enso_bucket
        FROM gold_heatwave_features
        WHERE NOT in_train
    ) f
    JOIN gold_heatwave_model m
      ON m.anomaly_bucket = f.anomaly_bucket
     AND m.enso_bucket = f.enso_bucket
),
metrics AS (
    SELECT
        location_id,
        count(*) AS n_test,
        sum(CASE WHEN is_extreme THEN 1 ELSE 0 END) AS n_extreme,
        round(avg(CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END), 4) AS observed_rate,
        round(avg(pow(p_model - CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END, 2)), 6)
            AS brier_model,
        round(avg(pow(p_base - CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END, 2)), 6)
            AS brier_base
    FROM scored
    GROUP BY location_id

    UNION ALL

    SELECT
        'GLOBAL',
        count(*),
        sum(CASE WHEN is_extreme THEN 1 ELSE 0 END),
        round(avg(CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END), 4),
        round(avg(pow(p_model - CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END, 2)), 6),
        round(avg(pow(p_base - CASE WHEN is_extreme THEN 1.0 ELSE 0.0 END, 2)), 6)
    FROM scored
)
SELECT
    location_id AS scope,
    n_test,
    n_extreme,
    observed_rate,
    brier_model,
    brier_base,
    round(1 - brier_model / nullif(brier_base, 0), 4) AS brier_skill_score,
    round(100 * (1 - brier_model / nullif(brier_base, 0)), 2) AS pct_improvement,
    brier_model < brier_base AS beats_climatology
FROM metrics
ORDER BY (location_id = 'GLOBAL') DESC, brier_skill_score DESC;
