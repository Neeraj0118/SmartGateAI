import { useEffect, useState, useCallback } from 'react'
import { DoorOpen, LogIn, LogOut, Users, RefreshCw, Camera } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { listAttendance } from '../api/attendance'
import { startCamera, stopCamera, getCameraStatus } from '../api/camera'
import { toIST, todayIST } from '../utils/time'

export default function GateActivity() {
  const { adminKey } = useAuth()
  const navigate = useNavigate()
  const [entries, setEntries] = useState([])
  const [exits, setExits] = useState([])
  const [present, setPresent] = useState([])
  const [loading, setLoading] = useState(true)
  const [cameraRunning, setCameraRunning] = useState(false)
  const [error, setError] = useState(null)
  const [cameraMsg, setCameraMsg] = useState(null)
  const [dateFilter, setDateFilter] = useState(todayIST())

  const fetchData = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      // Fetch known-only events for the selected date
      const r = await listAttendance(adminKey, {
        is_known: true,
        date_filter: dateFilter,
        limit: 500,
      })
      const items = r.data?.items || []

      // Separate by event_type
      const ent = items.filter(e => e.event_type === 'entry')
      const ext = items.filter(e => e.event_type === 'exit')
      setEntries(ent)
      setExits(ext)

      // Campus presence: for each student, check their LAST event
      // Build map: student_id -> latest event (sorted by captured_at desc already)
      const presenceMap = {}
      // items are already desc by captured_at
      items.forEach(e => {
        if (e.student_id && !presenceMap[e.student_id]) {
          presenceMap[e.student_id] = e
        }
      })
      // Present = last event was 'entry'
      setPresent(Object.values(presenceMap).filter(e => e.event_type === 'entry'))

      // Camera status
      const camStatus = await getCameraStatus()
      setCameraRunning(camStatus.data?.running || false)
    } catch (e) {
      setError('Failed to load gate data')
    } finally { setLoading(false) }
  }, [adminKey, dateFilter])

  useEffect(() => { fetchData() }, [fetchData])

  const handleStartCamera = async (mode) => {
    if (!adminKey) return
    setCameraMsg(null)
    try {
      if (cameraRunning) {
        await stopCamera(adminKey)
      }
      await startCamera(adminKey, mode)
      setCameraMsg(`Camera started in ${mode.toUpperCase()} mode`)
      navigate('/monitoring')
    } catch (e) {
      setCameraMsg(e.response?.data?.detail || `Failed to start ${mode} camera`)
    }
  }

  return (
    <Layout
      title="Gate Activity"
      subtitle="Entry and exit monitoring for campus gate"
      actions={
        <div className="flex items-center gap-2">
          <input type="date" className="input text-sm w-40" value={dateFilter}
            onChange={e => setDateFilter(e.target.value)} />
          <button onClick={fetchData} className="btn-secondary flex items-center gap-2 text-sm">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">{error}</div>
      )}
      {cameraMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-800 text-sm">{cameraMsg}</div>
      )}

      {/* Camera Controls */}
      {adminKey && (
        <div className="card mb-5">
          <h2 className="section-title flex items-center gap-2 mb-4">
            <Camera size={16} className="text-forest" /> Gate Camera Controls
          </h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => handleStartCamera('entry')}
              className="btn-primary flex items-center justify-center gap-2 flex-1"
            >
              <LogIn size={16} /> Start Entry Gate Camera
            </button>
            <button
              onClick={() => handleStartCamera('exit')}
              className="flex items-center justify-center gap-2 flex-1 px-4 py-2 rounded-lg font-medium text-sm bg-amber text-white hover:bg-amber/90 transition-colors"
            >
              <LogOut size={16} /> Start Exit Gate Camera
            </button>
          </div>
          <p className="text-xs text-muted mt-2">
            Camera status: {cameraRunning
              ? <span className="text-green-700 font-medium">● Running</span>
              : <span className="text-muted">○ Stopped</span>}
            {' '}· Only one gate can be active at a time.
          </p>
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-5">
        <div className="card text-center">
          <LogIn size={20} className="mx-auto text-forest mb-1" />
          <p className="text-2xl font-bold text-charcoal">{entries.length}</p>
          <p className="text-xs text-muted">Entries</p>
        </div>
        <div className="card text-center">
          <LogOut size={20} className="mx-auto text-amber mb-1" />
          <p className="text-2xl font-bold text-charcoal">{exits.length}</p>
          <p className="text-xs text-muted">Exits</p>
        </div>
        <div className="card text-center">
          <Users size={20} className="mx-auto text-forest mb-1" />
          <p className="text-2xl font-bold text-charcoal">{present.length}</p>
          <p className="text-xs text-muted">On Campus</p>
        </div>
      </div>

      {/* Entry + Exit panels side by side */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
        {/* Entry Panel */}
        <div className="card">
          <h2 className="section-title flex items-center gap-2 mb-4">
            <LogIn size={16} className="text-forest" />
            Entry Events
            <span className="ml-auto badge-green">{entries.length}</span>
          </h2>
          {loading ? (
            <p className="text-muted text-sm text-center py-6">Loading…</p>
          ) : entries.length === 0 ? (
            <div className="text-center py-8 text-muted text-sm">
              <LogIn size={28} className="mx-auto mb-2 opacity-20" />
              No entry events for selected date
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-stone-100">
                    <th className="text-left pb-2 text-xs text-muted font-semibold">Name</th>
                    <th className="text-left pb-2 text-xs text-muted font-semibold">Time (IST)</th>
                    <th className="text-left pb-2 text-xs text-muted font-semibold">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.slice(0, 20).map((e, i) => (
                    <tr key={i} className="border-b border-stone-50">
                      <td className="py-2 font-medium text-charcoal">{e.full_name}</td>
                      <td className="py-2 text-xs text-muted whitespace-nowrap">{toIST(e.captured_at)}</td>
                      <td className="py-2 text-xs text-muted">
                        {e.similarity != null ? (e.similarity * 100).toFixed(0) + '%' : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {entries.length > 20 && (
                <p className="text-xs text-muted text-center pt-2">+{entries.length - 20} more</p>
              )}
            </div>
          )}
        </div>

        {/* Exit Panel */}
        <div className="card">
          <h2 className="section-title flex items-center gap-2 mb-4">
            <LogOut size={16} className="text-amber" />
            Exit Events
            <span className="ml-auto badge-amber">{exits.length}</span>
          </h2>
          {loading ? (
            <p className="text-muted text-sm text-center py-6">Loading…</p>
          ) : exits.length === 0 ? (
            <div className="text-center py-8 text-muted text-sm">
              <LogOut size={28} className="mx-auto mb-2 opacity-20" />
              No exit events for selected date
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-stone-100">
                    <th className="text-left pb-2 text-xs text-muted font-semibold">Name</th>
                    <th className="text-left pb-2 text-xs text-muted font-semibold">Time (IST)</th>
                    <th className="text-left pb-2 text-xs text-muted font-semibold">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {exits.slice(0, 20).map((e, i) => (
                    <tr key={i} className="border-b border-stone-50">
                      <td className="py-2 font-medium text-charcoal">{e.full_name}</td>
                      <td className="py-2 text-xs text-muted whitespace-nowrap">{toIST(e.captured_at)}</td>
                      <td className="py-2 text-xs text-muted">
                        {e.similarity != null ? (e.similarity * 100).toFixed(0) + '%' : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {exits.length > 20 && (
                <p className="text-xs text-muted text-center pt-2">+{exits.length - 20} more</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Campus Presence */}
      <div className="card">
        <h2 className="section-title flex items-center gap-2 mb-4">
          <Users size={16} className="text-forest" />
          Currently on Campus
          <span className="ml-auto badge-green">{present.length} present</span>
        </h2>
        {!adminKey ? (
          <p className="text-muted text-sm text-center py-6">Log in to view</p>
        ) : loading ? (
          <p className="text-muted text-sm text-center py-6">Loading…</p>
        ) : present.length === 0 ? (
          <div className="text-center py-8 text-muted text-sm">
            <Users size={28} className="mx-auto mb-2 opacity-20" />
            No students currently on campus (or no entry events yet today)
          </div>
        ) : (
          <ul className="divide-y divide-stone-100">
            {present.map((e, i) => (
              <li key={i} className="py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-charcoal">{e.full_name}</p>
                  <p className="text-xs text-muted font-mono">{e.student_id}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted">Entry: {toIST(e.captured_at)}</p>
                  <StatusBadge status="online" label="Present" />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Layout>
  )
}
