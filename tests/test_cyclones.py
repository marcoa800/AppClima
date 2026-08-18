"""Tests del conector y modelado de ciclones tropicales."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from appclima.sources import ibtracs

HEADER_COLS = 174


def _row(**overrides) -> list[str]:
    """Fila de IBTrACS con 174 columnas, rellenable por nombre."""
    row = [""] * HEADER_COLS
    defaults = {
        "sid": "2023005S18142", "season": "2023", "number": "1",
        "basin": "SP", "subbasin": "EA", "name": "HALE",
        "time": "2023-01-04 18:00:00", "nature": "DS",
        "lat": "-18.2", "lon": "142.0",
    }
    for key, value in {**defaults, **overrides}.items():
        row[ibtracs.COLS[key]] = value
    return row


class TestIbtracsParsing:
    def test_parsea_fila_valida(self):
        p = ibtracs._parse_row(_row(usa_wind="20.0", usa_sshs="-3", track_type="main"))

        assert p is not None
        assert p.sid == "2023005S18142"
        assert p.season == 2023
        assert p.usa_wind_kt == 20.0
        assert p.usa_sshs == -3
        assert p.time == datetime(2023, 1, 4, 18, 0, tzinfo=UTC)

    def test_asigna_utc(self):
        """IBTrACS da la hora sin zona; es UTC por definición del archivo."""
        p = ibtracs._parse_row(_row())
        assert p is not None
        assert p.time.utcoffset().total_seconds() == 0

    @pytest.mark.parametrize(
        ("raw_lon", "expected"),
        [("142.0", 142.0), ("200.0", -160.0), ("359.0", -1.0), ("-175.0", -175.0)],
    )
    def test_normaliza_longitudes_por_encima_de_180(self, raw_lon, expected):
        """Algunas cuencas publican 0-360.

        Sin normalizar, el Pacífico occidental cae fuera del mapa y la distancia
        a las ciudades ancla sale disparatada.
        """
        p = ibtracs._parse_row(_row(lon=raw_lon))
        assert p is not None
        assert p.lon == pytest.approx(expected)

    def test_campos_vacios_son_none_no_cero(self):
        """IBTrACS marca lo ausente con blancos. Un 0 de viento sería un dato."""
        p = ibtracs._parse_row(_row(usa_wind="", wmo_wind="   "))
        assert p is not None
        assert p.usa_wind_kt is None
        assert p.wmo_wind_kt is None

    @pytest.mark.parametrize(
        "bad", [{"time": ""}, {"time": "no-es-fecha"}, {"sid": ""}, {"lat": ""}]
    )
    def test_descarta_filas_irrecuperables(self, bad):
        assert ibtracs._parse_row(_row(**bad)) is None

    def test_descarta_fila_demasiado_corta(self):
        assert ibtracs._parse_row(["2023005S18142", "2023"]) is None

    def test_sshs_fuera_de_escala_se_ignora(self):
        """La escala Saffir-Simpson de IBTrACS va de -5 a 5."""
        p = ibtracs._parse_row(_row(usa_sshs="99"))
        assert p is not None
        assert p.usa_sshs is None

    def test_rechaza_dataset_desconocido(self):
        with pytest.raises(ValueError, match="Dataset desconocido"):
            next(ibtracs.fetch_tracks("desde-siempre"))

    def test_los_datasets_declarados_existen(self):
        assert set(ibtracs.DATASETS) == {"since1980", "all", "last3years"}
        # El valor por defecto debe ser el de la era satelital, no el completo:
        # una serie desde 1842 mide observación, no actividad ciclónica.
        assert ibtracs.fetch_tracks.__defaults__[0] == "since1980"


class TestAceDefinition:
    """El ACE está definido sobre observaciones de 6 horas.

    Algunas cuencas reportan cada 3 h y otras cada 6. Calcular el ACE sobre
    todos los puntos duplicaría la energía de las primeras y haría que el
    Atlántico y el Pacífico occidental dejaran de ser comparables.
    """

    @pytest.mark.parametrize(
        ("hour", "minute", "expected"),
        [(0, 0, True), (6, 0, True), (12, 0, True), (18, 0, True),
         (3, 0, False), (9, 0, False), (6, 30, False)],
    )
    def test_marca_de_hora_sinoptica(self, hour, minute, expected):
        import duckdb

        con = duckdb.connect(":memory:")
        con.execute("SET TimeZone='UTC'")
        result = con.execute(
            """
            SELECT hour(t) IN (0, 6, 12, 18) AND minute(t) = 0
            FROM (SELECT make_timestamptz(2023, 1, 4, ?, ?, 0) AS t)
            """,
            [hour, minute],
        ).fetchone()[0]
        con.close()
        assert result is expected
