"""Ejecutor de modelos SQL sobre DuckDB.

Hace cuatro cosas, en este orden:

  1. Fija la zona horaria de la sesión a UTC (crítico, ver abajo)
  2. Siembra dim_locations desde el catálogo Python
  3. Ejecuta los modelos silver en orden numérico
  4. Ejecuta los modelos gold en orden numérico

Sobre el paso 1: DuckDB, por defecto, **muestra** los TIMESTAMPTZ en la zona
local del sistema. El dato guardado es correcto, pero al inspeccionarlo aparece
en hora local y es facilísimo concluir que la ingesta está mal cuando no lo
está. Fijar UTC en la sesión elimina esa ambigüedad de raíz.
"""

from __future__ import annotations

import logging
from functools import cache
from pathlib import Path

import duckdb
import pyarrow as pa

from appclima.config import settings
from appclima.historical_events import HistoricalEvent
from appclima.locations import LOCATIONS
from appclima.schemas import BirdObservation, Earthquake, WeatherHour
from appclima.schemas.cyclones import CycloneTrackPoint
from appclima.schemas.disasters import HistoricalDisaster, HistoricalEpidemic
from appclima.schemas.phenology import PhenologyYear
from appclima.schemas.population import (
    OniValue,
    PopulationYear,
    WorldPopulationEstimate,
)
from appclima.storage import bronze_glob

log = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"

# Mapa de tipos Python → DuckDB, para poder fabricar una fuente vacía con el
# esquema correcto cuando un dataset todavía no se ha ingerido nunca.
_DUCKDB_TYPES: dict[type, str] = {
    str: "VARCHAR",
    float: "DOUBLE",
    int: "BIGINT",
    bool: "BOOLEAN",
}


def _empty_source_sql(model: type) -> str:
    """Genera un SELECT vacío con el esquema de un modelo Pydantic.

    Sirve para que los modelos silver funcionen igual cuando una fuente aún no
    tiene datos (caso típico: eBird sin token). La alternativa sería que
    `read_parquet` fallara con "no files found" y tumbara todo el build por una
    fuente opcional.

    Derivar el esquema del modelo en lugar de escribirlo a mano evita que las
    dos definiciones se desincronicen con el tiempo.
    """
    columns: list[str] = []
    for name, field in model.model_fields.items():
        annotation = field.annotation
        # Desenvuelve Optional[X] / X | None quedándonos con el tipo real.
        args = [a for a in getattr(annotation, "__args__", ()) if a is not type(None)]
        base = args[0] if args else annotation

        sql_type = _DUCKDB_TYPES.get(base)
        if sql_type is None:
            # datetime y cualquier otro tipo temporal.
            sql_type = "TIMESTAMP WITH TIME ZONE"
        columns.append(f"NULL::{sql_type} AS {name}")

    # Columnas de procedencia que añade storage.write_bronze, más la columna
    # virtual del particionado hive.
    columns.extend([
        "NULL::TIMESTAMP WITH TIME ZONE AS _ingested_at",
        "NULL::VARCHAR AS _source",
        "NULL::VARCHAR AS ingest_date",
    ])

    return f"(SELECT {', '.join(columns)} WHERE false)"


@cache
def _source_sql(source: str, dataset: str, model: type) -> str:
    """Expresión de tabla para un dataset de bronze, o una fuente vacía.

    Cacheado porque se resuelve una vez por modelo, y un dataset ausente
    repetiría el mismo aviso una docena de veces en el log.
    """
    pattern = bronze_glob(source, dataset)
    base = settings.bronze_dir / source / dataset

    if not base.exists() or not any(base.glob("**/*.parquet")):
        log.warning("Sin datos en bronze para %s/%s — usando fuente vacía", source, dataset)
        return _empty_source_sql(model)

    # union_by_name es imprescindible: los ficheros del archivo histórico se
    # escribieron pidiendo solo CORE_VARIABLES, así que sus columnas no
    # coinciden posicionalmente con los del pronóstico. Sin esto, DuckDB
    # alinearía columnas por posición y mezclaría variables distintas.
    return (
        f"read_parquet('{pattern}', hive_partitioning=true, union_by_name=true)"
    )


