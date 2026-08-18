-- Rango válido, autocorrelación y potencia REAL de cada columna de los paneles.
--
-- Grano: (panel, column_name).
--
-- ════ POR QUÉ ESTA TABLA SE REESCRIBIÓ ════
--
-- La primera versión publicaba `r_significance_threshold = 1,96/√n` usando el
-- número BRUTO de observaciones. **Ese umbral es mentira para series
-- temporales**, y lo era por un factor de casi seis en la columna más
-- importante del warehouse.
--
-- El ONI mensual tiene ACF(1) ≈ 0,97. Con 918 observaciones el umbral ingenuo
-- da 0,065, pero los grados de libertad efectivos son ~30 y el umbral honesto
-- es 0,358. Todo lo que cayera entre esas dos cifras salía "significativo"
-- siendo ruido — y como la tabla existía precisamente para decidir qué se puede
-- analizar, el error se propagaba a cualquiera que la consultase.
--
-- Lo destapó una verificación adversarial sobre el panel mensual: de 153 pares
-- de columnas, 77 superaban el umbral ingenuo y solo 6 sobrevivían a corregir
-- por autocorrelación, estacionalidad, tendencia y ventana. Un 92% de
-- mortalidad.
--
-- ════ LA CORRECCIÓN ════
--
--     n_efectivo ≈ n · (1 − ρ²) / (1 + ρ²)
--
-- con ρ la autocorrelación a desfase 1. Es la aproximación de Bartlett para dos
-- series de autocorrelación similar, y es la que hay que usar para decidir si
-- una correlación entre columnas de este panel significa algo.
--
-- Tres avisos sobre sus límites, porque un umbral corregido invita a confiarse:
--
--   1. Solo captura estructura AR(1). Series con estacionalidad residual o
--      memoria larga tienen AÚN MENOS grados de libertad. Estos umbrales siguen
--      siendo optimistas, solo que mucho menos.
--   2. La ACF se calcula sobre observaciones consecutivas NO NULAS. En columnas
--      con huecos eso no es exactamente el desfase temporal de 1.
--   3. Para el espectro de UNA sola serie esto no aplica, y tampoco vale el
--      nulo por desplazamiento circular: rotar una serie cambia la fase de cada
--      coeficiente de Fourier pero no su módulo, así que el periodograma es
--      invariante y el p-valor sale 1,0 por construcción. Ahí hacen falta
--      surrogados paramétricos.

