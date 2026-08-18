"""Escritura en la capa bronze.

Regla de oro del lakehouse: **bronze es append-only e inmutable**. Nunca se
edita ni se borra una fila. Si un job se ejecuta dos veces el mismo día,
tendremos datos duplicados aquí — y eso está bien. La deduplicación es
responsabilidad de silver, que conoce las claves naturales de cada dataset.

El motivo es práctico: si mañana descubres un bug en tu lógica de limpieza,
puedes reconstruir silver y gold enteros desde bronze sin volver a llamar a
ninguna API. Si hubieras limpiado al escribir, ese dato original ya no existe.

Layout en disco:

    data/bronze/<fuente>/<dataset>/ingest_date=YYYY-MM-DD/<timestamp>.parquet

El particionado por fecha de ingesta permite a DuckDB saltarse ficheros
enteros al filtrar (partition pruning) y hace trivial reprocesar un solo día.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from appclima.config import settings

log = logging.getLogger(__name__)


def write_bronze(
    records: list[BaseModel],
    source: str,
    dataset: str,
    ingested_at: datetime | None = None,
) -> Path | None:
    """Serializa modelos Pydantic validados a un fichero Parquet en bronze.

    Devuelve la ruta escrita, o None si no había nada que escribir.
    """
    if not records:
        log.info("Nada que escribir en %s/%s", source, dataset)
        return None

    ingested_at = ingested_at or datetime.now(UTC)

    rows: list[dict[str, Any]] = []
    for record in records:
        row = record.model_dump(mode="python")
        # Sello de procedencia: sin esto, dentro de seis meses no sabrás
        # de qué ejecución salió una fila sospechosa.
        row["_ingested_at"] = ingested_at
        row["_source"] = source
        rows.append(row)

    table = pa.Table.from_pylist(rows)

    partition = f"ingest_date={ingested_at.date().isoformat()}"
    out_dir = settings.bronze_dir / source / dataset / partition
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{ingested_at.strftime('%Y%m%dT%H%M%S%f')}.parquet"
    out_path = out_dir / filename

    pq.write_table(table, out_path, compression="zstd")

    log.info("Escritas %d filas en %s", len(rows), out_path.relative_to(settings.data_dir))
    return out_path


def bronze_glob(source: str, dataset: str) -> str:
    """Patrón glob que DuckDB puede leer directamente con read_parquet()."""
    return str(settings.bronze_dir / source / dataset / "**" / "*.parquet")


def bronze_stats(source: str, dataset: str) -> dict[str, Any]:
    """Recuento rápido de ficheros y filas, para inspección y depuración."""
    base = settings.bronze_dir / source / dataset
    if not base.exists():
        return {"files": 0, "rows": 0, "bytes": 0}

    files = sorted(base.glob("**/*.parquet"))
    rows = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
    size = sum(f.stat().st_size for f in files)
    return {"files": len(files), "rows": rows, "bytes": size}
