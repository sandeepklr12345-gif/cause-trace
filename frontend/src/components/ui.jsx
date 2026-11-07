import { useState } from 'react'
import { Icon } from './icons'

/** Section card. `icon` + `tone` render the pastel tile from the CauseTrace theme. */
export function Card({ title, subtitle, right, children, flash, id, icon, tone = 'blue' }) {
  return (
    <section className={`card ${flash ? 'flash' : ''}`} id={id}>
      <header className="card-head">
        <div className="card-title">
          {icon && <span className={`tile tile-${tone}`}><Icon name={icon} size={16} /></span>}
          <div>
            <h3>{title}</h3>
            {subtitle && <p className="muted small">{subtitle}</p>}
          </div>
        </div>
        {right}
      </header>
      <div className="card-body">{children}</div>
    </section>
  )
}

export function Pill({ tone = 'neutral', children, title, caps = false }) {
  return <span className={`pill pill-${tone} ${caps ? 'caps' : ''}`} title={title}>{children}</span>
}

const SOURCE_LABEL = {
  document: ['From document', 'blue'],
  chat: ['From chat', 'blue'],
  ai_inference: ['AI suggestion', 'amber'],
  user: ['Edited by you', 'green'],
}

export function ProvBadge({ prov }) {
  if (!prov) return null
  const [label, tone] = SOURCE_LABEL[prov.source] || ['', 'neutral']
  const pending = !prov.accepted && prov.source !== 'user'
  return (
    <Pill tone={pending ? 'amber' : tone} title={prov.quote ? `“${prov.quote}”` : label}>
      {pending ? `${label} · review` : label}
    </Pill>
  )
}

/** Click-to-edit text. Used only in the review step; the AI panel is the primary way data enters. */
export function EditableText({ value, onSave, multiline = false, placeholder = '—', className = '' }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value || '')
  if (!editing) {
    return (
      <div className={`editable ${className}`} onClick={() => { setDraft(value || ''); setEditing(true) }} title="Click to edit">
        {value || <span className="empty">{placeholder}</span>}
        <span className="edit-hint">✎</span>
      </div>
    )
  }
  const commit = () => { setEditing(false); if (draft !== (value || '')) onSave(draft) }
  const common = {
    autoFocus: true, value: draft, onChange: (e) => setDraft(e.target.value), onBlur: commit,
    onKeyDown: (e) => {
      if (e.key === 'Escape') setEditing(false)
      if (e.key === 'Enter' && (!multiline || e.metaKey || e.ctrlKey)) commit()
    },
  }
  return multiline ? <textarea rows={3} className="edit-input" {...common} /> : <input className="edit-input" {...common} />
}
