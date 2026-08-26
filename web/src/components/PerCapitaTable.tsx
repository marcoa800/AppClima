import type { PerCapitaEvent } from '../api'

/** Catástrofes normalizadas por la población que había cuando ocurrieron.
 *
 * Toda la tabla existe para corregir un sesgo que las cifras absolutas producen
 * siempre y en la misma dirección: parecen más letales los desastres recientes,
 * porque había más gente disponible para morir.
 *
 * Por eso la columna que manda es «1 de cada N», y no el recuento de muertes.
 * Es la forma más directa de decirlo: en la peste negra murió una de cada tres
 * personas del planeta.
 *
 * Las muertes absolutas se conservan al lado, en gris, precisamente para que se
 * vea el contraste — quitarlas escondería el argumento en vez de demostrarlo.
 */
export function PerCapitaTable({ events }: { events: PerCapitaEvent[] }) {
  const maxPct = Math.max(...events.map((e) => e.pct_of_humanity), 0.01)
  const familia: Record<string, string> = {
    epidemic: 'epidemia',
    earthquake: 'terremoto',
    volcano: 'volcán',
    tsunami: 'tsunami',
    flood: 'inundación',
    cyclone: 'ciclón',
  }

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Suceso</th>
            <th className="num">Año</th>
            <th className="num">Muertes</th>
            <th className="num">Humanidad viva</th>
            <th>% de la humanidad</th>
            <th className="num">1 de cada</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr
              key={`${e.event_name}|${e.year}`}
              className={e.pct_of_humanity >= 5 ? 'pooled' : undefined}
            >
              <td>
                {e.event_name}
                <div className="src-org">
                  {familia[e.family] ?? e.family}
                  {e.subtype ? ` · ${e.subtype}` : ''}
                </div>
              </td>
              <td className="num">
                {e.year < 0 ? `${-e.year} a.C.` : e.year}
              </td>
              <td className="num" style={{ color: 'var(--text-muted)' }}>
                {(e.deaths_representative / 1e6).toFixed(1)} M
              </td>
              <td className="num" style={{ color: 'var(--text-muted)' }}>
                {(e.world_population / 1e6).toFixed(0)} M
              </td>
              <td>
                <span className="amp-row">
                  <svg
                    width={84}
                    height={12}
                    role="img"
                    aria-label={`${e.pct_of_humanity}% de la humanidad`}
                  >
                    <rect
                      x={0}
                      y={3}
                      width={Math.max(2, (e.pct_of_humanity / maxPct) * 84)}
                      height={6}
                      rx={3}
                      fill={
                        e.pct_of_humanity >= 5 ? 'var(--critical)' : 'var(--series-1)'
                      }
                    />
                  </svg>
                  <span className="amp-num">
                    {/* La fuente trae precisión variable —36,15 junto a
                        24,8756— y mezclarlas sugiere que unas cifras se conocen
                        mejor que otras. No es el caso: son todas estimaciones. */}
                    {e.pct_of_humanity >= 1
                      ? e.pct_of_humanity.toFixed(1)
                      : e.pct_of_humanity.toFixed(2)}
                    %
                  </span>
                </span>
              </td>
              <td className="num">
                {e.one_in_every != null ? (
                  <strong>{e.one_in_every.toLocaleString('es')}</strong>
                ) : (
                  '—'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
