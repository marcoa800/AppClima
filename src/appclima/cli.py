"""Interfaz de línea de comandos.

Un único punto de entrada para todo el pipeline. Esto es lo que después
ejecutará GitHub Actions en cron, así que cada comando tiene que ser
idempotente y seguro de reejecutar: bronze es append-only, y silver deduplica.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from appclima import locations as loc_catalog
from appclima.config import settings
from appclima.schemas.weather import CORE_VARIABLES, HOURLY_VARIABLES
from appclima.sources import (
    ebird,
    enso,
    gbif,
    ibtracs,
    noaa_hazards,
    open_meteo,
    usgs,
    worldbank,
)
from appclima.storage import bronze_stats, write_bronze

console = Console()

app = typer.Typer(
    help="AppClima — pipeline de datos abiertos de clima, sismos y biodiversidad.",
    no_args_is_help=True,
    add_completion=False,
)
ingest_app = typer.Typer(help="Ingesta desde fuentes externas hacia bronze.", no_args_is_help=True)
app.add_typer(ingest_app, name="ingest")


def _setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )


LocationOpt = Annotated[
    list[str] | None,
    typer.Option("--location", "-l", help="id de ubicación; repetible. Por defecto todas."),
]


@app.command()
def locations() -> None:
    """Muestra el catálogo de ubicaciones ancla."""
    table = Table(title=f"Ubicaciones ancla ({len(loc_catalog.LOCATIONS)})")
    for col in ("id", "nombre", "país", "lat", "lon", "köppen", "sismo", "ruta migratoria"):
        table.add_column(col)

    for location in sorted(loc_catalog.LOCATIONS, key=lambda x: -x.lat):
        table.add_row(
            location.id,
            location.name,
            location.country,
            f"{location.lat:>7.2f}",
            f"{location.lon:>8.2f}",
            location.koppen,
            "▁▃▅█"[location.seismic_level],
            location.flyway,
        )
    console.print(table)


@app.command()
def status() -> None:
    """Recuento de lo que hay actualmente en la capa bronze."""
    datasets = [
        ("open_meteo", "weather_hourly"),
        ("usgs", "earthquakes"),
        ("ebird", "observations"),
        ("noaa", "earthquakes"),
        ("noaa", "tsunamis"),
        ("noaa", "volcanos"),
        ("curated", "epidemics"),
        ("ibtracs", "track_points"),
        ("worldbank", "population"),
        ("curated", "world_population"),
        ("noaa_cpc", "oni"),
        ("curated", "historical_events"),
        ("gbif", "phenology"),
    ]

    table = Table(title="Capa bronze")
    table.add_column("fuente")
    table.add_column("dataset")
    table.add_column("ficheros", justify="right")
    table.add_column("filas", justify="right")
    table.add_column("tamaño", justify="right")

    for source, dataset in datasets:
        stats = bronze_stats(source, dataset)
        table.add_row(
            source,
            dataset,
            f"{stats['files']:,}",
            f"{stats['rows']:,}",
            f"{stats['bytes'] / 1_048_576:.1f} MB",
        )

    console.print(table)
    console.print(f"\n[dim]Raíz de datos: {settings.data_dir}[/dim]")


@ingest_app.command("weather")
def ingest_weather(
    location: LocationOpt = None,
    forecast_days: Annotated[int, typer.Option(help="Días de pronóstico hacia adelante.")] = 7,
    past_days: Annotated[int, typer.Option(help="Días de solape hacia atrás.")] = 2,
    verbose: bool = False,
) -> None:
    """Pronóstico horario desde Open-Meteo. Sin API key."""
    _setup_logging(verbose)
    settings.ensure_dirs()

    targets = loc_catalog.resolve(location)
    rows = open_meteo.fetch_forecast(targets, forecast_days=forecast_days, past_days=past_days)
    write_bronze(rows, source="open_meteo", dataset="weather_hourly")

    console.print(f"[green]✓[/green] {len(rows):,} horas de clima en bronze")


@ingest_app.command("weather-archive")
def ingest_weather_archive(
    start: Annotated[datetime, typer.Option(help="Fecha inicial YYYY-MM-DD.")],
    end: Annotated[datetime, typer.Option(help="Fecha final YYYY-MM-DD.")],
    location: LocationOpt = None,
    flagships: Annotated[
        bool,
        typer.Option("--flagships", help="Solo las 12 ciudades de historia profunda."),
    ] = False,
    all_variables: Annotated[
        bool,
        typer.Option("--all-variables", help="Las 14 variables en vez de las 5 básicas."),
    ] = False,
    chunk_days: Annotated[int, typer.Option(help="Tamaño del tramo por petición.")] = 90,
    verbose: bool = False,
) -> None:
    """Archivo histórico ERA5 desde Open-Meteo. Datos desde 1940.

    Dos avisos importantes:

    - ERA5 tiene unos 5 días de latencia. Pedir hasta ayer devuelve nulls.
    - El límite gratuito se cuenta por PESO (ubicaciones × variables × días).
      Un backfill largo sobre las 49 ciudades con las 14 variables NO cabe en
      la cuota diaria. Usa --flagships para historia profunda.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    if flagships and location:
        raise typer.BadParameter("--flagships y --location son mutuamente excluyentes")

    targets = loc_catalog.FLAGSHIPS if flagships else loc_catalog.resolve(location)
    variables = HOURLY_VARIABLES if all_variables else CORE_VARIABLES

    # Estimación del peso antes de gastar cuota. Es mejor avisar aquí que
    # descubrir a mitad del backfill que la API dejó de responder.
    days = (end.date() - start.date()).days + 1
    weight = len(targets) * (len(variables) / 10) * (days / 7)
    console.print(
        f"[dim]Peso estimado: ~{weight:,.0f} llamadas ponderadas "
        f"({len(targets)} ubicaciones × {len(variables)} variables × {days:,} días). "
        f"Cuota diaria gratuita ≈ 10.000.[/dim]"
    )
    if weight > 9_000:
        console.print(
            "[yellow]⚠[/yellow]  Esto supera la cuota diaria y acabará en 429. "
            "Reduce el rango, usa --flagships, o divídelo en varios días."
        )
        raise typer.Exit(code=1)

    # Escribimos tramo a tramo en lugar de acumular en memoria. Con 10 años y
    # 49 ubicaciones la diferencia son varios GB de RAM.
    total = 0
    for chunk in open_meteo.fetch_archive(
        targets,
        start=start.date(),
        end=end.date(),
        chunk_days=chunk_days,
        variables=variables,
    ):
        write_bronze(chunk, source="open_meteo", dataset="weather_hourly")
        total += len(chunk)
        console.print(f"[dim]  … {total:,} filas acumuladas[/dim]")

    console.print(f"[green]✓[/green] {total:,} horas históricas en bronze")


