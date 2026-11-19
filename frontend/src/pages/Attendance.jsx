import { useEffect, useState, useCallback } from 'react'
import { Search, Download, ChevronLeft, ChevronRight, ClipboardList, LogIn, LogOut } from 'lucide-react'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { listAttendance, exportAttendanceCsv } from '../api/attendance'
import { toIST } from '../utils/time'

const PAGE_SIZE = 25

function EventTypeBadge({ type }) {
  if (type === 'entry') return (
    <span className="inline-flex items-center gap-1 badge-green text-xs font-medium">
      <LogIn size={11} /> Entry
    </span>
  )
  if (type === 'exit') return (
    <span className="inline-flex items-center gap-1 badge-amber text-xs font-medium">
      <LogOut size={11} /> Exit
    </span>
  )
  return <span className="badge-slate text-xs">{type || 'detection'}</span>
}

export default function Attendance() {
  const { adminKey } = useAuth()
  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)
  const [dateFilter, setDateFilter] = useState('')
  const [knownFilter, setKnownFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('')
  const [searchId, setSearchId] = useState('')

  const fetchAttendance = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    const params = { skip: page * PAGE_SIZE, limit: PAGE_SIZE }
    if (dateFilter) params.date_filter = dateFilter
    if (knownFilter !== 'all') params.is_known = knownFilter === 'known'
    if (typeFilter) params.event_type = typeFilter
    if (searchId.trim()) params.student_id_search = searchId.trim()
    try {
      const r = await listAttendance(adminKey, params)
      setRecords(r.data?.items || [])
      setTotal(r.data?.total ?? 0)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load attendance records')
    } finally { setLoading(false) }
  }, [adminKey, page, dateFilter, knownFilter, typeFilter, searchId])

  useEffect(() => { fetchAttendance() }, [fetchAttendance])

  const handleExport = async () => {
    if (!adminKey) return
    setExporting(true)
    try {
      const params = {}
      if (dateFilter) params.date_filter = dateFilter
      if (knownFilter !== 'all') params.is_known = knownFilter === 'known'
      if (typeFilter) params.event_type = typeFilter
      if (searchId.trim()) params.student_id_search = searchId.trim()
      const r = await exportAttendanceCsv(adminKey, params)
      const url = URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `attendance_${new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError('CSV export failed')
    } finally { setExporting(false) }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const clearFilters = () => { setDateFilter(''); setKnownFilter('all'); setTypeFilter(''); setSearchId(''); setPage(0) }
  const hasFilters = dateFilter || knownFilter !== 'all' || typeFilter || searchId

  return (
    <Layout
      title="Attendance Records"
      subtitle={`${total} recognition events logged`}
      actions={
        adminKey && (
          <button onClick={handleExport} disabled={exporting} className="btn-secondary flex items-center gap-2 text-sm">
            <Download size={14} /> {exporting ? 'Exporting…' : 'Export CSV (IST)'}
          </button>
        )
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input pl-9 w-44 text-sm" placeholder="Student ID…"
            value={searchId} onChange={e => { setSearchId(e.target.value); setPage(0) }} />
        </div>
        <input type="date" className="input w-40 text-sm" value={dateFilter}
          onChange={e => { setDateFilter(e.target.value); setPage(0) }} />
        <select className="input w-36 text-sm" value={knownFilter}
          onChange={e => { setKnownFilter(e.target.value); setPage(0) }}>
          <option value="all">All faces</option>
          <option value="known">Known only</option>
          <option value="unknown">Unknown only</option>
        </select>
        <select className="input w-36 text-sm" value={typeFilter}
          onChange={e => { setTypeFilter(e.target.value); setPage(0) }}>
          <option value="">All types</option>
          <option value="entry">Entry only</option>
          <option value="exit">Exit only</option>
        </select>
        {hasFilters && (
          <button onClick={clearFilters} className="btn-ghost text-sm">Clear</button>
        )}
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="th">Time (IST)</th>
                <th className="th">Student ID</th>
                <th className="th">Name</th>
                <th className="th">Type</th>
                <th className="th">Gate</th>
                <th className="th">Confidence</th>
                <th className="th">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="td text-center text-muted py-10">Loading…</td></tr>
              ) : !adminKey ? (
                <tr><td colSpan={7} className="td text-center text-muted py-10">Log in to view attendance</td></tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={7} className="td text-center py-14">
                    <ClipboardList size={32} className="mx-auto text-muted opacity-20 mb-2" />
                    <p className="text-muted text-sm">No attendance records found</p>
                    <p className="text-muted text-xs mt-1">Start the camera to begin logging recognition events</p>
                  </td>
                </tr>
              ) : (
                records.map((r, i) => (
                  <tr key={r.id ?? i} className="tr-hover">
                    <td className="td text-xs text-muted whitespace-nowrap">{toIST(r.captured_at)}</td>
                    <td className="td font-mono text-xs text-forest">{r.student_id || '—'}</td>
                    <td className="td font-medium text-charcoal">{r.full_name || 'Unknown'}</td>
                    <td className="td"><EventTypeBadge type={r.event_type} /></td>
                    <td className="td text-xs text-muted capitalize">{r.gate_id || 'main'}</td>
                    <td className="td font-mono text-xs text-muted">
                      {r.similarity != null ? (r.similarity * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td className="td">
                      <StatusBadge status={r.is_known ? 'known' : 'unknown_face'} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-stone-100 text-sm text-muted">
            <span>Page {page + 1} of {totalPages} · {total} records</span>
            <div className="flex gap-1">
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                className="btn-secondary py-1 px-2 disabled:opacity-40">
                <ChevronLeft size={15} />
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
                className="btn-secondary py-1 px-2 disabled:opacity-40">
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
