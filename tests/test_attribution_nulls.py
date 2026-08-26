"""Tests de los catálogos de atribución y de resultados nulos.

Los nulos NO se publican en el sitio estático: son material de administración.
En un sitio estático "privado" solo es real si el fichero no existe, así que se
excluyen de la exportación en vez de esconderse tras una URL. El endpoint sigue
vivo en FastAPI para uso local, y estos tests siguen protegiendo el catálogo.

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
        """Todo conector debe tener su entrada de licencia. Sin excepciones.

        **Este test existía y no servía.** Comparaba el catálogo contra una
        lista de ids escrita a mano, así que añadir un conector nuevo lo dejaba
        pasando en vacío: su docstring prometía cazar lo que no miraba.

        Se descubrió con OpenDengue. Estuvo publicando datos CC BY 4.0 —que
        exigen cita— sin aparecer en `/sources`, y ningún test se quejó porque
        la lista no lo incluía.

        Ahora se recorre el paquete `appclima.sources` de verdad. Cada módulo
        declara su `SOURCE_ID`, así que un conector nuevo sin entrada de
        licencia rompe los tests en lugar de publicarse sin atribuir.
        """
        import importlib
        import pkgutil

        import appclima.sources as paquete

        sin_declarar: list[str] = []
        sin_catalogo: list[str] = []

        for modulo in pkgutil.iter_modules(paquete.__path__):
            mod = importlib.import_module(f"appclima.sources.{modulo.name}")
            source_id = getattr(mod, "SOURCE_ID", None)
            if source_id is None:
                sin_declarar.append(modulo.name)
            elif source_id not in SOURCE_BY_ID:
                sin_catalogo.append(f"{modulo.name} → {source_id}")

        assert not sin_declarar, (
            "conectores sin SOURCE_ID, así que nadie vigila su atribución: "
            f"{sin_declarar}"
        )
        assert not sin_catalogo, (
            f"conectores sin entrada en el catálogo de licencias: {sin_catalogo}"
        )

    def test_las_fuentes_con_datos_en_bronze_estan_atribuidas(self, warehouse):
        """La comprobación que mira lo PUBLICADO, no lo importado.

        Un módulo puede existir sin haberse ejecutado nunca, y al revés: bronze
        puede tener datos de una integración que se hizo a mano. Lo que obliga
        a atribuir no es tener el código, es servir el dato.
        """
        from appclima.config import settings

        alias = {"curated": "curated", "noaa": "noaa-ncei", "noaa_cpc": "noaa-cpc"}
        bronze = settings.bronze_dir
        if not bronze.exists():
            pytest.skip("sin bronze local")

        publicadas = {d.name for d in bronze.iterdir() if d.is_dir()}
        sin_atribuir = [
            f for f in publicadas
            if alias.get(f, f.replace("_", "-")) not in SOURCE_BY_ID
        ]
        assert not sin_atribuir, (
            f"hay datos en bronze de fuentes sin atribución: {sin_atribuir}"
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

    def test_no_se_exportan_al_sitio_publico(self):
        """Son material interno: se retiran de la exportación, no se esconden.

        En un sitio estático, esconder algo tras una URL rara es falsa
        privacidad — cualquiera puede pedirla. La única forma de retirarlo es
        que el fichero no se genere.
        """
        from appclima.api.export import _routes

        assert "patterns/nulls" not in _routes(), (
            "los nulos volverían a publicarse en el sitio estático"
        )

    def test_los_nulos_estrella_siguen_presentes(self):
        """Los tres que mejor resumen la disciplina del proyecto.

        Si alguno desaparece del catálogo, que sea una decisión consciente que
        rompa este test — no un descuido al reorganizar.
        """
        ids = {n.id for n in NULL_FINDINGS}
        for esperado in ("clima-sismico", "fenologia-aves",
                         "correlaciones-del-panel"):
            assert esperado in ids
