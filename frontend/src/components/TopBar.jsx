import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction, setError } from '../store/investigationSlice'
import { Icon } from './icons'

export default function TopBar() {
  const dispatch = useDispatch()
  const { id, status, error, data } = useSelector((s) => s.investigation)
  const busy = useSelector((s) => s.chat.busy)
  const hasConfirmed = data?.hypotheses.some((h) => h.status === 'confirmed')
  return (
    <>
      <header className="topbar">
        <div className="brand">
          <span className="brand-tile"><Icon name="ring" size={20} /></span>
          <div>
            <div className="brand-name">CauseTrace</div>
            <div className="brand-sub">AI root cause analysis · API manufacturing</div>
          </div>
        </div>
        <div className="top-right">
          <span className="status-pill">{status === 'saved' ? 'Saved' : 'Draft'}</span>
          <button type="button" className="btn dark" disabled={busy} onClick={() => dispatch(runAction(() => api.undo(id)))}
            title="Undo the last change (AI or manual)">
            <Icon name="undo" size={14} />Undo
          </button>
          <button type="button" className="btn primary" disabled={busy || !data?.deviation.description}
            title={hasConfirmed ? 'Save investigation' : 'A person must confirm a root cause before saving'}
            onClick={() => dispatch(runAction(() => api.save(id)))}>
            <Icon name="check" size={14} stroke={2.2} />Save investigation
          </button>
        </div>
      </header>
      {error && (
        <div className="toast" role="alert" onClick={() => dispatch(setError(null))}>
          <Icon name="alert" size={16} />{error} <span className="small">(click to dismiss)</span>
        </div>
      )}
    </>
  )
}
