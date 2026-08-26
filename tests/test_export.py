"""Tests de la exportación estática.

El requisito que protegen es la REPRODUCIBILIDAD: dos exportaciones seguidas
sobre los mismos datos deben producir ficheros byte a byte idénticos.

Sin eso, el workflow que publica el sitio generaría un diff en cada ejecución
aunque nada hubiera cambiado, y sería imposible distinguir un cambio real de
ruido de ordenación. Ya pasó: Sídney y Manaos tienen 89 especies cada una y se
intercambiaban de sitio en cada llamada porque el ORDER BY no desempataba.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from appclima.api.export import export_static


@pytest.fixture(scope="module")
def exported(tmp_path_factory, warehouse_required) -> Path:
    out = tmp_path_factory.mktemp("export")
    export_static(out)
    return out


class TestExportacion:
    def test_escribe_las_rutas_esperadas(self, exported: Path):
        """TODAS las rutas declaradas, no una muestra.

        Antes comprobaba cinco de veintiocho escritas a mano. Una ruta nueva
        que fallara al exportarse habría pasado desapercibida, y una retirada
        que siguiera publicándose también.
        """
        from appclima.api import export as exportador

        declaradas = set(exportador._routes())
        escritas = {
            str(f.relative_to(exported))[:-5]
            for f in exported.rglob("*.json")
        }
        faltan = declaradas - escritas
        assert not faltan, f"rutas declaradas que no se exportaron: {sorted(faltan)}"
        assert (exported / "manifest.json").exists()

    def test_el_manifiesto_declara_lo_exportado(self, exported: Path):
        manifest = json.loads((exported / "manifest.json").read_text())
        assert manifest["n_routes"] > 100
        assert manifest["total_bytes"] > 1_000_000
        assert "generated_at" in manifest

    def test_todos_los_ficheros_son_json_valido(self, exported: Path):
        ficheros = list(exported.rglob("*.json"))
        assert len(ficheros) > 100
        for f in ficheros:
            json.loads(f.read_text())  # revienta si alguno está corrupto

    def test_hay_una_ruta_por_ciudad(self, exported: Path):
        """Una ruta por ciudad del catálogo, ni una más ni una menos.

        Se compara contra LOCATIONS en vez de contra un número escrito a mano:
        al añadir las once ciudades peruanas este test falló por decir 49
        cuando ya eran 60, que es ruido, no una señal.
        """
        from appclima.locations import LOCATIONS

        anomalias = {p.parent.name for p in (exported / "weather").glob("*/anomaly.json")}
        esperadas = {loc.id for loc in LOCATIONS}
        assert anomalias == esperadas, (
            f"faltan {esperadas - anomalias}, sobran {anomalias - esperadas}"
        )

    def test_la_climatologia_solo_existe_en_las_flagship(self, exported: Path):
        """404 esperado en las otras 37: no es un fallo, es el diseño."""
        from appclima.locations import FLAGSHIP_IDS

        clim = list((exported / "climatology").glob("*.json"))
        assert len(clim) == len(FLAGSHIP_IDS)


class TestReproducibilidad:
    """El requisito que hace publicable la exportación desde CI."""

    def test_dos_exportaciones_son_identicas(
        self, tmp_path: Path, warehouse_required
    ):
        a, b = tmp_path / "a", tmp_path / "b"
        export_static(a)
        export_static(b)

        ficheros_a = sorted(p.relative_to(a) for p in a.rglob("*.json"))
        ficheros_b = sorted(p.relative_to(b) for p in b.rglob("*.json"))
        assert ficheros_a == ficheros_b

        distintos = [
            str(rel)
            for rel in ficheros_a
            # El manifiesto lleva timestamp: es el único que puede diferir.
            if rel.name != "manifest.json"
            and (a / rel).read_bytes() != (b / rel).read_bytes()
        ]
        assert distintos == [], (
            f"{len(distintos)} ficheros difieren entre exportaciones. "
            "Casi siempre es un ORDER BY sin desempate único: "
            f"{distintos[:3]}"
        )


class TestOrdenDeterminista:
    def test_ningun_order_by_queda_sin_desempate(self):
        """Barrido del código, no de los datos.

        Un ORDER BY por una columna que puede empatar produce orden arbitrario.
        Este test no puede saber qué columnas son únicas, así que comprueba lo
        que sí puede: que ninguna consulta ordene por UNA SOLA columna que sea
        un agregado o una métrica, que es donde los empates son seguros.
        """
        codigo = Path("src/appclima/api/main.py").read_text()
        sospechosos = re.findall(
            r"ORDER BY (\w+(?:\s+DESC)?)\s*\n", codigo
        )
        riesgo = [
            s for s in sospechosos
            if any(m in s.lower() for m in
                   ("count", "deaths", "richness", "improvement", "ace", "n_"))
        ]
        assert riesgo == [], (
            f"ORDER BY por una métrica sin desempate: {riesgo}. "
            "Añade una columna única al final."
        )
