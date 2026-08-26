import type { PanelColumn } from '../api'

/** Cuánta potencia REAL tiene cada columna de los paneles.
 *
 * Es la tabla más importante del proyecto y la que menos se parece a lo que
 * suele publicarse. No enseña un resultado: enseña **cuánto hay que exigirle a
 * un resultado antes de creérselo**.
 *
 * El diseño pone los dos umbrales uno al lado del otro porque el hallazgo está
 * en la distancia entre ellos. Con 918 meses de ONI, el umbral ingenuo es
 * r=0,065 y el honesto r=0,377: casi seis veces más exigente. Todo lo que caiga
 * en medio parece significativo y no lo es.
 *
 * La columna que lo explica es `n efectivo`. Una serie con memoria no aporta
 * tantos datos independientes como filas tiene: 918 meses de ONI valen 27.
 *
 * Se ordena por cuánto engaña el umbral ingenuo, no alfabéticamente: lo útil es
 * ver primero dónde está el peligro.
 */
export function PanelCoverage({ columns }: { columns: PanelColumn[] }) {
  const filas = [...columns].sort(
    (a, b) => (b.naive_underestimates_by ?? 0) - (a.naive_underestimates_by ?? 0),
  )
  const maxFactor = Math.max(
    ...filas.map((c) => c.naive_underestimates_by ?? 1),
    1,
  )

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Columna</th>
            <th className="num">Filas</th>
            <th className="num">Memoria</th>
            <th className="num">n efectivo</th>
            <th className="num">Umbral ingenuo</th>
            <th className="num">Umbral honesto</th>
            <th>Cuánto engaña</th>
            <th>Veredicto</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((c) => {
            const factor = c.naive_underestimates_by ?? 1
            const grave = factor >= 3
            return (
              <tr
                key={`${c.panel}|${c.column_name}`}
                className={grave ? 'pooled' : undefined}
              >
                <td>
                  {c.column_name.replace(/_/g, ' ')}
                  <div className="src-org">
                    {c.panel.replace('gold_', '').replace('_panel', '')} ·{' '}
                    {c.first_year ?? '—'}–{c.last_year ?? '—'}
                  </div>
                </td>
                <td className="num">{c.n_observations}</td>
                <td className="num" style={{ color: 'var(--text-muted)' }}>
                  {c.acf1 != null ? c.acf1.toFixed(2) : '—'}
                </td>
                <td className="num">
                  <strong
                    style={{
                      color: c.analyzable ? 'var(--text-primary)' : 'var(--critical)',
                    }}
                  >
                    {c.n_effective}
                  </strong>
                </td>
                <td className="num" style={{ color: 'var(--text-muted)' }}>
                  {c.r_threshold_naive ?? '—'}
                </td>
                <td className="num">
                  <strong>{c.r_threshold_honest ?? '—'}</strong>
                </td>
                <td>
                  <span className="amp-row">
                    <svg
                      width={72}
                      height={12}
                      role="img"
                      aria-label={`El umbral ingenuo se queda ${factor} veces corto`}
                    >
                      <rect
                        x={0}
                        y={3}
                        width={Math.max(2, (factor / maxFactor) * 72)}
                        height={6}
                        rx={3}
                        fill={grave ? 'var(--critical)' : 'var(--neutral)'}
                      />
                    </svg>
                    <span className="amp-num">×{factor}</span>
                  </span>
                </td>
                <td style={{ color: c.analyzable ? undefined : 'var(--text-muted)' }}>
                  {c.verdict}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
