-- Contraste del mito del "clima sísmico".
--
-- Grano: location_id (más una fila 'POOLED' con todo agrupado).
--
-- Existe una creencia extendida de que los terremotos son más probables con
-- determinadas condiciones atmosféricas: "tiempo de terremotos", calor
-- bochornoso, caída de presión. Aparece en prensa y en redes cada vez que hay un
-- sismo notable.
--
-- Este modelo lo contrasta con nuestros propios datos: para cada ciudad, cuenta
-- los sismos diarios en un radio de 500 km y los correlaciona con la presión
-- atmosférica media de ese día.
--
-- La expectativa física es correlación nula. Los sismos se originan a
-- kilómetros de profundidad, por acumulación de esfuerzo tectónico a lo largo de
-- décadas o siglos. Las variaciones de presión atmosférica son de ~2 kPa, unas
-- cinco órdenes de magnitud menores que los esfuerzos que rompen una falla.
--
-- Y ese es exactamente el valor de este modelo. **Un resultado nulo bien medido
-- es un resultado.** Publicar "no encontramos correlación, aquí está el r y el
-- tamaño de muestra" es mejor ingeniería de datos que buscar en veinte
-- variables hasta que una dé p<0,05 por azar.
--
-- Limitaciones que hay que declarar al presentarlo:
--   - Solo hay clima observado para las ciudades flagship
--   - Radio de 500 km y agregación diaria son elecciones arbitrarias
--   - La correlación de Pearson solo detecta relación lineal
--   - Con muchas ciudades, alguna dará |r| aparentemente alto por puro azar:
--     ahí está `n_days` para juzgarlo

CREATE OR REPLACE TABLE gold_quake_pressure_test AS
WITH quakes_per_city_day AS (
    SELECT
        l.id AS location_id,
        timezone(l.timezone, q.time)::DATE AS local_date,
        count(*) AS quakes
    FROM dim_locations l
    JOIN silver_earthquakes q
      ON haversine_km(l.lat, l.lon, q.lat, q.lon) <= 500
    GROUP BY 1, 2
),
joined AS (
    SELECT
        d.location_id,
        d.local_date,
        d.pressure_msl_mean,
        d.temp_mean,
        -- Los días sin sismos son datos, no ausencia de datos. Omitirlos
        -- (usando INNER JOIN) sería el error que fabricaría una correlación
        -- falsa: solo se mirarían los días en que sí tembló.
        coalesce(q.quakes, 0) AS quakes
    FROM gold_weather_daily d
    LEFT JOIN quakes_per_city_day q
      ON q.location_id = d.location_id
     AND q.local_date = d.local_date
    WHERE d.kind = 'observed'
      AND d.pressure_msl_mean IS NOT NULL
),
per_city AS (
    SELECT
        location_id,
        count(*) AS n_days,
        sum(quakes) AS total_quakes,
        round(100.0 * sum(CASE WHEN quakes > 0 THEN 1 ELSE 0 END) / count(*), 1)
            AS pct_days_with_quake,
        round(corr(quakes, pressure_msl_mean), 4) AS r_pressure,
        round(corr(quakes, temp_mean), 4) AS r_temperature
    FROM joined
    GROUP BY 1
),
pooled AS (
    SELECT
        'POOLED' AS location_id,
        count(*) AS n_days,
        sum(quakes) AS total_quakes,
        round(100.0 * sum(CASE WHEN quakes > 0 THEN 1 ELSE 0 END) / count(*), 1)
            AS pct_days_with_quake,
        round(corr(quakes, pressure_msl_mean), 4) AS r_pressure,
        round(corr(quakes, temp_mean), 4) AS r_temperature
    FROM joined
)
SELECT
    *,
    -- Umbral aproximado de significación al 5% para r: 1,96/√n. Es una
    -- aproximación normal, válida con n grande, que es nuestro caso.
    round(1.96 / sqrt(n_days), 4) AS r_significance_threshold,
    abs(r_pressure) > 1.96 / sqrt(n_days) AS pressure_significant,

    -- Y aquí la columna que desmonta la anterior.
    --
    -- Con más de doscientos mil días-ciudad, el umbral de significación baja
    -- por debajo de r = 0,005. Eso
    -- significa que una correlación de 0,012 sale "estadísticamente
    -- significativa" — y explica menos del 0,1% de la varianza. Es decir: nada.
    --
    -- Los valores exactos NO se escriben aquí a propósito: crecen con el
    -- catálogo. Este comentario decía 87.654 días y 0,014%, ciertos con 49
    -- ciudades y falsos con 66, sin que nada avisara. La columna
    -- `pct_variance_explained` lleva la cifra viva; el comentario solo el
    -- orden de magnitud, que sí aguanta.
    --
    -- Es la trampa clásica de la muestra gigante: la significación estadística
    -- mide "¿es distinto de cero?", no "¿importa?". Con suficientes datos,
    -- cualquier cosa es distinta de cero. r² es lo que responde a la pregunta
    -- que de verdad interesa, y por eso va al lado, no escondido.
    round(100 * pow(r_pressure, 2), 4) AS pct_variance_explained
FROM (SELECT * FROM per_city WHERE total_quakes >= 30 UNION ALL SELECT * FROM pooled)
ORDER BY total_quakes DESC;
