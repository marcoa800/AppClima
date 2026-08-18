"""Catálogo de fuentes con sus licencias y requisitos de atribución.

**No es cortesía: es obligación.** eBird exige reconocimiento explícito al
Cornell Lab of Ornithology, GBIF pide cita formal de los datos usados, y
Open-Meteo permite uso gratuito solo NO COMERCIAL — lo que incluye publicidad y
patrocinios.

Vive en Python y no en el HTML por la misma razón que el catálogo de ciudades:
así se versiona, se testea y se exporta con el resto de la API. Una atribución
escrita a mano en un componente de React se queda obsoleta la primera vez que se
añade una fuente y nadie se entera.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Commercial = Literal["permitido", "prohibido", "requiere permiso"]


class DataSource(BaseModel):
    """Una fuente con todo lo que hay que decir de ella públicamente."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    organization: str
    url: str
    license: str
    commercial_use: Commercial
    attribution_required: bool
    citation: str = Field(description="Texto exacto a mostrar")
    what_we_use: str
    note: str | None = None


SOURCES: list[DataSource] = [
    DataSource(
        id="open-meteo",
        name="Open-Meteo",
        organization="Open-Meteo",
        url="https://open-meteo.com",
        license="CC BY 4.0 (datos) · API gratuita solo para uso no comercial",
        commercial_use="prohibido",
        attribution_required=True,
        citation="Datos meteorológicos de Open-Meteo.com (CC BY 4.0), "
                 "basados en el reanálisis ERA5 de Copernicus / ECMWF.",
        what_we_use="Pronóstico horario de 49 ciudades y 20 años de reanálisis "
                    "ERA5 en 12 de ellas.",
        note="**El límite que condiciona el proyecto.** El uso gratuito es solo "
             "no comercial, e incluye publicidad y patrocinios. Monetizar de "
             "cualquier forma obliga a plan de pago (~29 €/mes) o a autoalojar "
             "su servidor, que es código abierto.",
    ),
    DataSource(
        id="usgs",
        name="USGS Earthquake Catalog",
        organization="United States Geological Survey",
        url="https://earthquake.usgs.gov/fdsnws/event/1/",
        license="Dominio público (obra del gobierno de EE. UU.)",
        commercial_use="permitido",
        attribution_required=False,
        citation="Catálogo sísmico del U.S. Geological Survey.",
        what_we_use="79.501 sismos de magnitud ≥ 4.5 desde 2016, más la ingesta "
                    "diaria con magnitud ≥ 2.5.",
    ),
    DataSource(
        id="noaa-ncei",
        name="NCEI Natural Hazards (HazEl)",
        organization="NOAA National Centers for Environmental Information",
        url="https://www.ngdc.noaa.gov/hazel/view/hazards",
        license="Dominio público",
        commercial_use="permitido",
        attribution_required=False,
        citation="NOAA National Centers for Environmental Information: bases de "
                 "datos de sismos significativos, tsunamis y erupciones "
                 "volcánicas. doi:10.7289/V5TD9V7K",
        what_we_use="10.722 desastres naturales históricos desde el año −4360, "
                    "con muertes, heridos y daños.",
    ),
    DataSource(
        id="ibtracs",
        name="IBTrACS v04r01",
        organization="NOAA National Centers for Environmental Information",
        url="https://www.ncei.noaa.gov/products/international-best-track-archive",
        license="Dominio público",
        commercial_use="permitido",
        attribution_required=True,
        citation="Knapp, K. R., et al. International Best Track Archive for "
                 "Climate Stewardship (IBTrACS) Project, versión 4r01. NOAA "
                 "NCEI. doi:10.25921/82ty-9e16",
        what_we_use="308.310 puntos de trayectoria de ciclones tropicales desde "
                    "1980.",
        note="NOAA pide citar tanto el artículo del proyecto como el DOI del "
             "conjunto de datos.",
    ),
    DataSource(
        id="ebird",
        name="eBird API 2.0",
        organization="Cornell Lab of Ornithology",
        url="https://ebird.org",
        license="Términos de uso de eBird · atribución obligatoria",
        commercial_use="requiere permiso",
        attribution_required=True,
        citation="eBird Basic Dataset. Cornell Lab of Ornithology, Ithaca, "
                 "Nueva York. Datos aportados por observadores voluntarios de "
                 "todo el mundo.",
        what_we_use="5.356 observaciones recientes de aves alrededor de 47 "
                    "ciudades.",
        note="El uso comercial requiere permiso expreso del Cornell Lab.",
    ),
    DataSource(
        id="gbif",
        name="GBIF Occurrence Search",
        organization="Global Biodiversity Information Facility",
        url="https://www.gbif.org",
        license="Los datasets subyacentes son CC0, CC BY o CC BY-NC según el "
                "publicador",
        commercial_use="requiere permiso",
        attribution_required=True,
        citation="GBIF.org — Occurrence Search API. Recuentos mensuales de seis "
                 "especies en siete zonas, 1995-2024.",
        what_we_use="734.000 registros agregados por mes, para el análisis de "
                    "fenología de aves migratorias.",
        note="**Cita incompleta, y conviene decirlo.** Se usó la API de "
             "búsqueda con facetas, que devuelve recuentos y no registros, así "
             "que GBIF no emite un DOI. Una cita formal exige la API de "
             "descargas —que requiere cuenta gratuita— y da un DOI citable con "
             "la lista exacta de datasets y publicadores. Es lo que habría que "
             "hacer antes de publicar cualquier resultado basado en GBIF. "
             "Además, algunos datasets subyacentes son CC BY-NC.",
    ),
    DataSource(
        id="worldbank",
        name="World Development Indicators",
        organization="Banco Mundial",
        url="https://data.worldbank.org",
        license="CC BY 4.0",
        commercial_use="permitido",
        attribution_required=True,
        citation="World Development Indicators, Banco Mundial (CC BY 4.0).",
        what_we_use="Población de 217 países y agregados, 1960-2024.",
    ),
    DataSource(
        id="noaa-cpc",
        name="Oceanic Niño Index (ONI)",
        organization="NOAA Climate Prediction Center",
        url="https://www.cpc.ncep.noaa.gov/data/indices/",
        license="Dominio público",
        commercial_use="permitido",
        attribution_required=False,
        citation="Oceanic Niño Index, NOAA Climate Prediction Center.",
        what_we_use="918 trimestres solapados del índice ONI desde 1950.",
    ),
    DataSource(
        id="curated",
        name="Catálogos curados de este proyecto",
        organization="AppClima",
        url="https://github.com/",
        license="Mismo que el código del proyecto",
        commercial_use="permitido",
        attribution_required=False,
        citation="Catálogos curados de AppClima: 22 epidemias históricas, 17 "
                 "anclas de población mundial y 20 hitos.",
        what_we_use="Lo que ninguna API abierta ofrece: pandemias históricas y "
                    "población anterior a 1950.",
        note="Cada entrada lleva rango de incertidumbre, nivel de confianza y "
             "fuente. Son síntesis de literatura (McEvedy & Jones, HYDE, ONU, "
             "OMS), no datos primarios.",
    ),
]

BY_ID: dict[str, DataSource] = {s.id: s for s in SOURCES}
