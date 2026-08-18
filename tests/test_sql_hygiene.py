"""Barrido de todos los modelos SQL buscando errores de clase.

Existe por una lección concreta: el bug de división en coma flotante apareció
dos veces en este proyecto. La primera en el cálculo del siglo, donde se
arregló la instancia. La segunda en `day_after` de las secuencias de réplicas,
donde sobrevivió sin que nadie lo notara — porque la curva resultante SEGUÍA
pareciendo un decaimiento de Omori razonable, solo que con el primer día
cubriendo 13 horas en lugar de 24. Lo encontró una verificación adversarial,
no una revisión del código.

Arreglar la instancia y no la clase es cómo un bug vuelve. Estos tests son la
clase.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pytest

from appclima.transform.runner import MODELS_DIR

SQL_FILES = sorted(MODELS_DIR.glob("**/*.sql"))


def _strip_comments(sql: str) -> str:
    """Quita los comentarios: solo interesa el SQL ejecutable."""
    return "\n".join(
        line.split("--")[0] for line in sql.splitlines()
    )


def test_hay_modelos_que_revisar():
    assert len(SQL_FILES) >= 20


@pytest.mark.parametrize("path", SQL_FILES, ids=lambda p: p.stem)
def test_sin_division_flotante_casteada_a_entero(path: Path):
    """`(x / n)::INTEGER` REDONDEA en DuckDB; casi siempre se quiere truncar.

    El patrón correcto es `x // n`. Este test no es una preferencia de estilo:
    cada aparición de este patrón ha sido un bug real en este repositorio.
    """
    code = _strip_comments(path.read_text())
    matches = re.findall(r"/\s*\d+\s*\)\s*::\s*(?:INTEGER|BIGINT|INT)", code, re.I)

    assert not matches, (
        f"{path.name} divide con '/' y castea a entero: {matches}. "
        "DuckDB redondea al más cercano en lugar de truncar. Usa '//'."
    )


@pytest.mark.parametrize("path", SQL_FILES, ids=lambda p: p.stem)
def test_los_marcadores_de_fuente_son_conocidos(path: Path):
    """Un marcador mal escrito llegaría a DuckDB tal cual y fallaría raro.

    Se contrasta contra el renderizador REAL en lugar de contra una lista
    duplicada en el test, que se desincronizaría a la primera fuente nueva.
    """
    from appclima.transform.runner import _render

    encontrados = set(re.findall(r"\{\{(\w+)\}\}", path.read_text()))
    renderizado = _render(path.read_text())

    assert "{{" not in renderizado, (
        f"{path.name} tiene marcadores sin sustituir. Encontrados: {encontrados}"
    )


class TestSemanticaDeDivisionEntera:
    """Comprueba en el motor lo que asumen los modelos, no de memoria."""

    @pytest.fixture
    def con(self):
        c = duckdb.connect(":memory:")
        yield c
        c.close()

    @pytest.mark.parametrize(
        ("horas", "dia_flotante", "dia_entero"),
        [
            (0, 1, 1),
            (12, 1, 1),   # aquí empiezan a divergir
            (13, 2, 1),   # el bug: la hora 13 se contaba como día 2
            (23, 2, 1),
            (24, 2, 2),
            (35, 2, 2),
            (36, 3, 2),
        ],
    )
    def test_el_bug_de_day_after_esta_caracterizado(
        self, con, horas, dia_flotante, dia_entero
    ):
        """Deja constancia ejecutable de qué hacía mal la versión anterior."""
        malo = con.execute(
            "SELECT (?::DOUBLE / 24)::INTEGER + 1", [horas]
        ).fetchone()[0]
        bueno = con.execute("SELECT (?::BIGINT // 24) + 1", [horas]).fetchone()[0]

        assert malo == dia_flotante
        assert bueno == dia_entero

    def test_el_dia_1_dura_24_horas_completas(self, con):
        """La propiedad que el bug rompía: todos los días miden lo mismo."""
        for dia in range(1, 6):
            horas = [
                h
                for h in range(0, 200)
                if con.execute("SELECT (?::BIGINT // 24) + 1", [h]).fetchone()[0] == dia
            ]
            assert len(horas) == 24, f"el día {dia} cubre {len(horas)} horas, no 24"
