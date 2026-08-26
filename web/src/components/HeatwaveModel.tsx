import type { HeatwaveBacktest, HeatwaveCell } from '../api'

/** Riesgo de calor extremo por anomalía previa y fase de El Niño.
 *
 * Matriz y no tabla larga: lo que hay que ver es si el efecto de ENSO cambia
 * según la anomalía de partida, y eso es una interacción. En filas y columnas
 * se lee de un vistazo; en una lista de quince filas, no.
 *
 * La celda muestra el LIFT —cuántas veces más probable que la tasa base— y no
 * la probabilidad absoluta, porque 14% suena poco hasta que se sabe que lo
 * normal es 4,5%.
 *
 * Debajo va el backtest, que es lo que decide si esto se usa o solo se mira.
 * Va con la misma prominencia que la matriz a propósito: un modelo bonito que
 * no bate a la climatología no es un modelo, es un gráfico.
 */
export function HeatwaveModel({
  cells,
  backtest,
}: {
  cells: HeatwaveCell[]
  backtest: HeatwaveBacktest[]
}) {
  const anomalias = [...new Set(cells.map((c) => c.anomaly_bucket))].sort()
  const fases = ['La Niña', 'Neutral', 'El Niño']
  const maxLift = Math.max(...cells.map((c) => c.lift), 1)
  const global = backtest.find((b) => b.scope === 'GLOBAL') ?? backtest[0]

  const celda = (a: string, f: string) =>
    cells.find((c) => c.anomaly_bucket === a && c.enso_bucket === f)

  return (
    <>
      <div className="chart-scroll">
        <table className="data">
          <thead>
            <tr>
              <th>Anomalía de los días previos</th>
              {fases.map((f) => (
                <th key={f} className="num">
                  {f}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {anomalias.map((a) => (
              <tr key={a}>
                <td>{a.replace(/^\d+\.\s*/, '')}</td>
                {fases.map((f) => {
                  const c = celda(a, f)
                  if (!c)
                    return (
                      <td key={f} className="num" style={{ color: 'var(--text-muted)' }}>
                        —
                      </td>
                    )
                  // Intensidad proporcional al lift: el color refuerza, no
                  // sustituye — la cifra está siempre escrita.
                  const alpha = Math.min(0.85, (c.lift / maxLift) * 0.85)
                  return (
                    <td
                      key={f}
                      className="num"
                      style={{
                        background:
                          c.lift > 1
                            ? `color-mix(in srgb, var(--hot) ${alpha * 100}%, transparent)`
                            : undefined,
                      }}
                      title={`${(c.p_extreme * 100).toFixed(1)}% frente a una base de ${(c.base_rate * 100).toFixed(1)}% · n=${c.n_train}`}
                    >
                      <strong>×{c.lift}</strong>
                      <div className="src-org">
                        {(c.p_extreme * 100).toFixed(1)}%
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {global && (
        <p className="caveat">
          <strong>
            {global.beats_climatology
              ? 'Bate a la climatología'
              : 'No bate a la climatología'}
            .
          </strong>{' '}
          Brier del modelo {global.brier_model} frente a {global.brier_base} de
          la línea base — una mejora del {global.pct_improvement}% sobre{' '}
          {global.n_test.toLocaleString('es')} días de prueba. El criterio de
          publicación exige que la mediana de todos los cortes temporales supere
          el 5% y que ningún corte salga negativo, y este modelo no lo cumple:
          por eso se muestra el número y no se ofrece como pronóstico.
        </p>
      )}
    </>
  )
}
