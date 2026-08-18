import type { Cascade } from '../api'

const fmt = (n: number | null) => (n === null ? '—' : n.toLocaleString('es'))

/** Desastres donde el peligro secundario mató más que el primario.
 *
 * Tabla y no gráfica: la columna que importa es una proporción muy cercana al
 * 100% en casi todas las filas, y un gráfico de barras de valores entre 75% y
 * 99,6% no aporta nada sobre los números. Lo interesante es el CONTRASTE entre
 * las dos primeras columnas numéricas — 1.001 frente a 227.899 — y eso se lee
 * mejor en cifras que en longitudes de barra.
 */
export function CascadeTable({ rows }: { rows: Cascade[] }) {
  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Año</th>
            <th>Lugar</th>
            <th className="num">Mag.</th>
            <th className="num">Muertes directas</th>
            <th className="num">Muertes totales</th>
            <th className="num">% del secundario</th>
            <th className="num">Ola máx.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.year}-${r.location_name}-${r.deaths_total}`}>
              <td>{r.year}</td>
              <td>
                {(r.location_name ?? r.country ?? '—')
                  .replace(/\s+/g, ' ')
                  .slice(0, 38)}
              </td>
              <td className="num">{r.eq_magnitude?.toFixed(1) ?? '—'}</td>
              <td className="num">{fmt(r.deaths_direct)}</td>
              <td className="num" style={{ fontWeight: 600 }}>
                {fmt(r.deaths_total)}
              </td>
              <td className="num">
                {r.pct_from_cascade !== null ? `${r.pct_from_cascade}%` : '—'}
              </td>
              <td className="num">
                {r.tsunami_wave_m !== null ? `${r.tsunami_wave_m} m` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
