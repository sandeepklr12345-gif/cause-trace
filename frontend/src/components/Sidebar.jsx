import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { newInvestigation, openInvestigation } from '../store/investigationSlice'
import { Icon } from './icons'

const KEY = 'causetrace.sidebar'

function fmt(iso) {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default function Sidebar() {
  const dispatch = useDispatch()
  const { id, list } = useSelector((s) => s.investigation)
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(KEY) === '1' } catch { return false }
  })
  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    try { localStorage.setItem(KEY, next ? '1' : '0') } catch { /* storage unavailable */ }
  }

  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''}`} aria-label="Investigations">
      <button type="button" className="side-btn" onClick={() => dispatch(newInvestigation())}
        title="Start a new investigation" aria-label="New investigation">
        <Icon name="plus" size={14} stroke={2.4} />
        {!collapsed && 'New investigation'}
      </button>

      {!collapsed && (
        <div className="side-label"><Icon name="menu" size={14} />Investigations</div>
      )}

      <nav className="side-list">
        {list.map((i) => {
          const saved = i.status === 'saved'
          const active = i.id === id
          return collapsed ? (
            <button key={i.id} type="button" className={`side-item mini ${active ? 'active' : ''}`}
              title={`#${i.id} · ${i.title}`} aria-current={active ? 'true' : undefined}
              onClick={() => dispatch(openInvestigation(i.id))}>
              <span className={`mini-dot ${saved ? 'saved' : 'draft'}`} />#{i.id}
            </button>
          ) : (
            <button key={i.id} type="button" className={`side-item ${active ? 'active' : ''}`}
              aria-current={active ? 'true' : undefined} onClick={() => dispatch(openInvestigation(i.id))}>
              <span className="side-item-top">
                <span className="side-item-title">{i.title || 'Untitled investigation'}</span>
                <span className={`side-pill ${saved ? 'saved' : 'draft'}`}>{saved ? 'Saved' : 'Draft'}</span>
              </span>
              <span className="side-item-sub">#{i.id} · {fmt(i.updated_at)}</span>
            </button>
          )
        })}
      </nav>

      <button type="button" className="side-btn" onClick={toggle}
        aria-label={collapsed ? 'Expand the sidebar' : 'Collapse the sidebar'}
        title={collapsed ? 'Expand the sidebar' : 'Collapse the sidebar'}>
        <Icon name={collapsed ? 'chevronRight' : 'chevronLeft'} size={14} stroke={2.4} />
        {!collapsed && 'Collapse'}
      </button>
    </aside>
  )
}
