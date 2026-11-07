import { useSelector } from 'react-redux'
import { Icon } from './icons'
import { Card, Pill } from './ui'

const CATS = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment']
const STATUS_TONE = { suggested: 'amber', supported: 'blue', confirmed: 'green', rejected: 'neutral' }
const KIND = { record: 'Record', test_result: 'Test result', observation: 'Observation', statement: 'Statement', document: 'Document' }

function WhyChain({ steps, evidence, flash }) {
  if (!steps.length) return <p className="empty-note">Run the analysis and the 5 Whys chain will appear here.</p>
  return (
    <ol className={`whys ${flash ? 'flash' : ''}`}>
      {steps.map((s) => {
        const evidenced = s.evidence_refs?.length > 0
        return (
          <li key={s.level} className={`why ${evidenced ? 'evidenced' : 'gap'}`}>
            <div className="why-rail">
              <span className="why-n">{s.level}</span>
              <span className={evidenced ? 'why-ok' : 'why-warn'}>
                <Icon name={evidenced ? 'check' : 'bang'} size={14} stroke={3} />
              </span>
            </div>
            <div className="why-main">
              <div className="why-head">
                <span className="why-q">{s.question}</span>
                {evidenced
                  ? <Pill tone="green" caps>Evidenced</Pill>
                  : <Pill tone="amber" caps title="No evidence on file backs this step yet">Not yet evidenced</Pill>}
              </div>
              <div className="why-a">{s.answer}</div>
              {evidenced && (
                <div className="chips">
                  {s.evidence_refs.map((ref) => {
                    const e = evidence.find((x) => x.id === ref)
                    return (
                      <span key={ref} className="chip chip-for" title={e?.description || 'Evidence behind this step'}>
                        {ref}{e ? ` · ${KIND[e.kind] || e.kind}` : ''}
                      </span>
                    )
                  })}
                </div>
              )}
              {s.critic_note && <div className="critic"><b>Critic note:</b> {s.critic_note}</div>}
            </div>
          </li>
        )
      })}
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

export default function InvestigationSection({ view }) {
  const data = useSelector((s) => s.investigation.data)
  const flash = useSelector((s) => s.investigation.flash)
  const whys = view === 'whys'
  const critic = data.why_chain.some((s) => s.critic_note)
  return (
    <Card
      id="sec-investigation"
      title={whys ? 'Investigation · 5 Whys' : 'Investigation · Fishbone (6M)'}
      icon={whys ? 'list' : 'fish'}
      tone="purple"
      right={whys && critic && <Pill tone="purple">Reviewed by AI critic</Pill>}
    >
      {whys
        ? <WhyChain steps={data.why_chain} evidence={data.evidence} flash={flash.includes('why_chain')} />
        : <Fishbone hypotheses={data.hypotheses} effect={data.deviation.title} />}
    </Card>
  )
}
