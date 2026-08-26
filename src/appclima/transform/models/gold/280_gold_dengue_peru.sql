-- Dengue en Perú: panel provincia-semana completo, emparejado con su clima.
--
-- Grano: (location_id, period_start). 12 provincias × 1.252 semanas = 15.024
-- filas, sin huecos.
--
-- Es la única tabla del proyecto que pone un **efecto sobre personas** y una
-- **causa física** en la misma fila y a la misma resolución temporal. Todo lo
-- demás mide el fenómeno; esto mide lo que el fenómeno le hace a la gente.
--
-- ══ El relleno de ceros, que es lo que decide si esta tabla sirve o miente ══
--
-- OpenDengue **no publica las semanas sin casos**: el mínimo de `cases` en
-- todo el dataset peruano es 1, nunca 0. Piura aparece con 779 semanas de las
-- 1.252 posibles.
--
-- Hay dos lecturas posibles y llevan a conclusiones opuestas:
--
--   (a) la semana ausente es un cero          → hay que rellenar
--   (b) la semana ausente es un boletín caído → hay que dejarla nula
--
-- Bajo (b), correlacionar clima y casos usando solo las semanas presentes
-- significaría **condicionar sobre el resultado**: se miraría únicamente las
-- semanas en las que hubo enfermos, que es el sesgo de selección de manual y
-- fabrica correlaciones de la nada.
--
-- El test que las distingue es la contigüidad. Una caída del sistema produce
-- un bloque de semanas seguidas; una racha de ceros produce semanas sueltas.
-- Piura en 2002 reportó 6 semanas: la 7, la 10, la 13, la 31, la 39 y la 46,
-- con **un caso cada una**. Dispersas por todo el año. Y en los años
-- epidémicos —2015, 2016, 2017, 2022, 2023— reporta las 52 sin fallar una.
-- Si el sistema se cayera, la avería no elegiría los años tranquilos.
--
-- Es (a). Se rellena con ceros explícitos.
--
-- ══ Un solo boletín ═════════════════════════════════════════════════════════
--
-- El envío `MOH-PER-20002023-Y02-00` cubre 115 provincias del 2000-01-02 al
-- 2023-12-30 con un calendario semanal común y semanas de 7 días exactos. Hay
-- otros dos envíos sueltos (2007 y 2008, tres provincias) que se ignoran: son
-- extracciones con completitud distinta y mezclarlas es el mismo error que
-- mezclar magnitudes sísmicas de catálogos con umbrales distintos.
--
-- ══ Un solo reanálisis ══════════════════════════════════════════════════════
--
-- `clima_completo` exige además que los siete días vengan del mismo modelo
-- (`era5_seamless`). Las semanas cuyo clima procede del IFS quedan con clima
-- nulo y desaparecen de todo lo que se modele — no se corrigen ni se mezclan.
-- Es la diferencia entre una ventana más corta y una ventana contaminada.
--
-- ══ Por qué provincia y no departamento ═════════════════════════════════════
--
-- Agregar por departamento sería una falacia ecológica con nombre y apellidos.
-- El departamento de Cusco acumula 13.106 casos, pero su capital está a
-- 3.399 m y allí el dengue no se transmite: los casos están en La Convención,
-- en la selva. Emparejarlos cruzaría la enfermedad de un sitio con el
-- termómetro de otro. Aquí solo se admite el par cuando la ciudad de AppClima
-- está DENTRO de la provincia que notifica.
--
-- Las seis provincias andinas y del sur se incluyen a pesar de tener ~0 casos,
-- o más bien **precisamente por eso**: un cero medido durante 24 años con
-- vigilancia activa es un dato, y es la mitad fría de la evidencia del umbral
-- térmico (ver 290_gold_dengue_temperature).

