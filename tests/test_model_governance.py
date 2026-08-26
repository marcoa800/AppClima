"""Tests del gobierno de modelos.

La tabla gold_model_skill decide qué se enseña en la interfaz. Estos tests
protegen ese criterio de la erosión: es exactamente el tipo de umbral que, sin
un test, alguien acaba bajando un martes por la tarde para que salga un número
más bonito.
"""

from __future__ import annotations

import pytest


# La conexión viene de conftest.warehouse, que se salta con un mensaje
# claro si no hay warehouse construido en lugar de reventar con un
# error de DuckDB ilegible.
@pytest.fixture
def con(warehouse):
    return warehouse


class TestCriterioDePublicacion:
    def test_ningun_modelo_publicado_tiene_un_corte_negativo(self, con):
        """La condición dura: un modelo que a veces estorba no se publica."""
        malos = con.execute("""
            SELECT DISTINCT model_id, improvement_min
            FROM gold_model_skill
            WHERE should_display AND improvement_min <= 0
        """).fetchall()
        assert malos == [], f"modelos publicados con cortes negativos: {malos}"

    def test_ningun_modelo_publicado_baja_del_umbral(self, con):
        malos = con.execute("""
            SELECT DISTINCT model_id, improvement_median
            FROM gold_model_skill
            WHERE should_display AND improvement_median < 5.0
        """).fetchall()
        assert malos == [], f"modelos publicados por debajo del 5%: {malos}"

    def test_todos_los_modelos_se_evaluan_en_varios_cortes(self, con):
        """Un solo corte fue el fallo de raíz de las tres hipótesis iniciales."""
        pocos = con.execute("""
            SELECT DISTINCT model_id, n_cuts FROM gold_model_skill WHERE n_cuts < 4
        """).fetchall()
        assert pocos == [], f"modelos con menos de 4 cortes: {pocos}"

    def test_la_mediana_no_es_el_maximo(self, con):
        """Si mediana == máximo en todos, el walk-forward no está midiendo nada."""
        rows = con.execute("""
            SELECT DISTINCT model_id, improvement_median, improvement_max
            FROM gold_model_skill
        """).fetchall()
        assert rows, "gold_model_skill está vacía"
        assert any(med < mx for _, med, mx in rows), (
            "ningún modelo varía entre cortes: el walk-forward no está funcionando"
        )

    def test_el_riesgo_de_calor_no_se_publica(self, con):
        """Caso concreto que motivó toda la tabla.

        Declaraba +16,9% en un solo corte; su mediana sobre cinco es ~+3,5%.
        Si alguna vez pasa a publicarse, que sea una decisión consciente que
        rompa este test, no un descuido.
        """
        row = con.execute("""
            SELECT DISTINCT improvement_median, should_display
            FROM gold_model_skill WHERE model_id = 'riesgo_calor_corregido'
        """).fetchone()
        assert row is not None
        median, display = row
        assert median < 16.9, (
            "la mediana coincide con el valor de corte único: sospecha de que "
            "el walk-forward no se está aplicando"
        )
        assert not display


class TestPronosticoReplicas:
    def test_las_replicas_se_suman_no_se_cuentan(self, con):
        """gold_quake_sequences viene agregada por día: count(*) cuenta DÍAS.

        Este bug hizo que el máximo del dataset fuera exactamente 7 (los días 2
        a 8) y que Kamchatka M8.8, con 552 réplicas, figurase con 7. El modelo
        salía 11% peor que la línea base y la conclusión habría sido "no
        funciona".
        """
        max_y, max_n1 = con.execute("""
            SELECT max(y_days_2_8), max(n1) FROM gold_aftershock_forecast
        """).fetchone()
        assert max_y > 50, (
            f"el máximo de réplicas en días 2-8 es {max_y}: si es <= 7 se están "
            "contando días en lugar de réplicas"
        )
        assert max_n1 > 50

    def test_los_principales_estan_declusterizados(self, con):
        """53 de 430 eventos M>=6.5 eran réplicas de otro mayor."""
        brutos = con.execute(
            "SELECT count(*) FROM silver_earthquakes WHERE magnitude >= 6.5"
        ).fetchone()[0]
        independientes = con.execute(
            "SELECT count(*) FROM gold_aftershock_forecast"
        ).fetchone()[0]
        assert independientes < brutos, "no se eliminó ningún evento dependiente"
        assert independientes > brutos * 0.7, "se eliminaron demasiados"

    def test_la_distribucion_es_de_cola_pesada(self, con):
        """Justifica que el producto exponga intervalo y nunca cifra única."""
        media, mediana, maximo = con.execute("""
            SELECT avg(y_days_2_8), median(y_days_2_8), max(y_days_2_8)
            FROM gold_aftershock_forecast WHERE is_predictable
        """).fetchone()
        assert media > mediana * 2, "la cola no es pesada; revisar el supuesto"
        assert maximo > media * 5


class TestVariasLineasBase:
    """El criterio que impide publicar un modelo por su línea base más cómoda.

    Se añadió por el dengue. Contra la climatología, Trujillo mejoraba un 22,9%
    y `should_display` lo habría dado por bueno. Contra la persistencia —"lo
    mismo que hace cuatro semanas"— perdía un 98%. Las dos cifras son ciertas;
    publicar solo la primera habría sido enseñar un modelo peor que la regla
    más tonta posible.
    """

    def test_ningun_modelo_se_publica_perdiendo_alguna_linea_base(self, con):
        incoherentes = con.execute(
            """
            SELECT DISTINCT model_family, scope, model_id, improvement_median
            FROM gold_model_skill
            WHERE should_display AND NOT bate_esta_linea_base
            ORDER BY 1, 2
            """
        ).fetchall()

        assert not incoherentes, (
            "modelos publicados que pierden contra alguna de sus líneas base: "
            f"{incoherentes}"
        )

    def test_el_criterio_de_familia_es_efectivo(self, con):
        """Que la regla no sea decorativa: tiene que estar frenando algo.

        Si algún día deja de frenar, o es que el dengue empezó a funcionar
        —improbable, y entonces habría que celebrarlo mirándolo dos veces— o
        es que alguien quitó la línea base incómoda.
        """
        familias_mixtas = con.execute(
            """
            SELECT model_family, count(DISTINCT model_id) AS lineas_base
            FROM gold_model_skill
            GROUP BY 1
            HAVING count(DISTINCT model_id) > 1
            """
        ).fetchall()

        assert familias_mixtas, (
            "ninguna familia se evalúa ya contra varias líneas base: la regla "
            "existe pero no vigila nada"
        )

    def test_el_pronostico_de_dengue_no_se_publica(self, con):
        """Correlación validada no es habilidad predictiva.

        Trujillo correlaciona r=0,65 con la temperatura de hace cuatro semanas
        y aguanta fuera de muestra, pero pierde contra la persistencia en los
        cuatro cortes. Las doce provincias pierden.

        Si este test falla, lo primero que hay que comprobar no es si el modelo
        mejoró, sino si sigue estando la línea base de persistencia.
        """
        publicadas, total = con.execute(
            """
            SELECT count(CASE WHEN should_display THEN 1 END), count(*)
            FROM (
                SELECT DISTINCT scope, should_display
                FROM gold_model_skill
                WHERE model_family = 'dengue_clima_4sem'
            )
            """
        ).fetchone()

        assert total >= 6, f"solo {total} provincias evaluadas: ¿se perdió el panel?"
        assert publicadas == 0, (
            f"{publicadas} provincias de dengue marcadas como publicables. "
            "Comprobar que sigue evaluándose contra persistencia."
        )
