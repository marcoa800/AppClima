/** Índice de secciones, con el tipo de cada una a la vista.
 *
 * La página mide más de treinta mil píxeles y tiene veintitrés secciones que
 * pesan exactamente lo mismo. El problema no es la longitud —un trabajo de
 * análisis es largo— sino que sin jerarquía **ninguna destaca**, y quien entra
 * no sabe si está mirando un hallazgo sólido o una hipótesis que se cayó.
 *
 * Por eso el índice no es solo navegación: cada entrada dice qué tipo de cosa
 * es. Esa distinción es la tesis del proyecto —publicar los nulos con la misma
 * seriedad que los hallazgos— y hasta ahora vivía solo en el texto.
 *
 * El tipo va con palabra además de con color: nunca solo color.
 */

export type Tipo = 'hallazgo' | 'nulo' | 'metodo' | 'catalogo'

export type Entrada = { id: string; titulo: string; tipo: Tipo }

const ETIQUETA: Record<Tipo, string> = {
  hallazgo: 'hallazgo',
  nulo: 'nulo',
  metodo: 'método',
  catalogo: 'catálogo',
}

const COLOR: Record<Tipo, string> = {
  hallazgo: 'var(--good)',
  nulo: 'var(--warning)',
  metodo: 'var(--series-2)',
  catalogo: 'var(--text-muted)',
}

export function SectionIndex({ entradas }: { entradas: Entrada[] }) {
  const porTipo = (t: Tipo) => entradas.filter((e) => e.tipo === t)

  return (
    <nav className="card" aria-label="Índice de secciones">
      <h2>Qué hay aquí</h2>
      <p className="note">
        {porTipo('hallazgo').length} hallazgos que sobrevivieron al contraste,{' '}
        {porTipo('nulo').length} hipótesis que no, y{' '}
        {porTipo('metodo').length + porTipo('catalogo').length} secciones de
        método y catálogo. Los nulos no están escondidos al final: van en su
        sitio, porque demuestran que lo demás pasó el mismo filtro.
      </p>
      <ul className="indice">
        {entradas.map((e) => (
          <li key={e.id}>
            <a href={`#${e.id}`}>{e.titulo}</a>
            <span className="pill" style={{ color: COLOR[e.tipo] }}>
              {ETIQUETA[e.tipo]}
            </span>
          </li>
        ))}
      </ul>
    </nav>
  )
}
