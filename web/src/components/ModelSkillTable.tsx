import type { ModelSkill, SkillByCut } from '../api'

/** Habilidad medida de cada modelo, con el criterio de publicación a la vista.
 *
 * Tabla y no gráfica, por la misma razón que el contraste del «clima sísmico»:
 * lo que importa es el CONTRASTE entre la mediana y el rango de cortes, y eso
 * son números, no longitudes. Una barra por modelo escondería que el riesgo de
 * calor oscila entre +1,9% y +6,0% según dónde se corte.
 *
 * El estado va con texto además de color: ✓ publicado / ✕ retenido. La
 * identidad nunca depende del color a secas.
 */
export function ModelSkillTable({
  models,
  byCut,
}: {
  models: ModelSkill[]
  byCut: SkillByCut[]
}) {
  // Filtrar también por ámbito, no solo por modelo. El dengue se evalúa por
  // provincia, así que un mismo model_id tiene doce series de cortes: sin el
  // filtro, la línea de un modelo mezclaría doce provincias en doce puntos que
  // parecerían una evolución temporal.
  const cutsFor = (id: string, scope: string) =>
    byCut
      .filter((c) => c.model_id === id && (c.scope === undefined || c.scope === scope))
      .sort((a, b) => a.cut_year - b.cut_year)

  return (
    <div className="chart-scroll">
      <table className="data">
        <thead>
          <tr>
            <th>Modelo</th>
            <th className="num">Cortes</th>
            <th className="num">Mediana</th>
            <th className="num">Peor corte</th>
            <th className="num">Mejor corte</th>
            <th>Por corte</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={`${m.model_id}|${m.scope}`} className={m.should_display ? 'pooled' : undefined}>
              <td>
                {m.model_id.replace(/_/g, ' ')}
                {/* El ámbito deja de ser decorativo desde que el dengue se
                    evalúa por provincia: sin él, doce filas idénticas. */}
                {m.scope !== 'GLOBAL' && (
                  <div className="src-org">{m.scope}</div>
                )}
              </td>
              <td className="num">{m.n_cuts}</td>
              <td className="num" style={{ fontWeight: 600 }}>
                {m.improvement_median > 0 ? '+' : ''}
                {m.improvement_median}%
              </td>
              <td
                className="num"
                style={{
                  color:
                    m.improvement_min <= 0 ? 'var(--hot)' : 'var(--text-secondary)',
                }}
              >
                {m.improvement_min > 0 ? '+' : ''}
                {m.improvement_min}%
              </td>
              <td className="num">
                {m.improvement_max > 0 ? '+' : ''}
                {m.improvement_max}%
              </td>
              <td>
                {/* Minigráfico: un punto por corte temporal. Deja ver de un
                    vistazo si el modelo es estable o depende de dónde cortes. */}
                <svg width={92} height={16} role="img" aria-label="mejora por corte">
                  {cutsFor(m.model_id, m.scope).map((c, i, arr) => {
                    const span = Math.max(
                      ...arr.map((x) => Math.abs(x.improvement_pct)),
                      1,
                    )
                    const x = 6 + (i * 80) / Math.max(arr.length - 1, 1)
                    const y = 8 - (c.improvement_pct / span) * 6
                    return (
                      <circle
                        key={`${c.model_id}|${c.cut_year}`}
                        cx={x}
                        cy={y}
                        r={2.5}
                        fill={
                          c.improvement_pct > 0 ? 'var(--series-1)' : 'var(--hot)'
                        }
                      />
                    )
                  })}
                  <line
                    x1={0}
                    x2={92}
                    y1={8}
                    y2={8}
                    stroke="var(--gridline)"
                    strokeWidth={1}
                  />
                </svg>
              </td>
              <td>
                <span
                  className="pill"
                  style={{
                    color: m.should_display
                      ? 'var(--text-primary)'
                      : 'var(--text-muted)',
                  }}
                >
                  {m.should_display ? '✓ se publica' : '✕ retenido'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
