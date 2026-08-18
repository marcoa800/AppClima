/** Cliente de la API propia. Ningún componente llama a fetch directamente. */

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`)
  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(`${response.status} en ${path}${detail ? `: ${detail}` : ''}`)
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
  cut_year: number
  n_test: number
  value_model: number
  value_baseline: number
  improvement_pct: number
}

export const api = {
  health: () =>
    get<{ status: string; freshness: Record<string, string | null> }>('/health'),
  locations: () => get<Location[]>('/locations'),
  anomaly: (id: string, start?: string) =>
    get<Anomaly[]>(
      `/weather/${id}/anomaly?limit=5000${start ? `&start=${start}` : ''}`,
    ),
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
      '/patterns/deadliest?limit=26',
    ),
  cascades: () =>
    get<{ cascades: Cascade[]; finding: string }>(
      '/disasters/cascades?min_deaths=1000&limit=12',
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
  quakes: (near: string) =>
    get<Quake[]>(`/quakes?near=${near}&min_magnitude=4.5&limit=50`),
}
