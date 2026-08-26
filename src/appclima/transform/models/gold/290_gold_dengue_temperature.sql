-- Temperatura y transmisión de dengue en doce provincias del Perú.
--
-- Grano: (location_id). Doce filas.
--
-- ══ Lo que esta tabla NO demuestra ══════════════════════════════════════════
--
-- Esta tabla nació para sostener una afirmación que **no sobrevivió al dato
-- limpio**, y se conserva contándolo porque el recorrido es más útil que el
-- resultado.
--
-- La hipótesis era un umbral térmico nítido. Tiene un mecanismo detrás bien
-- medido: el **período de incubación extrínseco** —lo que tarda el virus en
-- llegar a las glándulas salivales del mosquito y hacerlo infectante— dura
-- unos 7 días a 30 °C y unos 15 a 25 °C, y por debajo de ~18 °C se alarga más
-- que la vida del propio mosquito. La transmisión no debería decaer: debería
-- cortarse.
--
-- Y con los datos que había, se cortaba. Ordenadas por temperatura media, las
-- seis provincias más cálidas sumaban 309.765 casos y las seis más frías seis,
-- con un escalón entre Lima (18,9 °C) y Tacna (18,0 °C). El test era exacto y
-- pre-especificado: bajo la nula de que el orden térmico no importa, la
-- probabilidad de que las seis con casos fueran justo las seis más cálidas es
-- 1/C(12,6) = 0,0011.
--
-- El problema estaba en el termómetro. El archivo de Open-Meteo servía ERA5
-- hasta 2016 y el IFS de ECMWF desde 2017, y en Tacna esa costura vale
-- **2,44 °C**. Con un solo reanálisis, Tacna y Lima están las dos a 18,88 °C:
-- misma temperatura, cero casos frente a 32.466.
--
-- Así que la conclusión honesta es la contraria de la que se buscaba:
--
--   **La temperatura media no determina la transmisión en el margen.**
--
-- Sigue habiendo un gradiente enorme y real —las cinco provincias por encima
-- de 20 °C acumulan 279.000 casos y las cinco por debajo de 15 °C acumulan
-- seis— pero el borde no lo decide el termómetro. Entre Lima y Tacna, a la
-- misma temperatura, la diferencia tiene que ser otra cosa: tamaño,
-- conectividad e importación constante de virus, presencia del vector,
-- almacenamiento de agua. Esta tabla no puede distinguir entre ellas.
--
-- ── Por qué no se busca otro estadístico ────────────────────────────────────
--
-- Lima tiene 39 semanas por encima de 22 °C y Tacna 5, así que la cola cálida
-- sí las separa. Sería fácil cambiar la media por ese otro estadístico y
-- recuperar el escalón. Sería también exactamente el p-hacking que este
-- proyecto existe para no cometer: un umbral elegido DESPUÉS de ver que el
-- primero falla no tiene el p-valor que aparenta. La columna se conserva como
-- descripción, no como test.
--
-- ── Lo que sí queda en pie ──────────────────────────────────────────────────
--
--   1. El gradiente descriptivo, que es fuerte y no depende del umbral.
--   2. Que la temperatura es **necesaria pero no suficiente**: ninguna
--      provincia por debajo de 15 °C tiene transmisión, y no todas las que
--      están por encima la tienen.
--   3. La advertencia operativa: cruzar el rango térmico no basta para
--      predecir un brote, así que un plan basado solo en temperatura daría
--      falsos positivos.
--
-- ── Ventana ─────────────────────────────────────────────────────────────────
--
-- El clima cubre 2006-2015: es todo lo que hay hoy con un único reanálisis,
-- porque el re-backfill agotó la cuota diaria de Open-Meteo a mitad de 2015.
-- Los casos cubren 2000-2023 completos. Cuando el archivo se complete, esto
-- debe recalcularse — y las grandes epidemias que faltan (El Niño costero de
-- 2017, la de 2023) son justo donde una señal climática sería más visible.
-- Ver también `gold_dengue_lags`, que prueba lo mismo dentro de cada ciudad.

CREATE OR REPLACE TABLE gold_dengue_temperature AS
WITH clima AS (
    SELECT
        location_id,
        avg(temp_media_c) AS temp_media_c,
        avg(temp_min_c)   AS temp_min_c,
        avg(temp_max_c)   AS temp_max_c,
        sum(precip_mm) / count(DISTINCT year) AS precip_anual_mm
    FROM gold_dengue_peru
    WHERE clima_completo
    GROUP BY 1
),

epi AS (
    SELECT
        location_id,
        any_value(departamento)                     AS departamento,
        any_value(provincia)                        AS provincia,
        sum(casos)                                  AS casos_total,
        sum(CASE WHEN casos > 0 THEN 1 ELSE 0 END)  AS semanas_con_casos,
        count(*)                                    AS semanas_vigiladas,
        max(casos)                                  AS pico_semanal,
        count(DISTINCT CASE WHEN casos > 0 THEN year END) AS anios_con_casos
    FROM gold_dengue_peru
    GROUP BY 1
),

