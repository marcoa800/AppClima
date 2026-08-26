-- ¿Predice el clima de hace k semanas los casos de dengue de esta semana?
--
-- Grano: (location_id, lag_semanas).
--
-- ══ Por qué este modelo y no el 290 ═════════════════════════════════════════
--
-- El modelo 290 compara provincias entre sí, y ese diseño no puede, él solo,
-- sostener una relación causal: las provincias cálidas también son más pobres,
-- más húmedas, más urbanas y tienen otro sistema sanitario. Cualquiera de esas
-- cosas explicaría el escalón.
--
-- Aquí la comparación es **de una provincia consigo misma**. Todo lo que no
-- cambia semana a semana —la pobreza, la altitud, el sistema de salud, la
-- densidad, la cultura— queda controlado por construcción. Es la mitad del
-- argumento que el 290 no puede dar.
--
-- ══ Las tres correcciones, y qué pasa sin ellas ═════════════════════════════
--
-- 1. **Estacionalidad.** El calor y el dengue suben los dos en verano.
--    Correlacionar las series en bruto no mide una relación: mide que ambas
--    tienen verano. Por eso se trabaja con anomalías respecto a la media de
--    esa misma semana del año en esa misma provincia.
--
-- 2. **Escala.** Los casos son un recuento con cola larguísima: Piura pasa de
--    0 a 1.200 en una semana. Una correlación de Pearson sobre eso la deciden
--    tres semanas de 2017. Se usa log(1+casos), que además convierte el
--    crecimiento epidémico —multiplicativo— en algo lineal.
--
-- 3. **Autocorrelación.** Dos semanas seguidas no son dos datos
--    independientes: si hubo brote el martes, lo hay el jueves. Con 939
--    semanas el umbral ingenuo de significación es r=0,064, y basta con eso
--    para "descubrir" cualquier cosa. El n efectivo, n(1-ρ²)/(1+ρ²), suele
--    dejarlo en unas pocas decenas.
--
-- ══ Por qué se prueban retardos de 0 a 20 semanas ═══════════════════════════
--
-- Porque la biología dice dónde debería estar el máximo, y eso convierte el
-- barrido en una predicción falsable en vez de una pesca. Entre el clima y el
-- caso notificado median el ciclo del mosquito (1-3 semanas), la incubación
-- extrínseca (1-2), la incubación humana (~1) y el retraso de notificación
-- (1-2): entre 4 y 12 semanas.
--
-- Un máximo en ese rango apoya el mecanismo. Un máximo en el retardo 0, o en
-- el 19, es casi con seguridad ruido o estacionalidad mal quitada — y el
-- retardo negativo no se prueba porque significaría que los casos predicen el
-- clima anterior, que es el control que delata un análisis mal montado.
--
-- ══ Corrección por comparaciones múltiples ══════════════════════════════════
--
-- Se prueban 21 retardos × 2 variables por ciudad. Con 42 pruebas, el umbral
-- del 5% produce dos "hallazgos" por ciudad solo por azar. `r_umbral_bonferroni`
-- aplica la corrección; `significativo` la exige.

CREATE OR REPLACE TABLE gold_dengue_lags AS
WITH base AS (
    SELECT
        location_id,
        provincia,
        period_start,
        year,
        semana_iso,
        ln(1 + casos)  AS log_casos,
        temp_media_c,
        precip_mm
    FROM gold_dengue_peru
    WHERE clima_completo
      -- Transmisión REAL, no solo un caso suelto. `provincia_notificante` deja
      -- pasar a Huancayo con 3 casos en 24 años, y esa serie es prácticamente
      -- una constante de ceros: su autocorrelación sale 0, el n efectivo se
      -- infla de 37 a 937 y el umbral honesto se desploma a 0,10. Resultado:
      -- una r de -0,10 aparecía como "significativa". El filtro no es de
      -- conveniencia, es lo que impide que el ruido pase el corte.
      AND location_id IN (
          SELECT location_id FROM gold_dengue_peru
          GROUP BY 1
          HAVING sum(casos) >= 100
             AND sum(CASE WHEN casos > 0 THEN 1 ELSE 0 END) >= 50
      )
),

-- Climatología propia de cada provincia: la media de esa semana del año.
climatologia AS (
    SELECT
        location_id,
        semana_iso,
        avg(log_casos)    AS log_casos_normal,
        avg(temp_media_c) AS temp_normal,
        avg(precip_mm)    AS precip_normal
    FROM base
    GROUP BY 1, 2
),

anomalias AS (
    SELECT
        b.location_id,
        b.provincia,
        b.period_start,
        b.year,
        b.log_casos    - c.log_casos_normal AS a_casos,
        b.temp_media_c - c.temp_normal      AS a_temp,
        b.precip_mm    - c.precip_normal    AS a_precip,
        -- Índice entero de semana, para desplazar sin depender de fechas.
        row_number() OVER (PARTITION BY b.location_id ORDER BY b.period_start) AS t
    FROM base b
    JOIN climatologia c
      ON c.location_id = b.location_id AND c.semana_iso = b.semana_iso
),

lags(lag_semanas) AS (
    SELECT * FROM range(0, 21)
),

emparejado AS (
    SELECT
        a.location_id,
        a.provincia,
        a.year,
        l.lag_semanas,
        a.a_casos,
        p.a_temp,
        p.a_precip
    FROM anomalias a
    CROSS JOIN lags l
    JOIN anomalias p
      ON p.location_id = a.location_id
     AND p.t = a.t - l.lag_semanas
),

