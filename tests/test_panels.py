"""Tests de los paneles anual y mensual, y de su metadatos de cobertura.

El panel es la herramienta que más facilita cometer el error de correlacionar
sobre ventanas incomparables. Estos tests protegen las barandillas que se
pusieron precisamente para eso.
"""

from __future__ import annotations

import pytest


# La conexión viene de conftest.warehouse, que se salta con un mensaje
# claro si no hay warehouse construido en lugar de reventar con un
# error de DuckDB ilegible.
@pytest.fixture
def con(warehouse):
    return warehouse


class TestPanelMensual:
    def test_el_oni_mensual_multiplica_la_potencia(self, con):
        """La razón de existir del panel mensual.

        Promediar el ONI al año destruye su señal cíclica: con oni_aso la banda
        2-7 años da p=0,011 y con el promedio anual p=0,33, indistinguible de
        ruido. A resolución mensual hay 12 veces más observaciones.
        """
        mensual, anual = con.execute("""
            SELECT
                (SELECT n_observations FROM gold_panel_coverage
                 WHERE panel='gold_month_panel' AND column_name='oni'),
                (SELECT n_observations FROM gold_panel_coverage
                 WHERE panel='gold_year_panel' AND column_name='oni_year_mean')
        """).fetchone()
        assert mensual > anual * 10

    def test_recupera_la_antifase_cuasibienal(self, con):
        """El mínimo de autocorrelación debe caer en 24 meses.

        Es el mismo hallazgo que el panel anual insinuaba a 2 años (-0,295),
        pero medido con 900 observaciones en lugar de 75.
        """
        rows = con.execute("""
            WITH s AS (
                SELECT row_number() OVER (ORDER BY year, month) AS t, oni
                FROM gold_month_panel
                WHERE oni IS NOT NULL AND year BETWEEN 1950 AND 2024
            )
            SELECT k, corr(a.oni, b.oni) AS acf
            FROM (SELECT unnest([12, 18, 24, 30, 36]) AS k) ks
            JOIN s a ON true JOIN s b ON b.t = a.t + ks.k
            GROUP BY k ORDER BY acf
        """).fetchall()
        peor_desfase = rows[0][0]
        assert peor_desfase == 24, f"el mínimo cayó en {peor_desfase} meses, no en 24"
        assert rows[0][1] < -0.2

    def test_las_columnas_desestacionalizadas_tienen_media_cero(self, con):
        """Por construcción: valor menos la media de su mes calendario."""
        media = con.execute("""
            SELECT avg(cyclone_ace_deseason) FROM gold_month_panel
            WHERE cyclone_ace_deseason IS NOT NULL
        """).fetchone()[0]
        assert abs(media) < 0.5

    def test_la_estacionalidad_es_enorme_y_por_eso_hay_que_quitarla(self, con):
        """Justifica que exista la versión _deseason."""
        minimo, maximo = con.execute("""
            SELECT min(m), max(m) FROM (
                SELECT avg(cyclone_ace) AS m FROM gold_month_panel
                WHERE year BETWEEN 1980 AND 2024 GROUP BY month)
        """).fetchone()
        assert maximo > minimo * 4, "sin estacionalidad fuerte, _deseason sobraría"