@ingest_app.command("quakes")
def ingest_quakes(
    days_back: Annotated[int, typer.Option(help="Días hacia atrás.")] = 7,
    min_magnitude: Annotated[float, typer.Option(help="Magnitud mínima.")] = 2.5,
    verbose: bool = False,
) -> None:
    """Sismos globales desde USGS. Sin API key."""
    _setup_logging(verbose)
    settings.ensure_dirs()

    quakes = usgs.fetch_recent(days_back=days_back, min_magnitude=min_magnitude)
    write_bronze(quakes, source="usgs", dataset="earthquakes")

    console.print(f"[green]✓[/green] {len(quakes):,} sismos en bronze")


@ingest_app.command("quakes-archive")
def ingest_quakes_archive(
    start: Annotated[datetime, typer.Option(help="Fecha inicial YYYY-MM-DD.")],
    end: Annotated[datetime, typer.Option(help="Fecha final YYYY-MM-DD.")],
    min_magnitude: Annotated[float, typer.Option(help="Magnitud mínima.")] = 4.5,
    verbose: bool = False,
) -> None:
    """Catálogo sísmico histórico, troceado automáticamente."""
    _setup_logging(verbose)
    settings.ensure_dirs()

    quakes = usgs.fetch_range(start.date(), end.date(), min_magnitude=min_magnitude)
    write_bronze(quakes, source="usgs", dataset="earthquakes")

    console.print(f"[green]✓[/green] {len(quakes):,} sismos históricos en bronze")


@ingest_app.command("birds")
def ingest_birds(
    location: LocationOpt = None,
    radius_km: Annotated[int, typer.Option(help="Radio de búsqueda, máx 50.")] = 25,
    days_back: Annotated[int, typer.Option(help="Días hacia atrás, máx 30.")] = 7,
    verbose: bool = False,
) -> None:
    """Observaciones recientes de aves desde eBird. Requiere token gratuito."""
    _setup_logging(verbose)
    settings.ensure_dirs()

    if not ebird.has_token():
        console.print(
            "[yellow]⚠[/yellow]  Sin token de eBird — ingesta de aves omitida.\n"
            "   Consigue uno gratis en [link]https://ebird.org/api/keygen[/link]\n"
            "   y añádelo como APPCLIMA_EBIRD_TOKEN en el fichero .env"
        )
        raise typer.Exit(code=0)

    targets = loc_catalog.resolve(location)
    observations = ebird.fetch_recent_observations(
        targets, radius_km=radius_km, days_back=days_back
    )
    write_bronze(observations, source="ebird", dataset="observations")

    console.print(f"[green]✓[/green] {len(observations):,} observaciones de aves en bronze")


