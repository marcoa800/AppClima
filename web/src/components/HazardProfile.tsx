import type { HazardCity } from '../api'

/** Perfil de peligro por ciudad: cuatro dimensiones sin promediar.
 *
 * El diseño tiene una restricción que viene del modelo, no de la estética: la
 * tabla NO puede ordenarse por un total, porque no hay total. Sumar las cuatro
 * dimensiones exigiría pesos que nadie puede defender, y el orden resultante se
 * usaría para decidir cosas.
 *
 * Se ordena por "cuántas dimensiones están en el cuartil alto", que es un
 * recuento y no una ponderación: dice en cuántos frentes destaca una ciudad,
 * sin afirmar que un ciclón valga más o menos que un sismo.
 *
 * Las barras son cuatro carriles independientes, deliberadamente separados y
 * sin apilar. Apiladas sugerirían un total; una al lado de otra no.
 *
 * Un hueco no es un cero: las ciudades sin veinte años de archivo no tienen
 * dimensiones de calor y se marcan con un guion, nunca con una barra vacía.
 */

const CARRIL = 46

function Carril({
  pct,
  color,
  etiqueta,
}: {
  pct: number | null
  color: string
  etiqueta: string
}) {
  if (pct == null) {
    return (
      <span
        className="amp-num"
        style={{ width: CARRIL, display: 'inline-block', color: 'var(--text-muted)' }}
        title={`${etiqueta}: sin datos suficientes`}
      >
        —
      </span>
    )
  }
  const alto = pct >= 75
  // La barra sola no vale: es SVG sin texto, así que quien no la vea no obtiene
  // nada. El número va al lado, como en la tabla de umbrales de calor.
  return (
    <span className="amp-row">
      <svg
        width={CARRIL}
        height={12}
        role="img"
        aria-label={`${etiqueta}: percentil ${pct}`}
      >
        <rect x={0} y={4} width={CARRIL} height={4} rx={2} fill="var(--gridline)" />
        <rect
          x={0}
          y={3}
          width={Math.max(2, (pct / 100) * CARRIL)}
          height={6}
          rx={3}
          fill={alto ? color : 'var(--neutral)'}
        />
      </svg>
      <span
        className="amp-num"
        style={{ color: alto ? 'var(--text-primary)' : 'var(--text-muted)' }}
      >
        {pct}
      </span>
    </span>
  )
}

export function HazardProfile({
  cities,
  soloPeru,
}: {
  cities: HazardCity[]
  soloPeru: boolean
}) {
  // Los percentiles vienen calculados sobre las 66 ciudades y NO se recalculan
  // al filtrar. Un percentil 86 sigue significando "de las más expuestas del
  // catálogo": recalcularlo dentro de Perú diría algo completamente distinto
  // con el mismo aspecto.
  const base = soloPeru ? cities.filter((c) => c.country === 'PE') : cities
  const destacadas = base
    .filter((c) => c.dimensiones_en_cuartil_alto > 0 || soloPeru)
    .slice(0, soloPeru ? 20 : 24)

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Ciudad</th>
            <th>Ciclones</th>
            <th>Sismos</th>
            <th>Calor</th>
            <th>Sin precedente</th>
            <th className="num">Frentes</th>
            <th className="num">Detalle</th>
          </tr>
        </thead>
        <tbody>
          {destacadas.map((c) => (
            <tr key={c.location_id} className={c.dimensiones_en_cuartil_alto >= 3 ? 'pooled' : undefined}>
              <td>
                {c.location_name}
                <div className="src-org">
                  {c.country} · Köppen {c.koppen}
                </div>
              </td>
              <td>
                <Carril pct={c.pct_ciclones} color="var(--series-2)" etiqueta="Ciclones" />
              </td>
              <td>
                <Carril pct={c.pct_sismos} color="var(--series-3)" etiqueta="Sismos" />
              </td>
              <td>
                <Carril pct={c.pct_calor} color="var(--hot)" etiqueta="Calor" />
              </td>
              <td>
                <Carril
                  pct={c.pct_sin_precedente}
                  color="var(--warning)"
                  etiqueta="Días sin precedente"
                />
              </td>
              <td className="num">
                <strong>{c.dimensiones_en_cuartil_alto}</strong>
                <span style={{ color: 'var(--text-muted)' }}>
                  {' '}
                  / {c.dimensiones_disponibles}
                </span>
              </td>
              <td className="num" style={{ color: 'var(--text-secondary)' }}>
                {c.ciclones_200km > 0 && `${c.ciclones_200km} ciclones`}
                <div className="src-org">
                  {c.sismos_m5 > 0 && `${c.sismos_m5} sismos M5+`}
                  {c.magnitud_max != null && ` · máx M${c.magnitud_max}`}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
