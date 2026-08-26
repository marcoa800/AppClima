import type { WorldPopulationPoint } from '../api'

/** Población mundial con su banda de incertidumbre, en escala logarítmica.
 *
 * Dos decisiones que no son estéticas.
 *
 * **Logarítmica**, porque la serie cubre de 5 millones a 8.000 millones. En
 * escala lineal, los primeros once mil años serían una línea plana pegada al
 * eje y el gráfico contaría que «no pasó nada hasta 1800», que es falso: la
 * población se multiplicó por cien antes de eso.
 *
 * **Banda y no línea**, porque para el año -10000 las estimaciones van de 1 a
 * 10 millones —un factor de diez— y dibujar una línea fina ahí afirmaría una
 * precisión inexistente. La banda se estrecha sola conforme mejora el registro,
 * y esa forma es en sí misma el mensaje.
 */
export function WorldPopulationChart({
  series,
}: {
  series: WorldPopulationPoint[]
}) {
  const puntos = series.filter((p) => p.population_mid > 0)
  if (!puntos.length) return null

  const W = 640
  const H = 190
  const y0 = 1e6
  const y1 = 1e10

  const anioMin = puntos[0].year
  const anioMax = puntos[puntos.length - 1].year
  // Escala temporal comprimida: doce mil años en lineal dejarían todo lo
  // interesante en el último 2% del ancho.
  const tx = (a: number) =>
    (Math.log10(a - anioMin + 1) / Math.log10(anioMax - anioMin + 1)) * W
  const ty = (v: number) =>
    H - ((Math.log10(v) - Math.log10(y0)) / (Math.log10(y1) - Math.log10(y0))) * H

  const arriba = puntos.map((p) => `${tx(p.year)},${ty(p.population_high)}`)
  const abajo = [...puntos].reverse().map((p) => `${tx(p.year)},${ty(p.population_low)}`)

  return (
    <div className="chart-scroll">
      <svg
        width={W}
        height={H + 22}
        role="img"
        aria-label="Población mundial desde el año -10000, con banda de incertidumbre"
      >
        {[1e7, 1e8, 1e9, 1e10].map((v) => (
          <g key={v}>
            <line x1={0} y1={ty(v)} x2={W} y2={ty(v)} stroke="var(--gridline)" />
            <text x={2} y={ty(v) - 3} fontSize={9} fill="var(--text-muted)">
              {v >= 1e9 ? `${v / 1e9} mil M` : `${v / 1e6} M`}
            </text>
          </g>
        ))}
        <polygon
          points={[...arriba, ...abajo].join(' ')}
          fill="var(--series-1)"
          opacity={0.25}
        />
        <polyline
          points={puntos.map((p) => `${tx(p.year)},${ty(p.population_mid)}`).join(' ')}
          fill="none"
          stroke="var(--series-1)"
          strokeWidth={1.5}
        />
        {puntos
          .filter((p) => p.is_anchor)
          .map((p) => (
            <circle
              key={p.year}
              cx={tx(p.year)}
              cy={ty(p.population_mid)}
              r={2}
              fill="var(--series-2)"
            />
          ))}
      </svg>
      <p className="legend">
        Escala logarítmica en los dos ejes · la banda es el rango de estimaciones
        · <span style={{ color: 'var(--series-2)' }}>●</span> años ancla con
        fuente propia
      </p>
    </div>
  )
}
