import type { CenturyCoverage as Century } from '../api'

/** Cobertura del catálogo de desastres por siglo.
 *
 * Este gráfico no mide la historia: mide **cuánto sabemos de la historia**. Y
 * está aquí para desactivar la lectura equivocada de todas las series
 * históricas del proyecto — «hay más desastres que antes» es, en su mayor
 * parte, «hay más registro que antes».
 *
 * Por eso el eje no lleva muertes sino dos cosas superpuestas: cuántos sucesos
 * hay por siglo y qué fracción tiene cifra exacta de víctimas. La segunda es la
 * que importa: un siglo con muchos sucesos y pocas cifras exactas no es un
 * siglo mejor documentado, es uno con más entradas vagas.
 */
export function CenturyCoverage({ centuries }: { centuries: Century[] }) {
  const filas = centuries.filter((c) => c.century >= 1).sort((a, b) => a.century - b.century)
  const maxEventos = Math.max(...filas.map((c) => c.events), 1)

  const W = 640
  const H = 150
  const paso = W / Math.max(filas.length, 1)

  return (
    <div className="chart-scroll">
      <svg
        width={W}
        height={H + 26}
        role="img"
        aria-label="Sucesos registrados por siglo y porcentaje con cifra exacta de víctimas"
      >
        {[0, 0.5, 1].map((f) => (
          <line
            key={f}
            x1={0}
            y1={H - f * H}
            x2={W}
            y2={H - f * H}
            stroke="var(--gridline)"
          />
        ))}
        {filas.map((c, i) => {
          const alto = (c.events / maxEventos) * H
          const exactos = (c.pct_with_exact_deaths / 100) * alto
          return (
            <g key={c.century}>
              {/* Barra completa = sucesos registrados */}
              <rect
                x={i * paso + 1}
                y={H - alto}
                width={Math.max(1, paso - 2)}
                height={alto}
                fill="var(--neutral)"
              />
              {/* Porción sólida = los que tienen cifra exacta de víctimas */}
              <rect
                x={i * paso + 1}
                y={H - exactos}
                width={Math.max(1, paso - 2)}
                height={exactos}
                fill="var(--series-1)"
              />
              {c.century % 5 === 0 && (
                <text
                  x={i * paso + paso / 2}
                  y={H + 16}
                  textAnchor="middle"
                  fontSize={10}
                  fill="var(--text-muted)"
                >
                  s.{c.century}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <p className="legend">
        <span style={{ color: 'var(--series-1)' }}>█</span> con cifra exacta de
        víctimas · <span style={{ color: 'var(--neutral)' }}>█</span> registrados
        sin cifra
      </p>
    </div>
  )
}
