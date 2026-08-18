-- Sismos asociados a cada ciudad ancla, con distancia calculada.
--
-- Grano: (location_id, event_id).
--
-- Es el modelo que alimenta la parte "app": qué ha temblado cerca de aquí y a
-- qué distancia. Un mismo sismo aparece en varias filas si hay varias ciudades
-- en su radio, lo cual es correcto: la pregunta es por ciudad.
--
-- El radio de 700 km es generoso a propósito. Un M7 se percibe a cientos de
-- kilómetros, y para una app importa "¿me afecta?" más que "¿fue justo aquí?".
-- Quien quiera un radio menor filtra por distance_km, que va expuesto.

CREATE OR REPLACE TABLE gold_quakes_near_city AS
SELECT
    l.id AS location_id,
    l.name AS location_name,
    l.country,
    q.event_id,
    q.time,
    q.magnitude,
    q.magnitude_type,
    q.depth_km,
    q.depth_class,
    q.place,
    q.tsunami,
    q.alert,
    q.significance,
    q.url,
    round(haversine_km(l.lat, l.lon, q.lat, q.lon), 1) AS distance_km,
    q.lat,
    q.lon,
    -- Hora local de la ciudad. Para un usuario, "tembló a las 3 de la mañana"
    -- es más útil que un instante UTC.
    timezone(l.timezone, q.time) AS local_time
FROM dim_locations l
JOIN silver_earthquakes q
  ON haversine_km(l.lat, l.lon, q.lat, q.lon) <= 700;