def _seed_locations(con: duckdb.DuckDBPyConnection) -> None:
    """Materializa el catálogo Python como tabla de dimensión."""
    rows = [loc.model_dump() for loc in LOCATIONS]
    table = pa.Table.from_pylist(rows)
    con.register("_locations_seed", table)
    con.execute("CREATE OR REPLACE TABLE dim_locations AS SELECT * FROM _locations_seed")
    con.unregister("_locations_seed")
    log.info("dim_locations: %d ubicaciones", len(rows))


def _render(sql: str) -> str:
    """Sustituye los marcadores de fuente por expresiones reales."""
    replacements = {
        "{{bronze_weather}}": _source_sql("open_meteo", "weather_hourly", WeatherHour),
        "{{bronze_quakes}}": _source_sql("usgs", "earthquakes", Earthquake),
        "{{bronze_birds}}": _source_sql("ebird", "observations", BirdObservation),
        "{{bronze_noaa_eq}}": _source_sql("noaa", "earthquakes", HistoricalDisaster),
        "{{bronze_noaa_tsunami}}": _source_sql("noaa", "tsunamis", HistoricalDisaster),
        "{{bronze_noaa_volcano}}": _source_sql("noaa", "volcanos", HistoricalDisaster),
        "{{bronze_epidemics}}": _source_sql("curated", "epidemics", HistoricalEpidemic),
        "{{bronze_cyclones}}": _source_sql("ibtracs", "track_points", CycloneTrackPoint),
        "{{bronze_population}}": _source_sql("worldbank", "population", PopulationYear),
        "{{bronze_world_pop}}": _source_sql(
            "curated", "world_population", WorldPopulationEstimate
        ),
        "{{bronze_oni}}": _source_sql("noaa_cpc", "oni", OniValue),
        "{{bronze_events}}": _source_sql(
            "curated", "historical_events", HistoricalEvent
        ),
        "{{bronze_phenology}}": _source_sql("gbif", "phenology", PhenologyYear),
    }
    for marker, expression in replacements.items():
        sql = sql.replace(marker, expression)
    return sql


def _run_layer(con: duckdb.DuckDBPyConnection, layer: str) -> list[str]:
    """Ejecuta todos los modelos de una capa, en orden numérico de fichero."""
    layer_dir = MODELS_DIR / layer
    built: list[str] = []

    for path in sorted(layer_dir.glob("*.sql")):
        log.info("[%s] %s", layer, path.stem)
        con.execute(_render(path.read_text()))
        built.append(path.stem)

    return built


def build_warehouse() -> Path:
    """Reconstruye silver y gold desde cero a partir de bronze.

    Es idempotente y destructivo por diseño: todo son CREATE OR REPLACE. Si un
    modelo tiene un bug, lo arreglas y vuelves a lanzar esto — sin volver a
    llamar a ninguna API, porque bronze conserva el crudo.
    """
    settings.ensure_dirs()
    con = duckdb.connect(str(settings.warehouse_path))

    try:
        # Sin esto, inspeccionar el warehouse desde una máquina en otra zona
        # horaria muestra horas distintas y parece un bug de ingesta.
        con.execute("SET TimeZone='UTC'")

        # Migración: silver pasó de VISTAS a TABLAS por portabilidad, y DuckDB
        # no permite CREATE OR REPLACE TABLE sobre una vista existente. Sin
        # esto, cualquier warehouse construido antes del cambio rompe el build
        # con "Existing object is of type View".
        vistas_antiguas = con.execute("""
            SELECT view_name FROM duckdb_views() WHERE view_name LIKE 'silver_%'
        """).fetchall()
        for (nombre,) in vistas_antiguas:
            con.execute(f"DROP VIEW IF EXISTS {nombre} CASCADE")
        if vistas_antiguas:
            log.info("Migradas %d vistas silver a tablas", len(vistas_antiguas))

        _seed_locations(con)

        macros = MODELS_DIR / "macros.sql"
        if macros.exists():
            con.execute(macros.read_text())
            log.info("macros cargadas")

        silver = _run_layer(con, "silver")
        gold = _run_layer(con, "gold")

        log.info("Construidos %d modelos silver y %d gold", len(silver), len(gold))
        return settings.warehouse_path
    finally:
        con.close()


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Conexión al warehouse con la zona horaria ya fijada a UTC.

    Es lo que debe usar la API: read_only permite varios lectores a la vez, y
    evita que una consulta mal escrita modifique el almacén.
    """
    con = duckdb.connect(str(settings.warehouse_path), read_only=read_only)
    con.execute("SET TimeZone='UTC'")
    return con
