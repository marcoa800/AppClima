-- Vigilancia de dengue (OpenDengue V1.3), nacional y subnacional unificadas.
--
-- Grano: (uuid, full_name, period_start, period_end, spatial_res, temporal_res,
-- case_definition). 97.339 filas de 99.579 en bronze.
--
-- **El UUID de OpenDengue no es la clave de fila.** Es tentador creerlo —se
-- llama UUID— pero identifica el *boletín de origen*: todas las 30.991 filas
-- del envío del MINSA peruano comparten `MOH-PER-20002023-Y02-00`. Deduplicar
-- por uuid deja 1.005 filas de 99.579 y destruye el 99% del dataset sin que
-- nada falle: el build pasa, las tablas existen, los números son plausibles.
-- Se detectó porque Perú, que debía tener 116 provincias, tenía tres.
--
-- Los 2.240 duplicados restantes **los fabrica este proyecto, no la fuente**.
-- Un país-año cuya resolución espacial más fina disponible es la nacional
-- aparece idéntico en los dos extractos: Argentina 2015 está en el nacional
-- por ser nacional, y en el espacial por ser lo más fino que hay. Al unirlos
-- se duplica. Son filas byte a byte iguales, así que quedarse con una no
-- pierde nada — pero sumarlas habría inflado esos países al doble.
--
-- El único filtro es `cases IS NOT NULL`. Una fila sin recuento no es un cero:
-- es una semana en la que el boletín no salió, y tratarla como cero fabricaría
-- valles en la serie justo donde falta información. En una serie temporal, un
-- hueco y un cero significan cosas opuestas.

CREATE OR REPLACE TABLE silver_dengue AS
WITH unificado AS (
    SELECT *, 'subnacional' AS scope FROM {{bronze_dengue}}
    UNION ALL BY NAME
    SELECT *, 'nacional'    AS scope FROM {{bronze_dengue_national}}
),
ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (
            PARTITION BY
                uuid, full_name, period_start, period_end,
                spatial_res, temporal_res, case_definition
            -- Ante el empate exacto se prefiere el extracto espacial: es el
            -- que trae la jerarquía administrativa rellena.
            ORDER BY _ingested_at DESC, scope
        ) AS _rn
    FROM unificado
)
SELECT
    * EXCLUDE (_rn),
    -- Duración real del período. OpenDengue mezcla semanas, meses y años, y
    -- comparar un recuento semanal con uno mensual sin normalizar es comparar
    -- una semana de casos con cuatro.
    date_diff('day', period_start, period_end) + 1 AS period_days
FROM ranked
WHERE _rn = 1
  AND cases IS NOT NULL
  AND period_end >= period_start;
