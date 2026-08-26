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
  type CenturyCoverage as CenturyRow,
  type DeadliestEvent,
  type DengueLag,
  type DengueProvince,
  type DengueSkill,
  type Epidemic,
  type EnsoBasin,
  type HeatwaveBacktest,
  type HeatwaveCell,
  type HistoricalEvent,
  type DataSource,
  type ModelSkill,
  type AftershockSequence,
  type HazardCity,
  type HeatThreshold,
  type SkillByCut,
  type ClimatologyDay,
  type Location,
  type MagnitudeBin,
  type MythRow,
  type PanelColumn,
  type PerCapitaEvent,
  type OmoriDay,
  type Sequence,
  type Unprecedented,
  type WarmingYear,
  type WorldPopulationPoint,
} from './api'
import { AnomalyChart } from './components/AnomalyChart'
import { BirdEffortChart } from './components/BirdEffortChart'
import { CascadeTable } from './components/CascadeTable'
import { CycloneSeasonsChart } from './components/CycloneSeasonsChart'
import { DeadliestChart } from './components/DeadliestChart'
import { ClimatologyChart } from './components/ClimatologyChart'
import { GutenbergRichterChart } from './components/GutenbergRichterChart'
import { Attribution } from './components/Attribution'
import { ModelSkillTable } from './components/ModelSkillTable'
import { AftershockForecast } from './components/AftershockForecast'
import { HeatThresholds } from './components/HeatThresholds'
import { UnprecedentedDays } from './components/UnprecedentedDays'
import { HazardProfile } from './components/HazardProfile'
import { DengueClimate } from './components/DengueClimate'
import { EnsoBasins } from './components/EnsoBasins'
import { PanelCoverage } from './components/PanelCoverage'
import { HeatwaveModel } from './components/HeatwaveModel'
import { PerCapitaTable } from './components/PerCapitaTable'
import { EpidemicsTable } from './components/EpidemicsTable'
import { CenturyCoverage } from './components/CenturyCoverage'
import { WorldPopulationChart } from './components/WorldPopulationChart'
import { HistoricalEvents } from './components/HistoricalEvents'
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
  heat: HeatThreshold[]
  heatCorr: number | null
  heatWho: string
  heatLimits: string
  unprecedented: Unprecedented[]
  unprecedentedProof: string
  unprecedentedWhy: string
  unprecedentedLimits: string
  hazard: HazardCity[]
  hazardNoIndex: string
  hazardNotRisk: string
  dengue: DengueProvince[]
  dengueLags: DengueLag[]
  dengueSkill: DengueSkill[]
  dengueWhatIsIt: string
  dengueNotProven: string
  denguePredict: string
  dengueUseful: string
  enso: EnsoBasin[]
  ensoFinding: string
  panelCols: PanelColumn[]
  panelHow: string
  panelWhy: string
  heatwave: HeatwaveCell[]
  heatwaveBacktest: HeatwaveBacktest[]
  heatwaveDesign: string
  heatwaveFinding: string
  heatwaveTropics: string
  perCapita: PerCapitaEvent[]
  perCapitaFinding: string
  perCapitaCaveat: string
  epidemics: Epidemic[]
  epidemicsHow: string
  centuries: CenturyRow[]
  centuriesWarning: string
  worldPop: WorldPopulationPoint[]
  worldPopNote: string
  histEvents: HistoricalEvent[]
  histEventsNote: string
  aftershocks: AftershockSequence[]
  aftershockAvisos: string[]
  sources: DataSource[]
  sourcesCommercial: string
  sourcesCitation: string
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
      api.heatThresholds(),
      api.enso(),
      api.panelCoverage(),
      api.heatwave(),
      api.perCapita(),
      api.epidemics(),
      api.disastersByCentury(),
      api.worldPopulation(),
      api.historicalEvents(),
      api.unprecedented(),
      api.hazardProfile(),
      api.dengue(),
      api.aftershocks(),
      api.sources(),
      api.health(),
    ])
      .then(([locations, warming, gr, omori, myth, deadliest, cascades, cyclones, birds, skill, heat, enso, panelCov, hw, perCap, epi, cent, wpop, hev, unprec, hazard, dengue, after, sources, health]) =>
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
          heat: heat.cities,
          heatCorr: heat.variability_correlation.r,
          heatWho: heat.quien_sufre_mas,
          heatLimits: heat.limitaciones,
          enso: enso.by_basin,
          ensoFinding: enso.finding,
          panelCols: panelCov.columns,
          panelHow: panelCov.como_usarlo,
          panelWhy: panelCov.por_que,
          heatwave: hw.model,
          heatwaveBacktest: hw.backtest,
          heatwaveDesign: hw.design,
          heatwaveFinding: hw.finding,
          heatwaveTropics: hw.why_tropics,
          perCapita: perCap.events,
          perCapitaFinding: perCap.finding,
          perCapitaCaveat: perCap.caveat,
          epidemics: epi.epidemics,
          epidemicsHow: epi.how_to_read,
          centuries: cent.by_century,
          centuriesWarning: cent.warning,
          worldPop: wpop.series,
          worldPopNote: wpop.note,
          histEvents: hev.events,
          histEventsNote: hev.note,
          unprecedented: unprec.cities,
          unprecedentedProof: unprec.la_prueba,
          unprecedentedWhy: unprec.por_que_una_razon_y_no_un_recuento,
          unprecedentedLimits: unprec.limitaciones,
          hazard: hazard.cities,
          hazardNoIndex: hazard.por_que_no_hay_un_indice,
          hazardNotRisk: hazard.esto_es_peligro_no_riesgo,
          dengue: dengue.provincias,
          dengueLags: dengue.correlaciones_por_retardo,
          dengueSkill: dengue.habilidad_predictiva,
          dengueWhatIsIt: dengue.que_hay_aqui,
          dengueNotProven: dengue.que_no_demuestra,
          denguePredict: dengue.y_predecir,
          dengueUseful: dengue.para_que_sirve_entonces,
          aftershocks: after.recent_sequences,
          aftershockAvisos: after.avisos,
          sources: sources.sources,
          sourcesCommercial: sources.aviso_comercial,
          sourcesCitation: sources.cita_incompleta,
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
          {/* Agrupado y no en una lista plana. De las 66 ciudades del
              catálogo, solo 30 tienen los veinte años de archivo que la
              anomalía necesita: las otras 36 llevaban a un gráfico en blanco
              con una etiqueta discreta como única pista. Un optgroup lo dice
              antes de hacer clic, que es cuando sirve. */}
          <optgroup label="Con 20 años de archivo">
            {global.locations
              .filter((l) => l.has_climatology)
              .map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.country})
                </option>
              ))}
          </optgroup>
          <optgroup label="Sin archivo histórico todavía">
            {global.locations
              .filter((l) => !l.has_climatology)
              .map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} ({l.country})
                </option>
              ))}
          </optgroup>
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
          Mira las dos últimas columnas juntas. Con más de doscientos mil días, el umbral de
          significación estadística cae a r = 0,0066, así que una correlación de
          0,03 sale «significativa» explicando menos del 0,1% de la varianza. La
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
        <h2>El denominador: una de cada tres personas</h2>
        <p className="note">
          Todas las cifras de víctimas son absolutas, y eso engaña siempre en la
          misma dirección: parecen peores los desastres recientes, porque había
          más gente disponible para morir. Shaanxi mató a 830.000 personas en
          1556 y Tangshan a 242.769 en 1976 — pero en proporción, Shaanxi fue
          casi veintiocho veces más letal.
        </p>
        <PerCapitaTable events={global.perCapita} />
        <p className="caveat">{global.perCapitaFinding}</p>
        <p className="caveat">{global.perCapitaCaveat}</p>
        <WorldPopulationChart series={global.worldPop} />
        <p className="caveat">{global.worldPopNote}</p>
      </section>

      <section className="card">
        <h2>Epidemias: siempre un rango, nunca una cifra</h2>
        <p className="note">
          Las estimaciones de muertes de la peste negra van de 75 a 200 millones.
          Publicar «137 millones» sugeriría una precisión que ninguna fuente
          respalda, así que aquí la barra dibuja el intervalo entero: su anchura
          <em> es</em> la incertidumbre.
        </p>
        <EpidemicsTable epidemics={global.epidemics} />
        <p className="caveat">{global.epidemicsHow}</p>
      </section>

      <section className="card">
        <h2>Cuánto sabemos de cada siglo</h2>
        <p className="note">
          Este gráfico no mide la historia: mide cuánto se conserva de ella. Está
          aquí para desactivar la lectura equivocada de todas las series
          históricas — «hay más desastres que antes» es, en su mayor parte,
          «hay más registro que antes».
        </p>
        <CenturyCoverage centuries={global.centuries} />
        <p className="caveat">{global.centuriesWarning}</p>
      </section>

      <section className="card">
        <h2>Lo que cambió aquello que los datos miden</h2>
        <p className="note">
          No son catástrofes: son las razones por las que las series se comportan
          como se comportan. La Revolución Industrial no aparece en ningún
          catálogo de desastres y es la causa de la mitad de las tendencias de
          este proyecto.
        </p>
        <HistoricalEvents events={global.histEvents} />
        <p className="caveat">{global.histEventsNote}</p>
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
        <h2>El Niño y los ciclones: la señal que sí sobrevivió</h2>
        <p className="note">
          De todo lo que se contrastó en este proyecto, esta es de las pocas
          relaciones que aguantó la verificación adversarial. Y aguanta{' '}
          <strong>solo si no se promedia</strong>: El Niño dispara el Pacífico y
          apaga el Atlántico, así que una media global daría casi cero. Sería una
          cifra verdadera y completamente engañosa, porque las dos señales son
          fuertes y opuestas.
        </p>
        <EnsoBasins basins={global.enso} />
        <p className="caveat">{global.ensoFinding}</p>
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
          +16,9% medido en un solo corte; su mediana sobre cinco es +1,45%, y por
          eso queda retenido. La diferencia no está en el modelo: está en lo
          caliente que resultó el periodo de prueba que se eligiera. El criterio
          de publicación vive en los datos, no en el frontend — para que la
          tentación de enseñar el número bonito no gane.
        </p>
      </section>



      <section className="card">
        <h2>Cuándo una correlación significa algo</h2>
        <p className="note">
          Esta tabla no enseña un resultado: enseña{' '}
          <strong>cuánto hay que exigirle a un resultado antes de creérselo</strong>.
          Una serie con memoria no aporta tantos datos independientes como filas
          tiene — 918 meses del índice ONI valen 27— y el umbral de significación
          se calcula con los que valen, no con los que hay.
        </p>
        <p className="note">{global.panelWhy}</p>
        <PanelCoverage columns={global.panelCols} />
        <p className="caveat">{global.panelHow}</p>
      </section>

      <section className="card">
        <h2>Riesgo de calor extremo: qué añade saber la fase de El Niño</h2>
        <p className="note">{global.heatwaveDesign}</p>
        <HeatwaveModel
          cells={global.heatwave}
          backtest={global.heatwaveBacktest}
        />
        <p className="caveat">{global.heatwaveFinding}</p>
        <p className="caveat">{global.heatwaveTropics}</p>
      </section>

      <section className="card">
        <h2>Días para los que esta ciudad no tiene precedente</h2>
        <p className="note">
          Un día sin precedente supera todo lo registrado en su misma época del
          año durante los trece años anteriores. Importa porque las
          infraestructuras, los protocolos y las intuiciones se calibran con lo
          vivido: un valor nunca visto es, por definición, uno para el que nadie
          se preparó.
        </p>
        <p className="note">
          La cifra publicada no es el recuento sino la <strong>razón contra lo
          esperado</strong>. Contar récords y decir que aumentan es una trampa,
          porque los récords se vuelven más raros con el tiempo aunque el clima
          no cambie: con n valores previos, la probabilidad de que el siguiente
          los supere todos es 1/(n+1). Un 1,0 significa «lo normal».
        </p>
        <UnprecedentedDays cities={global.unprecedented} />
        <p className="caveat">{global.unprecedentedProof}</p>
        <p className="caveat">{global.unprecedentedLimits}</p>
      </section>

      <section className="card">
        <h2>Los umbrales de alerta por calor están desfasados</h2>
        <p className="note">
          Un plan de emergencia por calor se dispara al superar un umbral, y ese
          umbral se calibra con datos históricos: el percentil 95 de la máxima
          diaria, que por construcción debería superarse un 5% de los días. Ya no
          es así en ninguna de estas ciudades.
        </p>
        <HeatThresholds cities={global.heat} />
        <p className="caveat">
          {global.heatWho}
          {global.heatCorr !== null && (
            <>
              {' '}
              Medido: r = <strong>{global.heatCorr}</strong> entre variabilidad
              térmica y factor de amplificación.
            </>
          )}
        </p>
        <p className="caveat">{global.heatLimits}</p>
      </section>

      <section className="card">
        <h2>Pronóstico de réplicas tras un sismo</h2>
        <p className="note">
          Veinticuatro horas después de un sismo de magnitud 6,5 o mayor, las
          réplicas de ese primer día permiten estimar cuántas habrá entre el
          segundo y el octavo. Las réplicas matan rescatistas y vecinos que
          vuelven a casa, así que la cifra tiene un uso concreto: decidir cuándo
          es seguro entrar en un edificio dañado o levantar una evacuación.
        </p>
        <AftershockForecast
          sequences={global.aftershocks}
          skill={global.skill.find((m) => m.model_id === 'pronostico_replicas') ?? null}
        />
        <p className="caveat">
          {global.aftershockAvisos.join(' · ')}
        </p>
      </section>


      <section className="card">
        <h2>Perfil de peligro: cuatro frentes, sin sumarlos</h2>
        <p className="note">
          Lo natural sería fundir ciclones, sismos y calor en un «índice de
          riesgo». No se hace, y no por pereza: sumar exige pesos, y no existe
          forma defendible de decir cuántos sismos de magnitud 6 equivalen a un
          ciclón de categoría 3. Cualquier peso es una opinión disfrazada de
          cálculo — y el número resultante ordenaría ciudades para decidir cosas.
        </p>
        <HazardProfile cities={global.hazard} />
        <p className="caveat">{global.hazardNotRisk}</p>
        <p className="caveat">{global.hazardNoIndex}</p>
      </section>

      <section className="card">
        <h2>Dengue y clima en Perú: lo que se buscó y no está</h2>
        <p className="note">{global.dengueWhatIsIt}</p>
        <DengueClimate
          provincias={global.dengue}
          retardos={global.dengueLags}
          habilidad={global.dengueSkill}
        />
        <p className="caveat">
          <strong>Sin umbral térmico.</strong> {global.dengueNotProven}
        </p>
        <p className="caveat">
          <strong>Y sin capacidad de predecir.</strong> {global.denguePredict}
        </p>
        <p className="caveat">{global.dengueUseful}</p>
      </section>

      <section className="card">
        <h2>Fuentes, licencias y atribución</h2>
        <p className="note">
          Once fuentes abiertas. Cinco exigen atribución explícita y tres
          restringen el uso comercial — por eso este proyecto es y seguirá
          siendo gratuito.
        </p>
        <Attribution
          sources={global.sources}
          avisoComercial={global.sourcesCommercial}
          citaIncompleta={global.sourcesCitation}
        />
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
