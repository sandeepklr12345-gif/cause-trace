import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { sendChat, uploadAndExtract } from '../store/chatSlice'
import { Pill } from './ui'

const READINESS = {
  not_ready: ['Not ready', 'red'],
  needs_evidence: ['Needs evidence', 'amber'],
  ready_for_review: ['Ready for review', 'green'],
}
const ACTIONS = [
  ['analyze', 'Analyze root cause'],
  ['challenge', 'Challenge the reasoning'],
  ['gaps', "What's missing?"],
  ['capa', 'Suggest CAPA'],
]
const EXAMPLES = [
  'Atorvastatin API batch ATC260915A failed residual isopropanol at 5,800 ppm (limit 5,000) after tray drying in VTD-204.',
]

function HealthCard() {
  const h = useSelector((s) => s.investigation.data.health)
  const flash = useSelector((s) => s.investigation.flash.includes('health'))
  const warnings = h.warnings || []
  const [label, tone] = READINESS[h.readiness] || READINESS.not_ready
  return (
    <div className={`health ${flash ? 'flash' : ''}`}>
      <div className="health-top">
        <div>
          <div className="eyebrow">Investigation health</div>
          <div className="score">{h.evidence_sufficiency}<small>%</small> <span className="muted small">evidence sufficiency</span></div>
        </div>
        <Pill tone={tone}>{label}</Pill>
      </div>
      <div className="bar"><div className={`bar-fill bar-${tone}`} style={{ width: `${h.evidence_sufficiency}%` }} /></div>
      {h.summary && <p className="small">{h.summary}</p>}
      {warnings.length > 0 && (
        <ul className="warnings">{warnings.map((w, i) => <li key={i}>⚠ {w}</li>)}</ul>
      )}
    </div>
  )
}

function Progress({ steps, phase }) {
  return (
    <div className="progress">
      {phase && <div className="step active"><span className="spin" />{phase}</div>}
      {steps.map((s, i) => (
        <div key={i} className={`step ${i === steps.length - 1 ? 'active' : 'done'}`}>
          {i === steps.length - 1 ? <span className="spin" /> : <span className="tick">✓</span>}
          {s.label}
        </div>
      ))}
    </div>
  )
}

export default function Copilot() {
  const dispatch = useDispatch()
  const { messages, busy, progress, error, phase } = useSelector((s) => s.chat)
  const llm = useSelector((s) => s.investigation.llm)
  const [text, setText] = useState('')
  const [drag, setDrag] = useState(false)
  const fileRef = useRef(null)
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, progress, error])

  const working = busy || !!phase
  const submit = () => {
    const message = text.trim()
    if (!message || working) return
    setText('')
    dispatch(sendChat({ message, userText: message }))
  }
  const onFile = (file) => { if (file && !working) dispatch(uploadAndExtract(file)) }

  return (
    <aside
      className={`copilot ${drag ? 'drag' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); onFile(e.dataTransfer.files?.[0]) }}
    >
      <header className="copilot-head">
        <div>
          <h2>CauseTrace Copilot</h2>
          <p className="muted small">Describe the incident, drop a report (PDF / email / text), or correct a detail. The form fills itself.</p>
        </div>
        {llm && <Pill tone={llm === 'mock' ? 'amber' : 'green'} title={llm === 'mock' ? 'No Groq key: canned responses' : 'Groq model'}>{llm === 'mock' ? 'mock AI' : llm}</Pill>}
      </header>

      <HealthCard />

      <div className="chat">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>Start with one of these:</p>
            <button className="example" onClick={() => fileRef.current?.click()}>📎 Upload an incident report (PDF, .eml, .txt)</button>
            {EXAMPLES.map((e) => <button key={e} className="example" onClick={() => setText(e)}>{e}</button>)}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <div className="bubble">{m.content}</div>
            {m.meta?.changed?.length > 0 && <div className="muted small changed">Updated: {m.meta.changed.filter((p) => !p.startsWith('health')).slice(0, 8).join(', ')}{m.meta.changed.length > 8 ? '…' : ''}</div>}
          </div>
        ))}
        {working && <Progress steps={progress} phase={phase} />}
        {error && <div className="msg msg-error">⚠ {error}</div>}
        <div ref={endRef} />
      </div>

      <div className="quick">
        {ACTIONS.map(([a, label]) => (
          <button key={a} className="chip-btn" disabled={working}
            onClick={() => dispatch(sendChat({ action: a, message: '', userText: label }))}>{label}</button>
        ))}
      </div>

      <div className="composer">
        <input ref={fileRef} type="file" hidden accept=".pdf,.txt,.eml,.md" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = '' }} />
        <button className="icon-btn big" title="Upload incident document" disabled={working} onClick={() => fileRef.current?.click()}>📎</button>
        <textarea
          rows={2}
          value={text}
          placeholder="e.g. “Sorry, the batch number is X and the affected quantity is 50 kg”"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
        />
        <button className="btn primary" disabled={working || !text.trim()} onClick={submit}>Send</button>
      </div>
    </aside>
  )
}
