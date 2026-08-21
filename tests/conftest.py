"""Configuración común de los tests.

**El problema que resuelve.** Los tests se dividen en dos familias:

  - los que solo necesitan código (parseo, catálogos, higiene del SQL): 233 de
    263, y corren en cualquier sitio
  - los que comprueban INVARIANTES DE LOS DATOS y necesitan un warehouse
    construido: los paneles, el gobierno de modelos y la exportación

Los segundos son de los más valiosos del repositorio —vigilan supuestos, no
funciones— pero sin `data/appclima.duckdb` reventaban con 30 errores de DuckDB
ilegibles, tanto en un clon recién hecho como en CI.

La solución es que se SALTEN con un mensaje claro cuando no hay warehouse, y
que CI se lo descargue para que sí se ejecuten de verdad. Saltarlos en silencio
sería peor que el error: parecería que todo pasa.

Quien necesite el warehouse usa la fixture `warehouse` de aquí. Así un módulo
nuevo hereda el salto sin que nadie tenga que acordarse de añadirlo a una lista.
"""

from __future__ import annotations

import pytest

from appclima.config import settings
from appclima.transform import runner

MENSAJE = (
    f"Requiere el warehouse en {settings.warehouse_path}. "
    "Constrúyelo con: appclima ingest all --cadence full && appclima build, "
    "o descárgalo de la release `warehouse` del repositorio."
)


@pytest.fixture(scope="session")
def warehouse():
    """Conexión de solo lectura al warehouse, o salto si no existe."""
    if not settings.warehouse_path.exists():
        pytest.skip(MENSAJE)

    con = runner.connect(read_only=True)
    yield con
    con.close()


@pytest.fixture(scope="session")
def warehouse_required():
    """Para tests que no abren conexión pero sí necesitan que exista."""
    if not settings.warehouse_path.exists():
        pytest.skip(MENSAJE)
