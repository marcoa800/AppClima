"""Invariantes del cruce clima-dengue.

Los dos primeros vigilan errores que ya ocurrieron durante la construcción y
que no rompen nada al ocurrir: el almacén se construye igual, las tablas
existen y los números parecen razonables.
"""

from __future__ import annotations


def test_la_deduplicacion_no_colapsa_el_dataset(warehouse) -> None:
    """El `UUID` de OpenDengue identifica el boletín, no la fila.

    Deduplicar por uuid dejaba 1.005 filas de 99.579 y borraba el 99% del
    dataset sin que nada fallara. Perú pasaba de 116 provincias a tres.
    """
    filas, provincias = warehouse.execute(
        """
        SELECT count(*), count(DISTINCT adm_2_name)
        FROM silver_dengue
        WHERE country_name = 'PERU' AND spatial_res = 'Admin2'
        """
    ).fetchone()

    assert filas > 30_000, f"silver_dengue solo tiene {filas} filas peruanas"
    assert provincias > 100, f"solo {provincias} provincias peruanas: ¿se colapsó la clave?"


def test_las_semanas_sin_casos_son_ceros_explicitos(warehouse) -> None:
    """OpenDengue omite las semanas sin casos; el panel debe rellenarlas.

    Sin el relleno, cualquier correlación clima-casos usaría solo las semanas
    en las que hubo enfermos, que es condicionar sobre el resultado.
    """
    total, con_cero = warehouse.execute(
        """
        SELECT count(*), count(CASE WHEN casos = 0 THEN 1 END)
        FROM gold_dengue_peru
        """
    ).fetchone()

    assert con_cero > 0, (
        "El panel no tiene ni una semana con cero casos, y la fuente nunca "
        "publica ceros: el relleno de la rejilla no se está aplicando"
    )
    # Piura sola tiene 473 semanas sin casos de 1.252.
    assert con_cero > total * 0.3, (
        f"Solo {con_cero} de {total} semanas a cero: la rejilla está incompleta"
    )


def test_el_panel_es_una_rejilla_completa(warehouse) -> None:
    """Todas las provincias comparten el mismo calendario, sin huecos."""
    distintos = warehouse.execute(
        """
        SELECT count(DISTINCT n) FROM (
            SELECT location_id, count(*) AS n FROM gold_dengue_peru GROUP BY 1
        )
        """
    ).fetchone()[0]

    assert distintos == 1, (
        "Las provincias tienen distinto número de semanas: la rejilla no es "
        "un producto cartesiano y las comparaciones entre ellas están sesgadas"
    )


def test_el_gradiente_termico_se_mantiene(warehouse) -> None:
    """Lo que sí sobrevivió: ninguna provincia fría transmite.

    El umbral nítido se cayó al limpiar el termómetro, pero el gradiente no.
    Ninguna provincia por debajo de 15 °C llega a diez casos en 24 años,
    mientras que las de más de 20 °C suman cientos de miles.
    """
    frias, calidas = warehouse.execute(
        """
        SELECT
            max(CASE WHEN temp_media_c < 15 THEN casos_total END),
            min(CASE WHEN temp_media_c > 20 THEN casos_total END)
        FROM gold_dengue_temperature
        """
    ).fetchone()

    assert frias < 10, f"Una provincia bajo 15 °C acumula {frias} casos"
    assert calidas > 1000, f"Una provincia sobre 20 °C solo tiene {calidas} casos"


def test_el_umbral_no_se_reafirma_por_accidente(warehouse) -> None:
    """Guardia contra revivir una afirmación que ya se cayó.

    Con un solo reanálisis, Lima y Tacna están a la misma temperatura (18,88 °C)
    con resultados opuestos: 32.466 casos frente a cero. La separación por
    temperatura media NO es perfecta, y la tabla debe seguir diciéndolo.

    Si algún día este test fallara porque `separacion_perfecta` pasó a ser
    cierta, no es una buena noticia automática: hay que comprobar primero que
    no sea otra vez el termómetro. Fue así la primera vez.
    """
    perfecta = warehouse.execute(
        "SELECT DISTINCT separacion_perfecta FROM gold_dengue_temperature"
    ).fetchall()

    assert perfecta == [(False,)], (
        "gold_dengue_temperature afirma separación perfecta por temperatura. "
        "Revisar la procedencia del clima antes de creerlo."
    )


def test_el_clima_del_panel_viene_de_un_solo_reanalisis(warehouse) -> None:
    """El filtro de procedencia es lo que sostiene todo lo anterior."""
    modelos = warehouse.execute(
        """
        SELECT DISTINCT w.model
        FROM gold_dengue_peru d
        JOIN gold_weather_daily w
          ON w.location_id = d.location_id
         AND w.local_date BETWEEN d.period_start AND d.period_end
         AND w.kind = 'observed'
        WHERE d.clima_completo
        """
    ).fetchall()

    assert modelos == [("era5_seamless",)], (
        f"El panel de dengue mezcla reanálisis: {modelos}"
    )
