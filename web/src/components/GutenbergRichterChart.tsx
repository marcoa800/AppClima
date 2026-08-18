import { useState } from 'react'
import type { BValue, MagnitudeBin } from '../api'
import { linearScale, niceTicks } from '../lib/chart'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const H = 320
const M = { top: 16, right: 20, bottom: 38, left: 54 }

/** Ley de Gutenberg-Richter: log10(N) frente a magnitud.
 *
 * Una sola serie, así que no hay leyenda: el título ya la nombra. Puntos de
 * ≥8px de diámetro sobre línea de 2px, y anillo de superficie en los
 * marcadores para que no se fundan con la línea al solaparse.
 *
 * Si esta gráfica no sale recta, el problema está en los datos, no en la
 * sismología: es una de las relaciones empíricas más sólidas que existen.
 */
export function GutenbergRichterChart({
  distribution,
  bValues,
}: {
  distribution: MagnitudeBin[]
  bValues: BValue[]
}) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  const points = distribution.filter(
    (d) => d.log10_n_cumulative !== null && d.n_cumulative > 0,
  )
  if (points.length === 0) return <p className="loading">Sin datos sísmicos.</p>

  const global = bValues.find((b) => b.scope === 'global')

  const magMin = Math.min(...points.map((p) => p.mag_bin))
  const magMax = Math.max(...points.map((p) => p.mag_bin))
  const logMax = Math.max(...points.map((p) => p.log10_n_cumulative as number))

  const x = linearScale([magMin, magMax], [M.left, W - M.right])
  const y = linearScale([0, Math.ceil(logMax)], [H - M.bottom, M.top])

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.mag_bin)},${y(p.log10_n_cumulative as number)}`)
    .join(' ')

  // Recta teórica con el b ajustado por máxima verosimilitud, para poder
  // comparar visualmente el ajuste con los datos observados.
  const fitLine = global
    ? (() => {
        const anchor = points[0]
        const a =
          (anchor.log10_n_cumulative as number) + global.b_value * anchor.mag_bin
        return `M${x(magMin)},${y(a - global.b_value * magMin)} L${x(magMax)},${y(a - global.b_value * magMax)}`
      })()
    : null

  // Solo se etiquetan directamente algunos puntos, nunca todos.
  const labelled = new Set([magMin, 5.0, 6.0, 7.0, 8.0])

  return (
    <>
      {global && (
        <div className="legend">
          <span className="item">
            <span className="swatch line" style={{ background: 'var(--series-1)' }} />
            Observado ({global.n_events.toLocaleString('es')} sismos)
          </span>
          <span className="item">
            <span
              className="swatch line"
              style={{
                background: 'transparent',
                borderTop: '2px dashed var(--text-muted)',
              }}
            />
            Ajuste b = {global.b_value} ± {global.b_std_error}
          </span>
        </div>
      )}

      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Relación magnitud-frecuencia de sismos en escala logarítmica"
          onMouseLeave={() => setTooltip(null)}
        >
          {niceTicks(0, Math.ceil(logMax), 5).map((tick) => (
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
                {Math.pow(10, tick).toLocaleString('es', {
                  maximumSignificantDigits: 1,
                })}
              </text>
            </g>
          ))}

          {fitLine && (
            <path
              d={fitLine}
              fill="none"
              stroke="var(--text-muted)"
              strokeWidth={2}
              strokeDasharray="5 4"
            />
          )}

          <path
            d={path}
            fill="none"
            stroke="var(--series-1)"
            strokeWidth={2}
            strokeLinecap="round"
          />

          {points.map((p) => (
            <g key={p.mag_bin}>
              {labelled.has(p.mag_bin) && (
                <circle
                  cx={x(p.mag_bin)}
                  cy={y(p.log10_n_cumulative as number)}
                  r={4.5}
                  fill="var(--series-1)"
                  stroke="var(--surface-1)"
                  strokeWidth={2}
                />
              )}
              <circle
                cx={x(p.mag_bin)}
                cy={y(p.log10_n_cumulative as number)}
                r={9}
                fill="transparent"
                onMouseEnter={(event) =>
                  setTooltip({
                    x: event.clientX,
                    y: event.clientY,
                    title: `Magnitud ≥ ${p.mag_bin.toFixed(1)}`,
                    rows: [
                      `${p.n_cumulative.toLocaleString('es')} sismos acumulados`,
                      `${p.n_events.toLocaleString('es')} en esta banda de 0,1`,
                      `log10(N) = ${p.log10_n_cumulative}`,
                    ],
                  })
                }
              />
            </g>
          ))}

          <line
            className="axis-line"
            x1={M.left}
            x2={W - M.right}
            y1={H - M.bottom}
            y2={H - M.bottom}
          />
          {[4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5].map((mag) =>
            mag >= magMin && mag <= magMax ? (
              <text
                key={mag}
                x={x(mag)}
                y={H - M.bottom + 16}
                textAnchor="middle"
                className="tick-value"
              >
                {mag.toFixed(1)}
              </text>
            ) : null,
          )}
          <text
            x={(M.left + W - M.right) / 2}
            y={H - 4}
            textAnchor="middle"
            style={{ fill: 'var(--text-secondary)' }}
          >
            Magnitud
          </text>
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
