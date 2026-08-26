-- Perfil de peligro por ciudad: cuatro dimensiones, sin promediarlas.
--
-- Grano: (location_id).
--
-- ══ Por qué NO hay un número único ══════════════════════════════════════════
--
-- Lo natural sería sumar ciclones, sismos y calor en un "índice de riesgo".
-- No se hace, y la razón no es pereza.
--
-- Sumar exige pesos, y no existe ninguna forma defendible de decir cuántos
-- sismos de magnitud 6 equivalen a un ciclón de categoría 3 o a quince días de
-- calor sin precedente. Cualquier peso que se elija es una opinión disfrazada
-- de cálculo, y quien lo lea después no podrá distinguir una de otra. Peor: el
-- número resultante ordena ciudades, y ese orden se usará para decidir cosas.
--
-- Así que se publican las cuatro dimensiones por separado, con su percentil
-- dentro del catálogo, y un recuento de cuántas están en el cuartil superior.
-- Quien necesite un orden puede construirlo con sus propios pesos, a la vista.
--
-- ══ Esto es PELIGRO, no riesgo ══════════════════════════════════════════════
--
-- La distinción no es terminológica. El riesgo es peligro × exposición ×
-- vulnerabilidad, y aquí solo hay lo primero.
--
-- Tokio tiene uno de los peligros sísmicos más altos del mundo y un riesgo
-- sísmico comparativamente bajo, porque lleva décadas construyendo para eso.
-- Un terremoto idéntico mata órdenes de magnitud más gente según dónde ocurra.
-- Publicar "peligro" como si fuera "riesgo" invertiría la conclusión en
-- exactamente los sitios donde más importa acertar.
--
-- El almacén no tiene datos de vulnerabilidad —código sísmico, renta, sistema
-- sanitario, aire acondicionado— así que la columna que falta se nombra en vez
-- de estimarse a ojo.
--
-- ══ Los percentiles son de ESTE catálogo ════════════════════════════════════
--
-- 66 ciudades elegidas por cubrir climas y regímenes distintos, no una muestra
-- aleatoria del planeta. Un percentil 90 aquí significa "de las más expuestas
-- de esta lista", no "del mundo". Y las dimensiones de calor solo existen para
-- las ciudades con veinte años de archivo, así que `dimensiones_disponibles`
-- dice sobre cuántas se está hablando: comparar una ciudad con cuatro contra
-- otra con dos sería comparar cosas distintas.

CREATE OR REPLACE TABLE gold_city_hazard_profile AS
WITH ciclones AS (
    SELECT
        location_id,
        count(*)                       AS ciclones_total,
        count(DISTINCT season)         AS temporadas_con_ciclon,
        max(storm_max_wind_kt)         AS viento_max_kt,
        min(min_distance_km)           AS paso_mas_cercano_km,
        count(*) FILTER (WHERE min_distance_km <= 200) AS ciclones_200km
    FROM gold_cyclones_near_city
    GROUP BY 1
),

sismos AS (
    SELECT
        location_id,
        count(*) FILTER (WHERE magnitude >= 5.0) AS sismos_m5,
        max(magnitude)                           AS magnitud_max,
        min(distance_km) FILTER (WHERE magnitude >= 6.0) AS m6_mas_cercano_km,
        count(*) FILTER (WHERE tsunami = 1)      AS con_aviso_tsunami
    FROM gold_quakes_near_city
    GROUP BY 1
),

calor AS (
    SELECT location_id, amplification, days_per_year_now, threshold_drift_c
    FROM gold_heat_threshold_drift
    WHERE procedencia_fiable
),

sin_precedente AS (
    SELECT location_id, razon_calor, dias_calor_por_anio, asimetria_calor_frio
    FROM gold_unprecedented_weather
),

