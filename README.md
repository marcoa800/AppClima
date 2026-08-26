# AppClima

Plataforma de datos abiertos de clima, sismos y biodiversidad. Ingesta →
lakehouse → API → web, con los patrones contrastados sobre los datos reales.

Cobertura actual: **49 ciudades ancla** de 71°N a 55°S, **20 años de reanálisis
ERA5** en 12 de ellas, el **catálogo sísmico global de USGS desde 2016** (79.106
eventos M≥4.5), y **10.722 desastres naturales históricos** de NOAA NCEI desde el
año −4360, **308.310 puntos de trayectoria de ciclones** de IBTrACS desde 1980, y
**población por país desde 1960** (Banco Mundial), **El Niño desde 1950**, y
catálogos curados de 22 pandemias, 17 anclas de población histórica y 20 hitos.

## Arranque rápido

```bash
brew install uv
uv venv --python 3.12 && uv pip install -e ".[dev]"
```

```bash
.venv/bin/appclima ingest all --cadence full && .venv/bin/appclima build
```

```bash
.venv/bin/uvicorn appclima.api.main:app --reload --port 8000
```

```bash
npm install --prefix web && npm run dev --prefix web
```

La web queda en `localhost:5173` y la API en `localhost:8000/docs`.

### Publicar sin servidor

```bash
.venv/bin/appclima export && npm run build --prefix web
```

La web pública **no necesita servidor**. El payload completo son 5,6 MB de JSON,
así que cabe en cualquier hosting estático gratuito:

| | Con servidor | Estático |
|---|---|---|
| Coste | 5-20 €/mes | **0 €** |
| Rate limiting | Necesario | No existe el problema |
| Caída del servicio | Posible | Imposible |
| Latencia | Consulta a DuckDB | CDN |

Y no rompe la arquitectura: **los JSON estáticos son el contrato de la API,
materializado**. FastAPI se queda para desarrollo local y para el cliente de iOS,
que sí necesita consultas con parámetros. El cliente web funciona contra los dos
con el mismo código, según `VITE_API_STATIC`.

La exportación es **reproducible byte a byte**, y hay un test que lo verifica.
Sin eso el workflow de Pages generaría un diff en cada ejecución aunque nada
hubiera cambiado: Sídney y Manaos tienen 89 especies cada una y se
intercambiaban de sitio porque el `ORDER BY` no desempataba.

## Arquitectura

```
INGESTA   Open-Meteo·USGS·eBird·NOAA·IBTrACS·BM·CPC·curados   Python + Pydantic
   ↓
BRONZE    Parquet+zstd, append-only               particionado por fecha
   ↓
SILVER    limpio y deduplicado                    9 vistas DuckDB
   ↓
GOLD      agregados, patrones y predicción        27 tablas DuckDB
   ↓
API              contrato estable                   FastAPI
   ↓
WEB              React + SVG a mano                 Vite
```

La regla que sostiene todo: **bronze es inmutable**. Si mañana encuentras un bug
en la lógica de limpieza, reconstruyes silver y gold desde cero sin volver a
llamar a ninguna API. Silver solo limpia y deduplica; toda decisión discutible
vive en gold, donde se ve.

La API existe por una razón estratégica, no técnica: es la frontera que hará que
el salto de web a iOS cueste solo trabajo de interfaz, no reescribir la lógica
de datos.

### Estructura

| Ruta | Qué hay |
|---|---|
| `src/appclima/sources/` | Un módulo por fuente. Llaman, validan, devuelven. Nada más |
| `src/appclima/schemas/` | Pydantic: validación en el borde del sistema |
| `src/appclima/locations.py` | Catálogo de las 49 ciudades y las 12 flagship |
| `src/appclima/epidemics.py` | Catálogo curado de 22 pandemias, con rangos |
| `src/appclima/world_population.py` | 17 anclas de población mundial, con rangos |
| `src/appclima/historical_events.py` | 20 hitos; la categoría `observacion` explica los artefactos |
| `src/appclima/transform/models/` | Modelos SQL numerados, uno por fichero |
| `src/appclima/api/` | Endpoints sobre el warehouse |
| `web/src/components/` | Gráficas en SVG escrito a mano |