class TestNEfectivo:
    """El umbral corregido por autocorrelación.

    La primera versión de gold_panel_coverage publicaba 1,96/√n con el n BRUTO.
    Para el ONI mensual eso daba 0,065 cuando el umbral honesto es 0,377: un
    factor de casi 6. Como la tabla existe para decidir qué se puede analizar,
    el error se propagaba a cualquiera que la consultase.
    """

    def test_la_formula_del_n_efectivo_es_la_declarada(self, con):
        """n_eff = n·(1-ρ²)/(1+ρ²), acotado por abajo a 3."""
        rows = con.execute("""
            SELECT n_observations, acf1, n_effective FROM gold_panel_coverage
            WHERE acf1 IS NOT NULL
        """).fetchall()
        assert rows
        for n, acf1, n_eff in rows:
            esperado = max(3, round(n * (1 - acf1 ** 2) / (1 + acf1 ** 2)))
            assert abs(n_eff - esperado) <= 1, f"n={n} acf1={acf1}"

    def test_el_umbral_honesto_nunca_es_menor_que_el_ingenuo(self, con):
        """Corregir solo puede hacer el criterio MÁS exigente."""
        malos = con.execute("""
            SELECT panel, column_name, r_threshold_naive, r_threshold_honest
            FROM gold_panel_coverage
            WHERE r_threshold_honest < r_threshold_naive - 0.001
        """).fetchall()
        assert malos == [], f"umbral honesto por debajo del ingenuo: {malos}"

    def test_el_oni_mensual_no_pasa_el_filtro(self, con):
        """El caso concreto que motivó el arreglo.

        918 observaciones parecen mucha potencia, pero con ACF(1)=0,97 el n
        efectivo es ~27. Si algún día esto vuelve a marcarse como analizable,
        que sea una decisión consciente que rompa este test.
        """
        n, acf1, n_eff, factor, analizable = con.execute("""
            SELECT n_observations, acf1, n_effective, naive_underestimates_by,
                   analyzable
            FROM gold_panel_coverage
            WHERE panel = 'gold_month_panel' AND column_name = 'oni'
        """).fetchone()
        assert n > 900
        assert acf1 > 0.9
        assert n_eff < 50, "el n efectivo debería hundirse por la autocorrelación"
        assert factor > 4, "el umbral ingenuo subestima por un factor grande"
        assert not analizable

    def test_una_tendencia_monotona_es_ininterpretable(self, con):
        """world_population tiene ACF(1)=1: umbral honesto por encima de 1.

        Ninguna correlación contra ella puede significar nada. Cinco de los
        'supervivientes' del panel anual eran parejas con esta columna.
        """
        acf1, n_eff, umbral, analizable = con.execute("""
            SELECT acf1, n_effective, r_threshold_honest, analyzable
            FROM gold_panel_coverage
            WHERE panel = 'gold_year_panel' AND column_name = 'world_population'
        """).fetchone()
        assert acf1 > 0.99
        assert n_eff <= 5
        assert umbral > 1.0, "un umbral > 1 significa que nada puede superarlo"
        assert not analizable

    def test_desestacionalizar_reduce_la_autocorrelacion(self, con):
        """Efecto colateral bueno de las columnas _deseason: más n efectivo."""
        crudo, deseason = con.execute("""
            SELECT
              (SELECT acf1 FROM gold_panel_coverage
               WHERE panel='gold_month_panel' AND column_name='cyclone_ace'),
              (SELECT acf1 FROM gold_panel_coverage
               WHERE panel='gold_month_panel' AND column_name='cyclone_ace_deseason')
        """).fetchone()
        assert deseason < crudo

    def test_el_umbral_ingenuo_se_conserva_solo_como_contraste(self, con):
        """Sigue expuesto para poder VER la diferencia, no para decidir."""
        columnas = {r[0] for r in con.execute("DESCRIBE gold_panel_coverage").fetchall()}
        assert "r_threshold_naive" in columnas
        assert "r_threshold_honest" in columnas
        assert "naive_underestimates_by" in columnas


class TestCoberturaDeColumnas:
    def test_las_columnas_de_muestra_minima_estan_marcadas(self, con):
        """n=11 da un umbral de 0,591: nada por debajo significa algo.

        Un agente llegó a reportar 'tsunamigenic cae, r=-0,639 significativa'.
        Con once observaciones eso es ruido, y ahora la tabla lo dice.
        """
        no_analizables = {
            r[0] for r in con.execute("""
                SELECT column_name FROM gold_panel_coverage
                WHERE panel='gold_year_panel' AND NOT analyzable
            """).fetchall()
        }
        for col in ("tsunamigenic", "quakes_m7", "max_magnitude",
                    "aftershock_sequences"):
            assert col in no_analizables, f"{col} debería estar marcada"

    def test_el_umbral_ingenuo_sigue_la_formula(self, con):
        """1.96/sqrt(n) sobre el n bruto: es la cifra de contraste."""
        rows = con.execute("""
            SELECT n_observations, r_threshold_naive
            FROM gold_panel_coverage WHERE n_observations > 0
        """).fetchall()
        assert rows
        for n, umbral in rows:
            assert abs(umbral - 1.96 / (n ** 0.5)) < 0.002

    def test_ninguna_columna_queda_sin_veredicto(self, con):
        sin = con.execute("""
            SELECT count(*) FROM gold_panel_coverage WHERE verdict IS NULL
        """).fetchone()[0]
        assert sin == 0


class TestRegimenesDeCobertura:
    def test_los_regimenes_son_bloques_contiguos(self, con):
        """Cada régimen debe ser un tramo de años sin huecos."""
        rows = con.execute("""
            SELECT coverage_regime, min(year), max(year), count(*)
            FROM gold_year_panel GROUP BY 1 ORDER BY 1
        """).fetchall()
        assert len(rows) >= 4, "se esperaban varios regímenes de cobertura"
        for _, primero, ultimo, n in rows:
            assert ultimo - primero + 1 == n, "el régimen tiene huecos"

    def test_la_cobertura_crece_con_el_tiempo(self, con):
        """El sesgo documental, medido: es la señal más fuerte del panel."""
        r = con.execute("""
            SELECT corr(year, sources_available) FROM gold_year_panel
            WHERE year <= 2025
        """).fetchone()[0]
        assert r > 0.8, (
            "si esto baja, el panel cambió y hay que revisar todas las "
            "conclusiones que dependen de ventanas homogéneas"
        )

    def test_se_retiro_la_marca_no_fiable(self, con):
        """`data_coverage_change` venía del catálogo y era engañosa.

        Marcaba 1940 y 1979 (años de ARRANQUE de una fuente) pero dejaba sin
        marcar el tramo posterior, que es donde la serie ya cambió de
        naturaleza. Se sustituyó por `coverage_regime_change`, calculado desde
        los datos.
        """
        columnas = {
            r[0] for r in con.execute("DESCRIBE gold_year_panel").fetchall()
        }
        assert "data_coverage_change" not in columnas
        assert "coverage_regime_change" in columnas
        assert "coverage_regime" in columnas
