-- Ciclones que pasaron cerca de cada ciudad ancla.
--
-- Grano: (location_id, sid).
--
-- **Este es el modelo que justifica tener clima y ciclones en el mismo
-- warehouse.** Hasta aquí eran dos datasets sin relación; el cruce geográfico
-- los convierte en una sola pregunta respondible: qué tormentas pasaron por
-- aquí, con qué intensidad, y qué tiempo hizo esos días.
--
-- Se calcula la distancia mínima de la trayectoria completa a la ciudad, no la
-- distancia del punto de máxima intensidad. Un huracán que alcanza su pico en
-- mitad del océano y llega debilitado a la costa afecta a esa costa con la
-- intensidad que traía AL PASAR, que es lo que se guarda en
-- `wind_at_closest_kt`. Confundir ambas cosas sobrestima el impacto local.
--
-- 500 km es un radio generoso a propósito: el viento y sobre todo la lluvia de
-- un ciclón se extienden muy por delante de su centro.

CREATE OR REPLACE TABLE gold_cyclones_near_city AS
WITH proximity AS (
    SELECT
        l.id AS location_id,
        l.name AS location_name,
        t.sid,
        haversine_km(l.lat, l.lon, t.lat, t.lon) AS distance_km,
        t.time,
        t.wind_kt,
        t.pressure_mb,
        t.usa_sshs
    FROM dim_locations l
    JOIN silver_cyclone_tracks t
      ON haversine_km(l.lat, l.lon, t.lat, t.lon) <= 500
),
closest AS (
    SELECT
        location_id,
        location_name,
        sid,
        min(distance_km) AS min_distance_km,
        -- Intensidad en el punto más cercano, no la máxima de la tormenta.
        arg_min(wind_kt, distance_km) AS wind_at_closest_kt,
        arg_min(pressure_mb, distance_km) AS pressure_at_closest_mb,
        arg_min(usa_sshs, distance_km) AS category_at_closest,
        arg_min(time, distance_km) AS closest_time
    FROM proximity
    GROUP BY 1, 2, 3
)
SELECT
    c.location_id,
    c.location_name,
    c.sid,
    g.name AS storm_name,
    g.season,
    g.basin,
    c.min_distance_km,
    c.closest_time,
    c.wind_at_closest_kt,
    c.pressure_at_closest_mb,
    c.category_at_closest,
    -- Máxima de la tormenta en toda su vida, para contrastar con la de paso.
    g.max_wind_kt AS storm_max_wind_kt,
    g.max_category AS storm_max_category,
    g.ace AS storm_ace,
    -- Fecha local de la ciudad, que es la que permite unir con el clima diario.
    timezone(l.timezone, c.closest_time)::DATE AS local_date
FROM closest c
JOIN gold_cyclones g ON g.sid = c.sid
JOIN dim_locations l ON l.id = c.location_id
ORDER BY c.location_id, c.closest_time DESC;
