-- Actividad ciclónica por temporada y cuenca.
--
-- Grano: (season, basin).
--
-- Esta es la tabla donde se puede buscar tendencia de verdad, y por un motivo
-- muy concreto: **arranca en 1980**, cuando la cobertura satelital ya era
-- global. A diferencia de los desastres históricos o del catálogo de ciclones
-- completo desde 1842, aquí el sesgo de observación no domina la señal.
--
-- Sigue habiendo un matiz honesto: la capacidad de estimar la INTENSIDAD ha
-- mejorado desde 1980 (mejores satélites, más vuelos de reconocimiento en el
-- Atlántico). Así que una tendencia al alza en ACE es interpretable, pero no
-- está libre de sesgo instrumental. Lo que sí es sólido es comparar cuencas
-- entre sí dentro del mismo año.

CREATE OR REPLACE TABLE gold_cyclone_seasons AS
SELECT
    season,
    basin,
    count(*) AS systems,
    sum(CASE WHEN reached_tropical_storm THEN 1 ELSE 0 END) AS tropical_storms,
    sum(CASE WHEN reached_hurricane THEN 1 ELSE 0 END) AS hurricanes,
    sum(CASE WHEN reached_major_hurricane THEN 1 ELSE 0 END) AS major_hurricanes,
    sum(CASE WHEN made_landfall THEN 1 ELSE 0 END) AS landfalling,

    round(sum(ace), 2) AS ace_total,
    round(avg(ace), 3) AS ace_mean_per_system,
    max(max_wind_kt) AS strongest_wind_kt,
    min(min_pressure_mb) AS lowest_pressure_mb,
    round(avg(duration_days), 2) AS mean_duration_days
FROM gold_cyclones
WHERE basin IS NOT NULL
GROUP BY 1, 2
ORDER BY season, basin;
