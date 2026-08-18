"""Tests de los catálogos de atribución y de resultados nulos.

La atribución no es cortesía: es obligación de licencia. Un catálogo que se
desincroniza de las fuentes reales incumple sin que nadie se entere, y estos
tests son lo que lo impide.
"""

from __future__ import annotations

import pytest

from appclima.attribution import BY_ID as SOURCE_BY_ID
from appclima.attribution import SOURCES
from appclima.null_findings import NULL_FINDINGS


class TestAtribucion:
    def test_ids_unicos(self):
        ids = [s.id for s in SOURCES]
        assert len(ids) == len(set(ids))

    def test_toda_fuente_con_atribucion_obligatoria_tiene_cita(self):
        for s in SOURCES:
            if s.attribution_required:
                assert len(s.citation) > 30, f"{s.id}: cita demasiado escueta"

    def test_las_restricciones_comerciales_estan_declaradas(self):
        """Las tres que condicionan si el proyecto puede monetizarse.

        Open-Meteo prohíbe el uso comercial en su plan gratuito —y eso incluye
        publicidad y patrocinios—; eBird y GBIF lo someten a permiso. Si alguna
        deja de estar marcada, alguien podría monetizar incumpliendo.
        """
        for sid in ("open-meteo", "ebird", "gbif"):
            assert SOURCE_BY_ID[sid].commercial_use != "permitido", (
                f"{sid} debe seguir marcada como restringida"
            )

    def test_el_catalogo_cubre_las_fuentes_que_se_ingieren(self):
        """Si se añade un conector y no su atribución, este test lo caza."""
        from appclima.sources import (  # noqa: F401
            ebird,
            enso,
            gbif,
            ibtracs,
            noaa_hazards,
            open_meteo,
            usgs,
            worldbank,
        )

        esperadas = {
            "open-meteo", "usgs", "ebird", "noaa-ncei",
            "ibtracs", "worldbank", "noaa-cpc", "gbif",
        }
        assert esperadas <= set(SOURCE_BY_ID), (
            f"faltan en el catálogo: {esperadas - set(SOURCE_BY_ID)}"
        )

    def test_toda_fuente_dice_qué_se_usa_de_ella(self):
        for s in SOURCES:
            assert len(s.what_we_use) > 20, f"{s.id}: what_we_use vacío o vago"

    def test_las_urls_son_absolutas(self):
        for s in SOURCES:
            assert s.url.startswith("http"), s.id


class TestResultadosNulos:
    def test_ids_unicos(self):
        ids = [n.id for n in NULL_FINDINGS]
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("finding", NULL_FINDINGS, ids=lambda n: n.id)
    def test_cada_nulo_lleva_su_cifra(self, finding):
        """Un nulo sin estadístico es una opinión.

        El catálogo exige la cifra concreta con su n o su umbral: sin eso no se
        puede distinguir «lo medimos y no está» de «no lo miramos bien».
        """
        assert any(c.isdigit() for c in finding.statistic), (
            f"{finding.id}: el estadístico no contiene ninguna cifra"
        )
        assert len(finding.statistic) > 60

    @pytest.mark.parametrize("finding", NULL_FINDINGS, ids=lambda n: n.id)
    def test_cada_nulo_justifica_que_no_es_falta_de_datos(self, finding):
        """La distinción que separa un nulo medido de un «no sabemos»."""
        assert len(finding.why_solid) > 80, f"{finding.id}: justificación pobre"

    @pytest.mark.parametrize("finding", NULL_FINDINGS, ids=lambda n: n.id)
    def test_cada_nulo_deja_una_leccion(self, finding):
        assert len(finding.lesson) > 60, f"{finding.id}: sin lección"

    def test_cubren_varios_dominios(self):
        """Si todos fueran del mismo dominio, sería sesgo de búsqueda."""
        dominios = {n.domain for n in NULL_FINDINGS}
        assert len(dominios) >= 5, f"solo {len(dominios)} dominios: {dominios}"

    def test_hay_nulos_definitivos_y_no_solo_provisionales(self):
        """Un catálogo entero de 'provisional' no afirmaría nada."""
        assert sum(1 for n in NULL_FINDINGS if n.strength == "definitivo") >= 2

    def test_los_nulos_estrella_siguen_presentes(self):
        """Los tres que mejor resumen la disciplina del proyecto.

        Si alguno desaparece del catálogo, que sea una decisión consciente que
        rompa este test — no un descuido al reorganizar.
        """
        ids = {n.id for n in NULL_FINDINGS}
        for esperado in ("clima-sismico", "fenologia-aves",
                         "correlaciones-del-panel"):
            assert esperado in ids
