import type { HeatThreshold } from '../api'

/** Umbrales de alerta por calor desfasados, por ciudad.
 *
 * Tabla y no gráfica: lo accionable es el CONTRASTE entre tres cifras por
 * ciudad —el umbral viejo, el de hoy y cuántos días al año se dispara— y eso se
 * lee mejor en números que en longitudes de barra. La barra de amplificación
 * está solo como ayuda visual para ordenar de un vistazo.
 *
 * La prioridad va con texto además de con color: nunca solo color.
 */
export function HeatThresholds({ cities }: { cities: HeatThreshold[] }) {
  const maxAmp = Math.max(...cities.map((c) => c.amplification), 1)

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Ciudad</th>
            <th className="num">Umbral 2006-2018</th>
            <th className="num">Umbral hoy</th>
            <th className="num">Sube</th>
            <th className="num">Días/año</th>
            <th>Se dispara de más</th>
            <th>Prioridad</th>
          </tr>
        </thead>
        <tbody>
          {cities.map((c) => {
            const urgente = c.recalibration_priority.startsWith('1')
            return (
              <tr key={c.location_id} className={urgente ? 'pooled' : undefined}>
                <td>
                  {c.location_name}
                  <div className="src-org">
                    {c.country} · Köppen {c.koppen}
                  </div>
                </td>
                <td className="num">{c.threshold_2006_2018} °C</td>
                <td className="num">{c.threshold_2019_2025} °C</td>
                <td
                  className="num"
                  style={{
                    color:
                      c.threshold_drift_c > 1.5
                        ? 'var(--hot)'
                        : c.threshold_drift_c < 0
                          ? 'var(--cold)'
                          : 'var(--text-secondary)',
                  }}
                >
                  {c.threshold_drift_c > 0 ? '+' : ''}
                  {c.threshold_drift_c} °C
                </td>
                <td className="num">
                  <strong>{c.days_per_year_now}</strong>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {' '}
                    / {c.days_per_year_expected}
                  </span>
                </td>
                <td>
                  <span className="amp-row">
                    <svg width={78} height={12} role="img" aria-hidden="true">
                      <rect
                        x={0}
                        y={3}
                        width={Math.max(2, (c.amplification / maxAmp) * 78)}
                        height={6}
                        rx={3}
                        fill={
                          c.amplification >= 3 ? 'var(--hot)' : 'var(--series-1)'
                        }
                      />
                    </svg>
                    <span className="amp-num">×{c.amplification}</span>
                  </span>
                </td>
                <td>
                  <span
                    className="pill"
                    style={{
                      color: urgente ? 'var(--text-primary)' : 'var(--text-muted)',
                    }}
                  >
                    {c.recalibration_priority.replace(/^\d\.\s*/, '')}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
