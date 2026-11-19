import { useEffect, useState, useCallback } from 'react'
import { UserX, Eye, CheckCircle, RefreshCw } from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { listAttendance } from '../api/attendance'
import { toIST } from '../utils/time'

export default function Visitors() {
  const { adminKey } = useAuth()
  const [visitors, setVisitors] = useState([])
  const [reviewed, setReviewed] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dateFilter, setDateFilter] = useState('')

  const fetchVisitors = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      const params = { is_known: false, limit: 100 }
      if (dateFilter) params.date_filter = dateFilter
      const r = await listAttendance(adminKey, params)
      setVisitors(r.data?.items || [])
    } catch (e) {
      setError('Failed to load visitor events')
    } finally { setLoading(false) }
  }, [adminKey, dateFilter])

  useEffect(() => { fetchVisitors() }, [fetchVisitors])

  const markReviewed = (id) => setReviewed(s => new Set([...s, id]))

  return (
    <Layout
      title="Unknown Visitors"
      subtitle="Unrecognised face detection events"
      actions={
        <div className="flex items-center gap-2">
          <input type="date" className="input text-sm w-40" value={dateFilter}
            onChange={e => setDateFilter(e.target.value)} />
          <button onClick={fetchVisitors} className="btn-secondary flex items-center gap-2 text-sm">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">{error}</div>
      )}

      {/* Privacy notice */}
      <div className="card-inset mb-5 text-sm text-muted border-l-4 border-amber">
        <strong className="text-charcoal">Privacy Notice</strong>
        <p className="mt-1">
          Unknown visitor events are logged with timestamp and recognition metadata only.
          Face snapshots are not stored. Unknown persons are <strong>never</strong> automatically enrolled.
          Mark events as reviewed after inspection.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-3 gap-4 mb-5">
        <div className="card text-center">
          <UserX size={22} className="mx-auto text-errored mb-2" />
          <p className="text-2xl font-bold tabular-nums">{loading ? '…' : visitors.length}</p>
          <p className="text-xs text-muted mt-1">Unknown Events</p>
        </div>
        <div className="card text-center">
          <CheckCircle size={22} className="mx-auto text-forest mb-2" />
          <p className="text-2xl font-bold tabular-nums">{reviewed.size}</p>
          <p className="text-xs text-muted mt-1">Reviewed</p>
        </div>
        <div className="card text-center">
          <Eye size={22} className="mx-auto text-amber mb-2" />
          <p className="text-2xl font-bold tabular-nums">{visitors.length - reviewed.size}</p>
          <p className="text-xs text-muted mt-1">Pending Review</p>
        </div>
      </div>

      {/* Visitor Events */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="th">Detected At (IST)</th>
                <th className="th">Event ID</th>
                <th className="th">Closest Match</th>
                <th className="th">Confidence</th>
                <th className="th">Gate</th>
                <th className="th">Review Status</th>
                <th className="th">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="td text-center text-muted py-10">Loading…</td></tr>
              ) : !adminKey ? (
                <tr><td colSpan={7} className="td text-center text-muted py-10">Log in to view visitor events</td></tr>
              ) : visitors.length === 0 ? (
                <tr>
                  <td colSpan={7} className="td text-center py-14">
                    <UserX size={32} className="mx-auto text-muted opacity-20 mb-2" />
                    <p className="text-muted text-sm">No unknown visitor events</p>
                    <p className="text-xs text-muted mt-1">Events appear here when the camera detects unrecognised faces</p>
                  </td>
                </tr>
              ) : (
                visitors.map((v, i) => {
                  const isReviewed = reviewed.has(v.id)
                  return (
                    <tr key={v.id ?? i} className={`tr-hover ${isReviewed ? 'opacity-60' : ''}`}>
                      <td className="td text-xs text-muted whitespace-nowrap">{toIST(v.captured_at)}</td>
                      <td className="td font-mono text-xs text-muted">#{v.id}</td>
                      <td className="td text-muted italic text-sm">Unknown person</td>
                      <td className="td font-mono text-xs text-muted">
                        {v.similarity != null ? (v.similarity * 100).toFixed(1) + '%' : 'N/A'}
                      </td>
                      <td className="td text-xs text-muted capitalize">{v.gate_id || v.event_type || 'main'}</td>
                      <td className="td">
                        {isReviewed
                          ? <span className="badge-green">Reviewed</span>
                          : <span className="badge-amber">Pending</span>}
                      </td>
                      <td className="td">
                        {!isReviewed && (
                          <button
                            onClick={() => markReviewed(v.id)}
                            className="btn-secondary text-xs py-1 px-2.5 flex items-center gap-1"
                          >
                            <CheckCircle size={12} /> Review
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  )
}
