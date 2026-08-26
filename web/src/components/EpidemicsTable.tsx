import type { Epidemic } from '../api'

/** Epidemias históricas, siempre como rango y nunca como cifra única.
 *
 * La decisión de diseño es no publicar un número central destacado. Las
 * estimaciones de muertes de la peste negra van de 75 a 200 millones: dar
 * «137 millones» sugiere una precisión que no existe y que ninguna fuente
 * respalda.
 *
 * Así que la barra dibuja el INTERVALO —de dónde a dónde— en vez de una
 * longitud. Un lector que vea una banda ancha entiende de inmediato que ahí
 * nadie sabe la cifra, y eso es exactamente lo que hay que transmitir.
 *
 * El factor de incertidumbre va en su propia columna porque ordena mejor que
 * la confianza declarada: 2,7× es más informativo que «media».
 */
export function EpidemicsTable({ epidemics }: { epidemics: Epidemic[] }) {
  const maxMuertes = Math.max(...epidemics.map((e) => e.deaths_high), 1)
  const escala = (v: number) => (Math.sqrt(v) / Math.sqrt(maxMuertes)) * 110

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Epidemia</th>
            <th className="num">Periodo</th>
            <th>Muertes estimadas (rango)</th>
            <th className="num">Incertidumbre</th>
            <th>Confianza</th>
          </tr>
        </thead>
        <tbody>
          {epidemics.map((e) => (
            <tr key={e.id} className={e.ongoing ? 'pooled' : undefined}>
              <td>
                {e.name}
                <div className="src-org">
                  {e.pathogen ?? e.disease} · {e.regions}
                </div>
              </td>
              <td className="num">
                {e.start_year < 0 ? `${-e.start_year} a.C.` : e.start_year}
                {e.ongoing ? '–hoy' : e.end_year ? `–${e.end_year}` : ''}
              </td>
              <td>
                <span className="amp-row">
                  {/* Barra de intervalo: la anchura ES la incertidumbre. Escala
                      de raíz cuadrada porque el rango cubre cinco órdenes de
                      magnitud y en lineal casi todo quedaría invisible. */}
                  <svg
                    width={116}
                    height={12}
                    role="img"
                    aria-label={`Entre ${e.deaths_low} y ${e.deaths_high} muertes`}
                  >
                    <line
                      x1={escala(e.deaths_low)}
                      y1={6}
                      x2={Math.max(escala(e.deaths_high), escala(e.deaths_low) + 2)}
                      y2={6}
                      stroke="var(--series-1)"
                      strokeWidth={6}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="amp-num">
                    {(e.deaths_low / 1e6).toFixed(1)}–{(e.deaths_high / 1e6).toFixed(1)} M
                  </span>
                </span>
              </td>
              <td className="num">
                <span
                  style={{
                    color:
                      e.deaths_uncertainty_ratio >= 3
                        ? 'var(--warning)'
                        : 'var(--text-secondary)',
                  }}
                >
                  ×{e.deaths_uncertainty_ratio}
                </span>
              </td>
              <td>
                <span className="pill">{e.estimate_confidence}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
