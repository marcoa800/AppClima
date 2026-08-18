-- Los desastres naturales más mortales de los que existe registro.
--
-- Grano: (hazard_type, source_id), ordenado por muertes.
--
-- Solo entran filas con cifra exacta. Los registros que únicamente tienen orden
-- de magnitud quedan fuera de este ranking a propósito: mezclar "muchísimos
-- (>1000)" con "242.769" en una misma columna ordenable produciría un orden
-- inventado. Esos eventos siguen en silver y se cuentan aparte.
--
-- **Deduplicación de cascadas.** NOAA registra en el tsunami el `deathsTotal`
-- del evento COMPLETO, no las muertes del tsunami por separado. Consecuencia:
-- Haití 2010 aparecía dos veces con 316.000 muertes cada vez, una como sismo y
-- otra como tsunami, y lo mismo Antioquía 115 y China 1920. Cualquier suma por
-- tipo de peligro quedaba inflada, y el ranking mostraba el mismo desastre
-- duplicado en filas consecutivas.
--
-- La regla: cuando un tsunami está enlazado a un desencadenante que ya está en
-- la tabla, el evento canónico es el DESENCADENANTE. El tsunami no desaparece —
-- pasa a ser un atributo suyo (`generated_tsunami`, `tsunami_wave_m`), que es lo
-- que realmente es.
--
-- La regla vale para las DOS familias de cascada, y no siempre fue así. La
-- primera versión solo deduplicaba sismo→tsunami, y las cascadas VOLCÁNICAS
-- seguían duplicadas: Tambora 1815 (60.000 muertes), Krakatoa 1883 (36.417),
-- el Pelée de 1902 (28.000) y hasta el Vesubio del año 79 aparecían dos veces,
-- una como erupción y otra como tsunami, con la cifra íntegra en ambas. Las
-- erupciones más famosas de la historia, contadas por duplicado.
--
-- Lo encontró una verificación adversarial, no una revisión del código: es
-- otro caso de arreglar la instancia sin arreglar la clase.
--
-- Los tsunamis sin desencadenante enlazado (por deslizamiento, o cuya causa no
-- se codificó) se conservan como eventos propios.
--
-- **Duplicados sin enlace: se marcan, no se borran.** La deduplicación anterior
-- depende de que NOAA haya codificado el id de la cascada, y para eventos
-- antiguos a menudo no lo hizo. Quedan pares como el terremoto de Siria de 1752
-- y el tsunami de Latakia (20.000 muertes cada uno), o el Etna de 1169 y el
-- sismo de Siracusa (16.000): misma catástrofe, dos filas, sin enlace.
--
-- El criterio para señalarlos es proximidad: mismo año, misma cifra de muertes
-- y menos de 200 km. Eso distingue el caso real del falso positivo — en el año
-- 856 hay un sismo en Túnez y otro en Grecia, ambos con 45.000 muertes
-- redondeadas, pero a 1.500 km: son eventos distintos y no deben marcarse.
--
-- Se marcan y NO se eliminan a propósito. Borrar exigiría decidir cuál de los
-- dos es el canónico sin más información que la que ya se agotó, y un dato
-- dudoso visible vale más que uno desaparecido en silencio.
--
-- Sesgo que hay que declarar siempre que se muestre esta tabla: **el registro
-- histórico está brutalmente sesgado hacia el presente y hacia Occidente**. Un
-- terremoto del año 1200 en una región sin cronistas simplemente no está. Esta
-- tabla lista los desastres mejor DOCUMENTADOS, no los más mortales que hayan
-- ocurrido.

