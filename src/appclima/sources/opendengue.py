"""OpenDengue — la base de datos global de dengue de la LSHTM.

Reúne los boletines de vigilancia epidemiológica de ~100 países y los
homogeneiza a un esquema común. Para Perú, lo que hay dentro son los datos del
CDC-MINSA que alimentan la sala situacional de metaxénicas: 116 provincias,
semana a semana, de 2000 a 2023.

**Por qué esta fuente y no el portal nacional.** El dataset del MINSA está en
datosabiertos.gob.pe, pero el portal responde 418 a los clientes automatizados
(protección anti-bot de Cloudflare) y la sala situacional es una app Shiny que
habla por websocket: ninguno de los dos es ingerible sin scraping frágil.
OpenDengue publica exactamente los mismos boletines como ficheros CSV
versionados en un repositorio de GitHub, con DOI y licencia CC BY 4.0. Es la
misma información por un camino estable.

**Sobre la versión fijada.** RELEASE está clavado a propósito. OpenDengue
revisa retroactivamente años enteros cuando un país corrige sus boletines, así
que "la última" no es reproducible: el mismo código daría resultados distintos
según el día. Subir de versión es una decisión deliberada, con su commit y su
comprobación de que las series no se movieron bajo los pies.

**Sobre qué se ingiere.** El extracto espacial son 502 MB: 1,9 millones de
filas solo de Brasil. Meterlo entero en bronze sería triplicar el repositorio
para analizar países donde no tenemos clima. La regla es:

  · nacional      → todos los países. Es pequeño y da contexto global.
  · subnacional   → solo países con alguna ciudad *flagship*, es decir con
                    20 años de ERA5. Es exactamente el conjunto donde el cruce
                    clima-enfermedad es posible.

Brasil y Colombia quedan fuera hoy por esa regla, no por capricho: en cuanto
alguna de sus ciudades tenga historia larga de ERA5, entran solas.

Cita: Clarke J, Lim A, Gupte P, et al. A global dataset of publicly available
dengue case count data. Sci Data 11, 296 (2024).
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections.abc import Iterator
from datetime import date, datetime

import httpx

from appclima.config import settings
from appclima.locations import FLAGSHIP_IDS, LOCATIONS
from appclima.schemas.health import DengueWeek

log = logging.getLogger(__name__)

# Id en el catálogo de atribución. Lo lee `test_atribucion` recorriendo
# el paquete: así, añadir un conector sin su entrada de licencia rompe
# los tests en vez de publicarse sin atribuir.
SOURCE_ID = "opendengue"

RELEASE = "V1_3"
BASE_URL = (
    "https://github.com/OpenDengue/master-repo/raw/main/data/releases/V1.3"
)

EXTRACTS: dict[str, str] = {
    # Serie nacional de cada país, la resolución temporal más fina disponible.
    "national": f"National_extract_{RELEASE}.zip",
    # Resolución espacial más fina disponible. Es el fichero grande.
    "subnational": f"Spatial_extract_{RELEASE}.zip",
}

# OpenDengue identifica el país por ISO3; el catálogo de ubicaciones usa ISO2.
# Solo hacen falta los países que tienen ciudad en AppClima: una tabla completa
# de 249 códigos sería ruido que nadie volvería a leer.
ISO2_TO_ISO3: dict[str, str] = {
    "AR": "ARG", "AU": "AUS", "BR": "BRA", "CA": "CAN", "CD": "COD",
    "CL": "CHL", "CN": "CHN", "CO": "COL", "DE": "DEU", "EG": "EGY",
    "ES": "ESP", "ET": "ETH", "FR": "FRA", "GB": "GBR", "GL": "GRL",
    "ID": "IDN", "IN": "IND", "IQ": "IRQ", "IR": "IRN", "IS": "ISL",
    "IT": "ITA", "JP": "JPN", "KE": "KEN", "KR": "KOR", "MA": "MAR",
    "MX": "MEX", "NG": "NGA", "NO": "NOR", "NP": "NPL", "NZ": "NZL",
    "PE": "PER", "PH": "PHL", "PK": "PAK", "RU": "RUS", "SA": "SAU",
    "SE": "SWE", "SG": "SGP", "TH": "THA", "TR": "TUR", "TW": "TWN",
    "US": "USA", "VN": "VNM", "ZA": "ZAF",
}

_MISSING = {"", "NA", "N/A", "NULL", "None", "-"}


def flagship_countries() -> set[str]:
    """ISO3 de los países con al menos una ciudad de 20 años de ERA5."""
    return {
        ISO2_TO_ISO3[loc.country]
        for loc in LOCATIONS
        if loc.id in FLAGSHIP_IDS and loc.country in ISO2_TO_ISO3
    }


def _text(value: str | None) -> str | None:
    """Normaliza los centinelas de ausencia a None.

    OpenDengue viene de R, donde el ausente se escribe `NA`. Sin esta
    conversión, `adm_2_name` valdría la cadena "NA" para las filas nacionales y
    cualquier `WHERE adm_2_name IS NOT NULL` las dejaría pasar.
    """
    if value is None:
        return None
    value = value.strip().strip('"')
    return None if value in _MISSING else value


def _number(value: str | None) -> float | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _day(value: str | None) -> date | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_row(row: dict[str, str]) -> DengueWeek | None:
    """Convierte una fila del CSV en un registro validado, o None si no sirve."""
    start, end = _day(row.get("calendar_start_date")), _day(row.get("calendar_end_date"))
    uuid = _text(row.get("UUID"))
    country = _text(row.get("adm_0_name"))

    # Sin fechas o sin clave natural la fila no es utilizable: no se puede
    # ubicar en el tiempo ni deduplicar. Descartar es más honesto que inventar.
    if not (start and end and uuid and country):
        return None

    year = _number(row.get("Year"))

    return DengueWeek(
        uuid=uuid,
        country_name=country,
        iso3=_text(row.get("ISO_A0")),
        adm_1_name=_text(row.get("adm_1_name")),
        adm_2_name=_text(row.get("adm_2_name")),
        full_name=_text(row.get("full_name")) or country,
        period_start=start,
        period_end=end,
        year=int(year) if year is not None else start.year,
        cases=_number(row.get("dengue_total")),
        case_definition=_text(row.get("case_definition_standardised")),
        spatial_res=_text(row.get("S_res")) or "?",
        temporal_res=_text(row.get("T_res")) or "?",
    )


def _download(extract: str) -> bytes:
    """Descarga uno de los zips de la release.

    Se descarga entero a memoria en vez de en streaming, al revés que IBTrACS.
    El motivo es que un zip no se puede leer secuencialmente: el índice central
    está al **final** del fichero, así que `zipfile` necesita poder saltar hacia
    atrás. Streaming aquí obligaría a un fichero temporal sin ganar nada — el
    mayor de los dos son 52 MB comprimidos.
    """
    url = f"{BASE_URL}/{EXTRACTS[extract]}"
    log.info("OpenDengue: descargando %s", EXTRACTS[extract])

    with httpx.stream(
        "GET",
        url,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
        timeout=httpx.Timeout(60.0, read=300.0),
    ) as response:
        response.raise_for_status()
        payload = response.read()

    log.info("OpenDengue: %.1f MB descargados", len(payload) / 1e6)
    return payload


def _rows(payload: bytes) -> Iterator[dict[str, str]]:
    """Itera el CSV que hay dentro del zip, sin materializar los 502 MB."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"El zip no contiene ningún CSV: {archive.namelist()}")

        with archive.open(names[0]) as handle:
            # newline="" es obligatorio para csv: sin él, un salto de línea
            # dentro de un campo entrecomillado parte la fila en dos.
            stream = io.TextIOWrapper(handle, encoding="utf-8", newline="")
            yield from csv.DictReader(stream)


def fetch(
    extract: str = "subnational",
    countries: set[str] | None = None,
) -> list[DengueWeek]:
    """Descarga un extracto y devuelve los registros validados.

    `countries` filtra por ISO3. Para el extracto subnacional, None significa
    "los países con ciudad flagship" — no "todos", que serían 2,2 millones de
    filas de sitios sin clima con el que cruzarlas.
    """
    if extract not in EXTRACTS:
        raise ValueError(f"Extracto desconocido: {extract}. Opciones: {list(EXTRACTS)}")

    if countries is None and extract == "subnational":
        countries = flagship_countries()
        log.info("OpenDengue: filtrando a países flagship %s", sorted(countries))

    records: list[DengueWeek] = []
    seen, skipped = 0, 0

    for row in _rows(_download(extract)):
        seen += 1
        if countries and _text(row.get("ISO_A0")) not in countries:
            continue
        record = _parse_row(row)
        if record is None:
            skipped += 1
            continue
        records.append(record)

    log.info(
        "OpenDengue/%s: %d filas leídas, %d retenidas, %d descartadas por datos incompletos",
        extract, seen, len(records), skipped,
    )
    return records
