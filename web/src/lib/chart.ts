/** Utilidades mínimas de escalas y ejes.
 *
 * Escrito a mano en lugar de usar una librería de gráficas por una razón
 * concreta: el skill de visualización exige especificaciones de marca precisas
 * (líneas de 2px, extremos redondeados de 4px anclados a la línea base, hueco
 * de 2px entre rellenos contiguos, marcadores de ≥8px). Conseguir eso peleando
 * con los valores por defecto de una librería cuesta más que dibujar el SVG.
 */

export type Scale = (value: number) => number

export function linearScale(
  domain: [number, number],
  range: [number, number],
): Scale {
  const [d0, d1] = domain
  const [r0, r1] = range
  const span = d1 - d0
  // Un dominio degenerado (todos los valores iguales) dividiría por cero y
  // pintaría NaN, que en SVG se traduce en marcas invisibles sin error alguno.
  if (span === 0) return () => (r0 + r1) / 2
  return (value) => r0 + ((value - d0) / span) * (r1 - r0)
}

/** Ticks "redondos" para un eje: pasos de 1, 2, 5 o 10 por década. */
export function niceTicks(min: number, max: number, target = 5): number[] {
  if (!isFinite(min) || !isFinite(max) || min === max) return [min]
  const rawStep = (max - min) / target
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const normalized = rawStep / magnitude
  const step =
    (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) *
    magnitude

  const ticks: number[] = []
  for (let t = Math.ceil(min / step) * step; t <= max + step * 1e-9; t += step) {
    // El redondeo evita que la aritmética binaria produzca 0.30000000000000004
    // como etiqueta de eje.
    ticks.push(Math.round(t / step) * step)
  }
  return ticks
}

export function extent(values: (number | null)[]): [number, number] {
  const clean = values.filter((v): v is number => v !== null && isFinite(v))
  if (clean.length === 0) return [0, 1]
  return [Math.min(...clean), Math.max(...clean)]
}

/** Suaviza el dominio para que incluya el cero, necesario en divergentes. */
export function symmetricDomain(values: (number | null)[]): [number, number] {
  const [lo, hi] = extent(values)
  const bound = Math.max(Math.abs(lo), Math.abs(hi))
  return [-bound, bound]
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

const MONTHS = [
  'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'sep', 'oct', 'nov', 'dic',
]

/** Etiqueta de mes a partir del día del año (año no bisiesto de referencia). */
export function doyToMonthLabel(doy: number): string {
  const date = new Date(2001, 0, 1)
  date.setDate(doy)
  return MONTHS[date.getMonth()]
}

export function doyMonthStarts(): { doy: number; label: string }[] {
  const starts: { doy: number; label: string }[] = []
  let doy = 1
  const lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  lengths.forEach((len, i) => {
    starts.push({ doy, label: MONTHS[i] })
    doy += len
  })
  return starts
}
