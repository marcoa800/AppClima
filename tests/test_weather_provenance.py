"""Vigila que el archivo climático no esté cosido a partir de varios modelos.

**El bug que motiva este fichero.** El archivo de Open-Meteo, si no se le fija
el modelo, usa `best_match`: sirve ERA5 hasta 2016 y el análisis operativo del
IFS de ECMWF desde 2017. La serie resultante no tiene huecos, ni nulos, ni
avisos — pero tiene una costura en enero de 2017 que se lee como si fuera
clima.

En Tacna la costura vale 2,44 °C. Se manifestó como un enfriamiento de 1,7 °C
por década, que no es un valor físico. Ningún test lo habría detectado, porque
todos comprobaban completitud y rangos, y el dato era completo y plausible.

Lo que sí lo detecta es preguntar por la **procedencia**: una ciudad no puede
tener dos modelos distintos en su archivo observado.
"""

from __future__ import annotations

from appclima.sources import open_meteo


def test_el_archivo_fija_el_modelo() -> None:
    """`best_match` cambia de reanálisis a mitad de serie. No vale por defecto."""
    assert open_meteo.ARCHIVE_MODEL == "era5_seamless"
    assert open_meteo.ARCHIVE_MODEL != "best_match"


def test_fetch_archive_propaga_el_modelo() -> None:
    """El modelo debe llegar a la petición, no quedarse en la constante."""
    import inspect

    fuente = inspect.getsource(open_meteo.fetch_archive)
    assert "model=ARCHIVE_MODEL" in fuente, (
        "fetch_archive no pasa ARCHIVE_MODEL a _fetch: la constante existe "
        "pero la API sigue eligiendo el modelo por su cuenta"
    )


def test_ninguna_ciudad_mezcla_modelos(warehouse) -> None:
    """El invariante de fondo: un archivo, un reanálisis."""
    mezcladas = warehouse.execute(
        """
        SELECT location_id,
               string_agg(DISTINCT coalesce(model, '(sin registrar)'), ', ') AS cuales
        FROM silver_weather_hourly
        WHERE kind = 'observed'
        GROUP BY 1
        -- coalesce ANTES del count: `count(DISTINCT model)` descarta los NULL,
        -- y las filas contaminadas son precisamente las que tienen model NULL,
        -- porque se ingirieron antes de que existiera la columna. Sin el
        -- coalesce, este test miraba justo donde no estaba el problema.
        HAVING count(DISTINCT coalesce(model, '(sin registrar)')) > 1
        ORDER BY 1
        """
    ).fetchall()

    assert not mezcladas, (
        "Estas ciudades tienen su archivo cosido a partir de varios modelos, "
        f"así que sus tendencias miden el cambio de modelo: {mezcladas}"
    )


def test_los_saltos_grandes_no_coinciden_con_cambios_de_modelo(warehouse) -> None:
    """Distingue el artefacto de la variación climática real.

    Un salto interanual grande no es sospechoso por sí solo: la costa peruana
    subió más de 2,5 °C en 2023 con El Niño costero, y el Ártico oscila aún
    más. Lo que no puede ser casualidad es que el salto caiga **justo** en el
    año en que cambia el modelo de origen.

    Ese es exactamente el patrón de Tacna: ERA5 hasta 2016, IFS desde 2017,
    -2,83 °C en la juntura.
    """
    sospechosos = warehouse.execute(
        """
        WITH anual AS (
            SELECT location_id, year(local_date) AS anio,
                   avg(temp_mean) AS t,
                   any_value(coalesce(model, '(sin registrar)')) AS modelo
            FROM gold_weather_daily
            WHERE kind = 'observed'
            GROUP BY 1, 2
            HAVING count(*) >= 350          -- solo años completos
        ),
        pares AS (
            SELECT location_id, anio, modelo,
                   t - lag(t)      OVER (PARTITION BY location_id ORDER BY anio) AS salto,
                   lag(modelo)     OVER (PARTITION BY location_id ORDER BY anio) AS modelo_previo
            FROM anual
        )
        SELECT location_id, anio, round(salto, 2), modelo_previo, modelo
        FROM pares
        WHERE abs(salto) > 2.0 AND modelo IS DISTINCT FROM modelo_previo
        ORDER BY abs(salto) DESC
        """
    ).fetchall()

    assert not sospechosos, (
        "Salto interanual mayor de 2 °C que coincide con un cambio de modelo: "
        f"es la costura, no el clima. {sospechosos}"
    )
