import { useMemo, useState } from 'react'
import type { Anomaly, ClimatologyDay } from '../api'
import { doyMonthStarts, linearScale, niceTicks } from '../lib/chart'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const H = 320
const M = { top: 14, right: 16, bottom: 30, left: 46 }

/** Banda climatológica p05–p95 con la media, y el año en curso superpuesto.
 *
 * Es la gráfica que contesta "¿es raro lo que está pasando?" de un vistazo: si
 * la línea del año actual se sale de la banda gris, ese día fue inusual. La
 * banda es contexto (recesiva, sin color de serie); la línea es el sujeto.
 *
 * Dos series con significado → leyenda obligatoria, y además etiqueta directa
 * al final del trazo para no depender solo del color.
 */
export function ClimatologyChart({
  climatology,
  recent,
}: {
  climatology: ClimatologyDay[]
  recent: Anomaly[]
}) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  const clim = useMemo(
    () => climatology.filter((d) => d.temp_mean_avg !== null),
    [climatology],
  )

  // Serie del año en curso, indexada por día del año para poder superponerla
  // sobre la climatología sin depender de la fecha completa.
  const currentYear = useMemo(() => {
    if (recent.length === 0) return { year: null as number | null, points: [] }
    const year = Number(recent[0].local_date.slice(0, 4))
    const points = recent
      .filter((d) => d.local_date.startsWith(String(year)) && d.temp_mean !== null)
      .map((d) => {
        const date = new Date(`${d.local_date}T00:00:00Z`)
        const start = Date.UTC(date.getUTCFullYear(), 0, 1)
        const doy = Math.floor((date.getTime() - start) / 86_400_000) + 1
        return { doy, value: d.temp_mean as number, kind: d.kind }
      })
      .sort((a, b) => a.doy - b.doy)
    return { year, points }
  }, [recent])

  if (clim.length === 0) {
    return (
      <p className="loading">
        Esta ubicación no tiene climatología: solo las 12 ciudades con historia
        profunda de 20 años la tienen.
      </p>
    )
  }

  const allValues = [
    ...clim.map((d) => d.temp_mean_p05),
    ...clim.map((d) => d.temp_mean_p95),
    ...currentYear.points.map((p) => p.value),
  ].filter((v): v is number => v !== null)

  const lo = Math.min(...allValues)
  const hi = Math.max(...allValues)
  const pad = (hi - lo) * 0.08

  const x = linearScale([1, 366], [M.left, W - M.right])
  const y = linearScale([lo - pad, hi + pad], [H - M.bottom, M.top])
  const yTicks = niceTicks(lo - pad, hi + pad, 6)

  const bandPath = [
    'M',
    ...clim.map((d) => `${x(d.doy)},${y(d.temp_mean_p95 as number)}`),
    'L',
    ...[...clim].reverse().map((d) => `${x(d.doy)},${y(d.temp_mean_p05 as number)}`),
    'Z',
  ].join(' ')

  const meanPath = clim
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${x(d.doy)},${y(d.temp_mean_avg as number)}`)
    .join(' ')

  const currentPath = currentYear.points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.doy)},${y(p.value)}`)
    .join(' ')

  const last = currentYear.points.at(-1)

  return (
    <>
      <div className="legend">
        <span className="item">
          <span
            className="swatch"
            style={{ background: 'var(--neutral)', border: '1px solid var(--baseline)' }}
          />
          Rango normal (p05–p95, base 2006-2020)
        </span>
        <span className="item">
          <span
            className="swatch line"
            style={{ background: 'var(--text-muted)' }}
          />
          Media histórica
        </span>
        <span className="item">
          <span className="swatch line" style={{ background: 'var(--series-1)' }} />
          {currentYear.year ?? 'Año en curso'}
        </span>
      </div>

      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Temperatura media diaria del año en curso sobre el rango climatológico normal"
          onMouseLeave={() => setTooltip(null)}
        >
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                className="grid"
                x1={M.left}
                x2={W - M.right}
                y1={y(tick)}
                y2={y(tick)}
              />
              <text
                className="tick-value"
                x={M.left - 8}
                y={y(tick) + 4}
                textAnchor="end"
              >
                {tick}°
              </text>
            </g>
          ))}

          {/* Contexto: gris neutro, nunca un color de serie. */}
          <path d={bandPath} fill="var(--neutral)" stroke="none" />
          <path
            d={meanPath}
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
          />

          {/* Sujeto: 2px, extremos redondeados. */}
          <path
            d={currentPath}
            fill="none"
            stroke="var(--series-1)"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Etiqueta directa al final del trazo: identidad sin depender del color. */}
          {last && (
            <>
              <circle
                cx={x(last.doy)}
                cy={y(last.value)}
                r={4.5}
                fill="var(--series-1)"
                stroke="var(--surface-1)"
                strokeWidth={2}
              />
              <text
                x={Math.min(x(last.doy) + 9, W - M.right - 30)}
                y={y(last.value) + 4}
                style={{ fill: 'var(--text-secondary)', fontWeight: 600 }}
              >
                {currentYear.year}
              </text>
            </>
          )}

          {doyMonthStarts().map(({ doy, label }, i) =>
            i % 2 === 0 ? (
              <text key={doy} x={x(doy)} y={H - M.bottom + 16} textAnchor="middle">
                {label}
              </text>
            ) : null,
          )}

          {/* Capa de captura del ratón: hit target más ancho que la marca. */}
          {clim.map((d) => (
            <rect
              key={d.doy}
              x={x(d.doy) - 1.5}
              y={M.top}
              width={3}
              height={H - M.top - M.bottom}
              fill="transparent"
              onMouseEnter={(event) => {
                const point = currentYear.points.find((p) => p.doy === d.doy)
                setTooltip({
                  x: event.clientX,
                  y: event.clientY,
                  title: `Día ${d.doy} del año`,
                  rows: [
                    `Normal: ${d.temp_mean_avg}°C  (p05 ${d.temp_mean_p05} – p95 ${d.temp_mean_p95})`,
                    point
                      ? `${currentYear.year}: ${point.value}°C${point.kind === 'forecast' ? ' (pronóstico)' : ''}`
                      : `${currentYear.year}: sin dato`,
                    `Récord histórico: ${d.temp_max_record}°C / ${d.temp_min_record}°C`,
                    `${d.n_samples} muestras`,
                  ],
                })
              }}
            />
          ))}
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
