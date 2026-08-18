import type { MythRow } from '../api'

/** Resultado del contraste sismos-vs-presión, como TABLA y no como gráfica.
 *
 * Es la forma correcta aquí por dos motivos. Uno: son nueve filas con varias
 * medidas cada una, y más de ~7 clases con significado piden tabla. Dos, y más
 * importante: la conclusión es que **no hay patrón**. Dibujar un diagrama de
 * dispersión de una nube sin estructura invita a que el ojo invente una
 * tendencia que no existe. Los números desnudos son más honestos.
 */
export function MythTable({ rows }: { rows: MythRow[] }) {
  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Ubicación</th>
            <th className="num">Días</th>
            <th className="num">Sismos</th>
            <th className="num">% días con sismo</th>
            <th className="num">r (presión)</th>
            <th className="num">¿Significativo?</th>
            <th className="num">% varianza explicada</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.location_id}
              className={row.location_id === 'POOLED' ? 'pooled' : undefined}
            >
              <td>{row.location_id === 'POOLED' ? 'Todas agrupadas' : row.location_id}</td>
              <td className="num">{row.n_days.toLocaleString('es')}</td>
              <td className="num">{row.total_quakes.toLocaleString('es')}</td>
              <td className="num">{row.pct_days_with_quake}%</td>
              <td className="num">{row.r_pressure?.toFixed(4) ?? '—'}</td>
              <td className="num">
                {/* Nunca solo color: el estado va con texto siempre. */}
                {row.pressure_significant ? (
                  <span
                    className="pill"
                    style={{ color: 'var(--text-secondary)' }}
                    title="Cruza el umbral estadístico, pero mira la columna siguiente"
                  >
                    sí (pero…)
                  </span>
                ) : (
                  <span className="pill" style={{ color: 'var(--text-muted)' }}>
                    no
                  </span>
                )}
              </td>
              <td className="num" style={{ fontWeight: 600 }}>
                {row.pct_variance_explained?.toFixed(4) ?? '—'}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
