-- Secuencias de réplicas: la ley de Omori.
--
-- Grano: (mainshock_id, day_after).
--
-- Tras un sismo grande, la frecuencia de réplicas decae según:
--
--     n(t) = K / (t + c)^p
--
-- con p típicamente entre 0,9 y 1,4. En la práctica esto significa que el
-- segundo día hay aproximadamente la mitad de réplicas que el primero, el
-- cuarto la mitad que el segundo, y así. Es un decaimiento hiperbólico, no
-- exponencial: la cola es larga y las réplicas siguen durante meses.
--
-- Definición operativa usada aquí: réplica = cualquier evento de magnitud ≥ 4.5
-- en los 30 días siguientes, a menos de 150 km, y de magnitud menor que el
-- principal.
--
-- Ese corte en 4.5 es la corrección más importante del modelo, y no es
-- cosmética. Nuestro catálogo tiene **dos umbrales de completitud distintos**:
-- el histórico se ingirió con M≥4.5, pero la ingesta diaria reciente usa M≥2.5.
-- Sin filtrar, un sismo de la última semana mostraría muchísimas más réplicas
-- que uno de 2019 — no porque tuviera más, sino porque de él vemos los eventos
-- pequeños y del antiguo no.
--
-- Es un caso de libro de sesgo de detección, y de los que pasan inadvertidos
-- porque el resultado "parece" razonable. Homogeneizar en 4.5 sacrifica detalle
-- en las secuencias recientes y gana la única cosa que importaba: que las
-- secuencias sean comparables entre sí.
--
-- AVISO para quien vaya a ajustar la curva: esta tabla **no rellena los días
-- con cero réplicas**. Un GROUP BY solo produce filas donde hubo algo, así que
-- una secuencia que no tuvo réplicas el día 8 simplemente no tiene fila de día
-- 8. Promediar `aftershocks` por día sobre esta tabla sobrestima la cola,
-- porque solo entran en la media las secuencias que seguían activas.
--
-- Para ajustar p correctamente hay que hacer un cross join contra los 30 días y
-- rellenar los huecos con cero. Se deja fuera a propósito: multiplicaría las
-- filas por diez y la mayoría serían ceros.
--
-- Es una definición espacio-temporal simple y transparente. Los métodos
-- rigurosos (ventanas de Gardner-Knopoff, o el modelo ETAS) escalan el radio
-- con la magnitud del principal y modelan el disparo en cascada. Para ver el
-- decaimiento de Omori esta aproximación basta, pero conviene saber que
-- sobrecuenta en zonas de sismicidad de fondo alta como Indonesia o Japón,
-- donde parte de lo que contamos como réplica habría ocurrido igualmente.

CREATE OR REPLACE TABLE gold_quake_sequences AS
WITH mainshocks AS (
    SELECT event_id, time, magnitude, lat, lon, place, depth_km
    FROM silver_earthquakes
    WHERE magnitude >= 6.5
),
pairs AS (
    SELECT
        m.event_id AS mainshock_id,
        m.place AS mainshock_place,
        m.magnitude AS mainshock_mag,
        m.time AS mainshock_time,
        a.magnitude AS aftershock_mag,
        -- Día 1 = las primeras 24 horas. Empezar en 0 complicaría el ajuste
        -- logarítmico de Omori sin aportar nada.
        --
        -- OJO CON EL OPERADOR: `//` es división ENTERA. Con `/` (flotante) y un
        -- casteo a INTEGER, DuckDB REDONDEA en lugar de truncar, y el día 1
        -- pasaba a cubrir solo las horas 0-12 mientras el día 2 cubría de la 13
        -- a la 35. Es decir: un primer día de 13 horas y un segundo de 23.
        --
        -- El efecto era insidioso porque la curva SEGUÍA pareciendo un
        -- decaimiento de Omori razonable — solo que con el primer punto
        -- artificialmente bajo, que es justo el que más pesa al ajustar p.
        --
        -- Es el mismo bug que ya apareció en el cálculo del siglo. Allí se
        -- arregló la instancia y no la clase; ahora hay un test que barre
        -- TODOS los modelos SQL buscando este patrón.
        (date_diff('hour', m.time, a.time) // 24) + 1 AS day_after
    FROM mainshocks m
    JOIN silver_earthquakes a
      ON a.time > m.time
     AND a.time <= m.time + INTERVAL 30 DAY
     AND a.event_id <> m.event_id
     AND a.magnitude < m.magnitude
     -- Magnitud de completitud homogénea. Ver la cabecera: sin esto las
     -- secuencias recientes se inflan frente a las históricas.
     AND a.magnitude >= 4.5
     AND haversine_km(m.lat, m.lon, a.lat, a.lon) <= 150
)
SELECT
    mainshock_id,
    mainshock_place,
    mainshock_mag,
    mainshock_time,
    day_after,
    count(*) AS aftershocks,
    round(max(aftershock_mag), 1) AS max_aftershock_mag,
    -- Total de la secuencia, repetido en cada fila para poder ordenar y filtrar
    -- sin un segundo join.
    sum(count(*)) OVER (PARTITION BY mainshock_id) AS sequence_total
FROM pairs
GROUP BY 1, 2, 3, 4, 5
ORDER BY sequence_total DESC, day_after;
