import type { EnsoBasin } from '../api'

/** ENSO y actividad ciclónica, cuenca por cuenca.
 *
 * La decisión de diseño es no agregar. Un promedio global de «ciclones en El
 * Niño» daría casi cero, y esa cifra sería verdadera y totalmente engañosa: El
 * Niño dispara el Pacífico y apaga el Atlántico, así que las dos señales —que
 * son fuertes y opuestas— se anulan al sumarlas.
 *
 * Por eso la tabla se agrupa por cuenca y las fases van como filas dentro de
 * cada una: lo que hay que poder comparar de un vistazo es El Niño contra La
 * Niña DENTRO de la misma cuenca, nunca entre cuencas.
 *
 * La barra codifica ACE (energía ciclónica acumulada), que es la métrica
 * correcta aquí: cuenta intensidad y duración, no número de tormentas. Contar
 * tormentas mide sobre todo cuántas se detectaron.
 */
export function EnsoBasins({ basins }: { basins: EnsoBasin[] }) {
  const maxAce = Math.max(...basins.map((b) => b.ace_mean ?? 0), 1)

  const cuencas = [...new Set(basins.map((b) => b.basin))]
  const nombre: Record<string, string> = {
    NA: 'Atlántico norte',
    EP: 'Pacífico oriental',
    WP: 'Pacífico occidental',
    NI: 'Índico norte',
    SI: 'Índico sur',
    SP: 'Pacífico sur',
  }
  const orden = ['El Niño', 'Neutral', 'La Niña']

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Cuenca</th>
            <th>Fase</th>
            <th className="num">Temporadas</th>
            <th className="num">ACE medio</th>
            <th>Energía acumulada</th>
            <th className="num">Huracanes</th>
            <th className="num">Mayores</th>
            <th className="num">r con ONI</th>
          </tr>
        </thead>
        <tbody>
          {cuencas.flatMap((c) => {
            const filas = basins
              .filter((b) => b.basin === c)
              .sort((a, b) => orden.indexOf(a.phase) - orden.indexOf(b.phase))
            // La correlación es de la cuenca, no de la fase: se repite en las
            // tres filas, así que se muestra una vez y agrupada.
            const r = filas.find((f) => f.r_oni_vs_ace != null)?.r_oni_vs_ace ?? null
            const fuerte = r != null && Math.abs(r) >= 0.4
            return filas.map((b, i) => (
              <tr
                key={`${b.basin}|${b.phase}`}
                className={i === 0 && fuerte ? 'pooled' : undefined}
              >
                {i === 0 ? (
                  <td rowSpan={filas.length}>
                    {nombre[c] ?? c}
                    <div className="src-org">{c}</div>
                  </td>
                ) : null}
                <td>
                  <span
                    className="pill"
                    style={{
                      color:
                        b.phase === 'El Niño'
                          ? 'var(--hot)'
                          : b.phase === 'La Niña'
                            ? 'var(--cold)'
                            : 'var(--text-muted)',
                    }}
                  >
                    {b.phase}
                  </span>
                </td>
                <td className="num">{b.seasons}</td>
                <td className="num">{b.ace_mean ?? '—'}</td>
                <td>
                  <svg
                    width={96}
                    height={12}
                    role="img"
                    aria-label={`ACE medio ${b.ace_mean ?? 0}`}
                  >
                    <rect
                      x={0}
                      y={3}
                      width={Math.max(2, ((b.ace_mean ?? 0) / maxAce) * 96)}
                      height={6}
                      rx={3}
                      fill={
                        b.phase === 'El Niño'
                          ? 'var(--hot)'
                          : b.phase === 'La Niña'
                            ? 'var(--cold)'
                            : 'var(--neutral)'
                      }
                    />
                  </svg>
                </td>
                <td className="num">{b.hurricanes_mean ?? '—'}</td>
                <td className="num">{b.major_hurricanes_mean ?? '—'}</td>
                {i === 0 ? (
                  <td className="num" rowSpan={filas.length}>
                    <strong
                      style={{
                        color: fuerte ? 'var(--text-primary)' : 'var(--text-muted)',
                      }}
                    >
                      {r != null ? (r > 0 ? '+' : '') + r : '—'}
                    </strong>
                  </td>
                ) : null}
              </tr>
            ))
          })}
        </tbody>
      </table>
    </div>
  )
}
