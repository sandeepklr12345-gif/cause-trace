import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction } from '../store/investigationSlice'
import { Card, EditableText, ProvBadge } from './ui'

const DEVIATION = [
  ['deviation_id', 'Deviation no.'], ['title', 'Title'], ['deviation_type', 'Type'],
  ['classification', 'Classification (AI suggestion)'], ['date_detected', 'Date detected'],
  ['detected_by', 'Detected by'], ['department', 'Department'],
  ['description', 'Description', true], ['immediate_actions', 'Immediate actions', true],
  ['impact_assessment', 'Impact assessment (AI)', true],
]
const BATCH = [
  ['product_name', 'Product'], ['grade_or_spec', 'Grade / spec'], ['batch_number', 'Batch / lot no.'],
  ['process_stage', 'Process stage'], ['equipment_ids', 'Equipment'], ['raw_material_lots', 'Raw material lots'],
  ['batch_size', 'Batch size'], ['affected_quantity', 'Affected quantity'], ['manufacturing_date', 'Mfg date'],
  ['test_result', 'Test result', true],
]

function Field({ scope, name, label, wide }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const data = useSelector((s) => s.investigation.data)
  const flash = useSelector((s) => s.investigation.flash)
  const path = `${scope}.${name}`
  const value = data[scope][name]
  const prov = data.provenance[path]
  const pending = value && prov && !prov.accepted && prov.source !== 'user'
  return (
    <div className={`field ${wide ? 'wide' : ''} ${pending ? 'suggested' : ''} ${flash.includes(path) ? 'flash' : ''}`}>
      <div className="field-label">
        <span>{label}</span>
        <span className="field-tools">
          {value && <ProvBadge prov={prov} />}
          {pending && (
            <button className="icon-btn ok" title="Accept this value" onClick={() => dispatch(runAction(() => api.accept(id, [path])))}>✓</button>
          )}
        </span>
      </div>
      <EditableText
        value={value}
        multiline={wide}
        placeholder="Waiting for the AI…"
        className="field-value"
        onSave={(v) => dispatch(runAction(() => api.editField(id, path, v)))}
      />
    </div>
  )
}

function Section({ title, subtitle, scope, fields }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const data = useSelector((s) => s.investigation.data)
  const pendingPaths = fields
    .map(([k]) => `${scope}.${k}`)
    .filter((p) => { const [s, k] = p.split('.'); const pr = data.provenance[p]; return data[s][k] && pr && !pr.accepted && pr.source !== 'user' })
  return (
    <Card
      title={title}
      subtitle={subtitle}
      right={pendingPaths.length > 0 && (
        <button className="btn small" onClick={() => dispatch(runAction(() => api.accept(id, pendingPaths)))}>
          Accept all {pendingPaths.length} AI values
        </button>
      )}
    >
      <div className="grid">
        {fields.map(([k, label, wide]) => <Field key={k} scope={scope} name={k} label={label} wide={wide} />)}
      </div>
    </Card>
  )
}

export default function DetailsSection() {
  return (
    <>
      <Section title="1 · Deviation details" subtitle="Filled by the AI from your document or message. Amber = needs your review." scope="deviation" fields={DEVIATION} />
      <Section title="2 · Batch & process context" scope="batch" fields={BATCH} />
    </>
  )
}
