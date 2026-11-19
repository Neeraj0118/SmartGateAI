import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Users, Camera, Eye, AlertTriangle, Activity, Clock, RefreshCw, LogIn, LogOut, CheckCircle,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import Layout from '../components/Layout'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { getHealth } from '../api/health'
import { listStudents } from '../api/students'
import { getAttendanceStats, listAttendance } from '../api/attendance'
import { getCameraStatus, getCameraMode, startCamera, stopCamera } from '../api/camera'
import { toIST } from '../utils/time'

export default function Dashboard() {
  const { adminKey } = useAuth()
  const navigate = useNavigate()
  const [health, setHealth] = useState(null)
  const [students, setStudents] = useState([])
  const [stats, setStats] = useState(null)
  const [cameraStatus, setCameraStatus] = useState(null)
  const [cameraMode, setCameraMode] = useState(null)
  const [recentEvents, setRecentEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState(null)
  const [actionMsg, setActionMsg] = useState(null)

  const fetchAll = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [h, camSt, camMode] = await Promise.allSettled([
        getHealth(),
        getCameraStatus(),
        getCameraMode(),
      ])
      if (h.status === 'fulfilled') setHealth(h.value.data)
      if (camSt.status === 'fulfilled') setCameraStatus(camSt.value.data)
      if (camMode.status === 'fulfilled') setCameraMode(camMode.value.data)

      if (adminKey) {
        const [s, at, ev] = await Promise.allSettled([
          listStudents(adminKey, { active_only: true }),
          getAttendanceStats(adminKey),
          listAttendance(adminKey, { limit: 10 }),
        ])
        if (s.status === 'fulfilled') setStudents(s.value.data?.items || [])
        if (at.status === 'fulfilled') setStats(at.value.data)
        if (ev.status === 'fulfilled') setRecentEvents(ev.value.data?.items || [])
      }
    } catch (e) { setError('Failed to load dashboard data') }
    finally { setLoading(false) }
  }, [adminKey])

  useEffect(() => { fetchAll() }, [fetchAll])

  const handleStartGateCamera = async (mode) => {
    if (!adminKey) return
    setActionLoading(true); setActionMsg(null); setError(null)
    try {
      const res = await startCamera(adminKey, mode)
      setActionMsg(res.data?.message || `Camera started in ${mode.toUpperCase()} mode`)
      await fetchAll()
    } catch (e) {
      setError(e.response?.data?.detail || `Failed to start ${mode} camera`)
    } finally { setActionLoading(false) }
  }

  const handleStopCamera = async () => {
    if (!adminKey) return
    setActionLoading(true); setActionMsg(null); setError(null)
    try {
      const res = await stopCamera(adminKey)
      setActionMsg(res.data?.message || 'Camera stopped')
      await fetchAll()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to stop camera')
    } finally { setActionLoading(false) }
  }

  const isOnline = health?.status === 'healthy' || health?.status === 'ok'
  const camRunning = cameraStatus?.running
  const gateMode = cameraMode?.gate_mode || cameraStatus?.gate_mode || 'entry'

  return (
    <Layout
      title="Security Dashboard"
      subtitle="Real-time campus gate & face recognition overview"
      actions={
        <button onClick={fetchAll} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm flex items-center gap-2">
          <AlertTriangle size={15} /> {error}
        </div>
      )}
      {actionMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-forest text-sm flex items-center gap-2">
          <CheckCircle size={15} /> {actionMsg}
        </div>
      )}

      {/* Prominent Monitoring Action Cards (Entry / Exit) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        {/* Entry Gate Card */}
        <div className="card border-l-4 border-forest bg-gradient-to-br from-white to-stone-50/50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2.5 bg-green-100 text-forest rounded-xl">
                <LogIn size={20} />
              </div>
              <div>
                <h2 className="text-base font-bold text-charcoal">ENTRY GATE</h2>
                <p className="text-xs text-muted">Campus Arrival Monitoring</p>
              </div>
            </div>
            <StatusBadge
              status={camRunning && gateMode === 'entry' ? 'running' : 'stopped'}
              label={camRunning && gateMode === 'entry' ? 'Active' : 'Standby'}
            />
          </div>

          <div className="grid grid-cols-3 gap-2 my-4 text-center">
            <div className="p-2.5 bg-stone-100/70 rounded-lg">
              <p className="text-lg font-bold text-charcoal">
                {camRunning && gateMode === 'entry' ? (cameraStatus?.faces_detected ?? 0) : '—'}
              </p>
              <p className="text-[10px] text-muted font-semibold uppercase tracking-wider">Detected</p>
            </div>
            <div className="p-2.5 bg-green-50/80 rounded-lg">
              <p className="text-lg font-bold text-forest">
                {camRunning && gateMode === 'entry' ? (cameraStatus?.known_count ?? 0) : '—'}
              </p>
              <p className="text-[10px] text-muted font-semibold uppercase tracking-wider">Known</p>
            </div>
            <div className="p-2.5 bg-red-50/80 rounded-lg">
              <p className="text-lg font-bold text-errored">
                {camRunning && gateMode === 'entry' ? (cameraStatus?.unknown_count ?? 0) : '—'}
              </p>
              <p className="text-[10px] text-muted font-semibold uppercase tracking-wider">Unknown</p>
            </div>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={() => navigate('/monitoring?mode=entry')}
              className="btn-primary flex-1 flex items-center justify-center gap-1.5 text-xs py-2"
            >
              <Camera size={14} /> Open Entry Monitoring
            </button>
            {adminKey && (
              camRunning && gateMode === 'entry' ? (
                <button
                  onClick={handleStopCamera}
                  disabled={actionLoading}
                  className="btn-danger text-xs py-2 px-3.5"
                >
                  Stop
                </button>
              ) : (
                <button
                  onClick={() => handleStartGateCamera('entry')}
                  disabled={actionLoading}
                  className="btn-secondary text-xs py-2 px-3.5 font-medium"
                >
                  Start
                </button>
              )
            )}
          </div>
        </div>

        {/* Exit Gate Card */}
        <div className="card border-l-4 border-amber bg-gradient-to-br from-white to-stone-50/50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2.5 bg-amber-100 text-amber rounded-xl">
                <LogOut size={20} />
              </div>
              <div>
                <h2 className="text-base font-bold text-charcoal">EXIT GATE</h2>
                <p className="text-xs text-muted">Campus Departure Monitoring</p>
              </div>
            </div>
            <StatusBadge
              status={camRunning && gateMode === 'exit' ? 'running' : 'stopped'}
              label={camRunning && gateMode === 'exit' ? 'Active' : 'Standby'}
            />
          </div>

          <div className="grid grid-cols-3 gap-2 my-4 text-center">
            <div className="p-2.5 bg-stone-100/70 rounded-lg">
              <p className="text-lg font-bold text-charcoal">
                {camRunning && gateMode === 'exit' ? (cameraStatus?.faces_detected ?? 0) : '—'}
              </p>
              <p className="text-[10px] text-muted font-semibold uppercase tracking-wider">Detected</p>
            </div>
            <div className="p-2.5 bg-green-50/80 rounded-lg">
              <p className="text-lg font-bold text-forest">
                {camRunning && gateMode === 'exit' ? (cameraStatus?.known_count ?? 0) : '—'}
              </p>
              <p className="text-[10px] text-muted font-semibold uppercase tracking-wider">Known</p>
            </div>
            <div className="p-2.5 bg-red-50/80 rounded-lg">
              <p className="text-lg font-bold text-errored">
                {camRunning && gateMode === 'exit' ? (cameraStatus?.unknown_count ?? 0) : '—'}
              </p>
              <p className="text-[10px] text-muted font-semibold uppercase tracking-wider">Unknown</p>
            </div>
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={() => navigate('/monitoring?mode=exit')}
              className="flex-1 flex items-center justify-center gap-1.5 text-xs py-2 rounded-lg font-medium bg-amber text-white hover:bg-amber/90 transition-colors"
            >
              <Camera size={14} /> Open Exit Monitoring
            </button>
            {adminKey && (
              camRunning && gateMode === 'exit' ? (
                <button
                  onClick={handleStopCamera}
                  disabled={actionLoading}
                  className="btn-danger text-xs py-2 px-3.5"
                >
                  Stop
                </button>
              ) : (
                <button
                  onClick={() => handleStartGateCamera('exit')}
                  disabled={actionLoading}
                  className="btn-secondary text-xs py-2 px-3.5 font-medium"
                >
                  Start
                </button>
              )
            )}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Students Inside"
          value={loading ? '…' : (stats ? Math.max(0, (stats.entries_today ?? 0) - (stats.exits_today ?? 0)) : '—')}
          icon={Users}
          color="forest"
          subtitle={stats ? `${stats.unique_students_today ?? 0} unique students today` : 'Estimated on campus'}
        />
        <StatCard
          title="Total Entries Today"
          value={loading ? '…' : (stats?.entries_today ?? '—')}
          icon={LogIn}
          color="forest"
          subtitle="Entry gate recognition events"
        />
        <StatCard
          title="Total Exits Today"
          value={loading ? '…' : (stats?.exits_today ?? '—')}
          icon={LogOut}
          color="amber"
          subtitle="Exit gate recognition events"
        />
        <StatCard
          title="Unknown Visitors"
          value={loading ? '…' : (stats?.unknown_today ?? '—')}
          icon={AlertTriangle}
          color="red"
          subtitle="Unregistered faces today"
        />
      </div>

      {/* Chart + Recent Activity */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-5 mb-5">
        {/* Entry/Exit Comparison Chart */}
        <div className="card xl:col-span-3">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-charcoal">Today's Gate Traffic Breakdown</h2>
              <p className="text-xs text-muted mt-0.5">Entries vs Exits vs Unknown Detections</p>
            </div>
            <Activity size={16} className="text-muted" />
          </div>
          {stats ? (
            <ResponsiveContainer width="100%" height={210}>
              <BarChart
                data={[
                  { label: 'Entries', count: stats.entries_today ?? 0, fill: '#315C4A' },
                  { label: 'Exits', count: stats.exits_today ?? 0, fill: '#D58A36' },
                  { label: 'Unknown', count: stats.unknown_today ?? 0, fill: '#c2410c' },
                ]}
                barSize={36}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: '#737B78', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#737B78', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #e7e5e4', borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="count" name="Events" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex flex-col items-center justify-center text-muted text-sm">
              <Activity size={28} className="mb-2 opacity-20" />
              <span>No attendance data yet</span>
              <span className="text-xs mt-1">Start the camera to begin logging</span>
            </div>
          )}
        </div>

        {/* Recent Events */}
        <div className="card xl:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <Clock size={15} className="text-muted" />
            <h2 className="text-sm font-semibold text-charcoal">Recent Gate Activity</h2>
          </div>
          {recentEvents.length === 0 ? (
            <div className="text-center py-8 text-muted text-sm">
              <Clock size={28} className="mx-auto mb-2 opacity-20" />
              No events yet
            </div>
          ) : (
            <ul className="divide-y divide-stone-100 max-h-56 overflow-y-auto">
              {recentEvents.map((e, i) => (
                <li key={i} className="flex items-center justify-between py-2.5">
                  <div className="min-w-0 flex-1 mr-2">
                    <p className="text-sm font-medium text-charcoal truncate">
                      {e.full_name || 'Unknown'}
                    </p>
                    <p className="text-xs text-muted">{toIST(e.captured_at)}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {e.event_type === 'entry'
                      ? <span className="badge-green text-xs">Entry</span>
                      : e.event_type === 'exit'
                        ? <span className="badge-amber text-xs">Exit</span>
                        : null}
                    <StatusBadge status={e.is_known ? 'known' : 'unknown_face'} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Enrolled Students Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-charcoal">Enrolled Students ({students.length})</h2>
          <button onClick={() => navigate('/students')} className="text-xs text-forest hover:underline font-medium">
            Manage Students →
          </button>
        </div>
        {!adminKey ? (
          <p className="text-muted text-sm text-center py-6">Log in to view enrolled students</p>
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full">
              <thead className="bg-stone-50 border-y border-stone-100">
                <tr>
                  <th className="th">Student ID</th>
                  <th className="th">Name</th>
                  <th className="th">Department</th>
                  <th className="th">Photos</th>
                  <th className="th">Status</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} className="td text-center text-muted py-8">Loading…</td></tr>
                ) : students.length === 0 ? (
                  <tr><td colSpan={5} className="td text-center text-muted py-8">No students enrolled</td></tr>
                ) : (
                  students.map((s) => (
                    <tr key={s.student_id} className="tr-hover">
                      <td className="td font-mono text-xs text-forest">{s.student_id}</td>
                      <td className="td font-medium">{s.full_name}</td>
                      <td className="td text-muted">{s.department || '—'}</td>
                      <td className="td text-muted">{s.embeddings?.length ?? 0}</td>
                      <td className="td">
                        <StatusBadge status={s.is_active ? 'online' : 'offline'} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
