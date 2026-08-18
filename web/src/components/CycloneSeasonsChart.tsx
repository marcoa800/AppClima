import { useMemo, useState } from 'react'
import type { CycloneSeason } from '../api'
import { linearScale, niceTicks } from '../lib/chart'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const H = 300
const M = { top: 14, right: 16, bottom: 42, left: 54 }

/** Energía ciclónica acumulada global por temporada, 1980-2024.
 *
 * Una sola serie de magnitud a lo largo del tiempo: barras de un solo tono, sin
 * leyenda (el título ya nombra la serie). La línea de la media va superpuesta
 * como referencia para que se vea que la serie oscila alrededor de ella en
 * lugar de subir — que es justo el hallazgo.
 *
 * Deliberadamente NO se dibuja una línea de tendencia. Con r = -0,03 no hay
 * tendencia que dibujar, y trazar una recta casi plana invitaría al ojo a leer
 * una pendiente que los datos no sostienen.
 */
export function CycloneSeasonsChart({ seasons }: { seasons: CycloneSeason[] }) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  // La API devuelve una fila por cuenca; aquí interesa el total planetario.
  const byYear = useMemo(() => {
    const acc = new Map<number, { ace: number; hur: number; major: number }>()
    for (const s of seasons) {
      const cur = acc.get(s.season) ?? { ace: 0, hur: 0, major: 0 }
      cur.ace += s.ace_total ?? 0
      cur.hur += s.hurricanes
      cur.major += s.major_hurricanes
      acc.set(s.season, cur)
    }
    return [...acc.entries()]
      .map(([season, v]) => ({ season, ...v }))
      .sort((a, b) => a.season - b.season)
  }, [seasons])

  if (byYear.length === 0) return <p className="loading">Sin datos de ciclones.</p>

  const max = Math.max(...byYear.map((d) => d.ace))
  const mean = byYear.reduce((s, d) => s + d.ace, 0) / byYear.length

  const y = linearScale([0, max], [H - M.bottom, M.top])
  const slot = (W - M.left - M.right) / byYear.length
  const gap = 2
  const barWidth = slot - gap

  return (
    <>
      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Energía ciclónica acumulada global por temporada desde 1980"
          onMouseLeave={() => setTooltip(null)}
        >
          {niceTicks(0, max, 5).map((t) => (
            <g key={t}>
              <line className="grid" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
              <text
                className="tick-value"
                x={M.left - 8}
                y={y(t) + 4}
                textAnchor="end"
              >
                {t.toLocaleString('es')}
              </text>
            </g>
          ))}

          {byYear.map((d, i) => (
            <rect
              key={d.season}
              x={M.left + i * slot + gap / 2}
              y={y(d.ace)}
              width={barWidth}
              height={H - M.bottom - y(d.ace)}
              rx={4}
              fill="var(--series-1)"
              onMouseEnter={(e) =>
                setTooltip({
                  x: e.clientX,
                  y: e.clientY,
                  title: `Temporada ${d.season}`,
                  rows: [
                    `ACE global: ${Math.round(d.ace).toLocaleString('es')}`,
                    `${d.hur} huracanes · ${d.major} mayores`,
                    `Media del periodo: ${Math.round(mean).toLocaleString('es')}`,
                  ],
                })
              }
            />
          ))}

          {/* Media del periodo: referencia, en gris, nunca color de serie. */}
          <line
            x1={M.left}
            x2={W - M.right}
            y1={y(mean)}
            y2={y(mean)}
            stroke="var(--text-muted)"
            strokeWidth={2}
            strokeDasharray="5 4"
          />
          <text
            x={W - M.right - 4}
            y={y(mean) - 6}
            textAnchor="end"
            style={{ fill: 'var(--text-secondary)' }}
          >
            media {Math.round(mean).toLocaleString('es')}
          </text>

          <line
            className="axis-line"
            x1={M.left}
            x2={W - M.right}
            y1={H - M.bottom}
            y2={H - M.bottom}
          />
          {byYear
            .filter((d) => d.season % 5 === 0)
            .map((d) => (
              <text
                key={d.season}
                x={M.left + byYear.indexOf(d) * slot + barWidth / 2}
                y={H - M.bottom + 16}
                textAnchor="middle"
                className="tick-value"
              >
                {d.season}
              </text>
            ))}
          <text
            x={(M.left + W - M.right) / 2}
            y={H - 6}
            textAnchor="middle"
            style={{ fill: 'var(--text-secondary)' }}
          >
            Temporada · ACE = suma de v² / 10.000 sobre observaciones de 6 h con ≥34 kt
          </text>
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
