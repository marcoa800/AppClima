-- Panel MENSUAL: una fila por mes, con columnas de las fuentes que lo permiten.
--
-- Grano: (year, month).
--
-- **Existe porque el panel anual destruye la señal cíclica.** Lo midió una
-- verificación adversarial y es el hallazgo metodológico más útil del proyecto:
--
--   con oni_aso (agosto-octubre)  → 87,5% de la varianza en la banda 2-7 años,
--                                   p = 0,011 frente al nulo
--   con oni_year_mean (promedio)  → 76,5% frente al 73,0% esperado bajo ruido
--                                   blanco, p = 0,33, indistinguible de ruido
--
-- Promediar doce meses de ENSO al año borra justo lo que se quería estudiar.
-- Para ciclos, periodicidad y relaciones con desfase, ESTE es el panel.
--
-- El ONI se recupera mensual sin trucos: silver_oni trae trimestres SOLAPADOS
-- (DJF, JFM, FMA…) con season_index de 1 a 12, y cada uno está centrado en su
-- mes correspondiente — DJF en enero, JFM en febrero. Es una media móvil de tres
-- meses, no una partición, así que season_index = month da la serie mensual
-- directamente.
--
-- AVISO SOBRE ESTACIONALIDAD: a resolución mensual, el ciclo anual domina TODO.
-- Los ciclones se forman en verano, la temperatura sube y baja con las
-- estaciones. Correlacionar dos series mensuales crudas mide sobre todo que
-- ambas tienen verano. Por eso:
--
--   - `temp_anomaly_mean` ya viene desestacionalizado por construcción (es una
--     anomalía contra la climatología del día del año)
--   - `cyclone_ace` y los recuentos NO lo están, y se acompañan de su versión
--     desestacionalizada (`*_deseason`), que resta la media de ese mes
--     calendario a lo largo de toda la serie
--
-- Usa siempre las columnas `_deseason` para correlacionar. Las crudas están
-- para graficar.

CREATE OR REPLACE TABLE gold_month_panel AS
WITH months AS (
    SELECT
        y.year,
        m.month,
        make_date(y.year, m.month, 1) AS month_start
    FROM (SELECT unnest(generate_series(1950, 2026, 1)) AS year) y
    CROSS JOIN (SELECT unnest(generate_series(1, 12, 1)) AS month) m
),

-- ── ONI mensual ───────────────────────────────────────────────────────────
oni AS (
    SELECT year, season_index AS month, anomaly_c AS oni, phase AS oni_phase,
           intensity AS oni_intensity
    FROM silver_oni
),

-- ── Clima: la anomalía ya está desestacionalizada de origen ────────────────
clima AS (
    SELECT year(local_date) AS year, month(local_date) AS month,
           round(avg(anomaly_c), 3) AS temp_anomaly_mean,
           round(100.0 * avg(CASE WHEN extreme_heat THEN 1.0 ELSE 0.0 END), 2)
               AS pct_extreme_heat_days,
           count(DISTINCT location_id) AS climate_cities
    FROM gold_temperature_anomaly
    WHERE kind = 'observed'
    GROUP BY 1, 2
),

-- ── Ciclones: ACE calculado sobre los puntos de trayectoria del mes ────────
-- Se calcula desde silver_cyclone_tracks y no desde gold_cyclones porque una
-- tormenta puede cruzar el cambio de mes: atribuir todo su ACE al mes en que se
-- formó movería energía de octubre a septiembre.
ciclones AS (
    SELECT year(time) AS year, month(time) AS month,
           round(sum(pow(wind_kt, 2) / 10000.0)
                 FILTER (WHERE is_synoptic AND wind_kt >= 34), 3) AS cyclone_ace,
           count(DISTINCT sid) AS cyclones_active,
           count(DISTINCT sid) FILTER (WHERE is_hurricane) AS hurricanes_active,
           max(wind_kt) AS max_wind_kt
    FROM silver_cyclone_tracks
    GROUP BY 1, 2
),
ciclones_genesis AS (
    SELECT year(first_seen) AS year, month(first_seen) AS month,
           count(*) AS cyclones_formed
    FROM gold_cyclones GROUP BY 1, 2
),

