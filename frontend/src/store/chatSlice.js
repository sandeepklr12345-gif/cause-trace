import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api, streamChat } from '../api'
import { clearFlash, refreshList, setData, setInvestigation, setMeta } from './investigationSlice'

const slice = createSlice({
  name: 'chat',
  initialState: { messages: [], busy: false, progress: [], error: null, phase: '' },
  reducers: {
    userSent(state, { payload }) {
      state.messages.push({ role: 'user', content: payload })
      state.busy = true
      state.progress = []
      state.error = null
    },
    stepStarted(state, { payload }) { state.progress.push(payload) },
    assistantSaid(state, { payload }) {
      state.messages.push({ role: 'assistant', content: payload.content, meta: { tool: payload.tool, changed: payload.changed } })
    },
    chatFailed(state, { payload }) { state.error = payload; state.busy = false },
    chatDone(state) { state.busy = false },
    setPhase(state, { payload }) { state.phase = payload },
  },
  extraReducers: (b) => {
    b.addCase('chat/reset', (s, a) => { s.messages = a.payload || []; s.progress = []; s.error = null; s.busy = false })
    b.addCase('chat/syncMessages', (s, a) => { if (!s.busy) s.messages = a.payload || s.messages })
  },
})

export const { userSent, stepStarted, assistantSaid, chatFailed, chatDone, setPhase } = slice.actions
export default slice.reducer

export const sendChat = createAsyncThunk('chat/send', async (body, { dispatch, getState }) => {
  const id = getState().investigation.id
  dispatch(userSent(body.userText || body.message || (body.action ? `[${body.action}]` : '')))
  try {
    await streamChat(id, body.payload || body, (event, p) => {
      if (event === 'node') dispatch(stepStarted(p))
      else if (event === 'state') dispatch(setData(p.data))
      else if (event === 'message') dispatch(assistantSaid(p))
      else if (event === 'done') dispatch(setMeta(p))
      else if (event === 'error') throw new Error(p.detail)
    })
    dispatch(chatDone())
    dispatch(refreshList())
  } catch (e) {
    dispatch(chatFailed(e.message))
    const fresh = await api.get(id) // resync with whatever was persisted
    dispatch(setInvestigation(fresh))
  }
  setTimeout(() => dispatch(clearFlash()), 2200)
})

/** Document intake: upload -> plain text -> same chat pipeline with document_text. */
export const uploadAndExtract = createAsyncThunk('chat/upload', async (file, { dispatch, getState }) => {
  const id = getState().investigation.id
  dispatch(setPhase(`Reading ${file.name}…`))
  try {
    const doc = await api.upload(id, file)
    dispatch(setPhase(''))
    await dispatch(sendChat({
      userText: `📎 ${doc.name} (${doc.pages} page${doc.pages > 1 ? 's' : ''}, ${doc.chars.toLocaleString()} chars)`,
      payload: { message: '', document_text: doc.text, document_name: doc.name },
    }))
  } catch (e) {
    dispatch(setPhase(''))
    dispatch(chatFailed(e.message))
  }
})
