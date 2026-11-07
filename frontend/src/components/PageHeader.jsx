import { useDispatch, useSelector } from 'react-redux'
import { newInvestigation, openInvestigation } from '../store/investigationSlice'
import { goTo } from '../scroll'
import { Icon } from './icons'

const READINESS_TONE = { not_ready: 'red', needs_evidence: 'amber', ready_for_review: 'green' }

const VIEWS = [
  ['whys', '5 Whys', 'Causal chain with evidence', 'list'],
  ['fish', 'Fishbone', 'Grouped by Man, Machine, Material, Method, Measurement, Environment', 'fish'],
]

/** Title card: deviation, batch, evidence score, classification, plus the 5 Whys / Fishbone view tabs. */
export function PageHeader({ view, onView }) {
  const dispatch = useDispatch()
  const { id, status, list, data } = useSelector((s) => s.investigation)
  const { deviation, batch, provenance, health } = data
  const cls = deviation.classification
  const clsPending = cls && provenance['deviation.classification'] && !provenance['deviation.classification'].accepted
    && provenance['deviation.classification'].source !== 'user'
  const saved = status === 'saved'

  return (
    <section className="card page-card">
      <div className="mobile-switch">
        <select value={id || ''} onChange={(e) => dispatch(openInvestigation(Number(e.target.value)))} aria-label="Investigation">
          {list.map((i) => <option key={i.id} value={i.id}>#{i.id} · {i.title}</option>)}
        </select>
        <button type="button" className="btn small" onClick={() => dispatch(newInvestigation())}>+ New</button>
      </div>
      <div className="page-top">
        <div className="page-id">
          <h1 className="page-title">{deviation.title || 'Untitled investigation'}</h1>
          <div className="page-meta">
            {deviation.deviation_id && <><span>{deviation.deviation_id}</span><span aria-hidden="true">·</span></>}
            {batch.batch_number && <><span>Batch {batch.batch_number}</span><span aria-hidden="true">·</span></>}
            <span className={`meta-score tone-${READINESS_TONE[health.readiness] || 'red'}`}>
              <span className="dot8" />{health.evidence_sufficiency}% evidence
            </span>
          </div>
        </div>
        <div className="page-tags">
          {cls && <span className={`tag ${clsPending ? 'tag-amber' : 'tag-blue'}`}>{cls}{clsPending ? ' · AI suggestion' : ''}</span>}
          <span className={`tag ${saved ? 'tag-green' : 'tag-neutral'}`}>{saved ? 'Saved' : 'Draft'}</span>
        </div>
      </div>
      <div className="view-tabs" role="tablist" aria-label="Investigation view">
        {VIEWS.map(([key, title, sub, icon]) => (
          <button key={key} type="button" role="tab" aria-selected={view === key} className="view-tab"
            onClick={() => { onView(key); goTo('sec-investigation') }}>
            <Icon name={icon} size={18} />
            <span>
              <span className="view-tab-title">{title}</span>
              <span className="view-tab-sub">{sub}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}

/** Four headline numbers. Each one jumps to the section behind it. */
export function Kpis() {
  const { health, gaps, hypotheses, capa } = useSelector((s) => s.investigation.data)
  const openGaps = gaps.filter((g) => !g.resolved).length
  const supported = hypotheses.filter((h) => h.status === 'supported' || h.status === 'confirmed').length
  const accepted = capa.filter((c) => c.accepted).length
  const items = [
    ['blue', 'chart', `${health.evidence_sufficiency}%`, 'Evidence sufficiency', 'sec-evidence'],
    ['amber', 'alert', openGaps, 'Open evidence gaps', 'sec-evidence'],
    ['purple', 'layers', hypotheses.length, `Hypotheses${supported ? `, ${supported} supported` : ''}`, 'sec-hypotheses'],
    ['green', 'shield', capa.length, `CAPA drafted${accepted ? `, ${accepted} accepted` : ''}`, 'sec-capa'],
  ]
  return (
    <div className="kpis">
      {items.map(([tone, icon, value, label, target]) => (
        <button key={label} type="button" className="kpi" onClick={() => goTo(target)} title={`Go to ${label.toLowerCase()}`}>
          <span className={`kpi-tile tile-${tone}`}><Icon name={icon} size={20} /></span>
          <span>
            <span className="kpi-num">{value}</span>
            <span className="kpi-label">{label}</span>
          </span>
        </button>
      ))}
    </div>
  )
}
