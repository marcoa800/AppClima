import type { ReactNode } from 'react'

export type TooltipState = {
  x: number
  y: number
  title: string
  rows: string[]
} | null

/** Tooltip posicionado en coordenadas de viewport (position: fixed).
 *
 * Se desplaza para no salirse por el borde derecho: un tooltip cortado en el
 * último punto de la serie es justo donde más molesta.
 */
export function Tooltip({ state }: { state: TooltipState }): ReactNode {
  if (!state) return null

  const flipLeft = state.x > window.innerWidth - 260
  const style = {
    left: flipLeft ? undefined : state.x + 14,
    right: flipLeft ? window.innerWidth - state.x + 14 : undefined,
    top: Math.min(state.y + 12, window.innerHeight - 120),
  }

  return (
    <div className="tooltip" style={style} role="tooltip">
      <div className="tt-title">{state.title}</div>
      {state.rows.map((row, i) => (
        <div className="tt-row" key={i}>
          {row}
        </div>
      ))}
    </div>
  )
}
