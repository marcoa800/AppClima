-- Una fila por ciclón, agregando su trayectoria completa.
--
-- Grano: sid.
--
-- IBTrACS almacena puntos cada 3-6 horas; esto los colapsa a la tormenta.
--
-- Sobre el ACE (Accumulated Cyclone Energy): es la métrica estándar de energía
-- ciclónica, definida como la suma de v² / 10.000 sobre las observaciones
-- SINÓPTICAS de 6 horas con viento ≥ 34 nudos. Mide intensidad y duración a la
-- vez, que es lo que la hace mejor que "número de tormentas": una temporada con
-- tres huracanes largos e intensos es más severa que una con ocho tormentas
-- débiles y fugaces, y el recuento simple no lo distingue.
--
-- El filtro `is_synoptic` no es cosmético. Sin él, las cuencas que reportan cada
-- 3 horas doblan su ACE frente a las que reportan cada 6, y la comparación
-- entre océanos queda invalidada.

CREATE OR REPLACE TABLE gold_cyclones AS
SELECT
    sid,
    any_value(season) AS season,
    any_value(basin) AS basin,
    any_value(subbasin) AS subbasin,
    max(name) AS name,

    min(time) AS first_seen,
    max(time) AS last_seen,
    round(date_diff('hour', min(time), max(time)) / 24.0, 2) AS duration_days,
    count(*) AS track_points,

    max(wind_kt) AS max_wind_kt,
    min(pressure_mb) AS min_pressure_mb,
    max(usa_sshs) AS max_category,

    -- ACE, solo sobre horas sinópticas y por encima del umbral de tormenta.
    round(sum(
        CASE WHEN is_synoptic AND wind_kt >= 34 THEN pow(wind_kt, 2) / 10000.0 END
    ), 4) AS ace,

    bool_or(is_tropical_storm) AS reached_tropical_storm,
    bool_or(is_hurricane) AS reached_hurricane,
    bool_or(usa_sshs >= 3) AS reached_major_hurricane,

    -- ¿Llegó a tocar tierra? dist2land = 0 significa que el centro estaba
    -- sobre tierra en ese instante.
    bool_or(dist2land_km = 0) AS made_landfall,
    min(dist2land_km) AS min_dist_to_land_km,

    -- Posición del momento de máxima intensidad, útil para mapear dónde se
    -- forman los ciclones más fuertes de cada cuenca.
    arg_max(lat, wind_kt) AS peak_lat,
    arg_max(lon, wind_kt) AS peak_lon,
    arg_max(time, wind_kt) AS peak_time
FROM silver_cyclone_tracks
GROUP BY sid;
