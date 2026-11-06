import { configureStore } from '@reduxjs/toolkit'
import investigation from './investigationSlice'
import chat from './chatSlice'

export const store = configureStore({
  reducer: { investigation, chat },
})