-- Tendencia térmica propia de cada ciudad, sobre el archivo ERA5 completo.
-- regr_slope da °C por año directamente.
tendencia AS (
    SELECT
        location_id,
        regr_slope(temp_mean, year(local_date)) AS calentamiento_c_por_anio
    FROM gold_weather_daily
    WHERE kind = 'observed' AND local_date >= '2006-01-01'
    GROUP BY 1
),

-- El corte empírico: entre la provincia más cálida sin transmisión sostenida y
-- la más fría con ella. Se deriva, no se declara.
bracket AS (
    SELECT
        max(CASE WHEN e.casos_total < 10 THEN c.temp_media_c END) AS umbral_inferior,
        min(CASE WHEN e.casos_total >= 10 THEN c.temp_media_c END) AS umbral_superior,
        count(*)                                                   AS n_provincias,
        count(CASE WHEN e.casos_total >= 10 THEN 1 END)            AS n_con_transmision
    FROM epi e JOIN clima c USING (location_id)
),

-- Probabilidad de que el azar ordenara igual de bien: 1 / C(n, k).
-- exp(lgamma(...)) porque DuckDB no trae coeficiente binomial.
test AS (
    SELECT
        umbral_inferior,
        umbral_superior,
        (umbral_inferior + umbral_superior) / 2 AS umbral_c,
        n_provincias,
        n_con_transmision,
        1.0 / exp(
            lgamma(n_provincias + 1.0)
            - lgamma(n_con_transmision + 1.0)
            - lgamma(n_provincias - n_con_transmision + 1.0)
        ) AS p_exacto
    FROM bracket
)

SELECT
    e.location_id,
    e.departamento,
    e.provincia,

    round(c.temp_media_c, 2)    AS temp_media_c,
    round(c.temp_min_c, 2)      AS temp_min_c,
    round(c.temp_max_c, 2)      AS temp_max_c,
    round(c.precip_anual_mm, 0) AS precip_anual_mm,

    e.casos_total::BIGINT       AS casos_total,
    e.semanas_con_casos,
    e.semanas_vigiladas,
    e.anios_con_casos,
    e.pico_semanal::BIGINT      AS pico_semanal,

    round(100.0 * e.semanas_con_casos / e.semanas_vigiladas, 1) AS pct_semanas_con_casos,

    CASE
        WHEN e.casos_total = 0    THEN 'ausente'
        WHEN e.casos_total < 10   THEN 'esporádica'
        WHEN e.semanas_con_casos * 2 >= e.semanas_vigiladas THEN 'endémica'
        ELSE 'estacional'
    END AS transmision,

    -- Descriptivo, NO un test: el umbral se estima del propio dato que
    -- luego clasifica, y el caso frontera (Lima y Tacna a la misma
    -- temperatura, resultados opuestos) lo invalida como criterio.
    c.temp_media_c >= t.umbral_c AS sobre_umbral_descriptivo,
    round(c.temp_media_c - t.umbral_c, 2) AS margen_c,

    round(t.umbral_c, 2)          AS umbral_c,
    round(t.umbral_inferior, 2)   AS umbral_inferior_c,
    round(t.umbral_superior, 2)   AS umbral_superior_c,
    -- p que TENDRÍA el test exacto si la separación fuera perfecta. No lo
    -- es: Tacna está por encima del corte estimado y tiene cero casos.
    -- Se conserva para poder contar por qué no vale.
    round(t.p_exacto, 5)          AS p_exacto_no_valido,
    (SELECT count(*) = 0 FROM epi e2 JOIN clima c2 USING (location_id)
       CROSS JOIN test t2
      WHERE (c2.temp_media_c >= t2.umbral_c) <> (e2.casos_total >= 10)
    )                             AS separacion_perfecta,
    t.n_provincias,

    round(tn.calentamiento_c_por_anio, 4) AS calentamiento_c_por_anio,

    -- Solo tiene sentido para las que están por debajo y calentándose. Para
    -- las demás es NULL, no un número grande: "nunca" y "ya pasó" no son
    -- horizontes de planificación.
    CASE
        WHEN c.temp_media_c < t.umbral_c AND tn.calentamiento_c_por_anio > 0
        THEN round((t.umbral_c - c.temp_media_c) / tn.calentamiento_c_por_anio, 0)
    END AS anios_hasta_umbral,

    -- La banda del horizonte, porque el umbral es un intervalo. Se usa el
    -- extremo inferior con el techo del intervalo y viceversa.
    CASE
        WHEN c.temp_media_c < t.umbral_inferior AND tn.calentamiento_c_por_anio > 0
        THEN round((t.umbral_inferior - c.temp_media_c) / tn.calentamiento_c_por_anio, 0)
    END AS anios_hasta_umbral_optimista

FROM epi e
JOIN clima c USING (location_id)
LEFT JOIN tendencia tn USING (location_id)
CROSS JOIN test t
ORDER BY c.temp_media_c DESC;