@ingest_app.command("disasters")
def ingest_disasters(
    hazard: Annotated[
        str | None,
        typer.Option(help="earthquake | tsunami | volcano. Por defecto los tres."),
    ] = None,
    min_year: Annotated[int, typer.Option(help="Año mínimo; admite negativos.")] = -4400,
    verbose: bool = False,
) -> None:
    """Desastres naturales históricos desde NOAA NCEI. Sin API key.

    Cubre desde el año -4360 hasta hoy: sismos significativos, tsunamis y
    erupciones volcánicas, con muertes, heridos y daños económicos.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    hazards = [hazard] if hazard else list(noaa_hazards.ENDPOINTS)
    total = 0
    for name in hazards:
        events = noaa_hazards.fetch_hazard(name, min_year=min_year)
        write_bronze(events, source="noaa", dataset=f"{name}s")
        total += len(events)
        console.print(f"[green]✓[/green] {name}: {len(events):,} eventos")

    console.print(f"[green]✓[/green] {total:,} desastres históricos en bronze")


@ingest_app.command("epidemics")
def ingest_epidemics(verbose: bool = False) -> None:
    """Vuelca el catálogo curado de epidemias a bronze.

    No hay red aquí: no existe API abierta de pandemias históricas y el
    catálogo vive en el repositorio (src/appclima/epidemics.py). Este comando
    solo lo materializa en el lakehouse para que el warehouse lo trate como una
    fuente más.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    from appclima.epidemics import EPIDEMICS

    write_bronze(EPIDEMICS, source="curated", dataset="epidemics")
    console.print(
        f"[green]✓[/green] {len(EPIDEMICS)} epidemias en bronze "
        "[dim](catálogo curado, no API)[/dim]"
    )


@ingest_app.command("cyclones")
def ingest_cyclones(
    dataset: Annotated[
        str,
        typer.Option(help="since1980 (recomendado) | all (desde 1842) | last3years"),
    ] = "since1980",
    verbose: bool = False,
) -> None:
    """Ciclones tropicales desde IBTrACS (NOAA). Sin API key.

    Por defecto arranca en 1980, y no es arbitrario: antes de la cobertura
    satelital global, los ciclones que no tocaron tierra ni cruzaron una ruta
    marítima no se observaron. Una serie desde 1842 muestra una tendencia
    creciente espectacular que mide capacidad de observación, no actividad
    ciclónica.

    Usa --dataset all si quieres el archivo completo, sabiendo eso.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    total = 0
    for batch in ibtracs.fetch_tracks(dataset):
        write_bronze(batch, source="ibtracs", dataset="track_points")
        total += len(batch)
        console.print(f"[dim]  … {total:,} puntos de trayectoria[/dim]")

    console.print(f"[green]✓[/green] {total:,} puntos de ciclones en bronze")


@ingest_app.command("population")
def ingest_population(verbose: bool = False) -> None:
    """Población por país desde el Banco Mundial, más el histórico curado.

    Es el denominador que hace comparable todo lo demás: sin él, cualquier serie
    de víctimas mide sobre todo cuánta gente había disponible para morir.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    rows = worldbank.fetch_population()
    write_bronze(rows, source="worldbank", dataset="population")

    from appclima.world_population import WORLD_POPULATION

    write_bronze(WORLD_POPULATION, source="curated", dataset="world_population")

    console.print(
        f"[green]✓[/green] {len(rows):,} filas país-año del Banco Mundial "
        f"+ {len(WORLD_POPULATION)} años ancla históricos"
    )


@ingest_app.command("enso")
def ingest_enso(verbose: bool = False) -> None:
    """Índice ONI de El Niño / La Niña desde 1950. Sin API key."""
    _setup_logging(verbose)
    settings.ensure_dirs()

    values = enso.fetch_oni()
    write_bronze(values, source="noaa_cpc", dataset="oni")

    console.print(f"[green]✓[/green] {len(values):,} trimestres de ONI en bronze")


