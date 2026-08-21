-- Índice ONI de El Niño / La Niña.
--
-- Grano: (year, season).
--
-- Los "trimestres" de este índice son ventanas SOLAPADAS: DJF es dic-ene-feb,
-- JFM es ene-feb-mar. Cada mes aparece en tres estaciones distintas, lo cual es
-- correcto porque se trata de una media móvil de tres meses, no de una
-- partición del año.
--
-- La consecuencia práctica: agregar por año promediando las 12 estaciones da un
-- resultado razonable (cada mes pesa lo mismo, tres veces), pero SUMARLAS
-- triplicaría el total. Nunca sumar este índice.
--
-- Los umbrales ±0,5 °C son los oficiales de la NOAA para declarar fase. Un
-- episodio oficial además exige cinco trimestres consecutivos por encima del
-- umbral; aquí se marca la fase trimestre a trimestre, que es más granular y
-- suficiente para correlacionar.

CREATE OR REPLACE TABLE silver_oni AS
WITH ranked AS (
    SELECT
        * EXCLUDE (ingest_date, _source),
        row_number() OVER (
            PARTITION BY year, season ORDER BY _ingested_at DESC
        ) AS _rn
    FROM {{bronze_oni}}
)
SELECT
    * EXCLUDE (_rn),
    CASE
        WHEN anomaly_c >= 0.5 THEN 'El Niño'
        WHEN anomaly_c <= -0.5 THEN 'La Niña'
        ELSE 'Neutral'
    END AS phase,
    CASE
        WHEN anomaly_c >= 2.0 THEN 'El Niño muy fuerte'
        WHEN anomaly_c >= 1.5 THEN 'El Niño fuerte'
        WHEN anomaly_c >= 1.0 THEN 'El Niño moderado'
        WHEN anomaly_c >= 0.5 THEN 'El Niño débil'
        WHEN anomaly_c <= -1.5 THEN 'La Niña fuerte'
        WHEN anomaly_c <= -1.0 THEN 'La Niña moderada'
        WHEN anomaly_c <= -0.5 THEN 'La Niña débil'
        ELSE 'Neutral'
    END AS intensity
FROM ranked
WHERE _rn = 1;
