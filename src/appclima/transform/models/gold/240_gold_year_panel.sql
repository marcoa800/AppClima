-- Panel anual: una fila por año, con columnas de TODAS las fuentes.
--
-- Grano: year.
--
-- Es la tabla que permite buscar patrones ENTRE dominios en lugar de dentro de
-- uno. Hasta ahora cada fuente vivía en su propio silo: el clima por un lado,
-- los ciclones por otro, los sismos por otro. Aquí comparten el eje temporal,
-- que es lo único que todas tienen en común.
--
-- **La columna que hay que mirar antes que ninguna otra es `sources_available`.**
-- Las fuentes arrancan en fechas muy distintas — ONI en 1950, IBTrACS fiable en
-- 1980, ERA5 nuestro en 2006, USGS moderno en 2016 — así que una correlación
-- calculada sobre el rango completo mezcla años con ocho fuentes y años con dos.
-- Cualquier análisis serio sobre este panel debe restringirse a una ventana con
-- cobertura homogénea, y por eso el recuento va explícito.
--
-- Segundo aviso: los recuentos de eventos NO son comparables en el tiempo si
-- cruzan un cambio de cobertura. Ya está medido en el proyecto: los desastres
-- registrados pasan de 20 en el siglo III a.C. a 4.374 en el XXI, y eso mide
-- documentación, no geología.

CREATE OR REPLACE TABLE gold_year_panel AS
WITH years AS (
    SELECT unnest(generate_series(1900, 2026, 1)) AS year
),

-- ── Clima: anomalía y extremos de las 12 ciudades con historia profunda ────
clima AS (
    SELECT year(local_date) AS year,
           round(avg(anomaly_c), 3) AS temp_anomaly_mean,
           round(100.0 * avg(CASE WHEN extreme_heat THEN 1.0 ELSE 0.0 END), 2)
               AS pct_extreme_heat_days,
           sum(CASE WHEN record_heat THEN 1 ELSE 0 END) AS heat_records,
           count(DISTINCT location_id) AS climate_cities
    FROM gold_temperature_anomaly
    WHERE kind = 'observed'
    GROUP BY 1
),

-- ── Ciclones ──────────────────────────────────────────────────────────────
ciclones AS (
    SELECT season AS year,
           round(sum(ace_total), 1) AS cyclone_ace_global,
           sum(systems) AS cyclone_systems,
           sum(hurricanes) AS hurricanes,
           sum(major_hurricanes) AS major_hurricanes,
           sum(landfalling) AS landfalling,
           max(strongest_wind_kt) AS strongest_wind_kt,
           round(sum(CASE WHEN basin = 'NA' THEN ace_total END), 1) AS ace_atlantic,
           round(sum(CASE WHEN basin = 'EP' THEN ace_total END), 1) AS ace_east_pacific,
           round(sum(CASE WHEN basin = 'WP' THEN ace_total END), 1) AS ace_west_pacific
    FROM gold_cyclone_seasons
    GROUP BY 1
),

-- ── El Niño: fase del trimestre ASO, el pico ciclónico del hemisferio norte ─
enso AS (
    SELECT year,
           round(anomaly_c, 2) AS oni_aso,
           phase AS enso_phase,
           intensity AS enso_intensity
    FROM silver_oni
    WHERE season = 'ASO'
),
enso_annual AS (
    SELECT year, round(avg(anomaly_c), 3) AS oni_year_mean
    FROM silver_oni GROUP BY 1
),

-- ── Sismos modernos (USGS, desde 2016) ────────────────────────────────────
sismos AS (
    SELECT year(time) AS year,
           count(*) AS quakes_m45,
           sum(CASE WHEN magnitude >= 7 THEN 1 ELSE 0 END) AS quakes_m7,
           round(max(magnitude), 1) AS max_magnitude,
           sum(CASE WHEN tsunami THEN 1 ELSE 0 END) AS tsunamigenic
    FROM silver_earthquakes
    GROUP BY 1
),
secuencias AS (
    SELECT year, count(*) AS aftershock_sequences,
           sum(n1) AS aftershocks_day1
    FROM gold_aftershock_forecast
    WHERE is_predictable
    GROUP BY 1
),

-- ── Desastres históricos (NOAA, con impacto humano) ───────────────────────
desastres AS (
    SELECT year,
           count(*) AS noaa_disasters,
           sum(CASE WHEN has_exact_deaths THEN deaths_best END) AS disaster_deaths,
           max(deaths_best) AS deadliest_event_deaths
    FROM silver_historical_disasters
    GROUP BY 1
),

-- ── Población ─────────────────────────────────────────────────────────────
poblacion AS (
    SELECT year, population_mid AS world_population, source_kind AS population_source
    FROM gold_world_population
),