CREATE OR REPLACE TABLE gold_panel_coverage AS
WITH year_long AS (
    UNPIVOT (
        SELECT year,
               1 AS month,
               temp_anomaly_mean::DOUBLE AS temp_anomaly_mean,
               pct_extreme_heat_days::DOUBLE AS pct_extreme_heat_days,
               heat_records::DOUBLE AS heat_records,
               cyclone_ace_global::DOUBLE AS cyclone_ace_global,
               cyclone_systems::DOUBLE AS cyclone_systems,
               hurricanes::DOUBLE AS hurricanes,
               major_hurricanes::DOUBLE AS major_hurricanes,
               landfalling::DOUBLE AS landfalling,
               ace_atlantic::DOUBLE AS ace_atlantic,
               ace_east_pacific::DOUBLE AS ace_east_pacific,
               ace_west_pacific::DOUBLE AS ace_west_pacific,
               oni_aso::DOUBLE AS oni_aso,
               oni_year_mean::DOUBLE AS oni_year_mean,
               quakes_m45::DOUBLE AS quakes_m45,
               quakes_m7::DOUBLE AS quakes_m7,
               max_magnitude::DOUBLE AS max_magnitude,
               tsunamigenic::DOUBLE AS tsunamigenic,
               aftershock_sequences::DOUBLE AS aftershock_sequences,
               noaa_disasters::DOUBLE AS noaa_disasters,
               disaster_deaths::DOUBLE AS disaster_deaths,
               world_population::DOUBLE AS world_population,
               epidemics_active::DOUBLE AS epidemics_active
        FROM gold_year_panel
    )
    ON COLUMNS(* EXCLUDE (year, month))
    INTO NAME column_name VALUE value
),
month_long AS (
    UNPIVOT (
        SELECT year, month,
               oni::DOUBLE AS oni,
               temp_anomaly_mean::DOUBLE AS temp_anomaly_mean,
               pct_extreme_heat_days::DOUBLE AS pct_extreme_heat_days,
               cyclone_ace::DOUBLE AS cyclone_ace,
               cyclone_ace_deseason::DOUBLE AS cyclone_ace_deseason,
               cyclones_active::DOUBLE AS cyclones_active,
               hurricanes_active::DOUBLE AS hurricanes_active,
               cyclones_formed::DOUBLE AS cyclones_formed,
               max_wind_kt::DOUBLE AS max_wind_kt,
               quakes_m45::DOUBLE AS quakes_m45,
               max_magnitude::DOUBLE AS max_magnitude,
               noaa_disasters::DOUBLE AS noaa_disasters,
               disaster_deaths::DOUBLE AS disaster_deaths,
               bird_records::DOUBLE AS bird_records
        FROM gold_month_panel
    )
    ON COLUMNS(* EXCLUDE (year, month))
    INTO NAME column_name VALUE value
),
combined AS (
    SELECT 'gold_year_panel' AS panel, * FROM year_long
    UNION ALL BY NAME
    SELECT 'gold_month_panel' AS panel, * FROM month_long
),
-- Solo observaciones presentes, ordenadas: el desfase se toma sobre valores
-- consecutivos no nulos.
observed AS (
    SELECT panel, column_name, year, month, value,
           lag(value) OVER (
               PARTITION BY panel, column_name ORDER BY year, month
           ) AS prev_value
    FROM combined
    WHERE value IS NOT NULL
),
stats AS (
    SELECT
        panel,
        column_name,
        count(*) AS n_observations,
        min(year) AS first_year,
        max(year) AS last_year,
        corr(value, prev_value) AS acf1
    FROM observed
    GROUP BY 1, 2
)
SELECT
    panel,
    column_name,
    first_year,
    last_year,
    n_observations,
    round(acf1, 4) AS acf1,

    -- n efectivo. Se acota por abajo a 3: una serie con ACF(1) casi 1 daría un
    -- n efectivo cercano a cero y un umbral mayor que 1, que no significa nada.
    greatest(3, round(
        n_observations * (1 - pow(coalesce(acf1, 0), 2))
                       / nullif(1 + pow(coalesce(acf1, 0), 2), 0)
    ))::INTEGER AS n_effective,

    -- El umbral ingenuo se conserva SOLO para poder ver la diferencia. No se
    -- usa para decidir nada.
    round(1.96 / sqrt(nullif(n_observations, 0)), 3) AS r_threshold_naive,

    round(1.96 / sqrt(greatest(3.0,
        n_observations * (1 - pow(coalesce(acf1, 0), 2))
                       / nullif(1 + pow(coalesce(acf1, 0), 2), 0)
    )), 3) AS r_threshold_honest,

    -- Cuántas veces más exigente es el umbral honesto. Para el ONI mensual
    -- ronda 5,5: ahí es donde vivían los falsos positivos.
    round(
        (1.96 / sqrt(greatest(3.0,
            n_observations * (1 - pow(coalesce(acf1, 0), 2))
                           / nullif(1 + pow(coalesce(acf1, 0), 2), 0))))
        / nullif(1.96 / sqrt(nullif(n_observations, 0)), 0), 2
    ) AS naive_underestimates_by,

    -- EL CRITERIO. Usa el n EFECTIVO, no el bruto.
    (n_observations * (1 - pow(coalesce(acf1, 0), 2))
                    / nullif(1 + pow(coalesce(acf1, 0), 2), 0)) >= 30 AS analyzable,

    CASE
        WHEN n_observations IS NULL OR n_observations = 0 THEN 'sin datos'
        WHEN n_observations * (1 - pow(coalesce(acf1, 0), 2))
             / nullif(1 + pow(coalesce(acf1, 0), 2), 0) < 15
            THEN 'NO analizable: n efectivo minimo'
        WHEN n_observations * (1 - pow(coalesce(acf1, 0), 2))
             / nullif(1 + pow(coalesce(acf1, 0), 2), 0) < 30
            THEN 'dudoso: solo efectos enormes'
        WHEN n_observations * (1 - pow(coalesce(acf1, 0), 2))
             / nullif(1 + pow(coalesce(acf1, 0), 2), 0) < 60
            THEN 'analizable con cautela'
        ELSE 'analizable'
    END AS verdict
FROM stats
ORDER BY panel, n_effective DESC;
