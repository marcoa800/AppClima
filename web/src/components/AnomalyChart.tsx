import { useMemo, useState } from 'react'
import type { Anomaly } from '../api'
import { formatDate, linearScale, niceTicks, symmetricDomain } from '../lib/chart'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const H = 300
const M = { top: 14, right: 16, bottom: 30, left: 46 }

/** Anomalía térmica diaria como barras divergentes desde el cero.
 *
 * La forma la dicta el trabajo del dato: "por encima o por debajo de una línea
 * base" es polaridad, y la polaridad pide una escala divergente con punto medio
 * neutro. Rojo hacia arriba (calor), azul hacia abajo (frío), gris en el cero.
 *
 * Es deliberadamente NO una serie de temperatura: 33°C en Madrid no dice si es
 * raro. La anomalía sí.
 */
export function AnomalyChart({ data }: { data: Anomaly[] }) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  // La API devuelve descendente por fecha; para dibujar necesitamos ascendente.
  const rows = useMemo(
    () => [...data].filter((d) => d.anomaly_c !== null).reverse(),
    [data],
  )

  const domain = useMemo(
    () => symmetricDomain(rows.map((d) => d.anomaly_c)),
    [rows],
  )

  if (rows.length === 0) {
    return <p className="loading">Sin datos de anomalía para esta ubicación.</p>
  }

  const y = linearScale(domain, [H - M.bottom, M.top])
  const zero = y(0)
  const plotWidth = W - M.left - M.right
  const slot = plotWidth / rows.length
  // Hueco de 2px de superficie entre barras contiguas. Con series muy densas
  // el hueco se comería la barra, así que se reduce proporcionalmente.
  const gap = Math.min(2, slot * 0.35)
  const barWidth = Math.max(1, slot - gap)
  const radius = barWidth >= 8 ? 4 : barWidth / 2

  const yTicks = niceTicks(domain[0], domain[1], 5)

  // Una etiqueta de mes cada ~30 filas, para no apiñar el eje temporal.
  const xLabels = rows
    .map((row, i) => ({ row, i }))
    .filter(({ row, i }) => i === 0 || row.local_date.slice(8) === '01')
    .filter((_, k) => k % 2 === 0)

  return (
    <>
      <div className="legend">
        <span className="item">
          <span className="swatch" style={{ background: 'var(--hot)' }} />
          Más cálido que lo normal
        </span>
        <span className="item">
          <span className="swatch" style={{ background: 'var(--cold)' }} />
          Más frío que lo normal
        </span>
        <span className="item">
          <span
            className="swatch"
            style={{
              background: 'transparent',
              border: '1.5px dashed var(--text-muted)',
            }}
          />
          Pronóstico (trazo punteado)
        </span>
      </div>

      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Anomalía de temperatura diaria respecto a la normal 2006-2020"
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
                {tick > 0 ? `+${tick}` : tick}
              </text>
            </g>
          ))}

          {/* La línea del cero es la referencia del gráfico: más marcada. */}
          <line
            className="axis-line"
            x1={M.left}
            x2={W - M.right}
            y1={zero}
            y2={zero}
            strokeWidth={1.5}
          />

          {rows.map((row, i) => {
            const value = row.anomaly_c as number
            const x = M.left + i * slot + gap / 2
            const top = value >= 0 ? y(value) : zero
            const height = Math.max(1, Math.abs(y(value) - zero))
            const isForecast = row.kind === 'forecast'

            return (
              <rect
                key={`${row.local_date}-${row.kind}`}
                x={x}
                y={top}
                width={barWidth}
                height={height}
                rx={radius}
                fill={value >= 0 ? 'var(--hot)' : 'var(--cold)'}
                // El pronóstico se distingue por opacidad Y por trazo, no solo
                // por color: la identidad nunca debe depender del color a secas.
                opacity={isForecast ? 0.55 : 1}
                stroke={isForecast ? 'var(--text-muted)' : 'none'}
                strokeWidth={isForecast ? 0.75 : 0}
                strokeDasharray={isForecast ? '2 1.5' : undefined}
                onMouseEnter={(event) =>
                  setTooltip({
                    x: event.clientX,
                    y: event.clientY,
                    title: formatDate(row.local_date),
                    rows: [
                      `Media: ${row.temp_mean}°C · normal ${row.clim_mean}°C`,
                      `Anomalía: ${value > 0 ? '+' : ''}${value.toFixed(1)}°C  (z = ${row.z_score})`,
                      `Máxima: ${row.temp_max}°C`,
                      row.record_heat && !row.in_baseline
                        ? '⚑ Récord de calor'
                        : row.extreme_heat
                          ? 'Calor extremo (>p95)'
                          : row.extreme_cold
                            ? 'Frío extremo (<p05)'
                            : '',
                      row.kind === 'forecast' ? 'Pronóstico' : 'Observado (ERA5)',
                    ].filter(Boolean),
                  })
                }
              />
            )
          })}

          {xLabels.map(({ row, i }) => (
            <text
              key={row.local_date}
              x={M.left + i * slot + barWidth / 2}
              y={H - M.bottom + 16}
              textAnchor="middle"
            >
              {formatDate(row.local_date).slice(3)}
            </text>
          ))}
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
