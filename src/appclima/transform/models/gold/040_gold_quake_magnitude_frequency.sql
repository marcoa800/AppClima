-- Ley de Gutenberg-Richter: la relación magnitud-frecuencia.
--
-- Grano: mag_bin (bandas de 0,1 de magnitud).
--
-- Es probablemente la ley empírica más robusta de la sismología:
--
--     log10(N) = a - b·M
--
-- donde N es el número de sismos de magnitud ≥ M. Al graficar log10(N) frente a
-- M sale una recta casi perfecta a lo largo de varios órdenes de magnitud. El
-- valor `b` ronda 1,0 en casi toda la Tierra, lo que significa que por cada
-- sismo de magnitud 6 hay unos 10 de magnitud 5 y unos 100 de magnitud 4.
--
-- Es el mejor primer análisis que se puede hacer con este dataset: si la recta
-- no sale, hay un problema en los datos, no en la sismología.
--
-- El corte en 4.5 es la magnitud de completitud (Mc) de nuestra ingesta
-- histórica: por debajo faltan eventos porque así lo pedimos, no porque no
-- ocurrieran. Ajustar la recta incluyendo datos por debajo de Mc es el error
-- clásico en este análisis y curva el extremo inferior de forma engañosa.

CREATE OR REPLACE TABLE gold_quake_magnitude_frequency AS
WITH binned AS (
    SELECT
        -- floor a la décima. round() no serviría: agruparía 4.44 y 4.45 en
        -- bandas distintas de forma inconsistente en los bordes.
        floor(magnitude * 10) / 10 AS mag_bin,
        count(*) AS n_events
    FROM silver_earthquakes
    WHERE magnitude >= 4.5
    GROUP BY 1
)
SELECT
    mag_bin,
    n_events,
    -- Cuenta acumulada descendente: nº de sismos de magnitud ≥ mag_bin, que es
    -- exactamente la N de la ley.
    sum(n_events) OVER (
        ORDER BY mag_bin DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS n_cumulative,
    round(log10(sum(n_events) OVER (
        ORDER BY mag_bin DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )), 4) AS log10_n_cumulative
FROM binned
ORDER BY mag_bin;
