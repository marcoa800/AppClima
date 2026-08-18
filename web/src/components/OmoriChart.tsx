import { useState } from 'react'
import type { OmoriDay } from '../api'
import { linearScale, niceTicks } from '../lib/chart'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const H = 260
const M = { top: 14, right: 16, bottom: 40, left: 54 }

/** Decaimiento de réplicas. Una serie, magnitud → barras de un solo tono.
 *
 * El total de réplicas por día tras el sismo principal, sumado sobre todas las
 * secuencias M≥6.5 de la última década. La caída es hiperbólica: el día 2 tiene
 * aproximadamente la mitad que el día 1, y la cola se estira durante semanas.
 */
export function OmoriChart({ decay }: { decay: OmoriDay[] }) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  const rows = decay.filter((d) => d.day_after >= 1 && d.day_after <= 30)
  if (rows.length === 0) return <p className="loading">Sin secuencias de réplicas.</p>

  const max = Math.max(...rows.map((d) => d.aftershocks_total))
  const y = linearScale([0, max], [H - M.bottom, M.top])
  const plotWidth = W - M.left - M.right
  const slot = plotWidth / 30
  const gap = 2
  const barWidth = slot - gap

  return (
    <>
      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Número de réplicas por día tras el sismo principal"
          onMouseLeave={() => setTooltip(null)}
        >
          {niceTicks(0, max, 4).map((tick) => (
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
                {tick.toLocaleString('es')}
              </text>
            </g>
          ))}

          {rows.map((d) => {
            const x = M.left + (d.day_after - 1) * slot + gap / 2
            const top = y(d.aftershocks_total)
            return (
              <rect
                key={d.day_after}
                x={x}
                y={top}
                width={barWidth}
                height={H - M.bottom - top}
                rx={4}
                fill="var(--series-1)"
                onMouseEnter={(event) =>
                  setTooltip({
                    x: event.clientX,
                    y: event.clientY,
                    title: `Día ${d.day_after} tras el sismo principal`,
                    rows: [
                      `${d.aftershocks_total.toLocaleString('es')} réplicas en total`,
                      `${d.sequences_active} secuencias con actividad`,
                      `${d.aftershocks_mean} de media por secuencia activa`,
                    ],
                  })
                }
              />
            )
          })}

          <line
            className="axis-line"
            x1={M.left}
            x2={W - M.right}
            y1={H - M.bottom}
            y2={H - M.bottom}
          />
          {[1, 5, 10, 15, 20, 25, 30].map((day) => (
            <text
              key={day}
              x={M.left + (day - 1) * slot + barWidth / 2}
              y={H - M.bottom + 16}
              textAnchor="middle"
              className="tick-value"
            >
              {day}
            </text>
          ))}
          <text
            x={(M.left + W - M.right) / 2}
            y={H - 6}
            textAnchor="middle"
            style={{ fill: 'var(--text-secondary)' }}
          >
            Días desde el sismo principal
          </text>
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
