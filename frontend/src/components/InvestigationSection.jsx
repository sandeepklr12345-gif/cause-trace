import { useState } from 'react'
import { useSelector } from 'react-redux'
import { Card, Pill } from './ui'

const CATS = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
const STATUS_TONE = { suggested: 'amber', supported: 'blue', confirmed: 'green', rejected: 'neutral' }

function WhyChain({ steps, flash }) {
  if (!steps.length) return <p className="empty-note">Run the analysis and the 5 Whys chain will appear here.</p>
  return (
    <ol className={`whys ${flash ? 'flash' : ''}`}>
      {steps.map((s) => (
        <li key={s.level}>
          <div className="why-q"><span className="why-n">{s.level}</span>{s.question}</div>
          <div className="why-a">{s.answer}</div>
          <div className="chips">
            {s.evidence_refs?.length > 0
              ? s.evidence_refs.map((e) => <span key={e} className="chip chip-for" title="Evidence behind this step">{e}</span>)
              : <Pill tone="amber" title="No evidence on file backs this step yet">Not yet evidenced</Pill>}
            {s.critic_note && <Pill tone="blue" title="The critic pass changed this step">Critic: {s.critic_note}</Pill>}
          </div>
        </li>
      ))}
    </ol>
  )
}

function Fishbone({ hypotheses, effect }) {
  const by = (c) => hypotheses.filter((h) => h.category === c && h.status !== 'rejected')
  const box = (c) => (
    <div className="fb-cat" key={c}>
      <div className="fb-title">{c}</div>
      {by(c).length === 0 && <div className="muted small">No hypothesis</div>}
      {by(c).map((h) => (
        <div className="fb-item" key={h.id} title={h.rationale || ''}>
          <span className={`dot dot-${STATUS_TONE[h.status]}`} />
          <b>{h.id}</b> {h.statement}
        </div>
      ))}
    </div>
  )
  return (
    <div className="fishbone">
      <div className="fb-row">{CATS.slice(0, 3).map(box)}</div>
      <div className="fb-spine"><div className="fb-line" /><div className="fb-head">{effect || 'Deviation'}</div></div>
      <div className="fb-row">{CATS.slice(3).map(box)}</div>
    </div>
  )
}

export default function InvestigationSection() {
  const data = useSelector((s) => s.investigation.data)
  const flash = useSelector((s) => s.investigation.flash)
  const [view, setView] = useState('whys')
  return (
    <Card
      title="3 · Investigation"
      subtitle="Two views of the same causal model."
      right={
        <div className="seg">
          <button className={view === 'whys' ? 'on' : ''} onClick={() => setView('whys')}>5 Whys</button>
          <button className={view === 'fish' ? 'on' : ''} onClick={() => setView('fish')}>Fishbone (6M)</button>
        </div>
      }
    >
      {view === 'whys'
        ? <WhyChain steps={data.why_chain} flash={flash.includes('why_chain')} />
        : <Fishbone hypotheses={data.hypotheses} effect={data.deviation.title} />}
    </Card>
  )
}
