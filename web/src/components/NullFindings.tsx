import { useState } from 'react'
import type { NullFinding } from '../api'

/** Resultados nulos: lo que se buscó y no está.
 *
 * Formato de fichas plegables, no tabla ni gráfica. Cada nulo necesita cuatro
 * párrafos para sostenerse —la afirmación, el estadístico, por qué es un nulo y
 * no falta de datos, y la lección— y eso no cabe en celdas.
 *
 * Plegadas por defecto porque son diez: la lista de titulares se lee de un
 * vistazo y quien quiera el detalle lo despliega.
 */
export function NullFindings({ findings }: { findings: NullFinding[] }) {
  const [abierto, setAbierto] = useState<string | null>(findings[0]?.id ?? null)

  return (
    <div className="nulls">
      {findings.map((f) => {
        const activo = abierto === f.id
        return (
          <article key={f.id} className={`null-card${activo ? ' open' : ''}`}>
            <button
              className="null-head"
              onClick={() => setAbierto(activo ? null : f.id)}
              aria-expanded={activo}
            >
              {/* Sin envolver en comillas: algunas afirmaciones ya las
                  llevan dentro y salían dobles. El estilo del titular ya
                  indica que es una cita. */}
              <span className="null-claim">{f.claim}</span>
              <span className="null-meta">
                <span className="pill">{f.domain}</span>
                {/* El estado va con texto, no solo con color. */}
                <span
                  className="pill"
                  style={{
                    color:
                      f.strength === 'definitivo'
                        ? 'var(--text-primary)'
                        : 'var(--text-muted)',
                  }}
                >
                  {f.strength}
                </span>
                <span className="null-toggle">{activo ? '−' : '+'}</span>
              </span>
            </button>

            <p className="null-verdict">{f.verdict}</p>

            {activo && (
              <div className="null-body">
                <div>
                  <h4>La cifra</h4>
                  <p>{f.statistic}</p>
                </div>
                <div>
                  <h4>Por qué es un nulo y no falta de datos</h4>
                  <p>{f.why_solid}</p>
                </div>
                <div>
                  <h4>Qué se aprende</h4>
                  <p>{f.lesson}</p>
                </div>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
