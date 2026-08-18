"""Tests de desastres históricos y epidemias.

El foco está en las tres trampas de este dominio: fechas anteriores a Cristo,
muertes directas frente a totales, y rangos de incertidumbre.
"""

from __future__ import annotations

import duckdb
import pytest

from appclima.epidemics import BY_ID as EPI_BY_ID
from appclima.epidemics import EPIDEMICS
from appclima.schemas.disasters import HistoricalDisaster, HistoricalEpidemic
from appclima.sources import noaa_hazards
from appclima.transform.runner import _empty_source_sql


class TestNoaaParsing:
    def test_parsea_tangshan_1976(self):
        """El sismo más mortal con cifra fiable del archivo."""
        item = {
            "id": 4735, "year": 1976, "month": 7, "day": 27,
            "hour": 19, "minute": 42,
            "locationName": "CHINA:  NE:  TANGSHAN",
            "latitude": 39.57, "longitude": 117.98,
            "eqDepth": 23, "eqMagnitude": 7.5, "intensity": 11,
            "deaths": 242769, "deathsAmountOrder": 4,
            "injuries": 799000, "damageMillionsDollars": 5600,
            "deathsTotal": 242769, "country": "CHINA", "publish": True,
        }
        d = noaa_hazards._parse_item(item, "earthquake")

        assert d is not None
        assert d.deaths == 242769
        assert d.eq_intensity == 11
        assert d.hazard_type == "earthquake"

    def test_distingue_muertes_directas_de_totales(self):
        """Krakatoa: 2.000 por la erupción, 36.417 con el tsunami incluido.

        Es la distinción que, mal resuelta, cambia la cifra por un factor de 18.
        """
        item = {
            "id": 2429, "year": 1883, "month": 8, "day": 27,
            "name": "Krakatau", "location": "Indonesia", "country": "Indonesia",
            "latitude": -6.101, "longitude": 105.423, "vei": 6,
            "deaths": 2000, "deathsTotal": 36417,
            "tsunamiEventId": 1142, "publish": False,
        }
        d = noaa_hazards._parse_item(item, "volcano")

        assert d is not None
        assert d.deaths == 2000
        assert d.deaths_total == 36417
        assert d.caused_tsunami_id == 1142
        assert d.volcano_vei == 6
        # 'location' en volcanes, 'locationName' en los otros dos datasets.
        assert d.location_name == "Indonesia"

    def test_admite_anios_antes_de_cristo(self):
        item = {"id": 1, "year": -2150, "latitude": 35.0, "longitude": 25.0}
        d = noaa_hazards._parse_item(item, "earthquake")

        assert d is not None
        assert d.year == -2150
        assert d.month is None

    def test_descarta_eventos_sin_anio(self):
        assert noaa_hazards._parse_item({"id": 1}, "earthquake") is None

    def test_convierte_conteos_flotantes_a_entero(self):
        """NOAA devuelve a veces 1000.0 donde el campo es un conteo."""
        item = {"id": 1, "year": 1900, "deaths": 1000.0, "injuries": 55.0}
        d = noaa_hazards._parse_item(item, "earthquake")

        assert d is not None
        assert d.deaths == 1000
        assert isinstance(d.deaths, int)

    def test_rechaza_tipo_de_peligro_desconocido(self):
        with pytest.raises(ValueError, match="Peligro desconocido"):
            noaa_hazards.fetch_hazard("meteorito")

    def test_orden_de_magnitud_dentro_de_rango(self):
        """La escala ordinal de NOAA va de 0 a 4; fuera de ahí es un bug."""
        with pytest.raises(ValueError):
            HistoricalDisaster(
                source_id=1, hazard_type="earthquake", year=1900, deaths_order=9
            )


class TestEpidemicsCatalog:
    def test_ids_unicos(self):
        ids = [e.id for e in EPIDEMICS]
        assert len(ids) == len(set(ids))

    def test_rango_coherente(self):
        """deaths_high nunca por debajo de deaths_low."""
        for e in EPIDEMICS:
            if e.deaths_low is not None and e.deaths_high is not None:
                assert e.deaths_high >= e.deaths_low, e.id

    def test_anios_coherentes(self):
        for e in EPIDEMICS:
            if e.end_year is not None:
                assert e.end_year >= e.start_year, e.id

    def test_toda_entrada_lleva_fuente(self):
        """Es un catálogo curado: sin fuente no es auditable."""
        for e in EPIDEMICS:
            assert e.source.strip(), e.id

    def test_las_muy_disputadas_llevan_rango_ancho(self):
        """Confianza baja y rango estrecho a la vez sería contradictorio."""
        for e in EPIDEMICS:
            if (
                e.estimate_confidence == "baja"
                and e.deaths_low
                and e.deaths_high
                and e.deaths_low > 1000
            ):
                assert e.deaths_high / e.deaths_low >= 1.5, (
                    f"{e.id}: confianza baja pero rango casi cerrado"
                )

    def test_los_recuentos_modernos_son_de_confianza_alta(self):
        for slug in ("sars-2002", "ebola-africa-occidental"):
            assert EPI_BY_ID[slug].estimate_confidence == "alta"

    def test_las_pandemias_en_curso_no_tienen_fin(self):
        assert EPI_BY_ID["covid-19"].end_year is None
        assert EPI_BY_ID["vih-sida"].end_year is None

    def test_la_peste_negra_supera_al_peor_desastre_natural(self):
        """El hallazgo central: las pandemias operan en otra escala.

        El desastre natural más mortal con cifra fiable es el sismo de Shaanxi
        de 1556, con 830.000 muertes.
        """
        peste = EPI_BY_ID["peste-negra"]
        assert peste.deaths_low is not None
        assert peste.deaths_low > 830_000 * 50


class TestDisasterSql:
    @pytest.fixture
    def con(self):
        c = duckdb.connect(":memory:")
        c.execute("SET TimeZone='UTC'")
        yield c
        c.close()

    @pytest.mark.parametrize("model", [HistoricalDisaster, HistoricalEpidemic])
    def test_fuente_vacia_valida(self, con, model):
        assert con.execute(f"SELECT * FROM {_empty_source_sql(model)}").fetchall() == []

    @pytest.mark.parametrize(
        ("year", "expected_century"),
        [(1976, 20), (2004, 21), (1, 1), (100, 1), (101, 2), (-430, -5), (-1, -1)],
    )
    def test_calculo_de_siglo(self, con, year, expected_century):
        """No existe el año 0 y el año 1 abre el siglo I.

        Este test encontró un bug real: la versión original usaba `/`, que en
        DuckDB es división en coma flotante. (1976-1)/100 = 19,75, que al
        castear a INTEGER redondea a 20 y da siglo 21 en lugar de 20. Con `//`
        se trunca y sale bien. Afectaba a todos los siglos cuyo resto pasara de
        50 años, o sea a la mitad del archivo.
        """
        result = con.execute(
            """
            SELECT CASE
                WHEN ? > 0 THEN ((? - 1) // 100) + 1
                ELSE -(((-? - 1) // 100) + 1)
            END
            """,
            [year, year, year],
        ).fetchone()[0]
        assert result == expected_century

    def test_duckdb_admite_fechas_antes_de_cristo(self, con):
        """El evento más antiguo del archivo es del año -4360."""
        assert con.execute("SELECT year(make_date(-4360, 1, 1))").fetchone()[0] == -4360
