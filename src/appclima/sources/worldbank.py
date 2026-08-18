"""Banco Mundial — API de indicadores de desarrollo.

Gratis, sin API key, sin registro. Cubre 265 países y agregados desde 1960 con
cientos de indicadores. Aquí solo se usan tres, elegidos porque son los que
convierten recuentos absolutos en tasas comparables.

Un detalle que causa errores silenciosos: `country/all` devuelve **países y
agregados mezclados en la misma lista**. "Mundo", "América Latina y el Caribe" y
"Ingreso alto" vienen como filas hermanas de España o Japón. Sumar la columna de
población sin filtrar cuenta a cada persona tres o cuatro veces.

La forma de distinguirlos: en el endpoint de países, un agregado tiene
`region.id == "NA"`. No hay ninguna otra marca fiable.

Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from __future__ import annotations

import logging

from appclima.http import get_json
from appclima.schemas.population import PopulationYear

log = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2"

INDICATORS: dict[str, str] = {
    "population": "SP.POP.TOTL",
    "population_density": "EN.POP.DNST",
    "urban_pct": "SP.URB.TOTL.IN.ZS",
}

PAGE_SIZE = 20_000


def fetch_country_metadata() -> dict[str, dict]:
    """Metadatos por país, indexados por ISO3.

    Se pide aparte porque el endpoint de indicadores no dice si una fila es un
    país o un agregado, y esa distinción decide si los datos se pueden sumar.
    """
    payload = get_json(
        f"{BASE_URL}/country", params={"format": "json", "per_page": 400}
    )
    # La API devuelve [metadatos_de_paginación, [datos]]. Si solo llega el
    # primer elemento, la consulta falló silenciosamente.
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(f"Respuesta inesperada del Banco Mundial: {payload!r:.200}")

    countries: dict[str, dict] = {}
    for row in payload[1]:
        region = (row.get("region") or {}).get("id", "")
        countries[row["id"]] = {
            "iso2": row.get("iso2Code"),
            "name": row.get("name", "").strip(),
            # region "NA" = Not Applicable, la marca de los agregados.
            "is_aggregate": region == "NA",
            "region": (row.get("region") or {}).get("value", "").strip() or None,
            "income_level": (row.get("incomeLevel") or {}).get("value", "").strip()
            or None,
        }

    aggregates = sum(1 for c in countries.values() if c["is_aggregate"])
    log.info(
        "Banco Mundial: %d entidades (%d países, %d agregados)",
        len(countries), len(countries) - aggregates, aggregates,
    )
    return countries


def fetch_population(start_year: int = 1960) -> list[PopulationYear]:
    """Serie de población por país y año."""
    metadata = fetch_country_metadata()
    rows: list[PopulationYear] = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        payload = get_json(
            f"{BASE_URL}/country/all/indicator/{INDICATORS['population']}",
            params={
                "format": "json",
                "per_page": PAGE_SIZE,
                "page": page,
                "date": f"{start_year}:2030",
            },
        )
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError("El Banco Mundial no devolvió datos")

        total_pages = payload[0].get("pages", 1)

        for item in payload[1]:
            code = item.get("countryiso3code") or ""
            country = item.get("country") or {}
            meta = metadata.get(code, {})

            rows.append(
                PopulationYear(
                    country_id=code or country.get("id", "?"),
                    country_name=country.get("value", "").strip(),
                    iso2=meta.get("iso2"),
                    year=int(item["date"]),
                    population=int(item["value"]) if item.get("value") else None,
                    # Ante la duda, marcar como agregado es el error seguro: un
                    # agregado tratado como país infla las sumas.
                    is_aggregate=meta.get("is_aggregate", True),
                    region=meta.get("region"),
                    income_level=meta.get("income_level"),
                )
            )

        log.info("Banco Mundial: página %d/%d, %d filas", page, total_pages, len(rows))
        page += 1

    return rows
