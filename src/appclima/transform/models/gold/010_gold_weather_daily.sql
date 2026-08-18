-- Agregados diarios por ubicación.
--
-- Grano: (location_id, local_date, kind).
--
-- El detalle que hace esto correcto: agrupamos por **día LOCAL**, no por día
-- UTC. Para Tokio (UTC+9) un "día UTC" empieza a las 09:00 de la mañana local,
-- así que la temperatura máxima diaria calculada sobre días UTC mezclaría dos
-- tardes distintas. Con 49 ciudades repartidas en 24 husos, ignorar esto
-- corrompe todos los máximos y mínimos.
--
-- Por eso dim_locations lleva la zona IANA: `timezone(zona, instante)` convierte
-- el TIMESTAMPTZ a la hora de pared local, y de ahí sacamos la fecha.
--
-- El HAVING descarta días parciales. Aparecen inevitablemente en los bordes de
-- cada rango descargado, y un día con 6 horas de datos daría una "máxima
-- diaria" que no es una máxima diaria. 20 horas es el umbral: deja pasar los
-- días de 23 horas del cambio de hora, y corta los recortados de verdad.

CREATE OR REPLACE TABLE gold_weather_daily AS
SELECT
    w.location_id,
    timezone(l.timezone, w.time)::DATE AS local_date,
    w.kind,
    count(*) AS hours,

    round(avg(w.temperature_2m), 2) AS temp_mean,
    round(min(w.temperature_2m), 2) AS temp_min,
    round(max(w.temperature_2m), 2) AS temp_max,
    round(max(w.temperature_2m) - min(w.temperature_2m), 2) AS temp_range,

    round(min(w.apparent_temperature), 2) AS apparent_min,
    round(max(w.apparent_temperature), 2) AS apparent_max,

    round(sum(w.precipitation), 2) AS precip_sum,
    round(avg(w.pressure_msl), 2) AS pressure_msl_mean,
    round(min(w.pressure_msl), 2) AS pressure_msl_min,
    round(avg(w.surface_pressure), 2) AS surface_pressure_mean,

    round(avg(w.relative_humidity_2m), 1) AS humidity_mean,
    round(avg(w.cloud_cover), 1) AS cloud_cover_mean,
    round(max(w.wind_gusts_10m), 1) AS wind_gust_max,
    round(sum(w.shortwave_radiation), 1) AS radiation_sum
FROM silver_weather_hourly w
JOIN dim_locations l ON l.id = w.location_id
GROUP BY 1, 2, 3
HAVING count(*) >= 20;
