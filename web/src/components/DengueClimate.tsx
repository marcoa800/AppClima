import type { DengueLag, DengueProvince, DengueSkill } from '../api'

/** Dengue y clima en Perú: una investigación cuyo resultado es "no se puede".
 *
 * El reto de diseño aquí no es enseñar un hallazgo sino enseñar su AUSENCIA sin
 * que parezca que faltan datos. Por eso la tabla de habilidad va primero y con
 * las dos líneas base enfrentadas: la cifra contra la climatología es buena
 * —hasta +22,9%— y la de al lado, contra la persistencia, es catastrófica. Ver
 * las dos juntas es el argumento entero, y separarlas sería propaganda.
 *
 * La columna de correlación se muestra junto a su umbral corregido, nunca
 * sola: una r de 0,65 no significa nada sin saber que el umbral exigible con
 * esa autocorrelación es 0,51.
 */
export function DengueClimate({
  provincias,
  retardos,
  habilidad,
}: {
  provincias: DengueProvince[]
  retardos: DengueLag[]
  habilidad: DengueSkill[]
}) {
  // El mejor retardo de cada provincia, que es lo que se compara.
  const mejorPorProvincia = new Map<string, DengueLag>()
  for (const r of retardos) {
    if (r.r_temp == null) continue
    const previo = mejorPorProvincia.get(r.provincia)
    if (!previo || Math.abs(r.r_temp) > Math.abs(previo.r_temp ?? 0)) {
      mejorPorProvincia.set(r.provincia, r)
    }
  }

  const porProvincia = new Map<string, { clim?: DengueSkill; pers?: DengueSkill }>()
  for (const h of habilidad) {
    const fila = porProvincia.get(h.provincia) ?? {}
    if (h.model_id.endsWith('climatologia')) fila.clim = h
    else fila.pers = h
    porProvincia.set(h.provincia, fila)
  }

  const filas = provincias
    .filter((p) => porProvincia.has(p.provincia))
    .sort((a, b) => b.casos_total - a.casos_total)

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Provincia</th>
            <th className="num">Casos</th>
            <th className="num">Temp.</th>
            <th>Transmisión</th>
            <th className="num">Mejor r</th>
            <th className="num">Umbral exigible</th>
            <th className="num">vs climatología</th>
            <th className="num">vs persistencia</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((p) => {
            const mejor = mejorPorProvincia.get(p.provincia)
            const sk = porProvincia.get(p.provincia)
            const pasaUmbral =
              mejor?.r_temp != null &&
              Math.abs(mejor.r_temp) > mejor.r_umbral_bonferroni
            return (
              <tr key={p.location_id}>
                <td>
                  {p.provincia}
                  <div className="src-org">{p.departamento}</div>
                </td>
                <td className="num">{p.casos_total.toLocaleString('es')}</td>
                <td className="num">{p.temp_media_c ?? '—'} °C</td>
                <td>
                  <span className="pill">{p.transmision}</span>
                  <div className="src-org">
                    {p.pct_semanas_con_casos}% de las semanas
                  </div>
                </td>
                <td className="num">
                  {mejor?.r_temp != null ? (
                    <>
                      <strong
                        style={{
                          color: pasaUmbral
                            ? 'var(--text-primary)'
                            : 'var(--text-muted)',
                        }}
                      >
                        {mejor.r_temp.toFixed(2)}
                      </strong>
                      <div className="src-org">
                        retardo {mejor.lag_semanas} sem
                        {mejor.lag_plausible ? ' ✓' : ''}
                      </div>
                    </>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="num" style={{ color: 'var(--text-muted)' }}>
                  {mejor ? mejor.r_umbral_bonferroni.toFixed(2) : '—'}
                  <div className="src-org">n ef. {mejor?.n_efectivo ?? '—'}</div>
                </td>
                <td className="num" style={{ color: 'var(--good)' }}>
                  {sk?.clim ? `${sk.clim.improvement_median > 0 ? '+' : ''}${sk.clim.improvement_median}%` : '—'}
                </td>
                <td className="num">
                  <strong style={{ color: 'var(--critical)' }}>
                    {sk?.pers ? `${sk.pers.improvement_median}%` : '—'}
                  </strong>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
