import { useDispatch, useSelector } from 'react-redux'
import { api } from '../api'
import { runAction } from '../store/investigationSlice'
import { Icon } from './icons'
import { Card, EditableText, ProvBadge } from './ui'

const DEVIATION = [
  ['deviation_id', 'Deviation no.'], ['title', 'Title'], ['deviation_type', 'Type'],
  ['classification', 'Classification'], ['date_detected', 'Date detected'],
  ['detected_by', 'Detected by'], ['department', 'Department'],
  ['description', 'Description', true], ['immediate_actions', 'Immediate actions', true],
  ['impact_assessment', 'Impact assessment', true],
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
  const edited = value && prov?.source === 'user'
  return (
    <div className={`field ${wide ? 'wide' : ''} ${pending ? 'suggested' : ''} ${edited ? 'edited' : ''} ${flash.includes(path) ? 'flash' : ''}`}>
      <div className="field-label">
        <span>{label}</span>
        {pending && (
          <button type="button" className="accept-btn" title="Accept this value" aria-label={`Accept ${label}`}
            onClick={() => dispatch(runAction(() => api.accept(id, [path])))}>
            <Icon name="check" size={12} stroke={3} />
          </button>
        )}
      </div>
      <div className="field-box">
        <EditableText
          value={value}
          multiline={wide}
          placeholder="Waiting for the AI…"
          className="field-value"
          onSave={(v) => dispatch(runAction(() => api.editField(id, path, v)))}
        />
      </div>
      {value && <ProvBadge prov={prov} />}
    </div>
  )
}

function Section({ id: sectionId, title, icon, tone, scope, fields }) {
  const dispatch = useDispatch()
  const id = useSelector((s) => s.investigation.id)
  const data = useSelector((s) => s.investigation.data)
  const pendingPaths = fields
    .map(([k]) => `${scope}.${k}`)
    .filter((p) => { const [s, k] = p.split('.'); const pr = data.provenance[p]; return data[s][k] && pr && !pr.accepted && pr.source !== 'user' })
  return (
    <Card
      id={sectionId}
      title={title}
      icon={icon}
      tone={tone}
      right={pendingPaths.length > 0 && (
        <button type="button" className="btn small tint" onClick={() => dispatch(runAction(() => api.accept(id, pendingPaths)))}>
          <Icon name="check" size={13} stroke={2.4} />Accept all {pendingPaths.length} AI values
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
      <Section id="sec-details" title="Deviation details" icon="doc" tone="blue" scope="deviation" fields={DEVIATION} />
      <Section id="sec-batch" title="Batch and process context" icon="flask" tone="green" scope="batch" fields={BATCH} />
    </>
  )
}
