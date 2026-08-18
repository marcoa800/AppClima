"""Tests de la capa de transformación.

El macro haversine y la deduplicación se testean contra un DuckDB en memoria:
son las dos piezas donde un error silencioso corrompería todos los análisis
aguas abajo sin lanzar ninguna excepción.
"""

from __future__ import annotations

import duckdb
import pytest

from appclima.locations import BY_ID, FLAGSHIPS, LOCATIONS
from appclima.schemas import Earthquake, WeatherHour
from appclima.transform.runner import MODELS_DIR, _empty_source_sql


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    connection.execute("SET TimeZone='UTC'")
    connection.execute((MODELS_DIR / "macros.sql").read_text())
    yield connection
    connection.close()


class TestHaversine:
    @pytest.mark.parametrize(
        ("a", "b", "expected_km", "tolerance"),
        [
            # Madrid → Barcelona, ~505 km por la superficie.
            ((40.42, -3.70), (41.39, 2.17), 505, 15),
            # Tokio → Osaka, ~400 km.
            ((35.68, 139.65), (34.69, 135.50), 400, 15),
            # Un grado de latitud en el ecuador ≈ 111,2 km.
            ((0.0, 0.0), (1.0, 0.0), 111.2, 1),
            # Mismo punto = cero, sin NaN por raíz de un negativo diminuto.
            ((40.42, -3.70), (40.42, -3.70), 0, 0.001),
        ],
    )
    def test_distancias_conocidas(self, con, a, b, expected_km, tolerance):
        result = con.execute(
            "SELECT haversine_km(?, ?, ?, ?)", [a[0], a[1], b[0], b[1]]
        ).fetchone()[0]
        assert abs(result - expected_km) <= tolerance

    def test_cruza_el_antimeridiano(self, con):
        """De 179°E a 179°W son 222 km, no media vuelta al planeta."""
        result = con.execute(
            "SELECT haversine_km(0.0, 179.0, 0.0, -179.0)"
        ).fetchone()[0]
        assert abs(result - 222.4) < 2


class TestDoyDistance:
    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            (100, 105, 5),
            (105, 100, 5),
            # 31 de diciembre y 1 de enero son vecinos, no están a 365 días.
            (1, 366, 1),
            (365, 2, 3),
            (180, 1, 179),
        ],
    )
    def test_distancia_circular(self, con, a, b, expected):
        result = con.execute("SELECT doy_distance(?, ?)", [a, b]).fetchone()[0]
        assert result == expected


class TestEmptySource:
    @pytest.mark.parametrize("model", [WeatherHour, Earthquake])
    def test_genera_esquema_valido_y_vacio(self, con, model):
        """Sin esto, una fuente sin ingerir tumbaría el build entero."""
        sql = _empty_source_sql(model)
        result = con.execute(f"SELECT * FROM {sql}").fetchall()
        assert result == []

    def test_incluye_las_columnas_del_modelo_y_las_de_procedencia(self, con):
        sql = _empty_source_sql(WeatherHour)
        columns = [d[0] for d in con.execute(f"SELECT * FROM {sql}").description]

        assert "temperature_2m" in columns
        assert "location_id" in columns
        assert "_ingested_at" in columns
        assert "ingest_date" in columns

    def test_los_timestamps_llevan_zona(self, con):
        relation = con.sql(f"SELECT * FROM {_empty_source_sql(Earthquake)}")
        types = dict(zip(relation.columns, map(str, relation.types), strict=True))

        # Un TIMESTAMP sin zona perdería el offset y desplazaría los datos.
        assert types["time"].upper() == "TIMESTAMP WITH TIME ZONE"
        assert types["_ingested_at"].upper() == "TIMESTAMP WITH TIME ZONE"
        # Y los tipos escalares no deben degradarse a VARCHAR por el camino.
        assert types["magnitude"].upper() == "DOUBLE"
        assert types["tsunami"].upper() == "BOOLEAN"
        assert types["significance"].upper() == "BIGINT"


class TestCatalogo:
    def test_los_ids_son_unicos(self):
        ids = [loc.id for loc in LOCATIONS]
        assert len(ids) == len(set(ids))

    def test_las_flagship_existen_en_el_catalogo(self):
        assert len(FLAGSHIPS) == 12
        for loc in FLAGSHIPS:
            assert BY_ID[loc.id] is loc

    def test_las_flagship_cubren_climas_distintos(self):
        """El sentido de las flagship es cubrir el espectro, no repetir clima."""
        koppen = {loc.koppen for loc in FLAGSHIPS}
        assert len(koppen) >= 9

    def test_cubre_ambos_hemisferios_y_latitudes_extremas(self):
        lats = [loc.lat for loc in LOCATIONS]
        assert max(lats) > 65, "falta cobertura ártica"
        assert min(lats) < -50, "falta cobertura subantártica"

    def test_las_zonas_horarias_son_iana_validas(self):
        from zoneinfo import ZoneInfo

        for loc in LOCATIONS:
            ZoneInfo(loc.timezone)  # lanza si el identificador no existe