unido AS (
    SELECT
        l.id AS location_id,
        l.name AS location_name,
        l.country,
        l.koppen,
        c.ciclones_200km,
        c.viento_max_kt,
        c.paso_mas_cercano_km,
        s.sismos_m5,
        s.magnitud_max,
        s.m6_mas_cercano_km,
        h.amplification      AS calor_amplificacion,
        h.days_per_year_now  AS calor_dias_por_anio,
        u.razon_calor        AS sin_precedente_razon,
        u.dias_calor_por_anio AS sin_precedente_dias
    FROM dim_locations l
    LEFT JOIN ciclones c       ON c.location_id = l.id
    LEFT JOIN sismos s         ON s.location_id = l.id
    LEFT JOIN calor h          ON h.location_id = l.id
    LEFT JOIN sin_precedente u ON u.location_id = l.id
)

SELECT
    location_id,
    location_name,
    country,
    koppen,

    coalesce(ciclones_200km, 0) AS ciclones_200km,
    viento_max_kt,
    paso_mas_cercano_km,
    coalesce(sismos_m5, 0)      AS sismos_m5,
    magnitud_max,
    m6_mas_cercano_km,
    calor_amplificacion,
    calor_dias_por_anio,
    sin_precedente_razon,
    sin_precedente_dias,

    -- Percentiles dentro del catálogo.
    --
    -- Ciclones y sismos se rellenan con cero, y eso NO es inventarse un dato:
    -- IBTrACS y el catálogo del USGS son globales, así que una ciudad sin
    -- registros es una ciudad por la que no pasó ninguno. Ahí el cero es la
    -- medición. Sin el coalesce pasaba algo peor que perder la fila: DuckDB
    -- ordena los NULL al final, así que Madrid —sin un solo ciclón— salía en
    -- el percentil más alto de peligro ciclónico.
    --
    -- El calor es al revés: falta donde no hay veinte años de archivo, y ahí
    -- sí es ausencia de dato. Queda NULL.
    round(percent_rank() OVER (ORDER BY coalesce(ciclones_200km, 0)) * 100)
        AS pct_ciclones,
    round(percent_rank() OVER (ORDER BY coalesce(sismos_m5, 0)) * 100)
        AS pct_sismos,
    CASE WHEN calor_amplificacion IS NOT NULL THEN round(percent_rank() OVER (
        PARTITION BY calor_amplificacion IS NULL ORDER BY calor_amplificacion) * 100)
    END AS pct_calor,
    CASE WHEN sin_precedente_razon IS NOT NULL THEN round(percent_rank() OVER (
        PARTITION BY sin_precedente_razon IS NULL ORDER BY sin_precedente_razon) * 100)
    END AS pct_sin_precedente,

    -- Sobre cuántas dimensiones se está hablando. Ciclones y sismos cuentan
    -- siempre, porque sus catálogos son globales y el cero es una medición.
    (2 + CASE WHEN calor_amplificacion IS NOT NULL THEN 1 ELSE 0 END
       + CASE WHEN sin_precedente_razon IS NOT NULL THEN 1 ELSE 0 END)
        AS dimensiones_disponibles,

    -- Cuántas dimensiones en el cuartil superior del catálogo. Es el recuento
    -- que sustituye al índice sumado: no pondera nada, solo cuenta.
    (CASE WHEN percent_rank() OVER (ORDER BY coalesce(ciclones_200km, 0)) >= 0.75
          THEN 1 ELSE 0 END
     + CASE WHEN percent_rank() OVER (ORDER BY coalesce(sismos_m5, 0)) >= 0.75
            THEN 1 ELSE 0 END
     + CASE WHEN calor_amplificacion IS NOT NULL AND percent_rank() OVER (
            PARTITION BY calor_amplificacion IS NULL
            ORDER BY calor_amplificacion) >= 0.75 THEN 1 ELSE 0 END
     + CASE WHEN sin_precedente_razon IS NOT NULL AND percent_rank() OVER (
            PARTITION BY sin_precedente_razon IS NULL
            ORDER BY sin_precedente_razon) >= 0.75 THEN 1 ELSE 0 END)
        AS dimensiones_en_cuartil_alto

FROM unido
ORDER BY location_id;
