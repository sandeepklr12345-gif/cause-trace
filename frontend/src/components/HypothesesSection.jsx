import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction } from '../store/investigationSlice'
import { Card, EditableText, Pill } from './ui'

const TONE = { suggested: 'amber', supported: 'blue', confirmed: 'green', rejected: 'neutral' }
const NAME_KEY = 'causetrace.reviewer'

function EvidenceChips({ ids, evidence, kind }) {
  if (!ids.length) return null
  return (
    <div className="chips">
      <span className="muted small">{kind === 'for' ? 'Supports:' : 'Argues against:'}</span>
      {ids.map((i) => {
        const e = evidence.find((x) => x.id === i)
        return <span key={i} className={`chip chip-${kind}`} title={e?.description}>{i}</span>
      })}
    </div>
  )
}

function Confirm({ hid }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(() => { try { return localStorage.getItem(NAME_KEY) || '' } catch { return '' } })
  if (!open) return <button type="button" className="btn small primary" onClick={() => setOpen(true)}>Confirm as root cause</button>
  const go = () => {
    if (!name.trim()) return
    try { localStorage.setItem(NAME_KEY, name) } catch { /* storage unavailable */ }
    dispatch(runAction(() => api.confirm(id, hid, name)))
  }
  return (
    <span className="confirm-inline">
      <input autoFocus placeholder="Your name & role (QA)" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && go()} />
      <button type="button" className="btn small primary" onClick={go} disabled={!name.trim()}>Sign off</button>
      <button type="button" className="btn small" onClick={() => setOpen(false)}>Cancel</button>
    </span>
  )
}

function Hyp({ h }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const evidence = useSelector((s) => s.investigation.data.evidence)
  const flash = useSelector((s) => s.investigation.flash.includes(`hypotheses.${h.id}`))
  return (
    <div className={`hyp hyp-${h.status} ${flash ? 'flash' : ''}`}>
      <div className="hyp-top">
        <div className="hyp-tags">
          <span className="tag-id">{h.id} · {h.category}</span>
          <span className="muted small">confidence: {h.confidence}</span>
        </div>
        <Pill tone={TONE[h.status]} caps title={h.status === 'confirmed' ? `Signed off by ${h.confirmed_by}` : 'Only a qualified person can confirm'}>
          {h.status === 'confirmed' ? `Confirmed · ${h.confirmed_by}` : h.status}
        </Pill>
      </div>
      <EditableText value={h.statement} multiline className="hyp-statement"
        onSave={(v) => dispatch(runAction(() => api.editItem(id, 'hypotheses', h.id, { statement: v })))} />
      {h.rationale && <p className="body-text">{h.rationale}</p>}
      <EvidenceChips ids={h.evidence_for} evidence={evidence} kind="for" />
      <EvidenceChips ids={h.evidence_against} evidence={evidence} kind="against" />
      {h.status !== 'rejected' && h.status !== 'confirmed' && (
        <div className="row-actions">
          <button type="button" className="btn small" onClick={() => dispatch(runAction(() => api.reject(id, h.id)))}>Reject</button>
          <Confirm hid={h.id} />
        </div>
      )}
      {h.status === 'suggested' && !h.evidence_for.length && (
        <p className="warn small">No supporting evidence yet — this stays a suggestion.</p>
      )}
    </div>
  )
}

export default function HypothesesSection() {
  const hyps = useSelector((s) => s.investigation.data.hypotheses)
  return (
    <Card id="sec-hypotheses" title="Root cause hypotheses and evidence" subtitle="AI proposes and links evidence. A person confirms."
      icon="layers" tone="amber">
      {hyps.length === 0
        ? <p className="empty-note">No hypotheses yet.</p>
        : <div className="stack">{hyps.map((h) => <Hyp key={h.id} h={h} />)}</div>}
    </Card>
  )
}
