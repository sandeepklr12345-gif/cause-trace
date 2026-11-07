import { useEffect, useRef, useState } from 'react'
import { Icon } from './icons'

const KEY = 'causetrace.split'
const DEFAULT = 0.6 // investigation form 60% / AI copilot 40%
const HANDLE = 14 // px, width of the divider column
const MIN_LEFT = 380 // px
const MIN_RIGHT = 320 // px
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

function loadRatio() {
  try {
    const v = Number(localStorage.getItem(KEY))
    return v > 0.1 && v < 0.9 ? v : DEFAULT
  } catch { return DEFAULT }
}
function saveRatio(v) {
  try { localStorage.setItem(KEY, String(v)) } catch { /* storage unavailable */ }
}

/**
 * Two panes with a draggable divider. Default 60/40.
 * Divider: drag, arrow keys (Shift = bigger step), Home/End, double-click or Enter to reset;
 * the chevron buttons collapse one pane (or bring it back).
 * Below 1040px the CSS stacks the panes and hides the divider.
 */
export default function SplitPane({ left, right }) {
  const ref = useRef(null)
  const [width, setWidth] = useState(0)
  const [ratio, setRatio] = useState(loadRatio)
  const [collapsed, setCollapsed] = useState(null) // null | 'left' | 'right'
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return undefined
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Keep both panes above their minimum width, whatever the window size.
  const avail = Math.max(width - HANDLE, 1)
  const lo = width ? Math.min(0.5, MIN_LEFT / avail) : 0.3
  const hi = width ? Math.max(0.5, 1 - MIN_RIGHT / avail) : 0.7
  const eff = clamp(ratio, lo, hi)

  const columns = collapsed === 'left' ? `0 ${HANDLE}px minmax(0, 1fr)`
    : collapsed === 'right' ? `minmax(0, 1fr) ${HANDLE}px 0`
      : `minmax(0, ${eff * 1000}fr) ${HANDLE}px minmax(0, ${(1 - eff) * 1000}fr)`

  const fromPointer = (clientX) => {
    const rect = ref.current.getBoundingClientRect()
    return clamp((clientX - rect.left - HANDLE / 2) / Math.max(rect.width - HANDLE, 1), lo, hi)
  }
  const commit = (r) => { setRatio(r); saveRatio(r) }
  const reset = () => { setCollapsed(null); commit(DEFAULT) }

  const onPointerDown = (e) => {
    if (e.button !== 0 || collapsed) return
    e.currentTarget.setPointerCapture(e.pointerId)
    e.preventDefault()
    setDragging(true)
  }
  const onPointerMove = (e) => { if (dragging) setRatio(fromPointer(e.clientX)) }
  const onPointerUp = (e) => {
    if (!dragging) return
    setDragging(false)
    commit(fromPointer(e.clientX))
  }
  const onKeyDown = (e) => {
    if (collapsed) { if (e.key === 'Enter') setCollapsed(null); return }
    const step = e.shiftKey ? 0.1 : 0.02
    const next = { ArrowLeft: eff - step, ArrowRight: eff + step, Home: lo, End: hi, Enter: DEFAULT }[e.key]
    if (next === undefined) return
    e.preventDefault()
    commit(clamp(next, lo, hi))
  }

  const leftLabel = collapsed === 'right' ? 'Show the AI copilot' : 'Hide the investigation form'
  const rightLabel = collapsed === 'left' ? 'Show the investigation form' : 'Hide the AI copilot'

  return (
    <div ref={ref} className={`split ${dragging ? 'is-dragging' : ''}`} style={{ gridTemplateColumns: columns }}>
      <div className={`pane pane-left ${collapsed === 'left' ? 'is-collapsed' : ''}`}>{left}</div>

      <div className={`splitter ${dragging ? 'dragging' : ''} ${collapsed ? 'is-collapsed' : ''}`}>
        <div
          className="splitter-bar"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize the investigation form and the AI copilot"
          aria-valuemin={Math.round(lo * 100)}
          aria-valuemax={Math.round(hi * 100)}
          aria-valuenow={collapsed === 'left' ? 0 : collapsed === 'right' ? 100 : Math.round(eff * 100)}
          tabIndex={0}
          title="Drag to resize · double-click to reset to 60/40"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={() => setDragging(false)}
          onDoubleClick={reset}
          onKeyDown={onKeyDown}
        />
        <div className="splitter-tools">
          {collapsed !== 'left' && (
            <button type="button" className="split-btn" aria-label={leftLabel} title={leftLabel}
              onClick={() => setCollapsed(collapsed === 'right' ? null : 'left')}>
              <Icon name="chevronLeft" size={12} stroke={2.8} />
            </button>
          )}
          <span className="grip" aria-hidden="true" />
          {collapsed !== 'right' && (
            <button type="button" className="split-btn" aria-label={rightLabel} title={rightLabel}
              onClick={() => setCollapsed(collapsed === 'left' ? null : 'right')}>
              <Icon name="chevronRight" size={12} stroke={2.8} />
            </button>
          )}
        </div>
      </div>

      <div className={`pane pane-right ${collapsed === 'right' ? 'is-collapsed' : ''}`}>{right}</div>
    </div>
  )
}