CREATE OR REPLACE TABLE gold_disasters_ranked AS
WITH quakes AS (
    SELECT source_id, deaths_best, tsunami_max_water_height_m
    FROM silver_historical_disasters
    WHERE hazard_type = 'earthquake'
),
-- Tsunamis que son la misma tragedia ya contada en su desencadenante,
-- sea sismo o volcán.
redundant_tsunamis AS (
    SELECT t.source_id
    FROM silver_historical_disasters t
    JOIN quakes q ON q.source_id = t.caused_earthquake_id
    WHERE t.hazard_type = 'tsunami'
      AND t.deaths_best IS NOT DISTINCT FROM q.deaths_best

    UNION

    SELECT t.source_id
    FROM silver_historical_disasters v
    JOIN silver_historical_disasters t
      ON t.hazard_type = 'tsunami' AND t.source_id = v.caused_tsunami_id
    WHERE v.hazard_type = 'volcano'
      AND t.deaths_best IS NOT DISTINCT FROM v.deaths_best
),
-- Qué volcanes generaron tsunami, para marcarlo en su fila igual que se hace
-- con los sismos.
volcano_tsunamis AS (
    SELECT v.source_id AS volcano_id,
           max(t.tsunami_max_water_height_m) AS wave_m
    FROM silver_historical_disasters v
    JOIN silver_historical_disasters t
      ON t.hazard_type = 'tsunami' AND t.source_id = v.caused_tsunami_id
    WHERE v.hazard_type = 'volcano'
    GROUP BY 1
),
-- Qué sismos generaron tsunami, para poder marcarlo en su fila.
quake_tsunamis AS (
    SELECT caused_earthquake_id AS quake_id,
           max(tsunami_max_water_height_m) AS wave_m
    FROM silver_historical_disasters
    WHERE hazard_type = 'tsunami' AND caused_earthquake_id IS NOT NULL
    GROUP BY 1
)
SELECT
    d.hazard_type,
    d.source_id,
    d.year,
    d.month,
    d.day,
    d.event_date,
    d.date_precision,
    d.century,
    d.country,
    d.location_name,
    d.latitude,
    d.longitude,

    d.deaths_best AS deaths,
    d.deaths AS deaths_direct,
    d.deaths_total,

    -- Cuántas muertes aportó el peligro SECUNDARIO. En Krakatoa 1883 la
    -- erupción mató a 2.000 y el tsunami que provocó a 34.417 más: el 95% del
    -- total. Es la columna que justifica el modelo de cascadas.
    CASE
        WHEN d.deaths_total IS NOT NULL AND d.deaths IS NOT NULL
        THEN d.deaths_total - d.deaths
    END AS deaths_from_cascade,

    d.injuries_total,
    d.damage_musd_total AS damage_musd,
    d.houses_destroyed,

    d.eq_magnitude,
    d.eq_depth_km,
    d.eq_intensity,
    d.tsunami_max_water_height_m,
    d.tsunami_num_runups,
    d.volcano_vei,
    d.volcano_name,

    d.caused_earthquake_id,
    d.caused_tsunami_id,

    -- El tsunami deja de ser una fila y pasa a ser un atributo del sismo, que
    -- es lo que la fuente realmente está diciendo.
    (qt.quake_id IS NOT NULL OR vt.volcano_id IS NOT NULL) AS generated_tsunami,
    coalesce(d.tsunami_max_water_height_m, qt.wave_m, vt.wave_m) AS tsunami_wave_m,

    -- ¿Hay otro evento que probablemente sea esta misma catástrofe?
    --
    -- La comparación se hace contra los eventos que SOBREVIVEN a la
    -- deduplicación, no contra silver entero. Es una distinción que costó una
    -- lectura equivocada: al comparar contra silver, un sismo cuya cascada ya
    -- se había resuelto correctamente seguía viendo a su propio tsunami —
    -- excluido de esta tabla pero presente en silver— y se marcaba a sí mismo.
    -- El resultado era un 24% de filas señaladas, cifra que no significaba
    -- nada porque medía sobre todo las cascadas YA arregladas.
    EXISTS (
        SELECT 1 FROM silver_historical_disasters o
        WHERE o.year = d.year
          AND o.deaths_best = d.deaths_best
          AND o.deaths_best IS NOT NULL
          AND NOT (o.hazard_type = d.hazard_type AND o.source_id = d.source_id)
          AND NOT (
              o.hazard_type = 'tsunami'
              AND o.source_id IN (SELECT source_id FROM redundant_tsunamis)
          )
          AND o.latitude IS NOT NULL AND d.latitude IS NOT NULL
          AND haversine_km(d.latitude, d.longitude, o.latitude, o.longitude) <= 200
    ) AS suspected_duplicate
FROM silver_historical_disasters d
LEFT JOIN quake_tsunamis qt
       ON d.hazard_type = 'earthquake' AND qt.quake_id = d.source_id
LEFT JOIN volcano_tsunamis vt
       ON d.hazard_type = 'volcano' AND vt.volcano_id = d.source_id
WHERE d.has_exact_deaths
  AND d.deaths_best > 0
  AND NOT (
      d.hazard_type = 'tsunami'
      AND d.source_id IN (SELECT source_id FROM redundant_tsunamis)
  )
ORDER BY d.deaths_best DESC;
