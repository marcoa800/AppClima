-- Desastres naturales históricos, los tres datasets de NOAA unificados.
--
-- Grano: (hazard_type, source_id).
--
-- El grano lleva el tipo de peligro porque los ids de NOAA solo son únicos
-- DENTRO de cada dataset: existe un sismo con id 40 y una erupción con id 40, y
-- son eventos distintos. Deduplicar solo por source_id fusionaría un terremoto
-- con un volcán.
--
-- Sobre `event_date`: se construye solo cuando hay año, mes y día. Muchos
-- registros antiguos tienen únicamente el año, y rellenar con un 1 de enero
-- inventado convertiría una ausencia de dato en un dato falso — que además
-- generaría un pico espurio en cualquier gráfica por día del año. Year, month y
-- day quedan siempre disponibles por separado.
--
-- DuckDB sí admite fechas anteriores a Cristo, comprobado con el evento más
-- antiguo del archivo (año -4360).

CREATE OR REPLACE TABLE silver_historical_disasters AS
WITH unioned AS (
    SELECT * FROM {{bronze_noaa_eq}}
    UNION ALL BY NAME
    SELECT * FROM {{bronze_noaa_tsunami}}
    UNION ALL BY NAME
    SELECT * FROM {{bronze_noaa_volcano}}
),
ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (
            PARTITION BY hazard_type, source_id
            ORDER BY _ingested_at DESC
        ) AS _rn
    FROM unioned
)
SELECT
    * EXCLUDE (_rn),

    -- Fecha completa solo si la fuente la tiene entera.
    CASE
        WHEN month IS NOT NULL AND day IS NOT NULL AND month BETWEEN 1 AND 12
             AND day BETWEEN 1 AND 31
        THEN try(make_date(year, month, day))
    END AS event_date,

    -- Precisión temporal disponible, para que el consumidor sepa qué puede
    -- preguntarle a cada fila.
    CASE
        WHEN month IS NULL THEN 'solo año'
        WHEN day IS NULL THEN 'año y mes'
        ELSE 'fecha completa'
    END AS date_precision,

    -- Siglo, con el convenio historiográfico: el año 1 abre el siglo I y no
    -- existe el año 0. Sin el CASE, los años a.C. saldrían desplazados un siglo.
    --
    -- Y OJO con el operador: en DuckDB `/` es división en coma flotante, así
    -- que (1976-1)/100 da 19,75 y al castear a INTEGER redondea a 20, dando
    -- siglo 21 en vez de 20. Hace falta `//`, división entera, que trunca.
    -- Lo cazó un test parametrizado, no la vista previa de los datos.
    CASE
        WHEN year > 0 THEN ((year - 1) // 100) + 1
        ELSE -(((-year - 1) // 100) + 1)
    END AS century,

    -- La mejor cifra de muertes disponible, priorizando el total (que incluye
    -- los peligros secundarios). Krakatoa: 2.000 directas, 36.417 totales.
    coalesce(deaths_total, deaths) AS deaths_best,
    coalesce(deaths_order_total, deaths_order) AS deaths_order_best,

    -- ¿Hay cifra exacta o solo orden de magnitud? Determina si la fila puede
    -- entrar en una suma.
    coalesce(deaths_total, deaths) IS NOT NULL AS has_exact_deaths
FROM ranked
WHERE _rn = 1
  AND year IS NOT NULL;
