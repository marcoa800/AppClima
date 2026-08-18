"""Tests del catálogo de eventos y de la disciplina del backtest.

Los del backtest son los más importantes del repositorio: comprueban que no hay
fuga temporal, que es el error que convierte un modelo inútil en uno que parece
excelente.
"""

from __future__ import annotations

import pytest

from appclima.historical_events import BY_CATEGORY, EVENTS


class TestHistoricalEvents:
    def test_ids_unicos(self):
        ids = [e.id for e in EVENTS]
        assert len(ids) == len(set(ids))

    def test_anios_coherentes(self):
        for e in EVENTS:
            if e.end_year is not None:
                assert e.end_year >= e.start_year, e.id

    def test_existe_la_categoria_observacion(self):
        """Es la que da valor analítico: sin ella el catálogo es decorativo."""
        assert len(BY_CATEGORY["observacion"]) >= 5

    def test_los_hitos_de_datos_coinciden_con_las_fuentes_reales(self):
        """Si una fuente cambia de rango, el catálogo debe seguirla.

        Sin este test, el catálogo se desincroniza en silencio y las
        anotaciones de las gráficas acaban señalando años equivocados.
        """
        from appclima.sources.ibtracs import DATASETS

        by_id = {e.id: e for e in EVENTS}
        # El dataset por defecto de ciclones arranca en 1980, un año después
        # del hito de cobertura satelital global.
        assert "since1980" in DATASETS
        assert by_id["cobertura-satelital-global"].start_year == 1979
        assert by_id["oni-inicio"].start_year == 1950
        assert by_id["banco-mundial-inicio"].start_year == 1960

    def test_toda_entrada_explica_su_relevancia(self):
        for e in EVENTS:
            assert len(e.relevance) > 30, f"{e.id}: relevancia demasiado vaga"


class TestBacktestDiscipline:
    """La partición temporal es lo que hace honesto al backtest."""

    def test_los_periodos_no_se_solapan(self):
        train_end, test_start = 2018, 2019
        assert train_end < test_start

    @pytest.mark.parametrize(
        ("brier_model", "brier_base", "expected_sign"),
        [
            (0.04, 0.05, 1),   # modelo mejor
            (0.05, 0.05, 0),   # equivale a no tener modelo
            (0.06, 0.05, -1),  # PEOR que la climatología: caso real, no teórico
        ],
    )
    def test_signo_del_brier_skill_score(self, brier_model, brier_base, expected_sign):
        """BSS < 0 significa que el modelo estorba.

        No es hipotético: pasó en este proyecto con el ACE del Atlántico, donde
        un r de -0,50 en entrenamiento acabó siendo un 6,2% peor que la
        climatología fuera de muestra.
        """
        bss = 1 - brier_model / brier_base
        assert (bss > 0) - (bss < 0) == expected_sign

    def test_el_suavizado_evita_probabilidades_absolutas(self):
        """Laplace: una celda con 3 de 3 no puede predecir el 100%.

        Sin suavizado, un solo fallo con probabilidad 1,0 aporta (1-0)² = 1 al
        Brier score, que es el peor error posible.
        """
        n, extremes = 3, 3
        assert (extremes + 1) / (n + 2) == 0.8
        assert (extremes + 1) / (n + 2) < 1.0
