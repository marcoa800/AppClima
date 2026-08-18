-- Estimación del valor b por máxima verosimilitud (Aki, 1965).
--
-- Grano: scope (global y por clase de profundidad).
--
-- El valor b de Gutenberg-Richter mide la proporción entre sismos pequeños y
-- grandes. Se puede sacar ajustando una recta por mínimos cuadrados al gráfico
-- log-lineal, pero eso está sesgado: pondera igual las bandas con 20.000
-- eventos y las que tienen 3. El estimador de máxima verosimilitud de Aki es el
-- estándar en la literatura:
--
--     b = log10(e) / (M_media - (Mc - ΔM/2))
--
-- con Mc la magnitud de completitud (4.5, nuestro corte de ingesta) y ΔM el
-- ancho de banda (0,1). El término -ΔM/2 corrige el sesgo del redondeo de
-- magnitudes a la décima; omitirlo infla b de forma sistemática.
--
-- Error típico: σ_b = b / √n  (Aki, 1965).
--
-- Lo interesante es la comparación por profundidad. Es un resultado conocido
-- que b varía con el régimen tectónico, y aquí se puede ver con datos propios.

CREATE OR REPLACE TABLE gold_quake_b_value AS
WITH params AS (
    SELECT 4.5 AS mc, 0.1 AS delta_m
),
samples AS (
    SELECT 'global' AS scope, magnitude FROM silver_earthquakes WHERE magnitude >= 4.5
    UNION ALL
    SELECT depth_class AS scope, magnitude FROM silver_earthquakes WHERE magnitude >= 4.5
),
estimated AS (
    SELECT
        s.scope,
        count(*) AS n_events,
        round(avg(s.magnitude), 4) AS mag_mean,
        round(max(s.magnitude), 1) AS mag_max,
        log10(exp(1)) / (avg(s.magnitude) - (p.mc - p.delta_m / 2)) AS b_value
    FROM samples s
    CROSS JOIN params p
    GROUP BY s.scope, p.mc, p.delta_m
)
SELECT
    scope,
    n_events,
    mag_mean,
    mag_max,
    round(b_value, 3) AS b_value,
    round(b_value / sqrt(n_events), 4) AS b_std_error,
    -- El valor a de la ley, normalizado a un año, para poder comparar tasas
    -- entre subconjuntos de tamaño distinto.
    round(log10(n_events) + b_value * 4.5, 3) AS a_value
FROM estimated
ORDER BY n_events DESC;
