import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Provider } from 'react-redux'
import { store } from './store'
import { bootstrap } from './store/investigationSlice'
import TopBar from './components/TopBar'
import Sidebar from './components/Sidebar'
import SplitPane from './components/SplitPane'
import { PageHeader, Kpis } from './components/PageHeader'
import DetailsSection from './components/DetailsSection'
import InvestigationSection from './components/InvestigationSection'
import HypothesesSection from './components/HypothesesSection'
import EvidenceSection from './components/EvidenceSection'
import CapaSection from './components/CapaSection'
import Copilot from './components/Copilot'
import { Icon } from './components/icons'

function Workspace() {
  const dispatch = useDispatch()
  const data = useSelector((s) => s.investigation.data)
  const [view, setView] = useState('whys') // 5 Whys | Fishbone
  useEffect(() => { dispatch(bootstrap()) }, [dispatch])

  // Left: the investigation form (six sections). Right: the AI copilot.
  const form = !data ? <p className="empty-note">Loading…</p> : (
    <>
      <PageHeader view={view} onView={setView} />
      <div className="banner">
        <Icon name="info" size={16} />
        This form is filled by the AI copilot. Review each amber value, then accept or edit it.
      </div>
      <Kpis />
      <DetailsSection />
      <InvestigationSection view={view} />
      <HypothesesSection />
      <EvidenceSection />
      <CapaSection />
    </>
  )

  return (
    <div className="app">
      <TopBar />
      <div className="shell">
        <Sidebar />
        <main className="content">
          <SplitPane left={form} right={data ? <Copilot /> : null} />
        </main>
      </div>
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