CREATE OR REPLACE TABLE gold_dengue_peru AS
WITH mapa(location_id, departamento, provincia) AS (
    VALUES
    -- Costa desértica norte: el foco histórico. Piura sola acumula el 13%
    -- de todos los casos del país.
    ('piura',    'PIURA',        'PIURA'),
    ('chiclayo', 'LAMBAYEQUE',   'CHICLAYO'),
    ('trujillo', 'LA LIBERTAD',  'TRUJILLO'),
    ('lima',     'LIMA',         'LIMA'),
    -- Amazonía: transmisión todo el año, sin estación fría que la corte.
    ('iquitos',  'LORETO',       'MAYNAS'),
    ('pucallpa', 'UCAYALI',      'CORONEL PORTILLO'),
    -- Sierra y sur: el control negativo.
    ('arequipa', 'AREQUIPA',     'AREQUIPA'),
    ('huaraz',   'ANCASH',       'HUARAZ'),
    ('huancayo', 'JUNIN',        'HUANCAYO'),
    ('cusco',    'CUSCO',        'CUSCO'),
    ('puno',     'PUNO',         'PUNO'),
    ('tacna',    'TACNA',        'TACNA'),
    -- Añadidas por epidemiología, no por clima: son las provincias con más
    -- casos del país que no tenían ninguna ciudad cerca. Llevan el panel de 6
    -- a 12 series con transmisión y la carga cubierta del 38% al 59%.
    -- Ojo con Morropón: la provincia se llama así pero su capital es
    -- Chulucanas, y confundirlas rompe el emparejamiento en silencio.
    ('sullana',          'PIURA',         'SULLANA'),
    ('tumbes',           'TUMBES',        'TUMBES'),
    ('talara',           'PIURA',         'TALARA'),
    ('chulucanas',       'PIURA',         'MORROPON'),
    ('jaen',             'CAJAMARCA',     'JAEN'),
    ('puerto-maldonado', 'MADRE DE DIOS', 'TAMBOPATA'),
    -- Segunda tanda. Ojo con los nombres: la ciudad y la provincia no siempre
    -- coinciden, y aquí un desliz no da error, da una fila menos en silencio.
    ('ica',         'ICA',        'ICA'),
    ('yurimaguas',  'LORETO',     'ALTO AMAZONAS'),
    ('la-merced',   'JUNIN',      'CHANCHAMAYO'),
    ('chimbote',    'ANCASH',     'SANTA'),
    ('lambayeque',  'LAMBAYEQUE', 'LAMBAYEQUE'),
    ('quillabamba', 'CUSCO',      'LA CONVENCION'),
    ('tarapoto',    'SAN MARTIN', 'SAN MARTIN'),
    ('chincha',     'ICA',        'CHINCHA'),
    ('paita',       'PIURA',      'PAITA'),
    ('satipo',      'JUNIN',      'SATIPO')
),

boletin AS (
    SELECT adm_2_name AS provincia, period_start, period_end, year, cases
    FROM silver_dengue
    WHERE uuid = 'MOH-PER-20002023-Y02-00'
      AND spatial_res = 'Admin2'
      AND temporal_res = 'Week'
),

-- El calendario del propio boletín, no uno reconstruido. Reindexar a semanas
-- ISO desplazaría los bordes y desalinearía los casos del clima.
calendario AS (
    SELECT DISTINCT period_start, period_end, year FROM boletin
),

-- La rejilla completa: toda provincia existe en toda semana del período.
rejilla AS (
    SELECT m.location_id, m.departamento, m.provincia,
           c.period_start, c.period_end, c.year
    FROM mapa m CROSS JOIN calendario c
),

clima AS (
    SELECT
        r.location_id,
        r.period_start,
        avg(w.temp_mean)     AS temp_media_c,
        avg(w.temp_min)      AS temp_min_c,
        avg(w.temp_max)      AS temp_max_c,
        sum(w.precip_sum)    AS precip_mm,
        avg(w.humidity_mean) AS humedad_pct,
        count(*)             AS dias_con_clima
    FROM rejilla r
    JOIN gold_weather_daily w
      ON w.location_id = r.location_id
     AND w.kind = 'observed'
     -- Un solo reanálisis, sin excepciones. El archivo de Open-Meteo por
     -- defecto cose ERA5 con el IFS de ECMWF en 2017, y ese salto entraría
     -- aquí como si fuera una señal climática. Filtrar por procedencia hace
     -- que la ventana analizable se amplíe sola conforme avanza el backfill,
     -- sin tocar este modelo.
     AND w.model = 'era5_seamless'
     AND NOT w.modelo_mixto
     AND w.local_date BETWEEN r.period_start AND r.period_end
    GROUP BY 1, 2
),

-- Una provincia que jamás notificó un caso en 24 años no es lo mismo que una
-- que notificó y luego dejó de hacerlo. La distinción se expone, no se entierra.
notificantes AS (
    SELECT provincia FROM boletin GROUP BY 1 HAVING sum(cases) > 0
)

SELECT
    r.location_id,
    r.departamento,
    r.provincia,
    r.period_start,
    r.period_end,
    r.year,

    -- Aquí ocurre el relleno. `b.cases` nulo significa semana sin casos.
    coalesce(b.cases, 0)                        AS casos,
    b.cases IS NOT NULL                         AS notificada,
    n.provincia IS NOT NULL                     AS provincia_notificante,

    c.temp_media_c,
    c.temp_min_c,
    c.temp_max_c,
    c.precip_mm,
    c.humedad_pct,

    -- Una semana con menos de 7 días de ERA5 está incompleta y su media
    -- térmica no es comparable con la de una semana entera. ERA5 arranca en
    -- 2006, así que 2000-2005 sale con clima nulo — se conserva porque
    -- describe la epidemiología aunque no sirva para modelar.
    coalesce(c.dias_con_clima, 0) = 7           AS clima_completo,

    week(r.period_start)                        AS semana_iso

FROM rejilla r
LEFT JOIN boletin b
       ON b.provincia = r.provincia AND b.period_start = r.period_start
LEFT JOIN clima c
       ON c.location_id = r.location_id AND c.period_start = r.period_start
LEFT JOIN notificantes n ON n.provincia = r.provincia
ORDER BY r.location_id, r.period_start;
