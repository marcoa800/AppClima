"""Tests de los conectores, sin red.

Se testea el parseo con payloads reales recortados, porque ahí es donde viven
los bugs de verdad: nulls inesperados, formatos de fecha que cambian, y
respuestas que a veces son objeto y a veces lista.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from appclima.locations import BY_ID
from appclima.sources import ebird, open_meteo, usgs


class TestUSGS:
    def test_parsea_feature_completo(self):
        feature = {
            "id": "us7000abcd",
            "properties": {
                "mag": 7.7,
                "magType": "mww",
                "time": 1755190701564,
                "updated": 1755200000000,
                "place": "68 km NNW of Ende, Indonesia",
                "type": "earthquake",
                "tsunami": 1,
                "sig": 900,
                "alert": "orange",
                "status": "reviewed",
                "felt": 120,
                "cdi": 6.1,
                "mmi": 7.2,
                "net": "us",
                "url": "https://example.org/us7000abcd",
            },
            "geometry": {"coordinates": [121.5, -8.6, 10.0]},
        }
        quake = usgs._parse_feature(feature)

        assert quake is not None
        assert quake.event_id == "us7000abcd"
        assert quake.magnitude == 7.7
        # USGS da lon/lat en ese orden; invertirlos manda los sismos al océano
        # equivocado y es un error clásico.
        assert quake.lon == 121.5
        assert quake.lat == -8.6
        assert quake.depth_km == 10.0
        # tsunami llega como 0/1, no como booleano.
        assert quake.tsunami is True
        assert quake.time.tzinfo is not None
        assert quake.time == datetime.fromtimestamp(1755190701564 / 1000, tz=UTC)

    def test_tolera_campos_opcionales_ausentes(self):
        """La mayoría de sismos no tienen alert, felt, cdi ni mmi."""
        feature = {
            "id": "us1",
            "properties": {"mag": 4.6, "time": 1755190701564, "type": "earthquake"},
            "geometry": {"coordinates": [10.0, 20.0, 33.0]},
        }
        quake = usgs._parse_feature(feature)

        assert quake is not None
        assert quake.alert is None
        assert quake.felt is None
        assert quake.tsunami is False

    @pytest.mark.parametrize(
        "geometry",
        [
            {"coordinates": []},
            {"coordinates": [None, None, None]},
            {},
        ],
    )
    def test_descarta_eventos_sin_coordenadas(self, geometry):
        feature = {
            "id": "bad",
            "properties": {"mag": 5.0, "time": 1755190701564},
            "geometry": geometry,
        }
        assert usgs._parse_feature(feature) is None

    def test_descarta_eventos_sin_timestamp(self):
        feature = {
            "id": "bad",
            "properties": {"mag": 5.0},
            "geometry": {"coordinates": [1.0, 2.0, 3.0]},
        }
        assert usgs._parse_feature(feature) is None


class TestOpenMeteo:
    def test_normaliza_objeto_y_lista(self):
        """Con una coordenada devuelve objeto; con varias, lista."""
        assert open_meteo._as_list({"a": 1}) == [{"a": 1}]
        assert open_meteo._as_list([{"a": 1}, {"a": 2}]) == [{"a": 1}, {"a": 2}]

    def test_rechaza_respuesta_de_tipo_inesperado(self):
        with pytest.raises(TypeError):
            open_meteo._as_list("no soy json de open-meteo")

    def test_parsea_arrays_paralelos(self):
        block = {
            "hourly": {
                "time": ["2026-08-17T00:00", "2026-08-17T01:00"],
                "temperature_2m": [21.4, 20.8],
                "precipitation": [0.0, 0.2],
            }
        }
        rows = open_meteo._parse_block(block, BY_ID["madrid"], kind="observed")

        assert len(rows) == 2
        assert rows[0].temperature_2m == 21.4
        assert rows[1].precipitation == 0.2
        assert rows[0].location_id == "madrid"
        assert rows[0].kind == "observed"

    def test_asigna_utc_a_horas_sin_offset(self):
        """Con timezone=UTC la API omite el offset. Sin esto quedaría naive."""
        block = {"hourly": {"time": ["2026-08-17T14:00"], "temperature_2m": [30.0]}}
        rows = open_meteo._parse_block(block, BY_ID["madrid"], kind="forecast")

        assert rows[0].time.tzinfo is not None
        assert rows[0].time.utcoffset().total_seconds() == 0

    def test_variables_no_pedidas_quedan_a_null(self):
        """El esquema es siempre el mismo, se pidan 5 variables o 14.

        Es lo que permite que un solo glob de Parquet mezcle ficheros del
        archivo (5 variables) y del pronóstico (14) sin romper el esquema.
        """
        block = {"hourly": {"time": ["2026-08-17T00:00"], "temperature_2m": [15.0]}}
        rows = open_meteo._parse_block(block, BY_ID["london"], kind="observed")

        assert rows[0].temperature_2m == 15.0
        assert rows[0].wind_speed_10m is None
        assert rows[0].shortwave_radiation is None

    def test_bloque_vacio_no_revienta(self):
        assert open_meteo._parse_block({}, BY_ID["madrid"], "observed") == []


class TestEbird:
    def test_parsea_fecha_con_hora(self):
        parsed, date_only = ebird._parse_obs_datetime("2026-08-15 07:30")
        assert parsed == datetime(2026, 8, 15, 7, 30)
        assert date_only is False

    def test_parsea_fecha_sin_hora(self):
        """Muchos observadores no anotan la hora. No es un error."""
        parsed, date_only = ebird._parse_obs_datetime("2026-08-15")
        assert parsed == datetime(2026, 8, 15, 0, 0)
        assert date_only is True

    def test_how_many_ausente_es_none_no_cero(self):
        """None = 'vista pero no contada'. Convertirlo en 0 sesga los totales."""
        item = {
            "speciesCode": "houspa",
            "comName": "House Sparrow",
            "sciName": "Passer domesticus",
            "obsDt": "2026-08-15 07:30",
            "lat": 40.4,
            "lng": -3.7,
            "locId": "L123",
            "subId": "S456",
        }
        obs = ebird._parse_observation(item, BY_ID["madrid"], radius_km=25)

        assert obs is not None
        assert obs.how_many is None
        assert obs.species_code == "houspa"
        # eBird usa 'lng'; el esquema usa 'lon'.
        assert obs.lon == -3.7

    def test_descarta_observacion_con_fecha_ilegible(self):
        item = {"speciesCode": "x", "obsDt": "ayer por la tarde", "lat": 0, "lng": 0}
        assert ebird._parse_observation(item, BY_ID["madrid"], 25) is None

    def test_recorta_parametros_a_los_limites_de_la_api(self, monkeypatch):
        """dist máx 50 km, back máx 30 días. Pasarse devuelve 400."""
        captured: list[dict] = []

        def fake_get_json(url, params=None, headers=None):
            captured.append(params or {})
            return []

        monkeypatch.setattr(ebird, "get_json", fake_get_json)
        monkeypatch.setattr(ebird.settings, "ebird_token", "token-de-prueba")
        monkeypatch.setattr(ebird.settings, "rate_limit_sleep", 0)

        ebird.fetch_recent_observations([BY_ID["madrid"]], radius_km=999, days_back=999)

        assert captured[0]["dist"] == 50
        assert captured[0]["back"] == 30

    def test_falla_claro_sin_token(self, monkeypatch):
        monkeypatch.setattr(ebird.settings, "ebird_token", "")
        with pytest.raises(ebird.MissingTokenError, match="ebird.org/api/keygen"):
            ebird.fetch_recent_observations([BY_ID["madrid"]])
