import type { DataSource } from '../api'

/** Atribución de fuentes. No es cortesía: es obligación de licencia.
 *
 * Se renderiza desde el catálogo de la API y no escrito a mano, para que no se
 * quede obsoleto la primera vez que se añada una fuente.
 */
export function Attribution({
  sources,
  avisoComercial,
  citaIncompleta,
}: {
  sources: DataSource[]
  avisoComercial: string
  citaIncompleta: string
}) {
  return (
    <>
      <div className="chart-scroll">
        <table className="data">
          <thead>
            <tr>
              <th>Fuente</th>
              <th>Licencia</th>
              <th>Uso comercial</th>
              <th>Qué aporta</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id}>
                <td>
                  <a href={s.url} target="_blank" rel="noreferrer noopener">
                    {s.name}
                  </a>
                  <div className="src-org">{s.organization}</div>
                </td>
                <td>{s.license}</td>
                <td>
                  <span
                    className="pill"
                    style={{
                      color:
                        s.commercial_use === 'permitido'
                          ? 'var(--text-muted)'
                          : 'var(--text-primary)',
                    }}
                  >
                    {s.commercial_use}
                  </span>
                </td>
                <td className="src-use">{s.what_we_use}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="citations">
        <h4>Citas</h4>
        {sources
          .filter((s) => s.attribution_required)
          .map((s) => (
            <p key={s.id} className="citation">
              {s.citation}
            </p>
          ))}
      </div>

      <p className="caveat">
        <strong>Uso comercial:</strong> {avisoComercial}
      </p>
      <p className="caveat">
        <strong>Cita incompleta:</strong> {citaIncompleta}
      </p>
    </>
  )
}
