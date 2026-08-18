import { useState } from 'react'
import type { BirdLocation } from '../api'
import { linearScale, niceTicks } from '../lib/chart'
import { Tooltip, type TooltipState } from './Tooltip'

const W = 1100
const H = 340
const M = { top: 16, right: 20, bottom: 46, left: 58 }

/** Riqueza de especies frente al esfuerzo de observación.
 *
 * Un diagrama de dispersión de una sola serie, así que no hay leyenda ni
 * problema de colores categóricos: el título nombra la serie.
 *
 * La forma la elige el dato: la pregunta es "¿estas dos variables se mueven
 * juntas?", que es exactamente para lo que existe la dispersión. Y aquí la
 * respuesta salta a la vista — la nube es casi una recta, lo que significa que
 * este dataset mide sobre todo cuánta gente salió a mirar.
 *
 * Se dibuja la recta de ajuste porque en este caso SÍ hay pendiente que
 * sostener: r = 0,83. Es lo contrario del gráfico de ciclones, donde con
 * r = −0,03 trazarla habría sido engañoso.
 */
export function BirdEffortChart({ locations }: { locations: BirdLocation[] }) {
  const [tooltip, setTooltip] = useState<TooltipState>(null)

  const rows = locations.filter((d) => d.checklists > 0 && d.species_richness > 0)
  if (rows.length === 0) {
    return (
      <p className="loading">
        Sin datos de aves. Consigue un token gratuito en ebird.org/api/keygen y
        ejecuta <code>appclima ingest birds</code>.
      </p>
    )
  }

  const maxChecklists = Math.max(...rows.map((d) => d.checklists))
  const maxSpecies = Math.max(...rows.map((d) => d.species_richness))

  const x = linearScale([0, maxChecklists], [M.left, W - M.right])
  const y = linearScale([0, maxSpecies], [H - M.bottom, M.top])

  // Ajuste por mínimos cuadrados, solo para mostrar la relación.
  const n = rows.length
  const mx = rows.reduce((s, d) => s + d.checklists, 0) / n
  const my = rows.reduce((s, d) => s + d.species_richness, 0) / n
  const slope =
    rows.reduce((s, d) => s + (d.checklists - mx) * (d.species_richness - my), 0) /
    rows.reduce((s, d) => s + (d.checklists - mx) ** 2, 0)
  const intercept = my - slope * mx

  return (
    <>
      <div className="chart-scroll">
        <svg
          className="chart"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Riqueza de especies frente al número de listas de observación"
          onMouseLeave={() => setTooltip(null)}
        >
          {niceTicks(0, maxSpecies, 5).map((t) => (
            <g key={t}>
              <line className="grid" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
              <text className="tick-value" x={M.left - 8} y={y(t) + 4} textAnchor="end">
                {t}
              </text>
            </g>
          ))}

          <path
            d={`M${x(0)},${y(intercept)} L${x(maxChecklists)},${y(intercept + slope * maxChecklists)}`}
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth={2}
            strokeDasharray="5 4"
          />

          {rows.map((d) => (
            <circle
              key={d.location_id}
              cx={x(d.checklists)}
              cy={y(d.species_richness)}
              r={5}
              fill="var(--series-1)"
              stroke="var(--surface-1)"
              strokeWidth={2}
              opacity={0.85}
              onMouseEnter={(e) =>
                setTooltip({
                  x: e.clientX,
                  y: e.clientY,
                  title: `${d.location_name} (${d.country})`,
                  rows: [
                    `${d.species_richness} especies · ${d.checklists} listas`,
                    `Latitud ${d.lat.toFixed(1)}° · Köppen ${d.koppen}`,
                    `Ruta migratoria: ${d.flyway}`,
                  ],
                })
              }
            />
          ))}

          {/* Etiquetas directas solo en los casos que cuentan la historia. */}
          {rows
            .filter((d) =>
              ['denver', 'manaus', 'nairobi', 'singapore'].includes(d.location_id),
            )
            .map((d) => (
              <text
                key={`lbl-${d.location_id}`}
                x={x(d.checklists) + 9}
                y={y(d.species_richness) + 4}
                style={{ fill: 'var(--text-secondary)', fontWeight: 600 }}
              >
                {d.location_name}
              </text>
            ))}

          <line
            className="axis-line"
            x1={M.left}
            x2={W - M.right}
            y1={H - M.bottom}
            y2={H - M.bottom}
          />
          {niceTicks(0, maxChecklists, 6).map((t) => (
            <text
              key={t}
              x={x(t)}
              y={H - M.bottom + 16}
              textAnchor="middle"
              className="tick-value"
            >
              {t}
            </text>
          ))}
          <text
            x={(M.left + W - M.right) / 2}
            y={H - 8}
            textAnchor="middle"
            style={{ fill: 'var(--text-secondary)' }}
          >
            Listas de observación enviadas — el «esfuerzo» de los observadores
          </text>
        </svg>
      </div>

      <Tooltip state={tooltip} />
    </>
  )
}
