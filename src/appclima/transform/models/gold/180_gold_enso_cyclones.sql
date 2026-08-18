-- El Niño frente a la actividad ciclónica por cuenca.
--
-- Grano: (basin, phase).
--
-- **Este es el modelo predictivo del proyecto, y el único que merece ese
-- nombre.** Todo lo demás describe el pasado; esto relaciona una variable que
-- se conoce con meses de antelación (el estado de ENSO) con algo que aún no ha
-- ocurrido (la temporada de ciclones).
--
-- El mecanismo físico es conocido y va en direcciones OPUESTAS según la cuenca:
-- durante El Niño, la cizalladura vertical del viento aumenta sobre el
-- Atlántico y decapita las tormentas en formación, mientras que en el Pacífico
-- oriental y central las condiciones mejoran. Por eso agrupar todas las cuencas
-- juntas da casi cero: las señales se cancelan entre sí.
--
-- Se usa la fase de ASO (agosto-septiembre-octubre), el pico de la temporada en
-- el hemisferio norte. Para el hemisferio sur el emparejamiento año-temporada
-- no es correcto — su temporada cruza el cambio de año — y por eso SI, SP y SA
-- quedan fuera del análisis en lugar de colarse con un desfase silencioso.

CREATE OR REPLACE TABLE gold_enso_cyclones AS
WITH season_phase AS (
    -- ASO: el pico de la temporada del hemisferio norte.
    SELECT year, anomaly_c, phase, intensity
    FROM silver_oni
    WHERE season = 'ASO'
),
northern AS (
    SELECT s.season AS year, s.basin, s.ace_total, s.hurricanes,
           s.major_hurricanes, s.systems
    FROM gold_cyclone_seasons s
    -- Solo cuencas del hemisferio norte: su temporada cabe dentro del año civil.
    WHERE s.basin IN ('NA', 'EP', 'WP', 'NI')
      AND s.season BETWEEN 1980 AND 2024
)
SELECT
    n.basin,
    p.phase,
    count(*) AS seasons,
    round(avg(n.ace_total), 1) AS ace_mean,
    round(avg(n.hurricanes), 1) AS hurricanes_mean,
    round(avg(n.major_hurricanes), 1) AS major_hurricanes_mean,
    round(avg(n.systems), 1) AS systems_mean,

    -- Correlación entre la anomalía ONI y el ACE dentro de cada cuenca. El
    -- signo es lo interesante: negativo en el Atlántico, positivo en el
    -- Pacífico oriental.
    round(corr(p.anomaly_c, n.ace_total), 3) AS r_oni_vs_ace
FROM northern n
JOIN season_phase p ON p.year = n.year
GROUP BY 1, 2
ORDER BY basin, phase;
