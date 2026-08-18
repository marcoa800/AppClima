-- Desastres y muertes por siglo y tipo de peligro.
--
-- Grano: (century, hazard_type).
--
-- ADVERTENCIA, y es la más importante de todo el warehouse: **esta tabla NO
-- mide si los desastres son más frecuentes o más mortales con el tiempo.**
--
-- La curva ascendente que produce es casi enteramente un artefacto del registro
-- histórico. En el siglo XX hubo sismógrafos, prensa y censos; en el siglo XII
-- había cronistas monásticos en algunas regiones de Europa y prácticamente nada
-- en el resto del planeta. El aumento de eventos registrados mide **cobertura
-- documental**, no actividad geológica — que, en escalas de siglos, es
-- esencialmente constante.
--
-- Se construye igualmente porque el sesgo en sí es interesante y visualizable:
-- `pct_with_exact_deaths` sube de casi cero en la antigüedad a casi todo en el
-- siglo XX, y esa columna es la prueba directa del sesgo.
--
-- Cualquier gráfica basada en esta tabla debe llevar esa advertencia al lado.

CREATE OR REPLACE TABLE gold_disasters_by_century AS
SELECT
    century,
    hazard_type,
    count(*) AS events,
    sum(CASE WHEN has_exact_deaths THEN 1 ELSE 0 END) AS events_with_exact_deaths,
    round(
        100.0 * sum(CASE WHEN has_exact_deaths THEN 1 ELSE 0 END) / count(*), 1
    ) AS pct_with_exact_deaths,

    -- Suma solo sobre las filas con cifra exacta, y por eso va acompañada del
    -- recuento de filas que la componen: sin él parecería un total del siglo.
    sum(deaths_best) AS deaths_counted,
    max(deaths_best) AS deadliest_event_deaths,

    round(
        100.0 * sum(CASE WHEN date_precision = 'fecha completa' THEN 1 ELSE 0 END)
        / count(*), 1
    ) AS pct_full_date
FROM silver_historical_disasters
GROUP BY 1, 2
ORDER BY century, hazard_type;
