import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction } from '../store/investigationSlice'
import { Card, EditableText, Pill } from './ui'

const TONE = { Correction: 'amber', Corrective: 'green', Preventive: 'blue' }

function CapaCard({ c }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const flash = useSelector((s) => s.investigation.flash.includes(`capa.${c.id}`))
  const save = (patch) => dispatch(runAction(() => api.editItem(id, 'capa', c.id, patch)))
  return (
    <div className={`capa ${c.accepted ? 'accepted' : 'pending'} ${flash ? 'flash' : ''}`}>
      <div className="hyp-top">
        <div className="hyp-tags">
          <span className="tag-id">{c.id}</span>
          <Pill tone={TONE[c.type]} caps>{c.type}</Pill>
          {c.linked_hypothesis && <span className="chip chip-blue" title="Linked root cause hypothesis">Linked to {c.linked_hypothesis}</span>}
        </div>
        {c.accepted ? <Pill tone="green">Accepted</Pill> : <Pill tone="amber">AI suggestion · review</Pill>}
      </div>
      <EditableText value={c.action} multiline onSave={(v) => save({ action: v })} className="capa-action" />
      <p className="body-text"><b>Why:</b> {c.rationale}</p>
      <div className="capa-check">
        <span className="eyebrow">Effectiveness check</span>
        <EditableText value={c.effectiveness_check} placeholder="Define how success is measured" onSave={(v) => save({ effectiveness_check: v })} />
      </div>
      <div className="capa-meta">
        <label>Owner <input defaultValue={c.owner || ''} placeholder="Assign owner" onBlur={(e) => e.target.value !== (c.owner || '') && save({ owner: e.target.value })} /></label>
        <label>Due <input type="date" defaultValue={c.due_date || ''} onBlur={(e) => e.target.value !== (c.due_date || '') && save({ due_date: e.target.value })} /></label>
        {!c.accepted && <button type="button" className="btn small primary" onClick={() => dispatch(runAction(() => api.accept(id, [`capa.${c.id}`])))}>Accept</button>}
      </div>
    </div>
  )
}

export default function CapaSection() {
  const capa = useSelector((s) => s.investigation.data.capa)
  return (
    <Card id="sec-capa" title="CAPA plan" subtitle="Each action is linked to a hypothesis. Owners and dates are set by people."
      icon="shield" tone="green">
      {capa.length === 0 ? <p className="empty-note">CAPA recommendations appear after analysis.</p>
        : <div className="stack">{capa.map((c) => <CapaCard key={c.id} c={c} />)}</div>}
    </Card>
  )
}