@ingest_app.command("events")
def ingest_events(verbose: bool = False) -> None:
    """Vuelca el catálogo curado de hitos históricos y de datos.

    La categoría `observacion` es la útil: marca cuándo cambió nuestra capacidad
    de medir, que es lo que explica los saltos que parecen tendencias en las
    series largas.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    from appclima.historical_events import EVENTS

    write_bronze(EVENTS, source="curated", dataset="historical_events")
    console.print(f"[green]✓[/green] {len(EVENTS)} hitos históricos en bronze")


@ingest_app.command("phenology")
def ingest_phenology(
    start_year: Annotated[int, typer.Option(help="Año inicial.")] = 1995,
    end_year: Annotated[int, typer.Option(help="Año final.")] = 2024,
    controls: Annotated[
        bool,
        typer.Option("--controls", help="Especies residentes de control en vez de migratorias."),
    ] = False,
    verbose: bool = False,
) -> None:
    """Fenología de aves migratorias desde GBIF. Sin API key.

    Responde a la pregunta que eBird no puede: ¿llegan las aves antes que hace
    treinta años? Usa la API de facetas, así que descarga recuentos mensuales
    en lugar de millones de registros.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    years = range(start_year, end_year + 1)
    species = gbif.CONTROL_SPECIES if controls else gbif.SPECIES
    n_requests = len(species) * len(gbif.TARGET_CITIES) * len(years)
    console.print(
        f"[dim]{len(species)} especies{' CONTROL' if controls else ''} × "
        f"{len(gbif.TARGET_CITIES)} ciudades × {len(years)} años = "
        f"{n_requests:,} peticiones[/dim]"
    )

    total = 0
    for batch in gbif.fetch_phenology(years, species=species, is_control=controls):
        write_bronze(batch, source="gbif", dataset="phenology")
        total += len(batch)
        console.print(f"[dim]  … {total:,} filas especie-ciudad-año[/dim]")

    console.print(f"[green]✓[/green] {total:,} filas de fenología en bronze")


