import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../api'

const SECTIONS = ['hypotheses', 'evidence', 'gaps', 'capa']

/** Which parts of the form changed between two versions (drives the highlight flash). */
export function changedPaths(a, b) {
  if (!a || !b) return []
  const out = []
  for (const scope of ['deviation', 'batch']) {
    for (const k of Object.keys(b[scope] || {})) {
      if ((a[scope] || {})[k] !== b[scope][k]) out.push(`${scope}.${k}`)
    }
  }
  for (const sec of SECTIONS) {
    const old = new Map((a[sec] || []).map((x) => [x.id, JSON.stringify(x)]))
    for (const x of b[sec] || []) if (old.get(x.id) !== JSON.stringify(x)) out.push(`${sec}.${x.id}`)
  }
  if (JSON.stringify(a.why_chain) !== JSON.stringify(b.why_chain)) out.push('why_chain')
  if (JSON.stringify(a.health) !== JSON.stringify(b.health)) out.push('health')
  return out
}

const initialState = {
  id: null, title: '', status: 'draft', version: 1,
  data: null, flash: [], list: [], llm: '', error: null,
}

const slice = createSlice({
  name: 'investigation',
  initialState,
  reducers: {
    setInvestigation(state, { payload }) {
      state.flash = changedPaths(state.data, payload.data)
      Object.assign(state, {
        id: payload.id, title: payload.title, status: payload.status,
        version: payload.version, data: payload.data, error: null,
      })
    },
    setData(state, { payload }) {
      state.flash = [...new Set([...state.flash, ...changedPaths(state.data, payload)])]
      state.data = payload
    },
    setMeta(state, { payload }) {
      state.version = payload.version
      state.title = payload.title
      state.status = 'draft'
    },
    clearFlash(state) { state.flash = [] },
    setList(state, { payload }) { state.list = payload },
    setLlm(state, { payload }) { state.llm = payload },
    setError(state, { payload }) { state.error = payload },
  },
})

export const { setInvestigation, setData, setMeta, clearFlash, setList, setLlm, setError } = slice.actions
export default slice.reducer

const STORE_KEY = 'causetrace.activeId'

export const refreshList = createAsyncThunk('inv/list', async (_, { dispatch }) => {
  dispatch(setList(await api.list()))
})

export const openInvestigation = createAsyncThunk('inv/open', async (id, { dispatch }) => {
  const inv = await api.get(id)
  dispatch(setInvestigation({ ...inv, _fresh: true }))
  try { localStorage.setItem(STORE_KEY, String(id)) } catch { /* storage unavailable */ }
  dispatch({ type: 'chat/reset', payload: inv.messages })
})

export const newInvestigation = createAsyncThunk('inv/new', async (_, { dispatch }) => {
  const inv = await api.create()
  await dispatch(openInvestigation(inv.id))
  dispatch(refreshList())
})

export const bootstrap = createAsyncThunk('inv/bootstrap', async (_, { dispatch }) => {
  try { dispatch(setLlm((await api.health()).llm)) } catch { dispatch(setError('Cannot reach the backend on :8000')); return }
  const list = await api.list()
  dispatch(setList(list))
  let id = null
  try { id = Number(localStorage.getItem(STORE_KEY)) || null } catch { /* storage unavailable */ }
  if (!id || !list.some((x) => x.id === id)) id = list[0]?.id
  if (id) await dispatch(openInvestigation(id))
  else await dispatch(newInvestigation())
})

/** Run any human review action, then replace the investigation with the server's response. */
export const runAction = createAsyncThunk('inv/action', async (fn, { dispatch }) => {
  try {
    const inv = await fn()
    dispatch(setInvestigation(inv))
    dispatch({ type: 'chat/syncMessages', payload: inv.messages })
    dispatch(refreshList())
    setTimeout(() => dispatch(clearFlash()), 2000)
    return true
  } catch (e) {
    dispatch(setError(e.message))
    return false
  }
})
