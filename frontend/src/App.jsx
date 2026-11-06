import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Provider } from 'react-redux'
import { store } from './store'
import { bootstrap } from './store/investigationSlice'
import TopBar from './components/TopBar'
import DetailsSection from './components/DetailsSection'
import InvestigationSection from './components/InvestigationSection'
import HypothesesSection from './components/HypothesesSection'
import EvidenceSection from './components/EvidenceSection'
import CapaSection from './components/CapaSection'
import Copilot from './components/Copilot'

function Workspace() {
  const dispatch = useDispatch()
  const data = useSelector((s) => s.investigation.data)
  useEffect(() => { dispatch(bootstrap()) }, [dispatch])
  return (
    <div className="app">
      <TopBar />
      <main className="split">
        <div className="form-pane">
          {!data ? <p className="empty-note">Loading…</p> : (
            <>
              <div className="banner">This form is filled by the AI copilot →. Review each amber value, then accept or edit it.</div>
              <DetailsSection />
              <InvestigationSection />
              <HypothesesSection />
              <EvidenceSection />
              <CapaSection />
            </>
          )}
        </div>
        {data && <Copilot />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Provider store={store}>
      <Workspace />
    </Provider>
  )
}
