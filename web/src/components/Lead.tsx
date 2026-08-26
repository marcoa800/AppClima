import type { Unprecedented } from '../api'

/** El hallazgo principal, con el tamaño que merece.
 *
 * La página tenía veintitrés secciones del mismo peso y ninguna destacaba.
 * Este bloque existe para responder a la pregunta que se hace quien llega y no
 * conoce el proyecto: **¿y esto qué me dice?**
 *
 * Se eligió este dato y no otro por tres razones, en este orden:
 *
 *   1. Es de Perú, que es el foco.
 *   2. Se explica en una frase sin saber estadística.
 *   3. Tiene un control interno que lo sostiene sin depender de ningún modelo
 *      climático externo: si el clima solo fuera más variable, subirían también
 *      los récords de frío. No lo hacen.
 *
 * El número se calcula del dato, nunca se escribe. Un titular con la cifra
 * clavada a mano es exactamente lo que ya caducó tres veces en este proyecto.
 */
export function Lead({ cities }: { cities: Unprecedented[] }) {
  const peru = cities.filter((c) => c.country === 'PE')
  if (!peru.length) return null

  const top = [...peru].sort((a, b) => b.razon_calor - a.razon_calor)[0]
  const mediaMundo =
    cities.reduce((a, c) => a + c.razon_calor, 0) / Math.max(cities.length, 1)
  const mediaFrio =
    cities.reduce((a, c) => a + c.razon_frio, 0) / Math.max(cities.length, 1)
  const porEncima = cities.filter((c) => c.razon_calor >= 1).length

  return (
    <section className="card lead">
      <p className="lead-kicker">Lo que más nos ha sorprendido</p>
      <p className="lead-figure">
        ×{top.razon_calor.toFixed(1)}
      </p>
      <h2 className="lead-title">
        {top.location_name} vive {top.dias_calor_por_anio} días al año para los
        que no tiene precedente
      </h2>
      <p className="lead-body">
        Días que superan <em>todo</em> lo registrado en su misma época del año
        durante los trece anteriores. Cabría esperar{' '}
        <strong>{top.dias_esperados}</strong> en siete años y hay{' '}
        <strong>{top.dias_calor}</strong>.
      </p>
      <p className="lead-body">
        Y no es una rareza local: <strong>{porEncima} de {cities.length}</strong>{' '}
        ciudades del catálogo están por encima de lo esperado. La prueba de que
        es tendencia y no ruido está dentro del propio dato — si el clima solo
        fuera <em>más variable</em>, subirían también los récords de frío. La
        media mundial es <strong>×{mediaMundo.toFixed(1)}</strong> en calor y{' '}
        <strong>×{mediaFrio.toFixed(1)}</strong> en frío.
      </p>
      <p className="lead-links">
        <a href="#sin-precedente">Ver las {cities.length} ciudades →</a>
        <a href="#dengue">Y lo que no pudimos demostrar →</a>
      </p>
    </section>
  )
}
