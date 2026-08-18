import { useEffect, useMemo, useState } from 'react'
import {
  api,
  type Anomaly,
  type BValue,
  type BirdCorrelations,
  type BirdLocation,
  type Cascade,
  type CycloneSeason,
  type CycloneTrend,
  type DeadliestEvent,
  type ModelSkill,
  type SkillByCut,
  type ClimatologyDay,
  type Location,
  type MagnitudeBin,
  type MythRow,
  type OmoriDay,
  type Sequence,
  type WarmingYear,
} from './api'
import { AnomalyChart } from './components/AnomalyChart'
import { BirdEffortChart } from './components/BirdEffortChart'
import { CascadeTable } from './components/CascadeTable'
import { CycloneSeasonsChart } from './components/CycloneSeasonsChart'
import { DeadliestChart } from './components/DeadliestChart'
import { ClimatologyChart } from './components/ClimatologyChart'
import { GutenbergRichterChart } from './components/GutenbergRichterChart'
import { ModelSkillTable } from './components/ModelSkillTable'
import { MythTable } from './components/MythTable'
import { OmoriChart } from './components/OmoriChart'

type Global = {
  locations: Location[]
  warming: WarmingYear[]
  distribution: MagnitudeBin[]
  bValues: BValue[]
  omori: OmoriDay[]
  sequences: Sequence[]
  myth: MythRow[]
  deadliest: DeadliestEvent[]
  cascades: Cascade[]
  cycloneSeasons: CycloneSeason[]
  cycloneTrend: CycloneTrend | null
  birds: BirdLocation[]
  birdCorr: BirdCorrelations | null
  skill: ModelSkill[]
  skillByCut: SkillByCut[]
  freshness: Record<string, string | null>
}

