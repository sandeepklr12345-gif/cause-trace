import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { newInvestigation, openInvestigation, runAction, setError } from '../store/investigationSlice'
import { Pill } from './ui'

export default function TopBar() {
  const dispatch = useDispatch()
  const { id, title, status, list, error, data } = useSelector((s) => s.investigation)
  const busy = useSelector((s) => s.chat.busy)
  const hasConfirmed = data?.hypotheses.some((h) => h.status === 'confirmed')
  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="logo">◎</span>
          <div><b>CauseTrace</b><div className="muted small">AI root cause analysis · API manufacturing</div></div>
        </div>
        <div className="top-mid">
          <select value={id || ''} onChange={(e) => dispatch(openInvestigation(Number(e.target.value)))} aria-label="Investigation">
            {list.map((i) => <option key={i.id} value={i.id}>#{i.id} · {i.title}</option>)}
          </select>
          <button className="btn small" onClick={() => dispatch(newInvestigation())}>+ New</button>
          <Pill tone={status === 'saved' ? 'green' : 'neutral'}>{status === 'saved' ? 'Saved' : 'Draft'}</Pill>
        </div>
        <div className="top-right">
          <button className="btn" disabled={busy} onClick={() => dispatch(runAction(() => api.undo(id)))} title="Undo the last change (AI or manual)">↶ Undo</button>
          <button className="btn primary" disabled={busy || !data?.deviation.description}
            title={hasConfirmed ? 'Save investigation' : 'A person must confirm a root cause before saving'}
            onClick={() => dispatch(runAction(() => api.save(id)))}>Save investigation</button>
        </div>
      </header>
      {error && (
        <div className="toast" role="alert" onClick={() => dispatch(setError(null))}>⚠ {error} <span className="muted small">(click to dismiss)</span></div>
      )}
      <span hidden>{title}</span>
    </>
  )
}