@ingest_app.command("all")
def ingest_all(
    cadence: Annotated[
        str,
        typer.Option(
            "--cadence",
            help="daily | weekly | monthly | yearly | full",
        ),
    ] = "daily",
    verbose: bool = False,
) -> None:
    """Ejecuta las fuentes que corresponden a esta cadencia.

    **No todas las fuentes cambian al mismo ritmo, y tratarlas igual es un
    desperdicio o un olvido.** El pronóstico caduca en horas; el catálogo
    sísmico histórico de NOAA no ha cambiado en años; el Banco Mundial publica
    una vez al año.

    Este comando arrancó cubriendo solo las tres fuentes de la fase 1 y se quedó
    ahí mientras el proyecto crecía a once. El cron diario refrescaba tres y
    dejaba envejecer ocho en silencio, sin que nada lo detectara — porque
    /health solo vigila la frescura de cuatro datasets.

    Cadencias:

      daily    clima, sismos y aves. Lo que caduca de verdad.
      weekly   + ciclones (IBTrACS publica por lotes)
      monthly  + índice ONI (es una media móvil trimestral)
      yearly   + población, desastres históricos y fenología
      full     todo, para reconstruir desde cero

    Cada nivel incluye a los anteriores. Si una fuente falla, las demás siguen:
    no queremos perder el clima del día porque eBird estuviera caído.
    """
    _setup_logging(verbose)
    settings.ensure_dirs()

    niveles = ["daily", "weekly", "monthly", "yearly", "full"]
    if cadence not in niveles:
        raise typer.BadParameter(f"Cadencia desconocida. Opciones: {niveles}")
    # Cada nivel incluye a los anteriores: 'yearly' ejecuta también lo diario,
    # semanal y mensual. 'full' lo ejecuta todo.
    incluidas = set(niveles[: niveles.index(cadence) + 1])

    def _clima() -> str:
        rows = open_meteo.fetch_forecast(loc_catalog.LOCATIONS)
        write_bronze(rows, source="open_meteo", dataset="weather_hourly")
        return f"{len(rows):,} horas"

    def _sismos() -> str:
        quakes = usgs.fetch_recent()
        write_bronze(quakes, source="usgs", dataset="earthquakes")
        return f"{len(quakes):,} eventos"

    def _aves() -> str:
        if not ebird.has_token():
            return "[yellow]omitido: sin token[/yellow]"
        obs = ebird.fetch_recent_observations(loc_catalog.LOCATIONS)
        write_bronze(obs, source="ebird", dataset="observations")
        return f"{len(obs):,} observaciones"

    def _ciclones() -> str:
        total = 0
        for batch in ibtracs.fetch_tracks("last3years"):
            write_bronze(batch, source="ibtracs", dataset="track_points")
            total += len(batch)
        return f"{total:,} puntos (últimos 3 años)"

    def _enso() -> str:
        values = enso.fetch_oni()
        write_bronze(values, source="noaa_cpc", dataset="oni")
        return f"{len(values):,} trimestres"

    def _poblacion() -> str:
        rows = worldbank.fetch_population()
        write_bronze(rows, source="worldbank", dataset="population")
        from appclima.world_population import WORLD_POPULATION

        write_bronze(WORLD_POPULATION, source="curated", dataset="world_population")
        return f"{len(rows):,} país-año"

    def _desastres() -> str:
        total = 0
        for name in noaa_hazards.ENDPOINTS:
            events = noaa_hazards.fetch_hazard(name)
            write_bronze(events, source="noaa", dataset=f"{name}s")
            total += len(events)
        return f"{total:,} eventos"

    def _curados() -> str:
        from appclima.epidemics import EPIDEMICS
        from appclima.historical_events import EVENTS

        write_bronze(EPIDEMICS, source="curated", dataset="epidemics")
        write_bronze(EVENTS, source="curated", dataset="historical_events")
        return f"{len(EPIDEMICS)} epidemias + {len(EVENTS)} hitos"

    def _fenologia() -> str:
        total = 0
        for controls in (False, True):
            especies = gbif.CONTROL_SPECIES if controls else gbif.SPECIES
            for batch in gbif.fetch_phenology(
                range(1995, 2025), species=especies, is_control=controls
            ):
                write_bronze(batch, source="gbif", dataset="phenology")
                total += len(batch)
        return f"{total:,} especie-ciudad-año"

    # (nombre, cadencia mínima, función)
    FUENTES: list[tuple[str, str, Any]] = [
        ("clima", "daily", _clima),
        ("sismos", "daily", _sismos),
        ("aves", "daily", _aves),
        ("ciclones", "weekly", _ciclones),
        ("enso", "monthly", _enso),
        ("población", "yearly", _poblacion),
        ("desastres", "yearly", _desastres),
        ("catálogos curados", "yearly", _curados),
        ("fenología", "yearly", _fenologia),
    ]

    results: list[tuple[str, str]] = []
    for nombre, minima, fn in FUENTES:
        if minima not in incluidas:
            continue
        try:
            results.append((nombre, fn()))
        except Exception as exc:  # noqa: BLE001 — aislamos el fallo a propósito
            logging.exception("Falló la ingesta de %s", nombre)
            results.append((nombre, f"[red]error: {exc}[/red]"))

    table = Table(title=f"Ingesta ({cadence})")
    table.add_column("fuente")
    table.add_column("resultado")
    for name, outcome in results:
        table.add_row(name, outcome)
    console.print(table)

    fallos = sum(1 for _, r in results if "error:" in r)
    if fallos:
        console.print(f"[red]{fallos} fuente(s) fallaron[/red]")
        raise typer.Exit(code=1)


@app.command()
def export(
    out: Annotated[
        Path,
        typer.Option(help="Carpeta de salida. Se crea si no existe."),
    ] = Path("web/public/api"),
    verbose: bool = False,
) -> None:
    """Exporta toda la API como ficheros JSON estáticos.

    El payload completo son ~9 MB, así que cabe en cualquier hosting estático
    gratuito. Con esto la web pública no necesita servidor: sin coste, sin rate
    limiting, sin caídas y servido desde CDN.

    FastAPI se queda para desarrollo local y para el cliente de iOS, que sí
    necesita consultas con parámetros.
    """
    _setup_logging(verbose)

    from appclima.api.export import export_static

    result = export_static(out)

    console.print(
        f"[green]✓[/green] {result['written']} rutas en {result['out_dir']} "
        f"({result['total_bytes'] / 1_048_576:.1f} MB)"
    )
    if result.get("retired"):
        console.print(
            f"[yellow]↺[/yellow] {result['retired']} rutas retiradas que ya no "
            "se exportan (dejaban de estar en la API pero seguían publicadas)"
        )
    if result["skipped"]:
        console.print(
            f"[dim]  {result['skipped']} rutas omitidas (404 esperado: la "
            "climatología solo existe en las 12 ciudades flagship)[/dim]"
        )


@app.command()
def build(verbose: bool = False) -> None:
    """Construye las capas silver y gold en DuckDB desde bronze."""
    _setup_logging(verbose)
    from appclima.transform.runner import build_warehouse

    build_warehouse()


if __name__ == "__main__":
    app()
