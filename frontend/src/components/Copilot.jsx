import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { sendChat, uploadAndExtract } from '../store/chatSlice'
import { Icon } from './icons'
import { Pill } from './ui'

const READINESS = {
  not_ready: ['Not ready', 'red'],
  needs_evidence: ['Needs evidence', 'amber'],
  ready_for_review: ['Ready for review', 'green'],
}
const ACTIONS = [
  ['analyze', 'Analyze root cause'],
  ['challenge', 'Challenge the reasoning'],
  ['gaps', 'What is missing?'],
  ['capa', 'Suggest CAPA'],
]
const EXAMPLES = [
  'Atorvastatin API batch ATC260915A failed residual isopropanol at 5,800 ppm (limit 5,000) after tray drying in VTD-204.',
]
const CAN_DO = [
  ['doc', 'Reads PDF, email and text reports and fills the form'],
  ['chat', 'Takes a plain-language description of the incident'],
  ['layers', 'Investigates root cause and challenges the reasoning'],
  ['search', 'Finds the missing evidence'],
  ['shield', 'Recommends CAPA linked to each cause'],
  ['info', 'Answers questions and applies your corrections'],
]

function HealthCard() {
  const h = useSelector((s) => s.investigation.data.health)
  const flash = useSelector((s) => s.investigation.flash.includes('health'))
  const [open, setOpen] = useState(false)
  const warnings = h.warnings || []
  const [label, tone] = READINESS[h.readiness] || READINESS.not_ready
  const hasDetail = !!h.summary || warnings.length > 0
  return (
    <div className={`health ${flash ? 'flash' : ''}`}>
      <div className="health-top">
        <div>
          <div className="eyebrow">Investigation health</div>
          <div className="score">{h.evidence_sufficiency}<small>%</small> <span className="muted small">evidence sufficiency</span></div>
        </div>
        <Pill tone={tone} caps>{label}</Pill>
      </div>
      <div className="bar"><div className={`bar-fill bar-${tone}`} style={{ width: `${h.evidence_sufficiency}%` }} /></div>
      {hasDetail && (
        <button type="button" className="health-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? 'Hide details' : `Details${warnings.length ? ` · ${warnings.length} warning${warnings.length > 1 ? 's' : ''}` : ''}`}
        </button>
      )}
      {open && h.summary && <p className="small body-text">{h.summary}</p>}
      {open && warnings.length > 0 && (
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
          {i === steps.length - 1
            ? <span className="spin" />
            : <span className="check-dot"><Icon name="check" size={11} stroke={3.5} /></span>}
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
  const bodyRef = useRef(null)
  useEffect(() => {
    const el = bodyRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, progress, error])

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
      aria-label="AI copilot"
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); onFile(e.dataTransfer.files?.[0]) }}
    >
      <header className="copilot-head">
        <div className="copilot-title">
          <span className="ai-tile"><Icon name="sparkle" size={18} fill="currentColor" stroke={1.5} /></span>
          <div>
            <h2>AI copilot</h2>
            <p className="muted small">Fills the form, answers questions</p>
          </div>
        </div>
        <div className="copilot-badges">
          {llm && (
            <Pill tone={llm === 'mock' ? 'amber' : 'green'} title={llm === 'mock' ? 'No Groq key: canned responses' : 'Groq model'}>
              {llm === 'mock' ? 'mock AI' : llm}
            </Pill>
          )}
          <span className="badge-ai">AI</span>
        </div>
      </header>

      <div className="copilot-health"><HealthCard /></div>

      <div className="copilot-body" ref={bodyRef}>
        {messages.length === 0 && (
          <div className="empty-chat">
            <p className="empty-title">Start the investigation</p>
            <button type="button" className="example" onClick={() => fileRef.current?.click()}>
              <Icon name="clip" size={16} />Upload an incident report (PDF, .eml, .txt)
            </button>
            {EXAMPLES.map((e) => <button type="button" key={e} className="example" onClick={() => setText(e)}>{e}</button>)}
            <ul className="can-do">
              {CAN_DO.map(([icon, label]) => (
                <li key={label}><span className="can-do-icon"><Icon name={icon} size={14} /></span>{label}</li>
              ))}
            </ul>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg msg-${m.role}`}>
            <div className="bubble">{m.content}</div>
            {m.meta?.changed?.length > 0 && <div className="muted small changed">Updated: {m.meta.changed.filter((p) => !p.startsWith('health')).slice(0, 8).join(', ')}{m.meta.changed.length > 8 ? '…' : ''}</div>}
          </div>
        ))}
        {working && <Progress steps={progress} phase={phase} />}
        {error && <div className="msg-error" role="alert"><Icon name="alert" size={16} />{error}</div>}
      </div>

      <div className="copilot-foot">
        <div className="quick">
          {ACTIONS.map(([a, label]) => (
            <button type="button" key={a} className="chip-btn" disabled={working}
              onClick={() => dispatch(sendChat({ action: a, message: '', userText: label }))}>{label}</button>
          ))}
        </div>
        <div className="composer">
          <input ref={fileRef} type="file" hidden accept=".pdf,.txt,.eml,.md" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = '' }} />
          <button type="button" className="icon-btn" aria-label="Attach a document" title="Upload incident document (PDF, email, text)"
            disabled={working} onClick={() => fileRef.current?.click()}>
            <Icon name="clip" size={16} />
          </button>
          <textarea
            rows={1}
            value={text}
            aria-label="Message the AI copilot"
            placeholder="Describe the incident, or correct a detail…"
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
          />
          <button type="button" className="icon-btn send" aria-label="Send" title="Send" disabled={working || !text.trim()} onClick={submit}>
            <Icon name="send" size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
