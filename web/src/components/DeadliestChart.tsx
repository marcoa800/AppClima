import { useState } from 'react'
import type { DeadliestEvent } from '../api'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const ROW_H = 26
const M = { top: 10, right: 96, bottom: 42, left: 232 }

const fmt = (n: number) =>
  n >= 1_000_000
    ? `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)} M`
    : n.toLocaleString('es')

/** Epidemias frente a desastres naturales, en escala logarítmica.
 *
 * Tres decisiones de forma, y todas vienen del dato:
 *
 * 1. **Escala logarítmica.** El rango va de 10.000 a 200.000.000 — cuatro
 *    órdenes de magnitud. En escala lineal, todo salvo la peste negra sería una
 *    raya de un píxel. El eje va etiquetado como logarítmico bien visible,
 *    porque una log sin avisar engaña sobre las proporciones.
 *
 * 2. **Barras de rango, no barras simples.** Las epidemias no tienen una cifra
 *    sino un intervalo, y a veces enorme: la plaga de Justiniano va de 15 a 100
 *    millones. Dibujar solo el punto medio ocultaría justo lo que hay que ver.
 *    Los desastres naturales, que sí traen recuento, salen como marca única.
 *
 * 3. **Barras horizontales.** Los nombres son largos ("Pandemia de gripe de
 *    1918"); en vertical habría que rotarlos y se vuelven ilegibles.
 */
export function DeadliestChart({ events }: { events: DeadliestEvent[] }) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  const rows = events.filter(
    (e) => e.deaths_low !== null && e.deaths_high !== null && e.deaths_high > 0,
  )
  if (rows.length === 0) return <p className="loading">Sin datos.</p>

  const H = M.top + rows.length * ROW_H + M.bottom

  // Dominio en potencias de diez enteras, para que las líneas de rejilla caigan
  // en 10 mil, 100 mil, 1 millón… y no en valores arbitrarios.
  const lo = Math.floor(Math.log10(Math.min(...rows.map((r) => r.deaths_low!))))
  const hi = Math.ceil(Math.log10(Math.max(...rows.map((r) => r.deaths_high!))))
  const x = (v: number) =>
    M.left + ((Math.log10(Math.max(v, 1)) - lo) / (hi - lo)) * (W - M.left - M.right)

  const decades = Array.from({ length: hi - lo + 1 }, (_, i) => lo + i)

  return (
    <>
      <div className="legend">
        <span className="item">
          <span className="swatch" style={{ background: 'var(--series-2)' }} />
          Epidemia — barra = rango de estimaciones
        </span>
        <span className="item">
          <span className="swatch" style={{ background: 'var(--series-1)' }} />
          Desastre natural — recuento
        </span>
      </div>

      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Muertes por epidemias y desastres naturales en escala logarítmica"
          onMouseLeave={() => setTooltip(null)}
        >
          {decades.map((d) => (
            <g key={d}>
              <line
                className="grid"
                x1={x(10 ** d)}
                x2={x(10 ** d)}
                y1={M.top}
                y2={H - M.bottom}
              />
              <text
                className="tick-value"
                x={x(10 ** d)}
                y={H - M.bottom + 16}
                textAnchor="middle"
              >
                {fmt(10 ** d)}
              </text>
            </g>
          ))}

          {rows.map((row, i) => {
            const y = M.top + i * ROW_H + ROW_H / 2
            const isEpidemic = row.family === 'epidemic'
            const color = isEpidemic ? 'var(--series-2)' : 'var(--series-1)'
            const x0 = x(row.deaths_low!)
            const x1 = x(row.deaths_high!)
            const isRange = x1 - x0 > 3

            return (
              <g
                key={row.event_key}
                onMouseEnter={(event) =>
                  setTooltip({
                    x: event.clientX,
                    y: event.clientY,
                    title: row.event_name,
                    rows: [
                      isRange
                        ? `Entre ${fmt(row.deaths_low!)} y ${fmt(row.deaths_high!)} muertes`
                        : `${fmt(row.deaths_representative ?? 0)} muertes`,
                      row.deaths_uncertainty_ratio && row.deaths_uncertainty_ratio > 1
                        ? `Incertidumbre: factor ${row.deaths_uncertainty_ratio}`
                        : '',
                      `${row.year}${row.end_year && row.end_year !== row.year ? `–${row.end_year}` : ''} · ${row.duration_years} año${row.duration_years === 1 ? '' : 's'}`,
                      row.location ? `${row.location.slice(0, 52)}` : '',
                      `${row.estimate_kind} · confianza ${row.estimate_confidence}`,
                    ].filter(Boolean),
                  })
                }
              >
                <text
                  x={M.left - 10}
                  y={y + 4}
                  textAnchor="end"
                  style={{ fill: 'var(--text-secondary)' }}
                >
                  {row.event_name.length > 34
                    ? `${row.event_name.slice(0, 33)}…`
                    : row.event_name}
                </text>

                {isRange ? (
                  <>
                    <rect
                      x={x0}
                      y={y - 5}
                      width={x1 - x0}
                      height={10}
                      rx={4}
                      fill={color}
                      opacity={0.42}
                    />
                    {/* Extremos marcados: el ancho del rango es el dato. */}
                    <rect x={x0} y={y - 7} width={2.5} height={14} rx={1.2} fill={color} />
                    <rect x={x1 - 2.5} y={y - 7} width={2.5} height={14} rx={1.2} fill={color} />
                  </>
                ) : (
                  <circle
                    cx={x0}
                    cy={y}
                    r={4.5}
                    fill={color}
                    stroke="var(--surface-1)"
                    strokeWidth={2}
                  />
                )}

                <text
                  x={Math.min(x1 + 9, W - M.right + 88)}
                  y={y + 4}
                  style={{ fill: 'var(--text-muted)' }}
                  className="tick-value"
                >
                  {isRange
                    ? `${fmt(row.deaths_low!)}–${fmt(row.deaths_high!)}`
                    : fmt(row.deaths_representative ?? 0)}
                </text>

                <rect
                  x={M.left}
                  y={y - ROW_H / 2}
                  width={W - M.left - M.right}
                  height={ROW_H}
                  fill="transparent"
                />
              </g>
            )
          })}

          <text
            x={(M.left + W - M.right) / 2}
            y={H - 6}
            textAnchor="middle"
            style={{ fill: 'var(--text-secondary)' }}
          >
            Muertes — escala logarítmica (cada división ×10)
          </text>
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
