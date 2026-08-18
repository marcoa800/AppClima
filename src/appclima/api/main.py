"""Endpoints de la API.

Convenciones aplicadas en todos los endpoints:

  - Todas las horas salen en UTC con offset explícito. La conversión a hora
    local es responsabilidad del cliente, que es el único que sabe dónde está
    el usuario.
  - Los límites de paginación tienen tope duro. Un endpoint que acepta
    `limit=1000000` es una denegación de servicio esperando a ocurrir.
  - Nada de SQL construido por concatenación de parámetros. Todo va por
    parámetros enlazados de DuckDB.
  - **Todo ORDER BY termina en una columna que desempata de forma única.** Sin
    eso el orden de las filas empatadas es arbitrario y cambia entre
    ejecuciones: Sídney y Manaos tienen 89 especies cada una, y se
    intercambiaban de sitio en cada llamada. Da igual mientras la API se
    consulte en vivo, pero la exportación estática se publica desde CI y
    generaría un diff en cada ejecución aunque los datos no hubieran cambiado —
    haciendo imposible distinguir un cambio real del ruido.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated, Any

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from appclima.config import settings
from appclima.transform import runner

log = logging.getLogger(__name__)

MAX_LIMIT = 5_000

# Conexión única de solo lectura, compartida por todas las peticiones. DuckDB
# es seguro para lecturas concurrentes desde varios hilos sobre la misma
# conexión, y abrir una por petición sobre un fichero de 500 MB sería un
# desperdicio notable.
_con: duckdb.DuckDBPyConnection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _con
    if not settings.warehouse_path.exists():
        raise RuntimeError(
            f"No existe el warehouse en {settings.warehouse_path}. "
            "Ejecuta primero: appclima ingest all && appclima build"
        )
    _con = runner.connect(read_only=True)
    log.info("Warehouse abierto: %s", settings.warehouse_path)
    yield
    if _con is not None:
        _con.close()


app = FastAPI(
    title="AppClima API",
    version="0.1.0",
    description=(
        "Datos abiertos de clima, sismos y biodiversidad. "
        "Fuentes: Open-Meteo (ERA5), USGS Earthquake Catalog, eBird."
    ),
    lifespan=lifespan,
)

# En desarrollo el frontend corre en otro puerto, así que necesita CORS. En
# producción esto debe restringirse al dominio real: allow_origins=["*"] con
# allow_credentials sería un agujero, y por eso las credenciales van a False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _query(sql: str, params: list[Any] | None = None) -> list[dict]:
    """Ejecuta SQL y devuelve una lista de diccionarios lista para serializar."""
    if _con is None:
        raise HTTPException(status_code=503, detail="Warehouse no disponible")

    # cursor() da un cursor independiente por petición sobre la misma conexión:
    # es lo que permite consultas concurrentes sin que se pisen los resultados.
    cursor = _con.cursor()
    try:
        # Un cursor de DuckDB abre una SESIÓN nueva y no hereda los ajustes de
        # la conexión padre. Sin este SET, los TIMESTAMPTZ se serializan en la
        # zona horaria de la máquina que aloja la API, y el cliente recibiría
        # horas con offset local en lugar de UTC — que es justo lo que la API
        # promete. Detectado porque /health devolvía "-05" en vez de "+00".
        cursor.execute("SET TimeZone='UTC'")

        result = cursor.execute(sql, params or [])
        columns = [d[0] for d in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    finally:
        cursor.close()


@app.get("/health", summary="Estado del servicio y frescura de los datos")
def health() -> dict:
    """Incluye la fecha del dato más reciente de cada fuente.

    Un health check que solo dice "OK" es casi inútil en un sistema de datos: el
    servicio puede estar perfectamente vivo sirviendo datos de hace tres
    semanas porque el cron se rompió. La frescura es la métrica que importa.
    """
    freshness = _query("""
        SELECT 'weather_observed' AS dataset, max(local_date)::VARCHAR AS latest
        FROM gold_weather_daily WHERE kind = 'observed'
        UNION ALL
        SELECT 'weather_forecast', max(local_date)::VARCHAR
        FROM gold_weather_daily WHERE kind = 'forecast'
        UNION ALL
        SELECT 'earthquakes', max(time)::VARCHAR FROM silver_earthquakes
        UNION ALL
        SELECT 'birds', max(obs_date)::VARCHAR FROM gold_bird_daily
    """)
    return {"status": "ok", "freshness": {r["dataset"]: r["latest"] for r in freshness}}


@app.get("/locations", summary="Catálogo de ubicaciones ancla")
def locations() -> list[dict]:
    return _query("""
        SELECT l.id, l.name, l.country, l.lat, l.lon, l.timezone,
               l.koppen, l.seismic_level, l.flyway,
               -- Si tiene historia profunda o solo datos recientes. El cliente
               -- necesita saberlo para no ofrecer gráficas de 20 años en una
               -- ciudad que solo tiene 9 días.
               EXISTS (
                   SELECT 1 FROM gold_climatology c WHERE c.location_id = l.id
               ) AS has_climatology
        FROM dim_locations l
        ORDER BY l.name
    """)


@app.get("/weather/{location_id}/daily", summary="Serie diaria de una ubicación")
def weather_daily(
    location_id: str,
    start: date | None = None,
    end: date | None = None,
    kind: Annotated[str | None, Query(pattern="^(observed|forecast)$")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 400,
) -> list[dict]:
    conditions = ["location_id = ?"]
    params: list[Any] = [location_id]

    if start:
        conditions.append("local_date >= ?")
        params.append(start)
    if end:
        conditions.append("local_date <= ?")
        params.append(end)
    if kind:
        conditions.append("kind = ?")
        params.append(kind)

    params.append(limit)
    rows = _query(
        f"""
        SELECT location_id, local_date, kind, temp_mean, temp_min, temp_max,
               temp_range, apparent_max, precip_sum, pressure_msl_mean,
               humidity_mean, wind_gust_max, hours
        FROM gold_weather_daily
        WHERE {" AND ".join(conditions)}
        ORDER BY local_date DESC
        LIMIT ?
        """,
        params,
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Sin datos para '{location_id}'")
    return rows


@app.get("/weather/{location_id}/anomaly", summary="Anomalías frente a la climatología")
def weather_anomaly(
    location_id: str,
    start: date | None = None,
    end: date | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 400,
) -> list[dict]:
    conditions = ["location_id = ?"]
    params: list[Any] = [location_id]

    if start:
        conditions.append("local_date >= ?")
        params.append(start)
    if end:
        conditions.append("local_date <= ?")
        params.append(end)

    params.append(limit)
    return _query(
        f"""
        SELECT location_id, local_date, kind, temp_mean, clim_mean, anomaly_c,
               z_score, temp_max, clim_max_p95, clim_max_record,
               extreme_heat, record_heat, extreme_cold, record_cold,
               in_baseline, clim_n_samples
        FROM gold_temperature_anomaly
        WHERE {" AND ".join(conditions)}
        ORDER BY local_date DESC
        LIMIT ?
        """,
        params,
    )


@app.get("/climatology/{location_id}", summary="Normal climática por día del año")
def climatology(location_id: str) -> list[dict]:
    rows = _query(
        """
        SELECT doy, n_samples, temp_mean_avg, temp_mean_sd,
               temp_mean_p05, temp_mean_p95,
               temp_max_avg, temp_max_p95, temp_max_record,
               temp_min_avg, temp_min_p05, temp_min_record, precip_avg
        FROM gold_climatology
        WHERE location_id = ?
        ORDER BY doy
        """,
        [location_id],
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Sin climatología para '{location_id}'. Solo las 12 ciudades "
                "flagship tienen historia profunda — ver /locations."
            ),
        )
    return rows


@app.get("/quakes", summary="Sismos, opcionalmente filtrados por cercanía")
def quakes(
    near: Annotated[str | None, Query(description="id de ubicación ancla")] = None,
    radius_km: Annotated[float, Query(ge=1, le=700)] = 700,
    min_magnitude: Annotated[float, Query(ge=0, le=10)] = 4.5,
    days_back: Annotated[int | None, Query(ge=1, le=4000)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 200,
) -> list[dict]:
    """Sin `near` devuelve sismos globales; con `near`, los cercanos a esa ciudad."""
    params: list[Any] = []

    if near:
        conditions = ["location_id = ?", "distance_km <= ?", "magnitude >= ?"]
        params.extend([near, radius_km, min_magnitude])
        select = """
            SELECT event_id, time, local_time, magnitude, magnitude_type, depth_km,
                   depth_class, place, distance_km, lat, lon, tsunami, alert, url
            FROM gold_quakes_near_city
        """
    else:
        conditions = ["magnitude >= ?"]
        params.append(min_magnitude)
        select = """
            SELECT event_id, time, magnitude, magnitude_type, depth_km,
                   depth_class, place, lat, lon, tsunami, alert, url
            FROM silver_earthquakes
        """

    if days_back:
        conditions.append("time >= now() - INTERVAL (?) DAY")
        params.append(days_back)

    params.append(limit)
    return _query(
        f"{select} WHERE {' AND '.join(conditions)} ORDER BY time DESC LIMIT ?",
        params,
    )


@app.get("/patterns/gutenberg-richter", summary="Relación magnitud-frecuencia")
def gutenberg_richter() -> dict:
    return {
        "distribution": _query("""
            SELECT mag_bin, n_events, n_cumulative, log10_n_cumulative
            FROM gold_quake_magnitude_frequency ORDER BY mag_bin
        """),
        "b_values": _query("""
            SELECT scope, n_events, mag_mean, mag_max, b_value, b_std_error, a_value
            FROM gold_quake_b_value ORDER BY n_events DESC, scope
        """),
        "note": (
            "log10(N) = a - b·M. La magnitud de completitud es 4.5: por debajo "
            "el catálogo está incompleto por diseño de la ingesta, no por "
            "ausencia de sismos."
        ),
    }


@app.get("/patterns/omori", summary="Decaimiento de réplicas")
def omori(min_sequence: Annotated[int, Query(ge=1, le=1000)] = 20) -> dict:
    return {
        "decay": _query("""
            SELECT day_after,
                   count(DISTINCT mainshock_id) AS sequences_active,
                   sum(aftershocks) AS aftershocks_total,
                   round(avg(aftershocks), 2) AS aftershocks_mean
            FROM gold_quake_sequences
            WHERE day_after <= 30
            GROUP BY 1 ORDER BY 1
        """),
        "largest_sequences": _query(
            """
            SELECT DISTINCT mainshock_id, mainshock_place, mainshock_mag,
                   mainshock_time, sequence_total
            FROM gold_quake_sequences
            WHERE sequence_total >= ?
            ORDER BY sequence_total DESC, mainshock_id LIMIT 20
            """,
            [min_sequence],
        ),
        "caveat": (
            "aftershocks_mean está sesgado al alza en los días altos: solo "
            "entran secuencias que seguían activas, no hay relleno con ceros."
        ),
    }


@app.get("/patterns/seismic-weather-myth", summary="Contraste del 'clima sísmico'")
def seismic_weather_myth() -> dict:
    return {
        "results": _query("""
            SELECT location_id, n_days, total_quakes, pct_days_with_quake,
                   r_pressure, r_temperature, r_significance_threshold,
                   pressure_significant, pct_variance_explained
            FROM gold_quake_pressure_test ORDER BY total_quakes DESC, location_id
        """),
        "interpretation": (
            "No hay relación práctica. Con n=87.654 días el umbral de "
            "significación cae a r=0,0066, así que correlaciones de 0,01 salen "
            "'significativas' explicando el 0,014% de la varianza. La "
            "significación estadística responde a '¿es distinto de cero?', no a "
            "'¿importa?'. Un resultado nulo bien medido es un resultado."
        ),
    }


@app.get("/patterns/warming", summary="Anomalía media por año")
def warming() -> dict:
    return {
        "by_year": _query("""
            SELECT year(local_date) AS year,
                   round(avg(anomaly_c), 3) AS anomaly_mean_c,
                   round(100.0 * avg(CASE WHEN extreme_heat THEN 1.0 ELSE 0.0 END), 1)
                       AS pct_extreme_heat_days,
                   sum(CASE WHEN record_heat THEN 1 ELSE 0 END) AS heat_records,
                   count(DISTINCT location_id) AS locations,
                   count(*) AS days
            FROM gold_temperature_anomaly
            WHERE kind = 'observed'
            GROUP BY 1 ORDER BY 1
        """),
        "note": (
            "Base fija 2006-2020. Los años dentro de la base tienen anomalía "
            "media 0 por construcción y récords imposibles: la señal solo se "
            "interpreta de 2021 en adelante. Muestra: 12 ciudades, no global."
        ),
    }


# NOTA DE ENRUTADO: esta ruta estática DEBE declararse antes que
# /birds/{location_id}. FastAPI resuelve por orden de registro, así que si la
# ruta con parámetro va primero captura "summary" como si fuera un id de
# ubicación y devuelve una lista vacía en vez de este resumen. Costó un 200 con
# el cuerpo equivocado, que es peor que un error: falla en silencio.
@app.get("/birds/summary", summary="Riqueza de especies y sesgo de esfuerzo")
def birds_summary() -> dict:
    rows = _query("""
        SELECT b.location_id, l.name AS location_name, l.country, l.lat, l.lon,
               l.koppen, l.flyway, abs(l.lat) AS abs_lat,
               max(b.species_richness) AS species_richness,
               max(b.checklists) AS checklists,
               max(b.observations) AS observations,
               max(b.temp_mean) AS temp_mean
        FROM gold_bird_daily b
        JOIN dim_locations l ON l.id = b.location_id
        GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
        ORDER BY species_richness DESC, b.location_id
    """)

    correlations = _query("""
        SELECT round(corr(abs(l.lat), b.species_richness), 3) AS r_latitude,
               round(100 * pow(corr(abs(l.lat), b.species_richness), 2), 1)
                   AS pct_variance_latitude,
               round(corr(b.checklists, b.species_richness), 3) AS r_effort,
               round(100 * pow(corr(b.checklists, b.species_richness), 2), 1)
                   AS pct_variance_effort,
               count(*) AS n
        FROM gold_bird_daily b
        JOIN dim_locations l ON l.id = b.location_id
    """)

    return {
        "locations": rows,
        "correlations": correlations[0] if correlations else {},
        "finding": (
            "El esfuerzo de observación explica el 68,3% de la varianza en "
            "riqueza de especies; la latitud, el 1,0%. Denver encabeza la lista "
            "con 134 especies y Manaos, en plena Amazonía, tiene 89 — no porque "
            "Denver sea más biodiverso, sino porque tiene 56 listas de "
            "observación frente a 4. Este dataset mide sobre todo cuánta gente "
            "salió al campo."
        ),
        "caveat": (
            "eBird es ciencia ciudadana, no una red de sensores. Cualquier "
            "análisis de biodiversidad con estos datos debe normalizar por "
            "esfuerzo (dividir por `checklists`) antes de comparar lugares. Y "
            "el endpoint devuelve solo la observación más reciente por especie: "
            "sirve para 'qué hay ahora', no para series temporales."
        ),
    }

@app.get("/birds/{location_id}", summary="Riqueza de especies diaria")
def birds(
    location_id: str,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 90,
) -> list[dict]:
    return _query(
        """
        SELECT location_id, obs_date, species_richness, observations, checklists,
               individuals_counted, temp_mean, temp_max, precip_sum, temp_anomaly_c
        FROM gold_bird_daily
        WHERE location_id = ?
        ORDER BY obs_date DESC LIMIT ?
        """,
        [location_id, limit],
    )


# ─── Desastres históricos ────────────────────────────────────────────────────
#
# Fuente: NOAA NCEI (dominio público) para peligros naturales, y catálogo
# curado del repositorio para epidemias — no existe API abierta de pandemias
# históricas, y esa ausencia se documenta en cada respuesta.


@app.get("/disasters", summary="Desastres naturales históricos más mortales")
def disasters(
    hazard: Annotated[
        str | None, Query(pattern="^(earthquake|tsunami|volcano)$")
    ] = None,
    min_deaths: Annotated[int, Query(ge=0)] = 0,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 100,
) -> dict:
    conditions = ["deaths >= ?"]
    params: list[Any] = [min_deaths]

    if hazard:
        conditions.append("hazard_type = ?")
        params.append(hazard)
    if from_year is not None:
        conditions.append("year >= ?")
        params.append(from_year)
    if to_year is not None:
        conditions.append("year <= ?")
        params.append(to_year)

    params.append(limit)
    return {
        "events": _query(
            f"""
            SELECT hazard_type, source_id, year, month, day, date_precision,
                   century, country, location_name, latitude, longitude,
                   deaths, deaths_direct, deaths_from_cascade, damage_musd,
                   eq_magnitude, eq_intensity, volcano_vei, volcano_name,
                   generated_tsunami, tsunami_wave_m
            FROM gold_disasters_ranked
            WHERE {" AND ".join(conditions)}
            ORDER BY deaths DESC, hazard_type, source_id
            LIMIT ?
            """,
            params,
        ),
        "caveat": (
            "Solo eventos con cifra exacta de muertes. El registro histórico "
            "está muy sesgado hacia el presente: son los desastres mejor "
            "DOCUMENTADOS, no los más mortales que hayan ocurrido."
        ),
    }


@app.get("/disasters/cascades", summary="Cuando un peligro desencadena otro")
def disaster_cascades(
    min_deaths: Annotated[int, Query(ge=0)] = 1000,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 60,
) -> dict:
    return {
        "cascades": _query(
            """
            SELECT year, hazard_type, country, location_name, eq_magnitude,
                   volcano_vei, deaths_direct, deaths AS deaths_total,
                   deaths_from_cascade, tsunami_wave_m,
                   round(100.0 * deaths_from_cascade / deaths, 1) AS pct_from_cascade
            FROM gold_disasters_ranked
            WHERE deaths_from_cascade > 0 AND deaths >= ?
            ORDER BY deaths_from_cascade DESC, year, location_name
            LIMIT ?
            """,
            [min_deaths, limit],
        ),
        "finding": (
            "En los desastres costeros el peligro primario rara vez es el que "
            "mata. El sismo de Sumatra de 2004 causó 1.001 muertes directas; "
            "el tsunami que generó, 226.898 más — el 99,6% del total."
        ),
    }


@app.get("/disasters/by-century", summary="Sesgo del registro histórico")
def disasters_by_century() -> dict:
    return {
        "by_century": _query("""
            SELECT century,
                   sum(events) AS events,
                   sum(events_with_exact_deaths) AS events_with_exact_deaths,
                   round(100.0 * sum(events_with_exact_deaths) / sum(events), 1)
                       AS pct_with_exact_deaths,
                   sum(deaths_counted) AS deaths_counted
            FROM gold_disasters_by_century
            GROUP BY 1 ORDER BY 1
        """),
        "warning": (
            "Esta serie NO mide si hay más desastres con el tiempo. Mide "
            "cobertura documental. Los eventos registrados pasan de 20 en el "
            "siglo III a.C. a 4.374 en el XXI, y la proporción con cifra exacta "
            "de muertes de ~0% a 42%. La actividad geológica, en escalas de "
            "siglos, es esencialmente constante."
        ),
    }


@app.get("/epidemics", summary="Catálogo curado de epidemias y pandemias")
def epidemics() -> dict:
    return {
        "epidemics": _query("""
            SELECT id, name, pathogen, disease, start_year, end_year, ongoing,
                   duration_years, deaths_low, deaths_high, deaths_mid,
                   deaths_uncertainty_ratio, regions, estimate_confidence,
                   source, note, century
            FROM silver_epidemics
            ORDER BY coalesce(deaths_mid, 0) DESC, id
        """),
        "provenance": (
            "Catálogo CURADO, no una API. No existe fuente abierta con datos "
            "históricos de pandemias: WHO GHO sirve indicadores modernos, "
            "EM-DAT exige registro y licencia no comercial, y para la peste "
            "negra solo hay historiografía. Cada registro lleva rango de "
            "incertidumbre, nivel de confianza y fuente."
        ),
        "how_to_read": (
            "Nunca uses deaths_mid sola. Es un artefacto para poder ordenar. "
            "El dato real es el rango: la plaga de Justiniano va de 15 a 100 "
            "millones (ratio 6,7), y ese ancho ES la información."
        ),
    }


@app.get("/patterns/deadliest", summary="Epidemias frente a desastres naturales")
def deadliest(limit: Annotated[int, Query(ge=1, le=200)] = 30) -> dict:
    return {
        "events": _query(
            """
            SELECT family, event_key, event_name, subtype, year, end_year,
                   duration_years, location, deaths_low, deaths_high,
                   deaths_representative, deaths_uncertainty_ratio,
                   estimate_confidence, estimate_kind
            FROM gold_epidemics_vs_disasters
            ORDER BY deaths_representative DESC, event_key
            LIMIT ?
            """,
            [limit],
        ),
        "finding": (
            "La peor pandemia mató entre 300 y 800 veces más que el peor "
            "desastre natural registrado. El terremoto de Shaanxi de 1556, el "
            "más mortal del archivo, se llevó 830.000 vidas; la peste negra, "
            "entre 75 y 200 millones."
        ),
        "caveat": (
            "Comparación legítima solo si se leen tres columnas juntas: "
            "estimate_kind (recuento vs estimación), duration_years (segundos "
            "frente a décadas) y el par low/high (los desastres traen un "
            "número, las epidemias un rango que llega a factor 7)."
        ),
    }


# ─── Ciclones tropicales (IBTrACS) ───────────────────────────────────────────


@app.get("/cyclones", summary="Ciclones tropicales desde 1980")
def cyclones(
    basin: Annotated[str | None, Query(pattern="^(NA|EP|WP|NI|SI|SP|SA)$")] = None,
    season: int | None = None,
    min_wind_kt: Annotated[float, Query(ge=0, le=250)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 100,
) -> dict:
    conditions = ["max_wind_kt >= ?"]
    params: list[Any] = [min_wind_kt]

    if basin:
        conditions.append("basin = ?")
        params.append(basin)
    if season is not None:
        conditions.append("season = ?")
        params.append(season)

    params.append(limit)
    return {
        "cyclones": _query(
            f"""
            SELECT sid, name, season, basin, first_seen, last_seen, duration_days,
                   max_wind_kt, min_pressure_mb, max_category, ace,
                   reached_hurricane, reached_major_hurricane, made_landfall,
                   peak_lat, peak_lon, peak_time
            FROM gold_cyclones
            WHERE {" AND ".join(conditions)}
            ORDER BY max_wind_kt DESC NULLS LAST, min_pressure_mb ASC, sid
            LIMIT ?
            """,
            params,
        ),
        "note": (
            "Desde 1980, cuando la cobertura satelital pasó a ser global. Antes "
            "de esa fecha los ciclones que no tocaron tierra ni cruzaron una "
            "ruta marítima no se observaron, y cualquier serie temporal que los "
            "incluya mide capacidad de observación, no actividad ciclónica."
        ),
    }


@app.get("/cyclones/seasons", summary="Actividad ciclónica por temporada y cuenca")
def cyclone_seasons(
    basin: Annotated[str | None, Query(pattern="^(NA|EP|WP|NI|SI|SP|SA)$")] = None,
) -> dict:
    conditions = ["season BETWEEN 1980 AND 2024"]
    params: list[Any] = []
    if basin:
        conditions.append("basin = ?")
        params.append(basin)

    trend = _query("""
        SELECT round(corr(season, ace_year), 4) AS r_ace,
               round(corr(season, major), 4) AS r_major_hurricanes,
               count(*) AS n_years,
               round(1.96 / sqrt(count(*)), 4) AS significance_threshold
        FROM (
            SELECT season, sum(ace_total) AS ace_year,
                   sum(major_hurricanes) AS major
            FROM gold_cyclone_seasons
            WHERE season BETWEEN 1980 AND 2024
            GROUP BY 1
        )
    """)

    return {
        "seasons": _query(
            f"""
            SELECT season, basin, systems, tropical_storms, hurricanes,
                   major_hurricanes, landfalling, ace_total, strongest_wind_kt,
                   lowest_pressure_mb, mean_duration_days
            FROM gold_cyclone_seasons
            WHERE {" AND ".join(conditions)}
            ORDER BY season, basin
            """,
            params,
        ),
        "trend": trend[0] if trend else {},
        "finding": (
            "La energía ciclónica global (ACE) no muestra tendencia en 45 años: "
            "r = -0,03. Los huracanes mayores dan r = 0,29 frente a un umbral de "
            "significación de 0,292 — está justo en la línea, tan al filo que un "
            "año más de datos podría voltearlo. Coincide con la literatura: sin "
            "señal clara en frecuencia total, indicios débiles de mayor "
            "proporción de tormentas intensas."
        ),
    }


@app.get("/cyclones/near/{location_id}", summary="Ciclones que pasaron cerca")
def cyclones_near(
    location_id: str,
    max_distance_km: Annotated[float, Query(ge=1, le=500)] = 500,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 200,
) -> dict:
    rows = _query(
        """
        SELECT location_id, location_name, sid, storm_name, season, basin,
               min_distance_km, closest_time, local_date, wind_at_closest_kt,
               pressure_at_closest_mb, category_at_closest,
               storm_max_wind_kt, storm_max_category, storm_ace
        FROM gold_cyclones_near_city
        WHERE location_id = ? AND min_distance_km <= ?
        ORDER BY closest_time DESC
        LIMIT ?
        """,
        [location_id, max_distance_km, limit],
    )
    return {
        "cyclones": rows,
        "note": (
            "wind_at_closest_kt es la intensidad AL PASAR por la ciudad, no la "
            "máxima de la tormenta. Un huracán que alcanza su pico en mitad del "
            "océano y llega debilitado afecta a la costa con lo que traía al "
            "pasar: confundir ambas cifras sobrestima el impacto local."
        ),
    }


# ─── Población y ENSO ────────────────────────────────────────────────────────


@app.get("/population/world", summary="Población mundial año a año")
def world_population(
    from_year: int = -10000,
    to_year: int = 2030,
) -> dict:
    return {
        "series": _query(
            """
            SELECT year, population_low, population_high, population_mid,
                   uncertainty_ratio, is_anchor, confidence, source_kind
            FROM gold_world_population
            WHERE year BETWEEN ? AND ?
            ORDER BY year
            """,
            [from_year, to_year],
        ),
        "note": (
            "Dos regímenes de dato: hasta 1950 es estimación demográfica "
            "interpolada entre años ancla; desde 1960, Banco Mundial. "
            "`source_kind` los distingue. La única caída de toda la serie está "
            "entre 1300 y 1400: la peste negra."
        ),
    }


@app.get("/patterns/per-capita", summary="Catástrofes como fracción de la humanidad")
def per_capita(limit: Annotated[int, Query(ge=1, le=200)] = 25) -> dict:
    return {
        "events": _query(
            """
            SELECT family, event_name, subtype, year, deaths_representative,
                   world_population, deaths_per_million, one_in_every,
                   pct_of_humanity, deaths_per_million_low, deaths_per_million_high,
                   estimate_kind, population_source
            FROM gold_catastrophes_per_capita
            ORDER BY deaths_per_million DESC, event_key
            LIMIT ?
            """,
            [limit],
        ),
        "finding": (
            "Normalizar cambia el ranking, no solo la escala. La peste negra "
            "mató a 1 de cada 3 personas vivas (36% de la humanidad); la gripe "
            "de 1918, más letal en cifras absolutas que la plaga de Justiniano, "
            "cae del segundo al cuarto puesto al normalizar. El COVID-19 es el "
            "sexto en absoluto y el décimo en proporción: 1 de cada 444."
        ),
        "caveat": (
            "El denominador es la población MUNDIAL, no la de la región "
            "afectada. Responde a '¿qué fracción de la humanidad se llevó?', "
            "que es lo comparable entre épocas — no a '¿qué fracción de los "
            "expuestos murió?'."
        ),
    }


@app.get("/patterns/enso", summary="El Niño frente a la actividad ciclónica")
def enso_pattern() -> dict:
    return {
        "by_basin": _query("""
            SELECT basin, phase, seasons, ace_mean, hurricanes_mean,
                   major_hurricanes_mean, systems_mean, r_oni_vs_ace
            FROM gold_enso_cyclones
            ORDER BY basin, phase
        """),
        "oni_recent": _query("""
            SELECT year, season, season_index, anomaly_c, phase, intensity
            FROM silver_oni
            WHERE year >= 2020
            ORDER BY year DESC, season_index DESC
            LIMIT 24
        """),
        "finding": (
            "El signo cambia según la cuenca, y por eso agrupar el planeta "
            "entero da casi cero: las señales se cancelan. En el Atlántico El "
            "Niño frena la actividad (ACE medio 88 frente a 164 en La Niña); en "
            "el Pacífico oriental la dispara (190 frente a 96). El mecanismo es "
            "la cizalladura vertical del viento, que aumenta sobre el Atlántico "
            "y disminuye sobre el Pacífico."
        ),
    }


# ─── Predicción y eventos históricos ─────────────────────────────────────────


@app.get("/predict/heatwave", summary="Modelo de calor extremo y su backtest")
def heatwave_model() -> dict:
    return {
        "model": _query("""
            SELECT anomaly_bucket, enso_bucket, n_train, n_extreme,
                   p_extreme, base_rate, lift
            FROM gold_heatwave_model
            WHERE n_train >= 100
            ORDER BY p_extreme DESC, anomaly_bucket, enso_bucket
        """),
        "backtest": _query("""
            SELECT scope, n_test, n_extreme, observed_rate, brier_model,
                   brier_base, brier_skill_score, pct_improvement,
                   beats_climatology
            FROM gold_heatwave_backtest
            ORDER BY (scope = 'GLOBAL') DESC, brier_skill_score DESC, scope
        """),
        "design": (
            "Entrenamiento 2006-2018, prueba 2019-2025. Partición POR TIEMPO, "
            "nunca aleatoria: un split al azar sobre series temporales pone el "
            "día siguiente en el entrenamiento y el anterior en la prueba, y el "
            "resultado sale espectacular sin significar nada. El umbral p95 del "
            "objetivo también se calcula solo con 2006-2018, para que los años "
            "de prueba no contribuyan a definir su propio objetivo."
        ),
        "finding": (
            "El modelo apenas bate a la climatología (+1,3% de Brier Skill "
            "Score), y el motivo es más interesante que el modelo: **se rompió "
            "el supuesto de estacionariedad**. En 2006-2018 todas las ciudades "
            "daban ~4,5% de días extremos, como exige un percentil 95. En "
            "2019-2025, con el mismo umbral, Singapur da 45,8% y Ciudad de "
            "México 38,5%. Cualquier modelo entrenado con el pasado subestima "
            "sistemáticamente, porque el clima dejó de ser el mismo."
        ),
        "why_tropics": (
            "La correlación entre variabilidad térmica y factor de "
            "amplificación es r = -0,68: los climas estables se disparan y los "
            "extremos apenas se mueven. En Singapur (σ = 0,70 °C) un "
            "calentamiento pequeño empuja media distribución por encima del "
            "umbral antiguo; en Yakutsk (σ = 4,74 °C) las oscilaciones diarias "
            "de ±5 °C absorben el mismo desplazamiento."
        ),
    }


@app.get("/events", summary="Hitos históricos y de disponibilidad de datos")
def historical_events(
    category: Annotated[
        str | None,
        Query(pattern="^(guerra|economia|tecnologia|salud|clima|observacion)$"),
    ] = None,
) -> dict:
    conditions: list[str] = []
    params: list[Any] = []
    if category:
        conditions.append("category = ?")
        params.append(category)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return {
        "events": _query(
            f"""
            SELECT id, name, category, start_year, end_year, duration_years,
                   is_point_event, description, relevance
            FROM silver_historical_events
            {where}
            ORDER BY start_year
            """,
            params,
        ),
        "note": (
            "La categoría 'observacion' es la de uso analítico: marca cuándo "
            "cambió nuestra capacidad de medir. Cada uno de esos años debería "
            "ser una línea vertical en cualquier serie larga, porque ahí la "
            "serie cambia de régimen sin que el fenómeno cambie."
        ),
    }


# ─── Gobierno de modelos y producto ──────────────────────────────────────────
#
# La regla del proyecto: ningún número predictivo sale a la interfaz sin su
# mejora fuera de muestra al lado. El criterio vive en gold_model_skill, no en
# un `if` del frontend, precisamente para que la tentación de enseñar el número
# bonito no gane.


@app.get("/models/skill", summary="Habilidad medida de cada modelo")
def model_skill() -> dict:
    return {
        "models": _query("""
            SELECT DISTINCT model_id, scope, metric, n_cuts,
                   improvement_median, improvement_min, improvement_max,
                   should_display
            FROM gold_model_skill
            ORDER BY improvement_median DESC, model_id, scope
        """),
        "by_cut": _query("""
            SELECT model_id, cut_year, n_test, value_model, value_baseline,
                   improvement_pct
            FROM gold_model_skill
            ORDER BY model_id, cut_year
        """),
        "criterio": (
            "should_display exige DOS condiciones: que la mediana sobre todos "
            "los cortes bata a la línea base con al menos un 5% de margen, y "
            "que NINGÚN corte salga negativo. Un modelo que a veces estorba no "
            "se publica."
        ),
        "por_que_la_mediana": (
            "El riesgo de calor corregido declaraba +16,9% medido en un solo "
            "corte (2018/2019). Evaluado sobre cinco cortes su mediana es "
            "+3,5%, por debajo del umbral. La diferencia no está en el modelo: "
            "está en lo caliente que salió el periodo de prueba elegido."
        ),
    }


@app.get("/predict/aftershocks", summary="Pronóstico de réplicas tras un sismo")
def aftershock_forecast(
    limit: Annotated[int, Query(ge=1, le=500)] = 30,
) -> dict:
    skill = _query("""
        SELECT DISTINCT improvement_median, improvement_min, improvement_max,
               n_cuts, should_display
        FROM gold_model_skill WHERE model_id = 'pronostico_replicas'
    """)
    s = skill[0] if skill else {}

    if not s.get("should_display"):
        raise HTTPException(
            status_code=503,
            detail=(
                "El modelo de réplicas no supera el criterio de publicación en "
                "gold_model_skill. Endpoint deshabilitado a propósito."
            ),
        )

    return {
        "recent_sequences": _query(
            """
            WITH alpha AS (
                SELECT sum(y_days_2_8)::DOUBLE / nullif(sum(n1), 0) AS a
                FROM gold_aftershock_forecast WHERE is_predictable
            )
            SELECT f.mainshock_id, f.mainshock_time, f.mainshock_mag, f.place,
                   f.lat, f.lon, f.depth_km, f.mag_band, f.n1,
                   f.y_days_2_8 AS observed_days_2_8,
                   round((SELECT a FROM alpha) * f.n1, 1) AS predicted_days_2_8,
                   -- Intervalo, no cifra única: la distribución es asimétrica
                   -- y de cola pesada (media 16, mediana 4, máximo 212).
                   round(0.55 * (SELECT a FROM alpha) * f.n1, 0) AS predicted_low,
                   round(1.85 * (SELECT a FROM alpha) * f.n1, 0) AS predicted_high
            FROM gold_aftershock_forecast f
            WHERE f.is_predictable
            ORDER BY f.mainshock_time DESC, f.mainshock_id
            LIMIT ?
            """,
            [limit],
        ),
        "skill": s,
        "como_leerlo": (
            "Se estima el número de réplicas M≥4.5 a menos de 150 km entre los "
            "días 2 y 8, a partir de las que hubo en las primeras 24 horas. El "
            "modelo entero es y ≈ 0,93 × n1: una constante, sin parámetros por "
            "región."
        ),
        "avisos": [
            "NO es predicción de terremotos. Solo estima cuántas réplicas "
            "seguirán a uno que YA ocurrió.",
            "Siempre intervalo, nunca cifra única: la distribución tiene cola "
            "pesada (media 16, mediana 4, máximo observado 212).",
            "Los principales se declusterizan: 53 de 430 eventos M≥6.5 eran en "
            "realidad réplicas de otro mayor y falseaban la evaluación.",
            "Techo optimista: se entrena con el catálogo REVISADO. En tiempo "
            "real, a t+24 h, USGS aún no ha revisado casi nada y n1 será menor.",
        ],
    }


# ─── Paneles y su metadatos de cobertura ─────────────────────────────────────
#
# Estos tres endpoints van juntos a propósito. El panel sin su cobertura invita
# al error que una verificación adversarial midió: de 153 pares de columnas del
# panel mensual, 77 superaban el umbral ingenuo y solo 6 sobrevivían a corregir
# por autocorrelación, estacionalidad, tendencia y ventana. Un 92% de mortalidad.


@app.get("/panels/coverage", summary="Qué columna se puede analizar y con qué umbral")
def panel_coverage(
    panel: Annotated[
        str | None, Query(pattern="^(gold_year_panel|gold_month_panel)$")
    ] = None,
) -> dict:
    conditions: list[str] = []
    params: list[Any] = []
    if panel:
        conditions.append("panel = ?")
        params.append(panel)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    return {
        "columns": _query(
            f"""
            SELECT panel, column_name, first_year, last_year, n_observations,
                   acf1, n_effective, r_threshold_naive, r_threshold_honest,
                   naive_underestimates_by, analyzable, verdict
            FROM gold_panel_coverage
            {where}
            ORDER BY panel, n_effective DESC, column_name
            """,
            params,
        ),
        "como_usarlo": (
            "Antes de correlacionar dos columnas, mira el `r_threshold_honest` "
            "de AMBAS y quédate con el mayor. El `r_threshold_naive` está "
            "expuesto solo para que se vea la diferencia: para el ONI mensual "
            "es 0,065 frente a un umbral honesto de 0,377, un factor de 5,8."
        ),
        "por_que": (
            "1,96/√n es válido para observaciones independientes, y las series "
            "temporales no lo son. El ONI mensual tiene ACF(1) = 0,97, así que "
            "sus 918 observaciones equivalen a unas 27 independientes. "
            "`world_population` es el caso extremo: ACF(1) = 1 exacto y umbral "
            "honesto por encima de 1, o sea que ninguna correlación contra ella "
            "puede significar nada."
        ),
    }


@app.get("/panels/year", summary="Panel anual, una fila por año")
def year_panel(
    from_year: int = 1900,
    to_year: int = 2026,
    regime: Annotated[int | None, Query(description="coverage_regime homogéneo")] = None,
) -> dict:
    conditions = ["year BETWEEN ? AND ?"]
    params: list[Any] = [from_year, to_year]
    if regime is not None:
        conditions.append("coverage_regime = ?")
        params.append(regime)

    return {
        "rows": _query(
            f"""
            SELECT * FROM gold_year_panel
            WHERE {" AND ".join(conditions)}
            ORDER BY year
            """,
            params,
        ),
        "regimes": _query("""
            SELECT coverage_regime, min(year) AS first_year, max(year) AS last_year,
                   count(*) AS years, max(sources_available) AS sources
            FROM gold_year_panel GROUP BY 1 ORDER BY 1
        """),
        "aviso": (
            "Filtra por `regime` para restringir a cobertura homogénea. Una "
            "correlación sobre el rango completo mezcla años con 3 fuentes y "
            "años con 7, y la señal más fuerte del panel no es climática: es "
            "r(sources_available, año) = +0,903."
        ),
    }


@app.get("/panels/month", summary="Panel mensual, para ciclos y desfases")
def month_panel(
    from_year: int = 1950,
    to_year: int = 2026,
) -> dict:
    return {
        "rows": _query(
            """
            SELECT * FROM gold_month_panel
            WHERE year BETWEEN ? AND ?
            ORDER BY year, month
            """,
            [from_year, to_year],
        ),
        "usa_deseason": (
            "Para correlacionar usa SIEMPRE las columnas `_deseason`. A "
            "resolución mensual el ciclo anual domina todo: el ACE ciclónico va "
            "de 26 en mayo a 155 en septiembre, factor 6. Correlacionar series "
            "crudas mide sobre todo que ambas tienen verano. "
            "`temp_anomaly_mean` ya viene desestacionalizada por construcción."
        ),
        "cuidado_con_bird_records": (
            "**bird_records no mide aves, mide adopción de eBird.** Crece de "
            "32.300 registros en 2015 a 300.587 en 2024, factor 9,3 en diez "
            "años, y correlaciona con cualquier serie creciente. Su pareja con "
            "pct_extreme_heat_days da r = +0,676 que cae a +0,284 al "
            "destendenciar; con temp_anomaly_mean pasa de +0,378 a −0,110, o "
            "sea que CAMBIA DE SIGNO. Con ACF(1) = 0,91 su umbral honesto es "
            "0,336, más del triple del ingenuo."
        ),
        "no_es_mas_potente_que_el_anual": (
            "Se construyó esperando 12× de potencia y no la da. La correlación "
            "ONI×ciclones sobrevive en el panel anual (r = +0,709, q < 0,05) y "
            "MUERE en el mensual (r = +0,189, q = 0,44). El ACE mensual está "
            "dominado por ruido meteorológico que el ONI no explica. La "
            "agregación a temporada es el análisis, no una pérdida. Lo que el "
            "panel mensual sí compra es la capacidad de PREGUNTAR: el espectro "
            "del ENSO no existe sin resolución intraanual."
        ),
    }
