-- Clima horario limpio y deduplicado.
--
-- Grano: (location_id, time, kind).
--
-- La decisión de diseño importante está en incluir `kind` en el grano. Podría
-- deduplicarse a (location_id, time) dando prioridad al dato observado sobre el
-- pronóstico, pero eso escondería una decisión discutible dentro de silver.
--
-- Peor aún: el archivo histórico se ingiere con solo 5 variables (CORE) y el
-- pronóstico con las 14. Colapsar por (location_id, time) prefiriendo observed
-- perdería silenciosamente humedad, viento y radiación en las horas que
-- existen en ambos. Manteniendo `kind` en el grano no se pierde nada, y es gold
-- quien elige — a la vista de todos.
--
-- Dentro de un mismo kind sí deduplicamos: bronze es append-only, así que
-- reejecutar el cron el mismo día genera filas repetidas. Gana la más reciente.

CREATE OR REPLACE TABLE silver_weather_hourly AS
WITH ranked AS (
    SELECT
        location_id,
        time,
        kind,
        temperature_2m,
        apparent_temperature,
        relative_humidity_2m,
        dew_point_2m,
        precipitation,
        rain,
        snowfall,
        pressure_msl,
        surface_pressure,
        cloud_cover,
        wind_speed_10m,
        wind_direction_10m,
        wind_gusts_10m,
        shortwave_radiation,
        _ingested_at,
        row_number() OVER (
            PARTITION BY location_id, time, kind
            ORDER BY _ingested_at DESC
        ) AS _rn
    FROM {{bronze_weather}}
    -- Una fila sin temperatura no aporta nada a ningún análisis climático.
    WHERE temperature_2m IS NOT NULL
)
SELECT * EXCLUDE (_rn)
FROM ranked
WHERE _rn = 1;
