"""Tests de población y del índice ENSO."""

from __future__ import annotations

import pytest

from appclima.schemas.population import OniValue
from appclima.world_population import BY_YEAR, WORLD_POPULATION


class TestWorldPopulationCatalog:
    def test_anios_ordenados_y_unicos(self):
        years = [e.year for e in WORLD_POPULATION]
        assert years == sorted(years)
        assert len(years) == len(set(years))

    def test_rangos_coherentes(self):
        for e in WORLD_POPULATION:
            assert e.population_high >= e.population_low, e.year

    def test_recoge_la_caida_de_la_peste_negra(self):
        """La única caída de toda la serie, y tiene que estar.

        Se comprueba sobre los valores CENTRALES, no sobre los extremos, y el
        matiz importa: los rangos de 1300 (360-432 M) y 1400 (350-374 M) se
        solapan. La caída es clara en la estimación central pero no queda fuera
        de toda duda, y afirmar lo contrario sería atribuir a la demografía
        histórica una precisión que no tiene.

        La primera versión de este test exigía que los rangos NO se solaparan y
        falló — correctamente: encodaba una afirmación más fuerte que los datos.
        """
        mid_1300 = (BY_YEAR[1300].population_low + BY_YEAR[1300].population_high) / 2
        mid_1400 = (BY_YEAR[1400].population_low + BY_YEAR[1400].population_high) / 2
        assert mid_1400 < mid_1300, "se perdió la caída de la peste negra"

        # Y se deja constancia explícita de que los rangos sí se solapan.
        assert BY_YEAR[1400].population_high > BY_YEAR[1300].population_low

    def test_la_incertidumbre_baja_con_el_tiempo(self):
        """Los años antiguos tienen que ser MENOS precisos que los modernos."""
        antiguo = BY_YEAR[-10000]
        moderno = BY_YEAR[1950]
        ratio_antiguo = antiguo.population_high / antiguo.population_low
        ratio_moderno = moderno.population_high / moderno.population_low
        assert ratio_antiguo > ratio_moderno * 5

    def test_toda_entrada_lleva_fuente(self):
        for e in WORLD_POPULATION:
            assert e.source.strip(), e.year


class TestOni:
    @pytest.mark.parametrize(
        ("anomaly", "expected"),
        [
            (2.6, "El Niño"), (0.5, "El Niño"), (0.49, "Neutral"),
            (0.0, "Neutral"), (-0.49, "Neutral"), (-0.5, "La Niña"), (-1.9, "La Niña"),
        ],
    )
    def test_umbrales_oficiales_de_la_noaa(self, anomaly, expected):
        """±0,5 °C, y los límites son inclusivos."""
        v = OniValue(
            year=2023, season="ASO", season_index=9, sst_c=27.0, anomaly_c=anomaly
        )
        assert v.phase == expected

    def test_el_orden_de_estaciones_cubre_los_doce_trimestres(self):
        from appclima.sources.enso import SEASON_ORDER

        assert len(SEASON_ORDER) == 12
        assert sorted(SEASON_ORDER.values()) == list(range(1, 13))
        # Trimestres solapados: cada mes aparece en tres. DJF abre el ciclo.
        assert SEASON_ORDER["DJF"] == 1
        assert SEASON_ORDER["ASO"] == 9

    def test_indice_de_estacion_dentro_de_rango(self):
        with pytest.raises(ValueError):
            OniValue(
                year=2023, season="XXX", season_index=13, sst_c=27.0, anomaly_c=0.1
            )


class TestWorldBankAggregates:
    def test_los_agregados_se_marcan_no_se_borran(self):
        """'WLD' es el denominador que necesitamos: tirarlo sería absurdo.

        Pero mezclarlo con los países en una suma contaría a cada persona
        varias veces, así que la marca `is_aggregate` es obligatoria.
        """
        from appclima.schemas.population import PopulationYear

        wld = PopulationYear(
            country_id="WLD", country_name="World", year=2023,
            population=8_000_000_000, is_aggregate=True,
        )
        assert wld.is_aggregate is True
