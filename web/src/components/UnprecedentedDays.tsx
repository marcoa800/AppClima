import type { Unprecedented } from '../api'

/** Días sin precedente por ciudad, contra lo que cabría esperar.
 *
 * La decisión de diseño está en qué se pone en el centro. Lo intuitivo sería
 * destacar el recuento de días —177 en Chulucanas suena mucho— pero ese número
 * solo, sin la expectativa al lado, no significa nada: los récords se vuelven
 * más raros con el tiempo aunque el clima no cambie.
 *
 * Así que la columna ancha es la RAZÓN, y el gráfico enfrenta calor contra
 * frío en la misma escala. Esa comparación es la prueba entera: si el clima
 * solo fuera más variable, las dos barras crecerían juntas.
 *
 * La barra de frío se dibuja hacia la izquierda desde un eje central, no
 * apilada, para que "más frío del esperado" y "más calor del esperado" no se
 * puedan confundir con un total.
 */

const ANCHO = 132
const MEDIO = ANCHO / 2

export function UnprecedentedDays({
  cities,
  soloPeru,
}: {
  cities: Unprecedented[]
  soloPeru: boolean
}) {
  // La escala se calcula SIEMPRE sobre el catálogo completo, aunque se muestre
  // solo Perú. Si se recalculara con las filas visibles, al filtrar cambiarían
  // las longitudes de las barras y una ciudad parecería más extrema por haber
  // quitado otras: el gráfico contaría algo distinto según el filtro.
  const maxRazon = Math.max(
    ...cities.map((c) => Math.max(c.razon_calor, c.razon_frio)),
    1,
  )
  const visibles = soloPeru ? cities.filter((c) => c.country === 'PE') : cities

  // La referencia global es lo que convierte un número en un hallazgo: ×12,73
  // no dice nada hasta saber que la media del mundo es ×3,95.
  const mediaMundo =
    cities.reduce((a, c) => a + c.razon_calor, 0) / Math.max(cities.length, 1)
  const escala = (r: number) => Math.max(1, (r / maxRazon) * MEDIO)

  return (
    <div className="chart-scroll">
      {soloPeru && (
        <p className="legend">
          {visibles.length} provincias del Perú de {cities.length} ciudades del
          catálogo · media mundial en calor{' '}
          <strong>×{mediaMundo.toFixed(2)}</strong>
        </p>
      )}
      <table className="data">
        <thead>
          <tr>
            <th>Ciudad</th>
            <th className="num">Esperados</th>
            <th className="num">Calor</th>
            <th className="num">Frío</th>
            <th>
              Frío ← → Calor{' '}
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                (veces lo esperado)
              </span>
            </th>
            <th className="num">Días/año</th>
          </tr>
        </thead>
        <tbody>
          {visibles.map((c) => {
            const domina = c.razon_calor > 3 * c.razon_frio
            const inverso = c.razon_frio > c.razon_calor
            return (
              <tr key={c.location_id} className={domina ? 'pooled' : undefined}>
                <td>
                  {c.location_name}
                  <div className="src-org">
                    {c.country} · Köppen {c.koppen}
                  </div>
                </td>
                <td className="num" style={{ color: 'var(--text-muted)' }}>
                  {c.dias_esperados}
                </td>
                <td className="num">
                  <strong style={{ color: 'var(--hot)' }}>{c.dias_calor}</strong>
                </td>
                <td className="num" style={{ color: 'var(--cold)' }}>
                  {c.dias_frio}
                </td>
                <td>
                  <span className="amp-row">
                    <svg
                      width={ANCHO}
                      height={14}
                      role="img"
                      aria-label={`Calor ${c.razon_calor} veces lo esperado, frío ${c.razon_frio}`}
                    >
                      {/* Eje: la referencia visual de "lo normal" es el centro */}
                      <line
                        x1={MEDIO}
                        y1={0}
                        x2={MEDIO}
                        y2={14}
                        stroke="var(--gridline)"
                      />
                      <rect
                        x={MEDIO - escala(c.razon_frio)}
                        y={4}
                        width={escala(c.razon_frio)}
                        height={6}
                        fill="var(--cold)"
                      />
                      <rect
                        x={MEDIO}
                        y={4}
                        width={escala(c.razon_calor)}
                        height={6}
                        fill="var(--hot)"
                      />
                    </svg>
                    <span className="amp-num">×{c.razon_calor}</span>
                  </span>
                </td>
                <td className="num">
                  {c.dias_calor_por_anio}
                  {inverso && (
                    <div className="src-org" style={{ color: 'var(--cold)' }}>
                      domina el frío
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
