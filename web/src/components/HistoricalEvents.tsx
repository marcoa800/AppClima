import type { HistoricalEvent } from '../api'

/** Línea temporal de acontecimientos que cambiaron lo que los datos miden.
 *
 * No son desastres: son las razones por las que las series se comportan como se
 * comportan. La Revolución Industrial no aparece en ningún catálogo de
 * catástrofes y sin embargo es la causa de la mitad de las tendencias de este
 * proyecto.
 *
 * Los sucesos con duración se dibujan como barra y los puntuales como marca,
 * porque confundir «ochenta años de industrialización» con «un día de 1945»
 * distorsionaría cualquier lectura.
 */
export function HistoricalEvents({ events }: { events: HistoricalEvent[] }) {
  const filas = [...events].sort((a, b) => a.start_year - b.start_year)
  const min = Math.min(...filas.map((e) => e.start_year))
  const max = Math.max(...filas.map((e) => e.end_year ?? e.start_year), 2026)
  const W = 300
  const x = (a: number) => ((a - min) / (max - min)) * W

  const color: Record<string, string> = {
    tecnologia: 'var(--series-1)',
    guerra: 'var(--critical)',
    politica: 'var(--series-2)',
    ciencia: 'var(--series-3)',
    ambiental: 'var(--good)',
  }

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Acontecimiento</th>
            <th className="num">Años</th>
            <th>{min}–{max}</th>
            <th>Por qué está aquí</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((e) => {
            const fin = e.end_year ?? e.start_year
            const c = color[e.category] ?? 'var(--neutral)'
            return (
              <tr key={e.id}>
                <td>
                  {e.name}
                  <div className="src-org">{e.category}</div>
                </td>
                <td className="num">
                  {e.start_year}
                  {!e.is_point_event && fin !== e.start_year ? `–${fin}` : ''}
                </td>
                <td>
                  <svg
                    width={W}
                    height={12}
                    role="img"
                    aria-label={`De ${e.start_year} a ${fin}`}
                  >
                    <line x1={0} y1={6} x2={W} y2={6} stroke="var(--gridline)" />
                    {e.is_point_event ? (
                      <circle cx={x(e.start_year)} cy={6} r={3.5} fill={c} />
                    ) : (
                      <rect
                        x={x(e.start_year)}
                        y={3}
                        width={Math.max(3, x(fin) - x(e.start_year))}
                        height={6}
                        rx={3}
                        fill={c}
                      />
                    )}
                  </svg>
                </td>
                <td style={{ color: 'var(--text-secondary)', maxWidth: 320 }}>
                  {e.relevance}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