## Comandos

```bash
.venv/bin/appclima locations                    # catálogo de ubicaciones
.venv/bin/appclima status                       # qué hay en bronze
.venv/bin/appclima ingest all                   # cadencia diaria (3 fuentes)
.venv/bin/appclima ingest all --cadence weekly  # + ciclones
.venv/bin/appclima ingest all --cadence full    # las 11 fuentes
.venv/bin/appclima ingest quakes --days-back 30 --min-magnitude 2.5
.venv/bin/appclima ingest weather-archive --flagships --start 2006-01-01 --end 2025-12-31
.venv/bin/appclima ingest disasters             # 10.722 eventos históricos de NOAA
.venv/bin/appclima ingest epidemics             # catálogo curado de pandemias
.venv/bin/appclima ingest cyclones              # IBTrACS desde 1980 (137 MB → 4 MB)
.venv/bin/appclima ingest population            # Banco Mundial + histórico curado
.venv/bin/appclima ingest enso                  # índice ONI de El Niño
.venv/bin/appclima ingest events                # hitos históricos y de datos
.venv/bin/appclima build                        # reconstruye silver y gold
.venv/bin/appclima export                       # API → JSON estático (5,6 MB)
```

## Fuentes

| Fuente | Key | Coste | Qué aporta |
|---|---|---|---|
| [Open-Meteo](https://open-meteo.com) | ❌ | 0 € no comercial | Pronóstico + ERA5 desde 1940 |
| [USGS](https://earthquake.usgs.gov/fdsnws/event/1/) | ❌ | 0 € | Catálogo sísmico global |
| [eBird](https://ebird.org/api/keygen) | ✅ gratis | 0 € | Observaciones de aves |
| [NOAA NCEI HazEl](https://www.ngdc.noaa.gov/hazel/view/swagger) | ❌ | 0 € | Sismos, tsunamis y erupciones desde −4360 |
| [IBTrACS](https://www.ncei.noaa.gov/products/international-best-track-archive) | ❌ | 0 € | Ciclones tropicales globales (CSV, 137 MB) |
| [Banco Mundial](https://data.worldbank.org) | ❌ | 0 € | Población y desarrollo por país |
| [NOAA CPC](https://www.cpc.ncep.noaa.gov/data/indices/) | ❌ | 0 € | Índice ONI de El Niño desde 1950 |
| [OpenDengue](https://opendengue.org) | ❌ | 0 € | Vigilancia semanal de dengue, 129 países |
| Catálogos curados | — | 0 € | Pandemias, población histórica, hitos |

### Por qué las pandemias son un catálogo curado y no una API

Se buscó una fuente abierta y no existe:

- **WHO GHO** (OData, sin key) sirve indicadores sanitarios modernos por país,
  no eventos históricos.
- **EM-DAT**, la referencia internacional, cubre epidemias desde 1900 pero exige
  registro y su licencia es CC BY-NC, sin API pública.
- **ReliefWeb** retiró su API v1 y la v2 exige un `appname` aprobado a mano.
- Para la peste negra no hay base de datos: hay historiografía.

Así que `src/appclima/epidemics.py` es un catálogo versionado con la misma
disciplina que el de ciudades, y **cada entrada lleva rango, nivel de confianza
y fuente**. Las estimaciones de la plaga de Justiniano van de 15 a 100 millones:
guardar un punto medio y presentarlo como hecho sería el peor error posible con
estos datos. El ancho del rango es tanto información como el número.

### El límite de Open-Meteo se cuenta por peso, no por peticiones

Esto no está claro en su documentación y cuesta un 429 aprenderlo:

```
peso ≈ ubicaciones × (variables / 10) × (días / 7)
```

Con topes de ~600/minuto, ~5.000/hora y ~10.000/día. Consecuencias reales:

- Un backfill de 10 años × 49 ciudades × 14 variables ≈ **38.000 llamadas
  ponderadas**: no cabe en la cuota diaria.
- Por eso existen `FLAGSHIP_IDS` (12 ciudades para historia profunda) y
  `CORE_VARIABLES` (5 variables en vez de 14 para el histórico).
- `appclima ingest weather-archive` estima el peso y aborta antes de gastar
  cuota si va a chocar.

### Cadencias de ingesta

No todas las fuentes cambian al mismo ritmo, y tratarlas igual es un desperdicio
o un olvido. El pronóstico caduca en horas; el catálogo sísmico histórico de NOAA
no ha cambiado en años; el Banco Mundial publica una vez al año.

| Cadencia | Añade | Cron |
|---|---|---|
| `daily` | clima, sismos, aves | 06:15 UTC |
| `weekly` | + ciclones (IBTrACS publica por lotes) | domingos |
| `monthly` | + índice ONI | día 1 |
| `yearly` | + población, desastres, fenología, curados | 1 de enero |

Cada nivel incluye a los anteriores. El workflow deduce la cadencia de la fecha
—no del cron que disparó, porque GitHub no lo dice— y elige siempre la más
amplia que aplique ese día.

Esto se arregló tarde: `ingest all` se quedó cubriendo solo las tres fuentes de
la fase 1 mientras el proyecto crecía a once, así que el cron diario refrescaba
tres y dejaba envejecer ocho **en silencio**. El `/health` no lo detectaba porque
solo vigila la frescura de cuatro datasets.

### Token de eBird

Gratuito e instantáneo en https://ebird.org/api/keygen. Sin él la ingesta de aves
se omite con un aviso y el resto del pipeline sigue funcionando.

```bash
cp .env.example .env   # y pega el token en APPCLIMA_EBIRD_TOKEN
```

`.env` está en `.gitignore`: el token nunca sale de tu máquina.

## Patrones encontrados

Todo lo de abajo sale de los datos de este repo, no de la literatura.

**Ley de Gutenberg-Richter.** log10(N) frente a magnitud da una recta casi
perfecta a lo largo de cuatro órdenes de magnitud. Valor b global por máxima
verosimilitud (Aki): **1,222 ± 0,004**. Varía con la profundidad —
1,186 superficial, 1,395 intermedio, 1,312 profundo.

**Ley de Omori.** Sumando las 317 secuencias de M≥6.5 desde 2016, las réplicas
caen de 5.119 el primer día a 2.499 el segundo y 282 el décimo. Decaimiento
hiperbólico con cola larga, como predice la ley.

**Calentamiento.** Contra una base fija 2006-2020, la anomalía media de las 12
ciudades flagship sube de forma monótona: **+0,14 °C (2021) → +0,38 → +0,56 →
+0,59 → +0,86 (2025)**. Los días de calor extremo pasan del 8,9% al 18,1%, y los
récords batidos de 46 a 267.

**Las pandemias operan en otra escala.** La peor pandemia mató entre 300 y 800
veces más que el peor desastre natural registrado. El terremoto de Shaanxi de
1556, el más mortal del archivo, se llevó 830.000 vidas; la peste negra, entre 75
y 200 millones.

**En los desastres costeros, el peligro primario rara vez es el que mata.** Los
tres archivos de NOAA están enlazados por identificador, así que se reconstruye
la cadena causal. Sumatra 2004: el sismo mató a 1.001 personas y el tsunami que
generó a 226.898 más, el **99,6%** del total, con olas de 50,9 m. Tōhoku 2011
repite el patrón con un 92%, y Krakatoa 1883 con un 94,5%.

**El registro histórico está brutalmente sesgado hacia el presente.** Los eventos
registrados pasan de 20 en el siglo III a.C. a 4.374 en el XXI, y la proporción
con cifra exacta de muertes de ~0% a 42%. Eso NO mide actividad geológica —
que en escalas de siglos es constante — sino cobertura documental.

**Los ciclones tropicales no muestran tendencia en energía total.** Correlación
entre año y ACE global sobre 45 temporadas: **r = −0,03**. Plana. Los huracanes
mayores dan r = 0,29 frente a un umbral de significación de 0,292 — justo en la
línea, tan al filo que una temporada más podría voltearlo. Coincide con la
literatura: sin señal clara en frecuencia, indicios débiles en intensidad. Por eso
la gráfica no dibuja recta de tendencia: no hay pendiente que los datos sostengan.

**Normalizar por población cambia el ranking, no solo la escala.** La peste
negra mató a **1 de cada 3 personas vivas** (36% de la humanidad). La gripe de
1918, segunda en cifras absolutas, cae al cuarto puesto al normalizar. El
COVID-19 es sexto en absoluto y décimo en proporción: 1 de cada 444. Y la serie
de población mundial tiene una sola caída en 12.000 años, entre 1300 y 1400.

**El Niño predice la actividad ciclónica, y el signo se invierte según el
océano.** Atlántico: ACE medio 88 en El Niño frente a 164 en La Niña. Pacífico
oriental: 190 frente a 96. Por eso agrupar el planeta da casi cero — las señales
se cancelan.

**Se rompió el supuesto de estacionariedad, y se puede medir.** El umbral de
"día extremo" (percentil 95) se calculó con 2006-2018, donde las 12 ciudades dan
~4,5% de días extremos, exactamente lo esperado. Con el mismo umbral en
2019-2025: Singapur **45,8%**, Ciudad de México **38,5%**. La correlación entre
variabilidad térmica y factor de amplificación es **r = −0,68**: los climas
estables se disparan y los extremos apenas se mueven.

**El dataset de aves mide al observador, no a la naturaleza.** El esfuerzo de
observación explica el **68,3%** de la varianza en riqueza de especies (r = 0,83);
la latitud, el **1,0%** (r = −0,10). Denver encabeza con 134 especies y Manaos, en
plena Amazonía, tiene 89 — porque Denver envió 56 listas y Manaos 4. Es el aviso
que ya estaba documentado en el esquema, ahora cuantificado con datos propios.

**Promediar al año destruye la señal cíclica.** Con `oni_aso` (agosto-octubre)
la banda 2-7 años concentra el 87,5% de la varianza, p = 0,011. Con el promedio
anual: 76,5% frente al 73,0% del ruido blanco, **p = 0,33** — indistinguible de
ruido. Por eso existe `gold_month_panel`: a resolución mensual el ONI tiene 918
observaciones en vez de 77, y el umbral de detección cae de 0,223 a **0,065**.
La antifase cuasi-bienal aparece limpia con el mínimo exactamente en 24 meses.

**Casi todo lo que parece tendencia en el panel es cobertura.** De ~50 contrastes
cruzados por agentes, sobrevivió **un** acoplamiento sólido (ENSO↔ciclones, r
hasta +0,712 en el Pacífico Oeste, con signo invertido en el Atlántico) y se
demolieron seis tendencias:

| Afirmación | Antes | Después de restringir la ventana |
|---|---|---|
| «Los desastres crecen» | r = +0,656 | **r = −0,216 ns, signo invertido** |
| «Salvamos más vidas» | r = −0,849 | **r = +0,265 ns** |
| «Los récords se disparan» | r = +0,690 | **15 de 20 años valen 0** |
| «Menos sismos» | −45,8/año | **+91,1/año** según incluyas 2026 |

La señal más fuerte de todo el panel no es climática: es
`r(sources_available, año) = +0,903`.

**La letalidad por evento no ha bajado en un siglo.** Terremotos M≥7 con ≥100
muertos: mediana 1.070 antes de 1960, 844 después (p = 0,895, n = 154). La caída
per cápita que parecía buena noticia es **100% aritmética del denominador** — la
población se multiplicó por 4,7 y el numerador es plano. Siempre que reportes una
tasa, reporta numerador y denominador por separado.

**El ENSO es un oscilador amortiguado, no un ciclo.** AR(2) con raíces
complejas: cuasi-periodo de 29-34 meses y amortiguamiento de 6-9 meses. Es
predecible más allá de la persistencia pero solo hasta ~9 meses: a 6 meses el
AR(2) da R² = +0,38 frente a −0,19 de la persistencia. **No hay línea espectral**
— quien diga «el ENSO tiene un ciclo de 3,6 años» está leyendo ruido.

**La barrera de predictibilidad de primavera, con datos propios.** El ONI de
mayo explica el resto de la temporada ciclónica: r = +0,49 en el Pacífico Oeste,
+0,44 en el Este, **−0,23 en el Atlántico** (signo invertido, como manda la
cizalladura). Hasta abril el skill es cero en las tres cuencas; en mayo se
enciende de golpe. Descuento obligatorio: el ONI se publica con retraso, así que
la antelación real es un mes menor.

**Tres nulos definitivos.** La fenología de aves está muerta — el placebo
(carbonero menos gorrión, ambos residentes) da ±2,5 a 5,6 días/década, así que
el suelo de ruido del método es tan grande como cualquier residuo. La temporada
ciclónica **no se ha desplazado**: la mediana se mueve medio día por década.
Y **ningún mes se calienta más rápido** que otro: las pendientes de la primera y
la segunda mitad de la ventana correlacionan −0,30, la firma de un patrón
inexistente.

**El mito del «clima sísmico» no se sostiene.** Correlación entre sismos diarios
en 500 km y presión atmosférica, sobre 87.654 días-ciudad: r = 0,012, que explica
el **0,014% de la varianza**. Tokio, con la mayor muestra (1.903 sismos), da
r = −0,002.

Ese último resultado enseña algo más útil que el propio hallazgo: con n = 87.654
el umbral de significación cae a r = 0,0066, así que una correlación
irrelevante sale «estadísticamente significativa». La significación responde a
«¿es distinto de cero?», no a «¿importa?». Por eso `gold_quake_pressure_test`
expone la varianza explicada justo al lado del test.

## Decisiones que costaron un bug

Anotadas porque son las que no se ven en el código y volverían a morder:

0. **El archivo de Open-Meteo cose dos reanálisis y no lo dice.** Sin fijar
   `models`, usa `best_match`: sirve ERA5 hasta 2016 y el análisis operativo del
   IFS de ECMWF desde 2017, que es cuando empieza ese archivo. La serie no tiene
   huecos ni nulos, los valores son plausibles y la API no avisa. **La costura se
   lee como clima.**

   Medido sobre las 24 ciudades que entonces tenían archivo largo (2017-2019,
   IFS menos ERA5): sesgo medio −0,04 °C, |sesgo| medio 0,36 °C, y hasta
   −2,44 °C en Tacna. El sesgo medio casi nulo es lo que lo hace peligroso:
   desaparece en cualquier agregado global y solo asoma al comparar una ciudad
   consigo misma a lo largo del tiempo — que es lo que hace todo modelo de
   tendencia de este proyecto.

   Se detectó porque Tacna aparecía enfriándose 1,7 °C por década, que no es un
   valor físico. Lo que costó: `gold_heat_threshold_drift` daba a Singapur
   +2,0 °C de deriva y ×7,9 de amplificación; con un solo reanálisis son +0,3 °C
   y ×1,8. Y el umbral térmico del dengue, que parecía nítido con p=1/924,
   desapareció.

   La defensa son tres cosas: `models=era5_seamless` fijado, una columna `model`
   de procedencia que viaja de la ingesta hasta gold, y comprobar la coordenada
   que devuelve la respuesta en vez de suponer que el orden coincide con el de la
   petición.

1. **Agrupar por día UTC es incorrecto.** Para Tokio (UTC+9) un día UTC empieza
   a las 09:00 locales, así que las máximas diarias mezclaban dos tardes. Por eso
   el catálogo lleva zona IANA y los agregados usan `timezone(zona, instante)`.

2. **`record_heat` era siempre falso.** La climatología incluía el día que
   estaba evaluando, así que un día no podía superar un récord que lo contenía.
   Se arregló cerrando la base en 2020; `in_baseline` marca los días para los que
   los récords siguen sin ser interpretables.

3. **Dos magnitudes de completitud en el mismo catálogo.** El histórico se
   ingiere con M≥4.5 y la ingesta diaria con M≥2.5. Sin homogeneizar, un sismo de
   la semana pasada parecía tener el triple de réplicas que uno de 2019 — puro
   sesgo de detección. `gold_quake_sequences` filtra a M≥4.5.

4. **En FastAPI el orden de registro de rutas decide el enrutado.**
   `/birds/{location_id}` estaba declarada antes que `/birds/summary`, así que
   la palabra "summary" se capturaba como id de ubicación y el endpoint
   devolvía una lista vacía con HTTP 200. Un fallo silencioso, que es peor que
   un error. Las rutas estáticas van siempre primero.

5. **El cruce aves-clima no funcionaba en absoluto.** Unía solo contra
   `kind = 'observed'`, pero las observaciones de eBird son siempre de los
   últimos 30 días y para esas fechas ERA5 aún no existe. Todas las columnas de
   clima salían NULL. Ahora prefiere observado y cae al pronóstico, marcando
   cuál usó en `weather_kind`.

6. **Un cursor de DuckDB no hereda el `SET TimeZone` de su conexión.** La API
   servía offsets locales en lugar de UTC. Cada cursor lo fija de nuevo.

7. **Naranja y rojo juntos son indistinguibles.** El validador de paleta lo
   cazó: ΔE 7,1 en visión normal, por debajo del suelo de 15. La pareja
   divergente es azul↔rojo.

8. **En DuckDB `/` es división en coma flotante.** El cálculo del siglo hacía
   `((año - 1) / 100)::INTEGER + 1`, y para 1976 eso da 19,75 → redondea a 20 →
   siglo 21 en vez de 20. Fallaba en todos los años cuyo resto pasara de 50, o
   sea la mitad del archivo. Hace falta `//`. Lo encontró un test
   parametrizado, no mirar los datos.

9. **NOAA registra en el tsunami las muertes del evento COMPLETO.** Haití 2010
   aparecía dos veces con 316.000 muertes, una como sismo y otra como tsunami, y
   cualquier suma por tipo de peligro quedaba inflada. Se eliminaron 584 filas
   duplicadas: cuando un tsunami está enlazado a un sismo, el evento canónico es
   el sismo y el tsunami pasa a ser un atributo suyo.

## Tests

```bash
.venv/bin/pytest -q
```

263 tests, sin red. Cubren el parseo de las tres fuentes con nulls y formatos
raros, el macro haversine contra distancias conocidas (incluido el cruce del
antimeridiano), la distancia circular entre días del año, y la coherencia del
catálogo.

## Los dos paneles y su metadatos de cobertura

| Tabla | Grano | Para qué |
|---|---|---|
| `gold_year_panel` | año (1900-2026) | Contexto y comparación entre dominios |
| `gold_month_panel` | (año, mes) | **Ciclos, periodicidad y desfases** |
| `gold_panel_coverage` | (panel, columna) | Rango válido y umbral de cada columna |

Tres barandillas, todas puestas después de que una verificación adversarial
demostrara que hacían falta:

1. **`sources_available`** — cuántas fuentes tienen dato ese año. Va de 3 en 1900
   a 7 en 2016. Una correlación sobre el rango completo mezcla años
   incomparables.
2. **`coverage_regime`** — identificador de tramo homogéneo. `WHERE
   coverage_regime = 2` restringe a 1980-2005, donde la cobertura no cambia.
   Sustituye a `data_coverage_change`, que venía del catálogo de hitos y era
   engañosa: marcaba 1940 y 1979 pero no el tramo posterior.
3. **`gold_panel_coverage.analyzable`** — decide qué columna se puede analizar,
   y lo decide con el **n EFECTIVO**, no con el bruto.

   La primera versión de esta tabla publicaba `1,96/√n` sobre el número bruto de
   observaciones. **Para series temporales eso es mentira**, y lo era por un
   factor de casi seis en la columna más importante del warehouse:

   | Columna | n | ACF(1) | n efectivo | Umbral ingenuo | Umbral honesto | Factor |
   |---|---|---|---|---|---|---|
   | `oni` (mensual) | 918 | 0,971 | **27** | 0,065 | **0,377** | 5,8× |
   | `world_population` | 126 | **1,000** | **3** | 0,175 | **1,132** | 6,5× |
   | `bird_records` | 360 | 0,910 | 34 | 0,103 | 0,336 | 3,3× |
   | `pct_extreme_heat_days` | 240 | 0,845 | 40 | 0,127 | 0,310 | 2,5× |

   `world_population` es el caso extremo: ACF(1) = 1 exacto y umbral honesto
   **por encima de 1**, o sea que ninguna correlación contra ella puede
   significar nada. Es tendencia monótona pura, y cinco de los «supervivientes»
   del panel anual eran parejas con esa columna.

   Además, cinco columnas del panel anual (`tsunamigenic`, `quakes_m7`,
   `max_magnitude`, `aftershock_sequences`, `quakes_m45`) solo existen
   2016-2026. Nunca fueron analizables y nada lo advertía. No se borran: se
   marcan.

### Lo que NO ganó el panel mensual

Se construyó esperando 12× de potencia. **No la da.** Una verificación
adversarial lo midió:

| | r | n | n efectivo | q (Benjamini-Hochberg) |
|---|---|---|---|---|
| Anual `oni_aso × ace_west_pacific` | **+0,709** | 45 | 47 | **< 0,05 sobrevive** |
| Mensual `oni × cyclone_ace_deseason` | +0,189 | 539 | 390 | **0,44 muere** |

Multiplicar las filas por 12 costó dos órdenes de magnitud de p-valor. El ACE
mensual está dominado por ruido meteorológico que el ONI no puede explicar, y el
ONI mensual arrastra ACF(1) = 0,97. **La agregación a temporada es el análisis,
no una pérdida.**

Lo que el panel mensual sí compró es la **capacidad de preguntar**: el espectro
del ENSO y el calendario ciclónico (percentiles del ACE dentro de la temporada)
no existen sin resolución intraanual. A resolución anual el 74% de los bins de
Fourier caen dentro de la banda 2-7 años por pura aritmética, así que el test es
imposible de plantear.

Y en el panel mensual, usa siempre las columnas `_deseason` para correlacionar.
A resolución mensual el ciclo anual domina todo: el ACE ciclónico va de 26 en
mayo a 155 en septiembre, factor 6. Correlacionar series crudas mide sobre todo
que ambas tienen verano.

## Cómo se valida una predicción aquí

`gold_heatwave_backtest` es el único modelo del proyecto que puede decir "esto no
sirve", y por eso es el más importante. Su diseño:

| | |
|---|---|
| Entrenamiento | 2006-2018 — aquí y solo aquí se ajusta |
| Prueba | 2019-2025 — nunca vista durante el ajuste |
| Línea base | la tasa climatológica del entrenamiento |
| Métrica | Brier Skill Score: `1 − BS_modelo/BS_base` |

La partición es **por tiempo, nunca aleatoria**. Un `train_test_split` al azar
sobre series temporales pone el día siguiente en el entrenamiento y el anterior
en la prueba: el modelo interpola entre días que ya conoce, el resultado sale
espectacular y no significa nada.

El umbral p95 del objetivo también se recalcula solo con 2006-2018. Con la
climatología general del proyecto (2006-2020), dos años del conjunto de prueba
contribuirían a definir su propio objetivo — una fuga del 13% de las muestras,
pequeña pero real.

Y un BSS negativo no es hipotético: pasó con el ACE del Atlántico, donde un
r = −0,50 en entrenamiento acabó siendo **6,2% peor que la climatología** fuera
de muestra. Mientras tanto el Pacífico occidental, con r = 0,73, la batió en un
24,3%. Un buen ajuste dentro de la muestra no garantiza nada fuera de ella.

## Lo siguiente

- **GBIF** para fenología de verdad: ¿llegan las aves antes que hace 30 años? El
  endpoint de eBird que usamos solo da el presente
- **EM-DAT** para desastres de 1900 en adelante (inundaciones, ciclones,
  sequías), que NOAA no cubre. Exige registro y es CC BY-NC
- **Mapa** con MapLibre + Protomaps autoalojado, que evita el coste por tiles
- **R2** para persistir bronze entre ejecuciones del cron (ver `ingest.yml`)
- **NASA FIRMS** para incendios activos, y cruzarlos con días sin lluvia
- **iOS**: la API ya está lista; solo falta la interfaz

## Licencia y atribución

El **código** está bajo licencia MIT — ver [`LICENSE`](LICENSE). Los **datos**
no: conservan la licencia de cada fuente, y varias son más restrictivas que MIT.
Quien tome el código y use las mismas fuentes hereda esas condiciones, que no son
mías y no puedo levantar. El detalle está en
[`DATA-LICENSES.md`](DATA-LICENSES.md).

El catálogo completo vive en `src/appclima/attribution.py` y se sirve en
`/sources`. Está en Python y no escrito a mano en el HTML por la misma razón que
el catálogo de ciudades: así se versiona, se testea y no se queda obsoleto la
primera vez que se añade una fuente.

**Seis de las diez fuentes exigen atribución explícita** y **tres restringen el
uso comercial**, que es la razón de que este proyecto sea y siga siendo gratuito:

| Fuente | Uso comercial |
|---|---|
| Open-Meteo | ❌ Prohibido en el plan gratuito — incluye publicidad y patrocinios |
| eBird | ⚠️ Requiere permiso del Cornell Lab |
| GBIF | ⚠️ Algunos datasets subyacentes son CC BY-NC |
| USGS, NOAA NCEI, IBTrACS, NOAA CPC | ✅ Dominio público |
| Banco Mundial, OpenDengue | ✅ CC BY 4.0 (con cita obligatoria) |

**Y una cita que está incompleta, porque conviene decirlo.** Se usó la API de
búsqueda de GBIF con facetas, que devuelve recuentos y no registros, así que GBIF
no emite DOI. Una cita formal exige la API de descargas —cuenta gratuita— y da un
DOI citable con la lista exacta de datasets y publicadores. Es lo que habría que
hacer antes de publicar cualquier resultado basado en GBIF.

## Lo que buscamos y no está

`src/appclima/null_findings.py` documenta **diez resultados nulos**, servidos en
`/patterns/nulls` y mostrados en la web.

Publicar los nulos no es humildad decorativa: demuestra que lo que sí se afirma
pasó por el mismo filtro. Cada entrada exige la afirmación contrastada, el
estadístico con su n y su umbral, por qué es un nulo y no falta de datos, y qué
se aprende.

Los tres que mejor resumen la disciplina del proyecto:

- **El «clima sísmico» no existe.** r = 0,012 sobre 87.654 días-ciudad, el
  0,014% de la varianza.
- **La fenología de aves no es medible con ciencia ciudadana.** El placebo
  —carbonero contra gorrión, ambos residentes— da ±2,5 a 5,6 días/década: el
  suelo de ruido del método es tan grande como cualquier residuo.
- **El 92% de las correlaciones del panel mensual son falsas.** De 153 pares, 77
  superan el umbral ingenuo y 6 sobreviven a las correcciones.

Un test comprueba que cada nulo lleve su cifra, que justifique por qué no es
falta de datos, y que cubran al menos cinco dominios — si todos fueran del mismo,
sería sesgo de búsqueda.