-- ── Epidemias en curso ese año ────────────────────────────────────────────
epidemias AS (
    SELECT y.year,
           count(*) AS epidemics_active,
           string_agg(e.name, ' · ' ORDER BY e.start_year) AS epidemic_names
    FROM years y
    JOIN silver_epidemics e
      ON y.year >= e.start_year
     AND y.year <= coalesce(e.end_year, 2026)
    GROUP BY 1
),

-- ── Hitos históricos ──────────────────────────────────────────────────────
hitos AS (
    SELECT y.year,
           string_agg(h.name, ' · ' ORDER BY h.start_year) AS milestones,
           bool_or(h.category = 'observacion') AS data_coverage_change
    FROM years y
    JOIN silver_historical_events h
      ON y.year >= h.start_year
     AND y.year <= coalesce(h.end_year, h.start_year)
    GROUP BY 1
)

SELECT
    y.year,

    -- Clima
    c.temp_anomaly_mean,
    c.pct_extreme_heat_days,
    c.heat_records,

    -- Ciclones
    cy.cyclone_ace_global,
    cy.cyclone_systems,
    cy.hurricanes,
    cy.major_hurricanes,
    cy.landfalling,
    cy.ace_atlantic,
    cy.ace_east_pacific,
    cy.ace_west_pacific,

    -- ENSO
    e.oni_aso,
    e.enso_phase,
    e.enso_intensity,
    ea.oni_year_mean,

    -- Sismos
    s.quakes_m45,
    s.quakes_m7,
    s.max_magnitude,
    s.tsunamigenic,
    sq.aftershock_sequences,

    -- Desastres con impacto
    d.noaa_disasters,
    d.disaster_deaths,
    d.deadliest_event_deaths,

    -- Contexto
    p.world_population,
    p.population_source,
    ep.epidemics_active,
    ep.epidemic_names,
    h.milestones,

    -- CUÁNTAS fuentes tienen dato ese año. Se lee ANTES que cualquier otra
    -- columna: correlacionar sobre años con cobertura desigual es el error
    -- que este panel facilita cometer si nadie mira aquí primero.
    (CASE WHEN c.temp_anomaly_mean IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN cy.cyclone_ace_global IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN e.oni_aso IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN s.quakes_m45 IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN d.noaa_disasters IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN p.world_population IS NOT NULL THEN 1 ELSE 0 END
   + CASE WHEN ep.epidemics_active IS NOT NULL THEN 1 ELSE 0 END) AS sources_available,

    -- ¿Marca este año un hito de disponibilidad de datos según el catálogo?
    -- Se conserva como CONTEXTO, no como criterio: el catálogo solo marca el
    -- año de inicio de cada hito, así que señala 1940 y 1979 pero no el tramo
    -- posterior. Para saber si la cobertura cambió DE VERDAD hay que mirar
    -- `coverage_regime_change`, que se calcula abajo desde los datos.
    coalesce(h.data_coverage_change, false) AS milestone_year
FROM years y
LEFT JOIN clima c ON c.year = y.year
LEFT JOIN ciclones cy ON cy.year = y.year
LEFT JOIN enso e ON e.year = y.year
LEFT JOIN enso_annual ea ON ea.year = y.year
LEFT JOIN sismos s ON s.year = y.year
LEFT JOIN secuencias sq ON sq.year = y.year
LEFT JOIN desastres d ON d.year = y.year
LEFT JOIN poblacion p ON p.year = y.year
LEFT JOIN epidemias ep ON ep.year = y.year
LEFT JOIN hitos h ON h.year = y.year
ORDER BY y.year;

-- Segunda pasada: el cambio de régimen se calcula comparando cada año con el
-- anterior, que es la única forma honesta de detectarlo.
--
-- La versión anterior tomaba esta marca del catálogo de hitos y era engañosa:
-- señalaba 1940 y 1979 (los años en que ARRANCA una fuente) pero dejaba sin
-- marcar todo el tramo posterior, que es justo donde la serie ya cambió de
-- naturaleza. Una verificación adversarial la señaló como no fiable.
CREATE OR REPLACE TABLE gold_year_panel AS
WITH con_previo AS (
    -- El lag se calcula aquí y no en el SELECT final: DuckDB no permite anidar
    -- una función de ventana dentro de otra, y `coverage_regime` necesita un
    -- sum() OVER sobre el resultado del lag().
    SELECT *, lag(sources_available) OVER (ORDER BY year) AS _prev
    FROM gold_year_panel
)
SELECT
    * EXCLUDE (_prev),
    sources_available <> _prev AS coverage_regime_change,
    -- Identificador del régimen: todos los años consecutivos con el mismo
    -- número de fuentes comparten valor. Es la forma correcta de restringir
    -- una correlación a cobertura homogénea: `WHERE coverage_regime = X`.
    sum(CASE WHEN sources_available <> coalesce(_prev, sources_available)
             THEN 1 ELSE 0 END) OVER (ORDER BY year) AS coverage_regime
FROM con_previo;
