import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction } from '../store/investigationSlice'
import { Card, EditableText, Pill } from './ui'

const TONE = { Correction: 'red', Corrective: 'amber', Preventive: 'blue' }

function CapaCard({ c }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const flash = useSelector((s) => s.investigation.flash.includes(`capa.${c.id}`))
  const save = (patch) => dispatch(runAction(() => api.editItem(id, 'capa', c.id, patch)))
  return (
    <div className={`capa ${c.accepted ? 'accepted' : ''} ${flash ? 'flash' : ''}`}>
      <div className="hyp-top">
        <b>{c.id}</b>
        <Pill tone={TONE[c.type]}>{c.type}</Pill>
        {c.linked_hypothesis && <span className="chip" title="Linked root cause hypothesis">→ {c.linked_hypothesis}</span>}
        {c.accepted ? <Pill tone="green">Accepted</Pill> : <Pill tone="amber">AI suggestion · review</Pill>}
      </div>
      <EditableText value={c.action} multiline onSave={(v) => save({ action: v })} className="capa-action" />
      <p className="small"><b>Why:</b> {c.rationale}</p>
      <div className="small"><b>Effectiveness check:</b>{' '}
        <EditableText value={c.effectiveness_check} placeholder="Define how success is measured" onSave={(v) => save({ effectiveness_check: v })} />
      </div>
      <div className="capa-meta">
        <label>Owner <input defaultValue={c.owner || ''} placeholder="Assign owner" onBlur={(e) => e.target.value !== (c.owner || '') && save({ owner: e.target.value })} /></label>
        <label>Due <input type="date" defaultValue={c.due_date || ''} onBlur={(e) => e.target.value !== (c.due_date || '') && save({ due_date: e.target.value })} /></label>
        {!c.accepted && <button className="btn small primary" onClick={() => dispatch(runAction(() => api.accept(id, [`capa.${c.id}`])))}>Accept</button>}
      </div>
    </div>
  )
}

export default function CapaSection() {
  const capa = useSelector((s) => s.investigation.data.capa)
  return (
    <Card title="6 · CAPA plan" subtitle="Each action is linked to a hypothesis. Owners and dates are set by people.">
      {capa.length === 0 ? <p className="empty-note">CAPA recommendations appear after analysis.</p>
        : <div className="stack">{capa.map((c) => <CapaCard key={c.id} c={c} />)}</div>}
    </Card>
  )
}
