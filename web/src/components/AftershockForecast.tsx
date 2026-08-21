import type { AftershockSequence, ModelSkill } from '../api'

const fecha = (iso: string) => {
  const d = new Date(iso)
  return `${String(d.getUTCDate()).padStart(2, '0')}/${String(d.getUTCMonth() + 1).padStart(2, '0')}/${d.getUTCFullYear()}`
}

/** Pronóstico de réplicas: el único modelo del proyecto que sale a producción.
 *
 * Se muestran secuencias reales con lo PREDICHO y lo OBSERVADO juntos, que es la
 * única forma honesta de enseñar un modelo: si solo se enseñara la predicción,
 * nadie podría juzgar si acierta.
 *
 * Siempre intervalo, nunca cifra única. La distribución tiene cola pesada
 * —media 16, mediana 4, máximo observado 212— así que un número solo daría una
 * falsa sensación de precisión.
 */
export function AftershockForecast({
  sequences,
  skill,
}: {
  sequences: AftershockSequence[]
  skill: ModelSkill | null
}) {
  const conDatos = sequences.filter((s) => s.n1 > 0).slice(0, 10)
  if (conDatos.length === 0) {
    return <p className="loading">Sin secuencias recientes.</p>
  }

  return (
    <>
      {skill && (
        <div className="legend">
          <span className="item">
            Validado con walk-forward sobre {skill.n_cuts} cortes temporales:
            mediana <strong>{skill.improvement_median}%</strong> mejor que la
            media histórica, entre {skill.improvement_min}% y{' '}
            {skill.improvement_max}%.
          </span>
        </div>
      )}

      <div className="chart-scroll">
        <table className="data">
          <thead>
            <tr>
              <th>Sismo principal</th>
              <th className="num">Mag.</th>
              <th className="num">Réplicas día 1</th>
              <th className="num">Predicho días 2-8</th>
              <th className="num">Observado</th>
              <th>Acierto</th>
            </tr>
          </thead>
          <tbody>
            {conDatos.map((s) => {
              const dentro =
                s.observed_days_2_8 >= s.predicted_low &&
                s.observed_days_2_8 <= s.predicted_high
              return (
                <tr key={s.mainshock_id}>
                  <td>
                    {(s.place ?? '—').slice(0, 34)}
                    <div className="src-org">{fecha(s.mainshock_time)}</div>
                  </td>
                  <td className="num">{s.mainshock_mag}</td>
                  <td className="num">{s.n1}</td>
                  <td className="num">
                    {s.predicted_low}–{s.predicted_high}
                  </td>
                  <td className="num" style={{ fontWeight: 600 }}>
                    {s.observed_days_2_8}
                  </td>
                  <td>
                    {/* Texto además de color: la identidad nunca solo por color. */}
                    <span
                      className="pill"
                      style={{
                        color: dentro
                          ? 'var(--text-primary)'
                          : 'var(--text-muted)',
                      }}
                    >
                      {dentro ? '✓ en el intervalo' : '✕ fuera'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