export default function App() {
  const [global, setGlobal] = useState<Global | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [locationId, setLocationId] = useState('madrid')
  const [anomaly, setAnomaly] = useState<Anomaly[]>([])
  const [climatology, setClimatology] = useState<ClimatologyDay[]>([])

  // Carga inicial: todo lo que no depende de la ubicación elegida.
  useEffect(() => {
    Promise.all([
      api.locations(),
      api.warming(),
      api.gutenbergRichter(),
      api.omori(),
      api.myth(),
      api.deadliest(),
      api.cascades(),
      api.cycloneSeasons(),
      api.birdsSummary(),
      api.modelSkill(),
      api.health(),
    ])
      .then(([locations, warming, gr, omori, myth, deadliest, cascades, cyclones, birds, skill, health]) =>
        setGlobal({
          locations,
          warming: warming.by_year,
          distribution: gr.distribution,
          bValues: gr.b_values,
          omori: omori.decay,
          sequences: omori.largest_sequences,
          myth: myth.results,
          deadliest: deadliest.events,
          cascades: cascades.cascades,
          cycloneSeasons: cyclones.seasons,
          cycloneTrend: cyclones.trend,
          birds: birds.locations,
          birdCorr: birds.correlations,
          skill: skill.models,
          skillByCut: skill.by_cut,
          freshness: health.freshness,
        }),
      )
      .catch((e: Error) => setError(e.message))
  }, [])

  // Recarga al cambiar de ciudad. La climatología solo existe en las flagship,
  // así que un 404 aquí es esperado y se trata como lista vacía, no como error.
  useEffect(() => {
    api.anomaly(locationId, '2025-01-01').then(setAnomaly).catch(() => setAnomaly([]))
    api.climatology(locationId).then(setClimatology).catch(() => setClimatology([]))
  }, [locationId])

  const selected = global?.locations.find((l) => l.id === locationId)

  const latest = useMemo(
    () => anomaly.filter((a) => a.kind === 'observed')[0] ?? anomaly[0],
    [anomaly],
  )
  const lastWarming = global?.warming.at(-1)
  const globalB = global?.bValues.find((b) => b.scope === 'global')
  const pooledMyth = global?.myth.find((m) => m.location_id === 'POOLED')

  if (error) {
    return (
      <div className="shell">
        <p className="error">
          No se pudo cargar la API: {error}
          <br />
          <br />
          Arranca el backend con:{' '}
          <code>.venv/bin/uvicorn appclima.api.main:app --port 8000</code>
        </p>
      </div>
    )
  }

  if (!global) {
    return (
      <div className="shell">
        <p className="loading">Cargando datos…</p>
      </div>
    )
  }

  return (
    <div className="shell">
      <header className="masthead">
        <h1>AppClima</h1>
        <p>
          Datos abiertos de clima y sismos, ingeridos, modelados y contrastados.
          49 ciudades ancla, 20 años de reanálisis ERA5 en 12 de ellas y el
          catálogo sísmico completo de USGS desde 2016.
        </p>
      </header>

      <div className="kpi-row">
        <Tile
          label={`Anomalía media ${lastWarming?.year ?? ''}`}
          value={
            lastWarming?.anomaly_mean_c != null
              ? `${lastWarming.anomaly_mean_c > 0 ? '+' : ''}${lastWarming.anomaly_mean_c.toFixed(2)}°C`
              : '—'
          }
          sub={`vs base 2006-2020 · ${lastWarming?.locations ?? 0} ciudades`}
        />
        <Tile
          label="Días de calor extremo"
          value={`${lastWarming?.pct_extreme_heat_days ?? 0}%`}
          sub={`${lastWarming?.heat_records ?? 0} récords batidos en el año`}
        />
        <Tile
          label="Sismos catalogados"
          value={globalB ? globalB.n_events.toLocaleString('es') : '—'}
          sub={globalB ? `M≥4.5 · máx M${globalB.mag_max} · b = ${globalB.b_value}` : ''}
        />
        <Tile
          label="Correlación clima-sismos"
          value={
            pooledMyth?.pct_variance_explained != null
              ? `${pooledMyth.pct_variance_explained.toFixed(3)}%`
              : '—'
          }
          sub="de la varianza explicada por la presión"
        />
      </div>

      <div className="filters">
        <label htmlFor="loc">Ubicación</label>
        <select
          id="loc"
          value={locationId}
          onChange={(event) => setLocationId(event.target.value)}
        >
          {global.locations.map((l) => (
            <option key={l.id} value={l.id}>
              {l.name} ({l.country}) {l.has_climatology ? '· 20 años' : ''}
            </option>
          ))}
        </select>
        {selected && (
          <>
            <span className="pill">Köppen {selected.koppen}</span>
            <span className="pill">{selected.timezone}</span>
            <span className="pill">Ruta {selected.flyway}</span>
            {!selected.has_climatology && (
              <span className="pill" style={{ color: 'var(--text-muted)' }}>
                Sin historia profunda
              </span>
            )}
          </>
        )}
      </div>

      <section className="card">
        <h2>
          ¿Es normal el tiempo que hace en {selected?.name ?? locationId}?
        </h2>
        <p className="note">
          Cada barra es un día comparado con su propia normal para esa fecha del
          año. Rojo hacia arriba: más cálido de lo habitual. Azul hacia abajo:
          más frío. No es la temperatura — es lo raro que resulta esa
          temperatura, que es la pregunta interesante.
        </p>
        <AnomalyChart data={anomaly} />
        {latest?.clim_n_samples != null && (
          <p className="caveat">
            Base de referencia: {latest.clim_n_samples} muestras por día del año,
            periodo 2006-2020 cerrado. Los días dentro de la base tienen anomalía
            media cero por construcción, así que la señal solo se interpreta a
            partir de 2021.
          </p>
        )}
      </section>

      <section className="card">
        <h2>El año en curso sobre el rango histórico normal</h2>
        <p className="note">
          La banda gris es donde cae el 90% de los años (percentiles 5 a 95). Si
          la línea azul se sale de la banda, ese día fue inusual de verdad.
        </p>
        <ClimatologyChart climatology={climatology} recent={anomaly} />
      </section>

      <section className="card">
        <h2>Ley de Gutenberg-Richter</h2>
        <p className="note">
          Por cada sismo de magnitud 6 hay unos diez de magnitud 5 y unos cien de
          magnitud 4. En escala logarítmica esa relación es una recta, y es una
          de las leyes empíricas más robustas de la ciencia. Aquí está, calculada
          con nuestro propio catálogo.
        </p>
        <GutenbergRichterChart
          distribution={global.distribution}
          bValues={global.bValues}
        />
        <p className="caveat">
          El corte en M4.5 es la magnitud de completitud de la ingesta: por
          debajo faltan sismos porque no los pedimos, no porque no ocurrieran.
          Ajustar la recta incluyendo datos por debajo de ese corte curvaría el
          extremo inferior y daría un valor b equivocado.
        </p>
      </section>

      <section className="card">
        <h2>Ley de Omori: cómo se apagan las réplicas</h2>
        <p className="note">
          Réplicas por día tras cada sismo principal de M≥6.5, sumadas sobre
          todas las secuencias desde 2016. La caída es hiperbólica, no
          exponencial: baja rápido al principio y luego arrastra una cola larga
          de semanas.
        </p>
        <OmoriChart decay={global.omori} />
        {global.sequences.length > 0 && (
          <p className="caveat">
            Secuencia más numerosa del periodo:{' '}
            {global.sequences[0].mainshock_place} (M
            {global.sequences[0].mainshock_mag}), con{' '}
            {global.sequences[0].sequence_total.toLocaleString('es')} réplicas
            registradas. La media por secuencia activa está sesgada al alza en
            los días altos, porque solo entran secuencias que seguían vivas.
          </p>
        )}
      </section>

      <section className="card">
        <h2>El mito del «clima sísmico», contrastado</h2>
        <p className="note">
          Cada vez que hay un terremoto notable alguien dice que hacía «tiempo de
          terremotos». Lo medimos: sismos diarios en 500 km alrededor de cada
          ciudad, contra la presión atmosférica de ese día.
        </p>
        <MythTable rows={global.myth} />
        <p className="caveat">
          Mira las dos últimas columnas juntas. Con 87.654 días, el umbral de
          significación estadística cae a r = 0,0066, así que una correlación de
          0,01 sale «significativa» explicando el 0,014% de la varianza. La
          significación responde a «¿es distinto de cero?», no a «¿importa?». Con
          datos suficientes, todo es distinto de cero. Aquí no hay relación
          práctica — y un resultado nulo bien medido también es un resultado.
        </p>
      </section>


      <section className="card">
        <h2>Las mayores catástrofes de las que hay registro</h2>
        <p className="note">
          Epidemias y desastres naturales en la misma escala. El resultado es
          brutal: la peor pandemia mató entre 300 y 800 veces más que el peor
          desastre natural registrado. El terremoto de Shaanxi de 1556, el más
          mortal del archivo, se llevó 830.000 vidas; la peste negra, entre 75 y
          200 millones.
        </p>
        <DeadliestChart events={global.deadliest} />
        <p className="caveat">
          Las barras de las epidemias son rangos porque nadie sabe la cifra
          exacta: la plaga de Justiniano va de 15 a 100 millones, un factor de
          casi 7. Los desastres naturales traen recuento, no estimación, y por
          eso son marcas únicas. Comparar segundos de terremoto con décadas de
          pandemia solo es legítimo teniendo eso presente — el tooltip muestra
          la duración de cada uno.
        </p>
      </section>

      <section className="card">
        <h2>Cuando el desastre no es el que mata</h2>
        <p className="note">
          Los tres archivos de NOAA están enlazados por identificador, así que se
          puede reconstruir la cadena causal: qué sismo generó qué tsunami. Y ahí
          aparece un patrón que casi ningún catálogo modela.
        </p>
        <CascadeTable rows={global.cascades} />
        <p className="caveat">
          Sumatra 2004: el terremoto mató a 1.001 personas y el tsunami que
          generó a 226.898 más — el 99,6% del total, con olas de 50,9 metros.
          Tōhoku 2011 repite el patrón con un 92%. Tratar sismo y tsunami como
          eventos independientes, que es lo habitual, o duplica las muertes o
          pierde la relación entera. Aquí se eliminaron 584 filas duplicadas
          justamente por eso.
        </p>
      </section>


      <section className="card">
        <h2>¿Hay más ciclones tropicales que antes?</h2>
        <p className="note">
          Energía ciclónica acumulada de todo el planeta, temporada a temporada
          desde 1980. El ACE mide intensidad y duración a la vez, no solo cuántas
          tormentas hubo: tres huracanes largos e intensos pesan más que ocho
          débiles y fugaces.
        </p>
        <CycloneSeasonsChart seasons={global.cycloneSeasons} />
        {global.cycloneTrend && (
          <p className="caveat">
            La respuesta honesta es que no se ve tendencia. Correlación entre año
            y ACE global: <strong>r = {global.cycloneTrend.r_ace}</strong> sobre{' '}
            {global.cycloneTrend.n_years} temporadas. Los huracanes mayores dan
            r = {global.cycloneTrend.r_major_hurricanes} frente a un umbral de
            significación de {global.cycloneTrend.significance_threshold} — está
            justo en la línea, tan al filo que una temporada más podría voltearlo.
            Coincide con la literatura: sin señal clara en frecuencia total,
            indicios débiles de mayor proporción de tormentas intensas. Por eso
            no hay recta de tendencia dibujada: trazarla invitaría a leer una
            pendiente que los datos no sostienen.
          </p>
        )}
      </section>


      <section className="card">
        <h2>Aves: cuando el dato mide al observador, no a la naturaleza</h2>
        <p className="note">
          Riqueza de especies observadas alrededor de cada ciudad, frente al
          número de listas que enviaron los observadores. Datos de eBird, ciencia
          ciudadana del Cornell Lab of Ornithology.
        </p>
        <BirdEffortChart locations={global.birds} />
        {global.birdCorr && (
          <p className="caveat">
            La nube es casi una recta, y eso es el hallazgo. El esfuerzo de
            observación explica el{' '}
            <strong>{global.birdCorr.pct_variance_effort}%</strong> de la
            varianza (r = {global.birdCorr.r_effort}); la latitud, apenas el{' '}
            {global.birdCorr.pct_variance_latitude}% (r ={' '}
            {global.birdCorr.r_latitude}). Denver encabeza la lista con 134
            especies y Manaos, en plena Amazonía, tiene 89 — no porque Denver sea
            más biodiverso, sino porque tiene 56 listas frente a 4. Cualquier
            comparación de biodiversidad con estos datos debe dividir por
            esfuerzo antes de concluir nada.
          </p>
        )}
      </section>


      <section className="card">
        <h2>Qué predice de verdad, y qué no sale a producción</h2>
        <p className="note">
          Cada modelo evaluado con walk-forward sobre varios cortes temporales,
          no sobre uno. Se guarda la <strong>mediana</strong>, nunca el máximo.
          Un modelo se publica solo si su mediana bate a la línea base con más
          de un 5% de margen <em>y</em> ningún corte sale negativo.
        </p>
        <ModelSkillTable models={global.skill} byCut={global.skillByCut} />
        <p className="caveat">
          Esta tabla existe porque tres hipótesis que parecían tener señal la
          perdieron al verificarlas. El riesgo de calor corregido declaraba
          +16,9% medido en un solo corte; su mediana sobre cinco es +3,5%, y por
          eso queda retenido. La diferencia no está en el modelo: está en lo
          caliente que resultó el periodo de prueba que se eligiera. El criterio
          de publicación vive en los datos, no en el frontend — para que la
          tentación de enseñar el número bonito no gane.
        </p>
      </section>

      <footer className="credits">
        Fuentes: <a href="https://open-meteo.com">Open-Meteo</a> (pronóstico y
        reanálisis ERA5) ·{' '}
        <a href="https://earthquake.usgs.gov/fdsnws/event/1/">
          USGS Earthquake Catalog
        </a>{' '}
        · <a href="https://ebird.org/api/keygen">eBird</a> (pendiente de token).
        <br />
        Frescura de los datos:{' '}
        {Object.entries(global.freshness)
          .map(([k, v]) => `${k}: ${v ?? 'sin datos'}`)
          .join(' · ')}
      </footer>
    </div>
  )
}

function Tile({
  label,
  value,
  sub,
}: {
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  )
}
