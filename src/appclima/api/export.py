"""Exportación estática de la API a ficheros JSON.

**Por qué existe.** El payload fijo de la web son 109 KB, y con las 49 ciudades
llega a ~9 MB. Eso cabe entero en un sitio estático, así que desplegar un
servidor para servirlo sería pagar por un problema que no hace falta tener:

    con servidor          estático
    5-20 €/mes            0 €
    rate limiting         no existe el problema
    puede caerse          imposible
    consulta a DuckDB     CDN

**Una ruta se queda fuera a propósito: `/patterns/nulls`.** En un sitio
estático, "privado" solo es real si el fichero NO EXISTE — esconderlo tras una
URL rara sería falsa privacidad, porque cualquiera puede pedirla. El endpoint
sigue vivo en FastAPI para uso local y de administración; simplemente no se
publica.

**Lo que NO cambia.** Los JSON estáticos SON el contrato de la API,
materializado. FastAPI se queda para desarrollo local y para el cliente de iOS,
que necesita consultas con parámetros. La frontera entre datos e interfaz sigue
exactamente donde estaba.

**La decisión de diseño que importa:** este módulo llama a las funciones de
`api.main`, no reimplementa sus consultas. Si duplicase el SQL, las dos versiones
divergirían al primer cambio y el sitio estático serviría algo distinto de lo que
promete la API. Aquí es idéntico por construcción.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from appclima.api import main as api
from appclima.transform import runner

log = logging.getLogger(__name__)


def _routes() -> dict[str, Callable[[], Any]]:
    """Ruta de salida → función que produce su contenido.

    Las rutas replican las de la API con sus parámetros ya fijados, porque un
    fichero estático no tiene query string. El cliente web, en modo estático,
    pide la misma ruta con sufijo .json y sin parámetros.
    """
    return {
        "health": api.health,
        "locations": api.locations,
        "models/skill": api.model_skill,
        "health/dengue": api.dengue,
        "patterns/warming": api.warming,
        "patterns/gutenberg-richter": api.gutenberg_richter,
        "patterns/omori": lambda: api.omori(min_sequence=20),
        "patterns/seismic-weather-myth": api.seismic_weather_myth,
        "patterns/deadliest": lambda: api.deadliest(limit=26),
        "patterns/per-capita": lambda: api.per_capita(limit=25),
        "patterns/enso": api.enso_pattern,
        "disasters": lambda: api.disasters(limit=100),
        "disasters/cascades": lambda: api.disaster_cascades(
            min_deaths=1000, limit=12
        ),
        "disasters/by-century": api.disasters_by_century,
        "epidemics": api.epidemics,
        "cyclones": lambda: api.cyclones(limit=100),
        "cyclones/seasons": lambda: api.cyclone_seasons(basin=None),
        "birds/summary": api.birds_summary,
        "population/world": lambda: api.world_population(
            from_year=-10000, to_year=2030
        ),
        "predict/heatwave": api.heatwave_model,
        "predict/aftershocks": lambda: api.aftershock_forecast(limit=30),
        "events": lambda: api.historical_events(category=None),
        "sources": api.data_sources,
        "prevention/heat-thresholds": api.heat_thresholds,
        "panels/coverage": lambda: api.panel_coverage(panel=None),
        "panels/year": lambda: api.year_panel(
            from_year=1900, to_year=2026, regime=None
        ),
        "panels/month": lambda: api.month_panel(from_year=1950, to_year=2026),
    }


def _per_location_routes(location_ids: list[str]) -> dict[str, Callable[[], Any]]:
    """Rutas que dependen de la ciudad seleccionada."""
    routes: dict[str, Callable[[], Any]] = {}
    for lid in location_ids:
        routes[f"weather/{lid}/anomaly"] = (
            lambda i=lid: api.weather_anomaly(i, start="2025-01-01", limit=5000)
        )
        routes[f"climatology/{lid}"] = lambda i=lid: api.climatology(i)
        routes[f"birds/{lid}"] = lambda i=lid: api.birds(i, limit=90)
    return routes


def _write(path: Path, payload: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    # separators sin espacios: en 9 MB de JSON el ahorro es real y nadie lee
    # estos ficheros a mano.
    text = json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def export_static(out_dir: Path) -> dict[str, Any]:
    """Escribe toda la API como ficheros JSON bajo `out_dir`."""
    # La API guarda su conexión en un global que normalmente rellena el
    # lifespan de FastAPI. Aquí no hay servidor, así que se abre a mano.
    api._con = runner.connect(read_only=True)

    try:
        locations = api.locations()
        location_ids = [loc["id"] for loc in locations]

        routes = {**_routes(), **_per_location_routes(location_ids)}

        total_bytes = 0
        written = 0
        skipped: list[str] = []

        for route, fn in routes.items():
            try:
                payload = fn()
            except HTTPException as exc:
                # Esperado: /climatology solo existe para las 12 ciudades con
                # historia profunda. Un 404 aquí no es un fallo.
                if exc.status_code == 404:
                    skipped.append(route)
                    continue
                raise

            total_bytes += _write(out_dir / f"{route}.json", payload)
            written += 1

        # **Limpieza de rutas retiradas.** Sin esto, un endpoint que deja de
        # exportarse conserva su JSON antiguo en la carpeta de salida y se
        # sigue publicando indefinidamente. Pasó de verdad al sacar
        # /patterns/nulls del sitio público: el fichero seguía ahí.
        #
        # En un sitio estático eso es lo contrario de retirar algo, porque el
        # fichero sigue siendo accesible para cualquiera que conozca la ruta.
        esperados = {out_dir / f"{r}.json" for r in routes}
        esperados.add(out_dir / "manifest.json")

        retirados = 0
        for existente in out_dir.rglob("*.json"):
            if existente not in esperados:
                existente.unlink()
                retirados += 1
        if retirados:
            log.info("Retiradas %d rutas que ya no se exportan", retirados)

        # Carpetas que quedaron vacías tras la limpieza.
        for carpeta in sorted(out_dir.rglob("*"), reverse=True):
            if carpeta.is_dir() and not any(carpeta.iterdir()):
                carpeta.rmdir()

        # Manifiesto: qué se exportó y cuándo. Sirve para que el cliente pueda
        # comprobar la frescura sin pedir todos los ficheros.
        from datetime import UTC, datetime

        manifest = {
            "generated_at": datetime.now(UTC).isoformat(),
            "routes": sorted(routes),
            "skipped": sorted(skipped),
            "n_routes": written,
            "total_bytes": total_bytes,
        }
        total_bytes += _write(out_dir / "manifest.json", manifest)

        log.info("Exportadas %d rutas (%.1f MB)", written, total_bytes / 1_048_576)
        return {
            "written": written,
            "skipped": len(skipped),
            "total_bytes": total_bytes,
            "retired": retirados,
            "out_dir": out_dir,
        }
    finally:
        if api._con is not None:
            api._con.close()
            api._con = None
