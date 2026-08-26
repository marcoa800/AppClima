/** Cliente de la API propia. Ningún componente llama a fetch directamente.
 *
 * Funciona contra DOS backends con el mismo código:
 *
 *   desarrollo   proxy de Vite → FastAPI en :8000, con query strings
 *   producción   ficheros JSON estáticos, sin servidor
 *
 * La web pública no necesita servidor: el payload completo son 5,6 MB y cabe en
 * cualquier hosting estático gratuito. Sin coste, sin rate limiting, sin caídas
 * y servido desde CDN. FastAPI se queda para desarrollo y para el cliente de
 * iOS, que sí necesita consultas con parámetros.
 *
 * Por eso cada método pasa la ruta y los parámetros POR SEPARADO: en modo
 * estático los parámetros se ignoran (ya vienen fijados en el fichero) y en
 * modo servidor se serializan como query string.
 */

const STATIC = import.meta.env.VITE_API_STATIC === 'true'

// En modo estático las rutas cuelgan del base del SITIO, que en GitHub Pages
// es /AppClima/ y no la raíz del dominio. `BASE_URL` lo rellena Vite a partir
// de su opción `base` y siempre termina en '/', así que concatenar 'api' da la
// ruta correcta tanto en la raíz como en un subdirectorio.
//
// En desarrollo se usa /api, que el proxy de Vite reenvía a FastAPI.
const BASE = STATIC ? `${import.meta.env.BASE_URL}api` : '/api'

type Params = Record<string, string | number | undefined>

