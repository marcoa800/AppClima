"""Invariantes de los días sin precedente.

El modelo cuenta días que superan todo lo registrado en su misma época del año
durante los trece años anteriores, y lo compara con lo que cabría esperar bajo
clima estacionario. La trampa que evita es que **los récords se vuelven más
raros con el tiempo aunque nada cambie**: con n valores previos, la
probabilidad de que el siguiente los supere todos es 1/(n+1).
"""

from __future__ import annotations


def test_la_esperanza_es_la_de_un_clima_estacionario(warehouse) -> None:
    """dias_esperados debe ser exactamente dias_evaluados / (n_referencia + 1).

    Si esta cuenta se desviara, todas las razones publicadas estarían mal por
    el mismo factor y nadie lo notaría: seguirían siendo números plausibles.
    """
    desviados = warehouse.execute(
        """
        SELECT location_id, dias_esperados,
               round(dias_evaluados / (n_referencia + 1), 1) AS deberia_ser
        FROM gold_unprecedented_weather
        WHERE abs(dias_esperados - dias_evaluados / (n_referencia + 1)) > 0.15
        """
    ).fetchall()
    assert not desviados, f"la esperanza no cuadra: {desviados}"


def test_la_referencia_tiene_el_tamano_previsto(warehouse) -> None:
    """15 días de calendario × 13 años = 195, con margen por bisiestos."""
    minimo, maximo = warehouse.execute(
        "SELECT min(n_referencia), max(n_referencia) FROM gold_unprecedented_weather"
    ).fetchone()
    assert minimo >= 180 and maximo <= 210, (
        f"ventana de referencia entre {minimo} y {maximo}: se esperaba ~195"
    )


def test_el_calor_domina_sobre_el_frio(warehouse) -> None:
    """El hallazgo, escrito como invariante.

    Un clima más VARIABLE produciría más récords de calor y también más de
    frío. Uno que se calienta produce más de calor y menos de frío. La
    asimetría es la prueba, y no depende de ninguna serie externa.
    """
    n, calor_gana, r_calor, r_frio = warehouse.execute(
        """
        SELECT count(*),
               sum(CASE WHEN razon_calor > razon_frio THEN 1 ELSE 0 END),
               round(avg(razon_calor), 2), round(avg(razon_frio), 2)
        FROM gold_unprecedented_weather
        """
    ).fetchone()

    assert n >= 20, f"solo {n} ciudades evaluadas"
    assert r_calor > 2 * r_frio, (
        f"la asimetría se perdió: calor {r_calor}, frío {r_frio}. Antes de "
        "celebrarlo, comprobar la procedencia del archivo climático"
    )
    assert calor_gana >= 0.75 * n, (
        f"solo {calor_gana} de {n} ciudades tienen más récords de calor que de frío"
    )


def test_ninguna_ciudad_por_debajo_de_lo_esperado(warehouse) -> None:
    """Con 30 ciudades, que ni una sola esté por debajo de 1 es el resultado."""
    debajo = warehouse.execute(
        """
        SELECT location_id, razon_calor FROM gold_unprecedented_weather
        WHERE razon_calor < 1.0 ORDER BY razon_calor
        """
    ).fetchall()
    assert not debajo, (
        f"ciudades con menos días de calor sin precedente de los esperados: {debajo}"
    )


def test_invertir_las_ventanas_da_el_espejo(warehouse) -> None:
    """La comprobación que caza un bug en la lógica de ventanas.

    Si se toma 2019-2025 como referencia y se evalúa 2006-2012, un clima
    estacionario daría razones cercanas a 1 en ambos sentidos. Con tendencia
    tiene que volcarse: pocos récords de calor y muchos de frío.

    Medido: hacia adelante calor ×4,63 y frío ×1,15; invertido calor ×0,48 y
    frío ×2,19. Si el invertido dejara de volcarse, el modelo estaría contando
    algo que no es una tendencia.
    """
    calor, frio = warehouse.execute(
        """
        WITH base AS (
            SELECT location_id, dayofyear(local_date) AS doy,
                   year(local_date) AS yr, temp_max, temp_min
            FROM gold_weather_daily
            WHERE kind = 'observed' AND model = 'era5_seamless'
              AND temp_max IS NOT NULL
        ),
        ref AS (SELECT * FROM base WHERE yr BETWEEN 2019 AND 2025),
        ev  AS (SELECT * FROM base WHERE yr BETWEEN 2006 AND 2012),
        lim AS (
            SELECT e.location_id, e.temp_max, e.temp_min,
                   max(r.temp_max) AS rmax, min(r.temp_min) AS rmin, count(*) AS n
            FROM ev e
            JOIN ref r ON r.location_id = e.location_id
                      AND doy_distance(r.doy, e.doy) <= 7
            GROUP BY 1, 2, 3, e.doy, e.yr
        )
        SELECT round(avg(cal), 2), round(avg(fri), 2) FROM (
            SELECT location_id,
                sum(CASE WHEN temp_max > rmax THEN 1 ELSE 0 END)
                    / (count(*) / (avg(n) + 1)) AS cal,
                sum(CASE WHEN temp_min < rmin THEN 1 ELSE 0 END)
                    / (count(*) / (avg(n) + 1)) AS fri
            FROM lim GROUP BY 1
        )
        """
    ).fetchone()

    assert calor < 1.0, f"invertido, el calor sigue por encima de lo esperado: {calor}"
    assert frio > calor, f"invertido, el frío no domina: frío {frio}, calor {calor}"
