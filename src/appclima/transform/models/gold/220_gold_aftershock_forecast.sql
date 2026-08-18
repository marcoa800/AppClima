-- Pronóstico de réplicas: la única señal del proyecto que es producto.
--
-- Grano: mainshock_id.
--
-- Pregunta: 24 horas después de un sismo M≥6.5, ¿cuántas réplicas M≥4.5 habrá
-- entre los días 2 y 8?
--
-- El modelo entero es una constante: y ≈ alpha × n1, donde n1 son las réplicas
-- del primer día. No hay ajuste de Omori que almacenar ni parámetros por
-- región. Que algo tan simple bata a la media histórica por un 45% dice más de
-- lo informativas que son las primeras 24 horas que de la sofisticación del
-- método.
--
-- **DECLUSTERIZACIÓN.** Es la corrección que impuso la verificación adversarial.
-- Sin ella, 19 de 191 "sismos principales" del conjunto de prueba eran en
-- realidad réplicas de otro M≥6.5 mayor ocurrido antes y cerca: el M7.5 de
-- Elbistan dentro de la secuencia de Kahramanmaraş, tres eventos de Kamchatka
-- dentro del M8.8. Sus réplicas se contaban dos veces, en su propia fila y en la
-- del principal de verdad, inflando la habilidad medida.
--
-- La ventana es de 90 días, no de 30: una secuencia grande sigue produciendo
-- M≥6.5 mucho después del mes.
--
-- LÍMITE HONESTO DE PRODUCCIÓN: esto se entrena con el catálogo REVISADO. En
-- tiempo real, a t+24 h, USGS todavía no ha revisado el 99,6% de los eventos, y
-- `n1` será menor. Cualquier cifra de habilidad de aquí es un techo optimista
-- hasta que se capture el catálogo tal como se ve a las 24 horas.

CREATE OR REPLACE TABLE gold_aftershock_forecast AS
WITH mainshocks AS (
    SELECT event_id, time, magnitude, lat, lon, place, depth_km
    FROM silver_earthquakes
    WHERE magnitude >= 6.5
),
-- Un principal es INDEPENDIENTE si no hay otro mayor poco antes y cerca.
independent AS (
    SELECT m.*
    FROM mainshocks m
    WHERE NOT EXISTS (
        SELECT 1 FROM mainshocks p
        WHERE p.event_id <> m.event_id
          AND p.magnitude > m.magnitude
          AND p.time < m.time
          AND p.time >= m.time - INTERVAL 90 DAY
          AND haversine_km(p.lat, p.lon, m.lat, m.lon) <= 150
    )
),
counts AS (
    SELECT
        i.event_id AS mainshock_id,
        i.time AS mainshock_time,
        i.magnitude AS mainshock_mag,
        i.lat, i.lon, i.place, i.depth_km,
        year(i.time) AS year,
        -- OJO: gold_quake_sequences ya viene AGREGADA por (principal, día),
        -- con el recuento en la columna `aftershocks`. Un count(*) aquí cuenta
        -- FILAS, es decir días distintos con actividad — no réplicas.
        --
        -- Ese fue exactamente el bug de la primera versión: n1 salía siempre 0
        -- o 1, y el objetivo nunca pasaba de 7 (los días 2 a 8). Kamchatka M8.8,
        -- con 552 réplicas reales, figuraba con 7. El modelo salía un 11% PEOR
        -- que la línea base y la conclusión habría sido "esto no funciona",
        -- cuando lo que no funcionaba era la consulta.
        --
        -- Lo delató que el máximo de todo el dataset fuera exactamente 7.
        sum(s.aftershocks) FILTER (WHERE s.day_after = 1) AS n1,
        sum(s.aftershocks) FILTER (WHERE s.day_after BETWEEN 2 AND 8) AS y_days_2_8
    FROM independent i
    LEFT JOIN gold_quake_sequences s ON s.mainshock_id = i.event_id
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
)
SELECT
    *,
    -- Banda de magnitud, para la línea base "media histórica por magnitud".
    CASE
        WHEN mainshock_mag >= 8.0 THEN 'M8+'
        WHEN mainshock_mag >= 7.5 THEN 'M7.5-7.9'
        WHEN mainshock_mag >= 7.0 THEN 'M7.0-7.4'
        ELSE 'M6.5-6.9'
    END AS mag_band,
    -- Solo los eventos con actividad el primer día son predecibles: con n1 = 0
    -- no hay nada de lo que partir, y el modelo no debe pronunciarse.
    coalesce(n1, 0) > 0 AS is_predictable
FROM counts
ORDER BY mainshock_time DESC;