async function get<T>(path: string, params?: Params): Promise<T> {
  let url: string
  if (STATIC) {
    url = `${BASE}${path}.json`
  } else {
    const entries = Object.entries(params ?? {}).filter(([, v]) => v !== undefined)
    const qs = entries.length
      ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}`
      : ''
    url = `${BASE}${path}${qs}`
  }

  const response = await fetch(url)
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(`${response.status} en ${url}${detail ? `: ${detail}` : ''}`)
  }
  return response.json() as Promise<T>
}

export type Location = {
  id: string
  name: string
  country: string
  lat: number
  lon: number
  timezone: string
  koppen: string
  seismic_level: number
  flyway: string
  has_climatology: boolean
}

export type Anomaly = {
  location_id: string
  local_date: string
  kind: 'observed' | 'forecast'
  temp_mean: number | null
  clim_mean: number | null
  anomaly_c: number | null
  z_score: number | null
  temp_max: number | null
  clim_max_p95: number | null
  clim_max_record: number | null
  extreme_heat: boolean | null
  record_heat: boolean | null
  extreme_cold: boolean | null
  in_baseline: boolean
  clim_n_samples: number | null
}

export type ClimatologyDay = {
  doy: number
  n_samples: number
  temp_mean_avg: number | null
  temp_mean_sd: number | null
  temp_mean_p05: number | null
  temp_mean_p95: number | null
  temp_max_record: number | null
  temp_min_record: number | null
}

export type WarmingYear = {
  year: number
  anomaly_mean_c: number | null
  pct_extreme_heat_days: number | null
  heat_records: number
  locations: number
  days: number
}

export type MagnitudeBin = {
  mag_bin: number
  n_events: number
  n_cumulative: number
  log10_n_cumulative: number | null
}

export type BValue = {
  scope: string
  n_events: number
  mag_mean: number
  mag_max: number
  b_value: number
  b_std_error: number
}

export type OmoriDay = {
  day_after: number
  sequences_active: number
  aftershocks_total: number
  aftershocks_mean: number
}

export type Sequence = {
  mainshock_id: string
  mainshock_place: string
  mainshock_mag: number
  mainshock_time: string
  sequence_total: number
}

export type MythRow = {
  location_id: string
  n_days: number
  total_quakes: number
  pct_days_with_quake: number
  r_pressure: number | null
  r_temperature: number | null
  r_significance_threshold: number
  pressure_significant: boolean
  pct_variance_explained: number | null
}

export type Quake = {
  event_id: string
  time: string
  local_time?: string
  magnitude: number
  magnitude_type: string | null
  depth_km: number | null
  depth_class: string | null
  place: string | null
  distance_km?: number
  tsunami: boolean
  alert: string | null
  url: string | null
}


export type DeadliestEvent = {
  family: 'epidemic' | 'natural_disaster'
  event_key: string
  event_name: string
  subtype: string | null
  year: number
  end_year: number | null
  duration_years: number
  location: string | null
  deaths_low: number | null
  deaths_high: number | null
  deaths_representative: number | null
  deaths_uncertainty_ratio: number | null
  estimate_confidence: string
  estimate_kind: 'recuento' | 'estimación'
}

export type Cascade = {
  year: number
  hazard_type: string
  country: string | null
  location_name: string | null
  eq_magnitude: number | null
  deaths_direct: number | null
  deaths_total: number
  deaths_from_cascade: number
  tsunami_wave_m: number | null
  pct_from_cascade: number | null
}

export type CenturyRow = {
  century: number
  events: number
  events_with_exact_deaths: number
  pct_with_exact_deaths: number | null
  deaths_counted: number | null
}

export type CycloneSeason = {
  season: number
  basin: string
  systems: number
  tropical_storms: number
  hurricanes: number
  major_hurricanes: number
  landfalling: number
  ace_total: number | null
  strongest_wind_kt: number | null
}

export type CycloneTrend = {
  r_ace: number | null
  r_major_hurricanes: number | null
  n_years: number
  significance_threshold: number
}

export type BirdLocation = {
  location_id: string
  location_name: string
  country: string
  lat: number
  lon: number
  koppen: string
  flyway: string
  abs_lat: number
  species_richness: number
  checklists: number
  observations: number
  temp_mean: number | null
}

export type BirdCorrelations = {
  r_latitude: number | null
  pct_variance_latitude: number | null
  r_effort: number | null
  pct_variance_effort: number | null
  n: number
}

export type ModelSkill = {
  model_id: string
  scope: string
  metric: string
  n_cuts: number
  improvement_median: number
  improvement_min: number
  improvement_max: number
  should_display: boolean
}

export type SkillByCut = {
  model_id: string
  scope: string
  cut_year: number
  n_test: number
  value_model: number
  value_baseline: number
  improvement_pct: number
}

export type NullFinding = {
  id: string
  claim: string
  verdict: string
  statistic: string
  why_solid: string
  lesson: string
  strength: 'definitivo' | 'sólido' | 'provisional'
  domain: string
}

export type DataSource = {
  id: string
  name: string
  organization: string
  url: string
  license: string
  commercial_use: string
  attribution_required: boolean
  citation: string
  what_we_use: string
  note: string | null
}

export type HeatThreshold = {
  location_id: string
  location_name: string
  country: string
  koppen: string
  abs_lat: number
  threshold_2006_2018: number
  threshold_2019_2025: number
  threshold_drift_c: number
  pct_exceeded_now: number
  pct_expected: number
  amplification: number
  days_per_year_expected: number
  days_per_year_now: number
  temp_variability_sd: number
  temp_max_record: number
  recalibration_priority: string
}

export type AftershockSequence = {
  mainshock_id: string
  mainshock_time: string
  mainshock_mag: number
  place: string | null
  mag_band: string
  n1: number
  observed_days_2_8: number
  predicted_days_2_8: number
  predicted_low: number
  predicted_high: number
}

export type Unprecedented = {
  location_id: string
  location_name: string
  country: string
  koppen: string
  abs_lat: number
  dias_evaluados: number
  n_referencia: number
  dias_esperados: number
  dias_calor: number
  dias_frio: number
  dias_lluvia: number
  razon_calor: number
  razon_frio: number
  razon_lluvia: number
  asimetria_calor_frio: number | null
  mayor_exceso_c: number | null
  dias_calor_por_anio: number
  patron: string
}

export type HazardCity = {
  location_id: string
  location_name: string
  country: string
  koppen: string
  ciclones_200km: number
  viento_max_kt: number | null
  paso_mas_cercano_km: number | null
  sismos_m5: number
  magnitud_max: number | null
  m6_mas_cercano_km: number | null
  calor_amplificacion: number | null
  calor_dias_por_anio: number | null
  sin_precedente_razon: number | null
  sin_precedente_dias: number | null
  pct_ciclones: number
  pct_sismos: number
  pct_calor: number | null
  pct_sin_precedente: number | null
  dimensiones_disponibles: number
  dimensiones_en_cuartil_alto: number
}

export type DengueProvince = {
  location_id: string
  departamento: string
  provincia: string
  temp_media_c: number | null
  casos_total: number
  semanas_con_casos: number
  semanas_vigiladas: number
  pct_semanas_con_casos: number
  transmision: string
  pico_semanal: number
  precip_anual_mm: number | null
}

export type DengueLag = {
  provincia: string
  lag_semanas: number
  n: number
  r_temp: number | null
  pct_varianza_temp: number | null
  acf1_casos: number | null
  n_efectivo: number
  r_umbral_ingenuo: number
  r_umbral_honesto: number
  r_umbral_bonferroni: number
  r_temp_entreno: number | null
  r_temp_prueba: number | null
  lag_plausible: boolean
  aguanta_fuera_de_muestra: boolean | null
}

export type DengueSkill = {
  model_id: string
  provincia: string
  improvement_median: number
  improvement_min: number
  improvement_max: number
  n_cuts: number
  bate_esta_linea_base: boolean
  should_display: boolean
}

export const api = {
  health: () =>
    get<{ status: string; freshness: Record<string, string | null> }>('/health'),
  locations: () => get<Location[]>('/locations'),
  anomaly: (id: string, start?: string) =>
    get<Anomaly[]>(`/weather/${id}/anomaly`, { limit: 5000, start }),
  climatology: (id: string) => get<ClimatologyDay[]>(`/climatology/${id}`),
  warming: () =>
    get<{ by_year: WarmingYear[]; note: string }>('/patterns/warming'),
  gutenbergRichter: () =>
    get<{ distribution: MagnitudeBin[]; b_values: BValue[]; note: string }>(
      '/patterns/gutenberg-richter',
    ),
  omori: () =>
    get<{ decay: OmoriDay[]; largest_sequences: Sequence[]; caveat: string }>(
      '/patterns/omori',
    ),
  myth: () =>
    get<{ results: MythRow[]; interpretation: string }>(
      '/patterns/seismic-weather-myth',
    ),
  deadliest: () =>
    get<{ events: DeadliestEvent[]; finding: string; caveat: string }>(
      '/patterns/deadliest', { limit: 26 },
    ),
  cascades: () =>
    get<{ cascades: Cascade[]; finding: string }>(
      '/disasters/cascades', { min_deaths: 1000, limit: 12 },
    ),
  byCentury: () =>
    get<{ by_century: CenturyRow[]; warning: string }>('/disasters/by-century'),
  cycloneSeasons: () =>
    get<{ seasons: CycloneSeason[]; trend: CycloneTrend; finding: string }>(
      '/cyclones/seasons',
    ),
  birdsSummary: () =>
    get<{
      locations: BirdLocation[]
      correlations: BirdCorrelations
      finding: string
      caveat: string
    }>('/birds/summary'),
  modelSkill: () =>
    get<{
      models: ModelSkill[]
      by_cut: SkillByCut[]
      criterio: string
      por_que_la_mediana: string
    }>('/models/skill'),
  nulls: () =>
    get<{
      findings: NullFinding[]
      por_que_publicarlos: string
      de_donde_salen: string
    }>('/patterns/nulls'),
  unprecedented: () =>
    get<{
      cities: Unprecedented[]
      que_significa: string
      por_que_una_razon_y_no_un_recuento: string
      la_prueba: string
      limitaciones: string
    }>('/patterns/unprecedented'),
  hazardProfile: () =>
    get<{
      cities: HazardCity[]
      por_que_no_hay_un_indice: string
      esto_es_peligro_no_riesgo: string
      sobre_los_percentiles: string
    }>('/prevention/hazard-profile'),
  dengue: () =>
    get<{
      provincias: DengueProvince[]
      correlaciones_por_retardo: DengueLag[]
      habilidad_predictiva: DengueSkill[]
      que_hay_aqui: string
      que_no_demuestra: string
      y_predecir: string
      para_que_sirve_entonces: string
    }>('/health/dengue'),
  heatThresholds: () =>
    get<{
      cities: HeatThreshold[]
      variability_correlation: { r: number | null; n: number }
      que_significa: string
      quien_sufre_mas: string
      limitaciones: string
    }>('/prevention/heat-thresholds'),
  aftershocks: () =>
    get<{
      recent_sequences: AftershockSequence[]
      skill: ModelSkill
      como_leerlo: string
      avisos: string[]
    }>('/predict/aftershocks'),
  sources: () =>
    get<{
      sources: DataSource[]
      aviso_comercial: string
      cita_incompleta: string
    }>('/sources'),
  quakes: (near: string) =>
    get<Quake[]>('/quakes', { near, min_magnitude: 4.5, limit: 50 }),
}
