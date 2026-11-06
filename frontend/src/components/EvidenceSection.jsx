import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction } from '../store/investigationSlice'
import { Card, EditableText, Pill } from './ui'

const SRC = { document: 'document', chat: 'chat', ai_inference: 'AI', user: 'you' }
const PRIO = { high: 'red', medium: 'amber', low: 'neutral' }

export default function EvidenceSection() {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const { evidence, gaps } = useSelector((s) => s.investigation.data)
  const flash = useSelector((s) => s.investigation.flash)
  const open = gaps.filter((g) => !g.resolved)
  const done = gaps.filter((g) => g.resolved)
  return (
    <Card title="5 · Evidence & missing information" subtitle="What supports the investigation, and what is still needed.">
      <div className="two-col">
        <div>
          <h4>Evidence on file ({evidence.length})</h4>
          {evidence.length === 0 && <p className="empty-note">None logged yet.</p>}
          <ul className="list">
            {evidence.map((e) => (
              <li key={e.id} className={flash.includes(`evidence.${e.id}`) ? 'flash' : ''}>
                <b>{e.id}</b> <span className="muted small">({SRC[e.source]})</span>
                <EditableText value={e.description} multiline onSave={(v) => dispatch(runAction(() => api.editItem(id, 'evidence', e.id, { description: v })))} />
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Gap radar ({open.length} open)</h4>
          {gaps.length === 0 && <p className="empty-note">Run the analysis to see what is missing.</p>}
          <ul className="list">
            {open.map((g) => (
              <li key={g.id} className={flash.includes(`gaps.${g.id}`) ? 'flash' : ''}>
                <div className="gap-top">
                  <Pill tone={PRIO[g.priority]}>{g.priority}</Pill>
                  {g.related_hypothesis && <span className="chip">{g.related_hypothesis}</span>}
                </div>
                <div>{g.item}</div>
                <p className="muted small">{g.why_needed}</p>
              </li>
            ))}
            {done.map((g) => (
              <li key={g.id} className={`resolved ${flash.includes(`gaps.${g.id}`) ? 'flash' : ''}`}>
                <span className="tick">✓</span> {g.item}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p className="muted small hint">Tip: tell the copilot what you found (e.g. “the PM record shows it was 3 weeks overdue”) and the gap closes.</p>
    </Card>
  )
}