-- Autocorrelación de la propia serie de casos: es la que manda al calcular
-- cuántos datos independientes hay realmente.
-- `corr` devuelve NaN, no NULL, cuando una de las series es constante — y NaN
-- se propaga en silencio hasta reventar el cast a entero del n efectivo. Se
-- sanea aquí, en el origen, en vez de parchearlo en cada uso.
persistencia AS (
    SELECT
        location_id,
        CASE WHEN isnan(corr(a_casos, prev)) THEN NULL
             ELSE corr(a_casos, prev) END AS acf1
    FROM (
        SELECT location_id, a_casos,
               lag(a_casos) OVER (PARTITION BY location_id ORDER BY t) AS prev
        FROM anomalias
    )
    WHERE prev IS NOT NULL
    GROUP BY 1
),

-- ══ La partición temporal, que es la que decide ═════════════════════════════
--
-- El retardo con la r más alta se elige mirando los datos, así que su r está
-- inflada por construcción. Lo que no se puede inflar es que esa MISMA r, con
-- el retardo ya fijado, aguante en años que no participaron en elegirlo.
--
-- La partición es temporal (≤2016 / ≥2017), nunca aleatoria: repartir semanas
-- al azar pondría la semana siguiente a un brote en el conjunto de prueba y
-- mediría persistencia, no predicción.
--
-- Es lo que separa el grano de la paja: Piura pasa de r=0,485 a r=0,045 y se
-- cae, mientras Trujillo pasa de 0,507 a 0,759 y se refuerza.
crudo AS (
    SELECT
        e.location_id,
        any_value(e.provincia)          AS provincia,
        e.lag_semanas,
        count(*)                        AS n,
        corr(CASE WHEN e.year <= 2016 THEN e.a_casos END,
             CASE WHEN e.year <= 2016 THEN e.a_temp  END) AS r_temp_entreno,
        corr(CASE WHEN e.year >= 2017 THEN e.a_casos END,
             CASE WHEN e.year >= 2017 THEN e.a_temp  END) AS r_temp_prueba,
        count(CASE WHEN e.year <= 2016 THEN 1 END)        AS n_entreno,
        count(CASE WHEN e.year >= 2017 THEN 1 END)        AS n_prueba,
        CASE WHEN isnan(corr(e.a_casos, e.a_temp)) THEN NULL
             ELSE corr(e.a_casos, e.a_temp) END   AS r_temp,
        CASE WHEN isnan(corr(e.a_casos, e.a_precip)) THEN NULL
             ELSE corr(e.a_casos, e.a_precip) END AS r_precip
    FROM emparejado e
    GROUP BY e.location_id, e.lag_semanas
)

SELECT
    c.location_id,
    c.provincia,
    c.lag_semanas,
    c.n,

    round(c.r_temp, 4)   AS r_temp,
    round(c.r_precip, 4) AS r_precip,

    round(p.acf1, 4)     AS acf1_casos,

    -- n efectivo, acotado por abajo a 3 como en el resto del proyecto: con
    -- ρ≈1 el n efectivo tiende a cero y el umbral saldría mayor que 1.
    greatest(3, round(
        c.n * (1 - pow(coalesce(p.acf1, 0), 2))
            / nullif(1 + pow(coalesce(p.acf1, 0), 2), 0)
    ))::INTEGER AS n_efectivo,

    round(1.96 / sqrt(nullif(c.n, 0)), 4) AS r_umbral_ingenuo,

    round(1.96 / sqrt(greatest(3.0,
        c.n * (1 - pow(coalesce(p.acf1, 0), 2))
            / nullif(1 + pow(coalesce(p.acf1, 0), 2), 0))), 4) AS r_umbral_honesto,

    -- Bonferroni sobre las 42 pruebas por ciudad (21 retardos × 2 variables).
    -- z para α=0,05/42 ≈ 3,08.
    round(3.08 / sqrt(greatest(3.0,
        c.n * (1 - pow(coalesce(p.acf1, 0), 2))
            / nullif(1 + pow(coalesce(p.acf1, 0), 2), 0))), 4) AS r_umbral_bonferroni,

    -- El retardo cae donde la biología dice que debería.
    c.lag_semanas BETWEEN 4 AND 12 AS lag_plausible,

    abs(c.r_temp) > 3.08 / sqrt(greatest(3.0,
        c.n * (1 - pow(coalesce(p.acf1, 0), 2))
            / nullif(1 + pow(coalesce(p.acf1, 0), 2), 0)))
        AS temp_significativa,

    abs(c.r_precip) > 3.08 / sqrt(greatest(3.0,
        c.n * (1 - pow(coalesce(p.acf1, 0), 2))
            / nullif(1 + pow(coalesce(p.acf1, 0), 2), 0)))
        AS precip_significativa,

    -- % de varianza de los casos explicada. Una r de 0,2 "significativa"
    -- explica el 4%: significativo y despreciable a la vez.
    round(c.r_temp_entreno, 4) AS r_temp_entreno,
    round(c.r_temp_prueba, 4)  AS r_temp_prueba,
    c.n_entreno,
    c.n_prueba,

    -- EL CRITERIO. No basta con ser significativo en el total: hay que
    -- mantener al menos el 60% de la correlación en años que no se usaron
    -- para elegir el retardo, y hacerlo en la ventana biológica.
    (abs(c.r_temp_prueba) >= 0.6 * abs(c.r_temp_entreno)
     AND abs(c.r_temp) > 3.08 / sqrt(greatest(3.0,
         c.n * (1 - pow(coalesce(p.acf1, 0), 2))
             / nullif(1 + pow(coalesce(p.acf1, 0), 2), 0)))
    ) AS aguanta_fuera_de_muestra,

    round(100 * pow(c.r_temp, 2), 2)   AS pct_varianza_temp,
    round(100 * pow(c.r_precip, 2), 2) AS pct_varianza_precip

FROM crudo c
LEFT JOIN persistencia p USING (location_id)
ORDER BY c.location_id, c.lag_semanas;
