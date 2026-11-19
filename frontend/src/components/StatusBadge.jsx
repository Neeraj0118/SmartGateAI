export default function StatusBadge({ status, label }) {
  const map = {
    online:       'badge-green',
    running:      'badge-green',
    known:        'badge-green',
    offline:      'badge-red',
    stopped:      'badge-slate',
    unknown:      'badge-slate',
    unknown_face: 'badge-red',
    pending:      'badge-amber',
    reviewed:     'badge-blue',
  }
  const labels = {
    online: 'Online', offline: 'Offline', unknown: 'Unknown',
    running: 'Running', stopped: 'Stopped',
    known: 'Known', unknown_face: 'Unknown', pending: 'Pending', reviewed: 'Reviewed',
  }
  const cls = map[status] || 'badge-slate'
  const text = label || labels[status] || status

  return (
    <span className={cls}>
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-75 inline-block" />
      {text}
    </span>
  )
}