-- ── Sismos (solo 2016+) ───────────────────────────────────────────────────
sismos AS (
    SELECT year(time) AS year, month(time) AS month,
           count(*) AS quakes_m45,
           round(max(magnitude), 1) AS max_magnitude
    FROM silver_earthquakes GROUP BY 1, 2
),

-- ── Desastres históricos con mes conocido ─────────────────────────────────
desastres AS (
    SELECT year, month,
           count(*) AS noaa_disasters,
           sum(deaths_best) FILTER (WHERE has_exact_deaths) AS disaster_deaths
    FROM silver_historical_disasters
    WHERE month IS NOT NULL
    GROUP BY 1, 2
),

-- ── Fenología: recuentos mensuales de GBIF, ya vienen por mes ─────────────
fenologia AS (
    SELECT year, month, sum(cnt) AS bird_records,
           sum(cnt) FILTER (WHERE NOT is_control) AS bird_records_migratory
    FROM (
        SELECT year, coalesce(is_control, false) AS is_control, m AS month, cnt
        FROM (
            SELECT *, row_number() OVER (
                PARTITION BY species_key, location_id, year
                ORDER BY _ingested_at DESC) AS _rn
            FROM {{bronze_phenology}}
        ) t,
        UNNEST([m01,m02,m03,m04,m05,m06,m07,m08,m09,m10,m11,m12])
            WITH ORDINALITY AS u(cnt, m)
        WHERE _rn = 1
    )
    GROUP BY 1, 2
),

joined AS (
    SELECT
        mo.year, mo.month, mo.month_start,
        o.oni, o.oni_phase, o.oni_intensity,
        c.temp_anomaly_mean, c.pct_extreme_heat_days, c.climate_cities,
        cy.cyclone_ace, cy.cyclones_active, cy.hurricanes_active, cy.max_wind_kt,
        cg.cyclones_formed,
        s.quakes_m45, s.max_magnitude,
        d.noaa_disasters, d.disaster_deaths,
        f.bird_records, f.bird_records_migratory
    FROM months mo
    LEFT JOIN oni o ON o.year = mo.year AND o.month = mo.month
    LEFT JOIN clima c ON c.year = mo.year AND c.month = mo.month
    LEFT JOIN ciclones cy ON cy.year = mo.year AND cy.month = mo.month
    LEFT JOIN ciclones_genesis cg ON cg.year = mo.year AND cg.month = mo.month
    LEFT JOIN sismos s ON s.year = mo.year AND s.month = mo.month
    LEFT JOIN desastres d ON d.year = mo.year AND d.month = mo.month
    LEFT JOIN fenologia f ON f.year = mo.year AND f.month = mo.month
)
SELECT
    *,

    -- Versiones desestacionalizadas: valor menos la media de ese mes calendario
    -- a lo largo de toda la serie. Es lo que hay que usar para correlacionar,
    -- porque si no se mide sobre todo que ambas series tienen verano.
    round(cyclone_ace - avg(cyclone_ace) OVER (PARTITION BY month), 3)
        AS cyclone_ace_deseason,
    round(cyclones_formed - avg(cyclones_formed) OVER (PARTITION BY month), 3)
        AS cyclones_formed_deseason,
    round(hurricanes_active - avg(hurricanes_active) OVER (PARTITION BY month), 3)
        AS hurricanes_active_deseason,
    round(bird_records - avg(bird_records) OVER (PARTITION BY month), 1)
        AS bird_records_deseason,

    -- Cobertura, igual que en el panel anual: se lee ANTES que nada.
    (CASE WHEN oni IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN temp_anomaly_mean IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN cyclone_ace IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN quakes_m45 IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN noaa_disasters IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN bird_records IS NOT NULL THEN 1 ELSE 0 END) AS sources_available
FROM joined
ORDER BY year, month;
