const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, opts = {}) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* not json */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body ?? {}),
})
const I = (id) => `/api/investigations/${id}`

export const api = {
  health: () => request('/api/health'),
  list: () => request('/api/investigations'),
  create: () => request('/api/investigations', { method: 'POST' }),
  get: (id) => request(I(id)),
  upload: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request(`${I(id)}/upload`, { method: 'POST', body: fd })
  },
  editField: (id, path, value) => request(`${I(id)}/fields`, json('PATCH', { path, value })),
  accept: (id, paths) => request(`${I(id)}/accept`, json('POST', { paths })),
  editItem: (id, section, itemId, patch) => request(`${I(id)}/items/${section}/${itemId}`, json('PATCH', patch)),
  confirm: (id, hid, confirmed_by) => request(`${I(id)}/hypotheses/${hid}/confirm`, json('POST', { confirmed_by })),
  reject: (id, hid) => request(`${I(id)}/hypotheses/${hid}/reject`, json('POST')),
  save: (id) => request(`${I(id)}/save`, json('POST')),
  undo: (id) => request(`${I(id)}/undo`, json('POST')),
}

/** POST + Server-Sent Events (EventSource can't POST, so we read the stream by hand). */
export async function streamChat(id, body, onEvent) {
  const res = await fetch(`${BASE}${I(id)}/chat`, json('POST', body))
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* not json */ }
    throw new Error(detail)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      let event = 'message'
      let data = ''
      for (const line of block.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7)
        else if (line.startsWith('data: ')) data += line.slice(6)
      }
      if (data) onEvent(event, JSON.parse(data))
    }
  }
}
