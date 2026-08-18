-- Riqueza de especies diaria, cruzada con el clima del mismo día.
--
-- Grano: (location_id, obs_date).
--
-- Es la primera piedra del análisis clima-aves. Cuenta especies distintas
-- observadas por ciudad y día, y las une con la temperatura y precipitación
-- correspondientes.
--
-- AVISO METODOLÓGICO, y es grande: la riqueza medida aquí depende tanto del
-- esfuerzo de observación como de las aves presentes. Un domingo soleado de
-- mayo hay mucha gente en el campo; un martes lluvioso de noviembre, casi
-- nadie. Eso genera por sí solo una correlación positiva entre buen tiempo y
-- "más especies" que **no dice nada sobre las aves** — dice que a la gente no
-- le gusta salir con lluvia.
--
-- Para separar las dos cosas hace falta normalizar por esfuerzo: número de
-- checklists, horas de observación, o el protocolo completo de eBird. Por eso
-- `checklists` está expuesto aquí, para poder dividir después.
--
-- Y una limitación de la fuente: el endpoint que usamos devuelve solo la
-- observación más reciente por especie, no el histórico completo. Esta tabla
-- sirve para "qué hay ahora", no para series largas. Para fenología de verdad
-- (¿llegan las aves antes que hace 30 años?) hace falta GBIF o las descargas
-- masivas de eBird.
--
-- Sobre el join con el clima: las observaciones son SIEMPRE recientes (máximo 30
-- días atrás), y para esas fechas el reanálisis ERA5 todavía no existe — tiene
-- unos 5 días de latencia y nuestro archivo llega a 2025. Lo único disponible
-- ahí es el pronóstico, incluidos sus días de pasado reciente.
--
-- Unir solo contra `kind = 'observed'` dejaba TODAS las columnas de clima a
-- NULL, y el cruce clima-aves no funcionaba en absoluto. Ahora se prefiere el
-- dato observado y se cae al pronóstico cuando no lo hay, marcando cuál se usó
-- en `weather_kind` — porque mezclar reanálisis y pronóstico sin decirlo es
-- justo lo que este proyecto evita en todas partes.

CREATE OR REPLACE TABLE gold_bird_daily AS
SELECT
    b.location_id,
    b.obs_datetime::DATE AS obs_date,

    count(DISTINCT b.species_code) AS species_richness,
    count(*) AS observations,
    count(DISTINCT b.checklist_id) AS checklists,

    -- Solo suma donde hubo recuento. Los NULL de how_many significan "vista
    -- pero no contada", y tratarlos como 0 hundiría el total.
    sum(b.how_many) AS individuals_counted,
    count(b.how_many) AS observations_with_count,

    d.temp_mean,
    d.temp_min,
    d.temp_max,
    d.precip_sum,
    d.kind AS weather_kind,
    a.anomaly_c AS temp_anomaly_c
FROM silver_bird_observations b
LEFT JOIN (
    -- Una fila por ubicación y día, prefiriendo observado sobre pronóstico.
    SELECT * EXCLUDE (_pref) FROM (
        SELECT *,
               row_number() OVER (
                   PARTITION BY location_id, local_date
                   ORDER BY CASE WHEN kind = 'observed' THEN 0 ELSE 1 END
               ) AS _pref
        FROM gold_weather_daily
    ) WHERE _pref = 1
) d
  ON d.location_id = b.location_id
 AND d.local_date = b.obs_datetime::DATE
LEFT JOIN (
    SELECT * EXCLUDE (_pref) FROM (
        SELECT *,
               row_number() OVER (
                   PARTITION BY location_id, local_date
                   ORDER BY CASE WHEN kind = 'observed' THEN 0 ELSE 1 END
               ) AS _pref
        FROM gold_temperature_anomaly
    ) WHERE _pref = 1
) a
  ON a.location_id = b.location_id
 AND a.local_date = b.obs_datetime::DATE
GROUP BY 1, 2, d.temp_mean, d.temp_min, d.temp_max, d.precip_sum, d.kind,
         a.anomaly_c;
