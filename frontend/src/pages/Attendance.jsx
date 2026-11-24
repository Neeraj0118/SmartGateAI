import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Search, Download, ChevronLeft, ChevronRight, ClipboardList, LogIn, LogOut,
  Calendar, RefreshCw, Filter, Users, Building, Sparkles
} from 'lucide-react'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { listAttendance, exportAttendanceCsv } from '../api/attendance'
import { toIST } from '../utils/time'

const PAGE_SIZE = 25

function EventTypeBadge({ type }) {
  if (type === 'entry') return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
      <LogIn size={11} /> Entry
    </span>
  )
  if (type === 'exit') return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
      <LogOut size={11} /> Exit
    </span>
  )
  return <span className="badge-slate text-xs">{type || 'detection'}</span>
}

export default function Attendance() {
  const { adminKey } = useAuth()

  // Calculate Today and Yesterday strings in IST (YYYY-MM-DD)
  const todayIST = useMemo(() => {
    return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })
  }, [])

  const yesterdayIST = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() - 1)
    return d.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })
  }, [])

  const [records, setRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)

  // Default to Today's IST date so today's live entries are highlighted
  const [dateFilter, setDateFilter] = useState(todayIST)
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [knownFilter, setKnownFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('')
  const [searchId, setSearchId] = useState('')

  const fetchAttendance = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    const params = { skip: page * PAGE_SIZE, limit: PAGE_SIZE }
    if (dateFilter) params.date_filter = dateFilter
    if (categoryFilter !== 'all') params.category = categoryFilter
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
  }, [adminKey, page, dateFilter, categoryFilter, knownFilter, typeFilter, searchId])

  useEffect(() => { fetchAttendance() }, [fetchAttendance])

  const handleExport = async () => {
    if (!adminKey) return
    setExporting(true)
    try {
      const params = {}
      if (dateFilter) params.date_filter = dateFilter
      if (categoryFilter !== 'all') params.category = categoryFilter
      if (knownFilter !== 'all') params.is_known = knownFilter === 'known'
      if (typeFilter) params.event_type = typeFilter
      if (searchId.trim()) params.student_id_search = searchId.trim()
      const r = await exportAttendanceCsv(adminKey, params)
      const url = URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a')
      a.href = url
      const dateLabel = dateFilter || 'all_dates'
      a.download = `attendance_${dateLabel}_${new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError('CSV export failed')
    } finally { setExporting(false) }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const clearFilters = () => {
    setDateFilter('')
    setCategoryFilter('all')
    setKnownFilter('all')
    setTypeFilter('')
    setSearchId('')
    setPage(0)
  }

  const isToday = dateFilter === todayIST
  const isYesterday = dateFilter === yesterdayIST
  const isAllDates = dateFilter === ''

  return (
    <Layout
      title="Attendance & Gate Activity Log"
      subtitle={`${total} recognition event(s) logged ${dateFilter ? `for ${dateFilter}` : 'in total'}`}
      actions={
        adminKey && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchAttendance()}
              className="btn-secondary flex items-center gap-1.5 text-xs py-2 px-3"
              title="Refresh attendance"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
            </button>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Download size={14} /> {exporting ? 'Exporting…' : 'Export CSV (IST)'}
            </button>
          </div>
        )
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm flex items-center justify-between">
          <span>{error}</span>
          <button className="underline text-xs" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Date Filter & Selector Bar */}
      <div className="card p-4 mb-4 border-l-4 border-forest bg-gradient-to-r from-stone-50 via-white to-stone-50/50">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Quick Date Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-charcoal uppercase tracking-wider flex items-center gap-1.5 mr-1">
              <Calendar size={14} className="text-forest" /> Date Selection:
            </span>
            <button
              type="button"
              onClick={() => { setDateFilter(todayIST); setPage(0) }}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                isToday
                  ? 'bg-forest text-white shadow-sm'
                  : 'bg-white border border-stone-200 text-stone-700 hover:bg-stone-50'
              }`}
            >
              <span>Today (Live)</span>
              {isToday && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />}
            </button>
            <button
              type="button"
              onClick={() => { setDateFilter(yesterdayIST); setPage(0) }}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                isYesterday
                  ? 'bg-forest text-white shadow-sm'
                  : 'bg-white border border-stone-200 text-stone-700 hover:bg-stone-50'
              }`}
            >
              Yesterday
            </button>
            <button
              type="button"
              onClick={() => { setDateFilter(''); setPage(0) }}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                isAllDates
                  ? 'bg-forest text-white shadow-sm'
                  : 'bg-white border border-stone-200 text-stone-700 hover:bg-stone-50'
              }`}
            >
              All Dates
            </button>
          </div>

          {/* Custom Date Picker */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-muted">Specific Date:</label>
            <input
              type="date"
              className="input bg-white text-xs py-1.5 px-3 w-40 font-semibold text-charcoal"
              value={dateFilter}
              onChange={e => { setDateFilter(e.target.value); setPage(0) }}
            />
          </div>
        </div>

        {/* Status info bar */}
        <div className="mt-2.5 pt-2 border-t border-stone-100 flex flex-wrap items-center justify-between text-xs text-muted">
          <span>
            {isToday ? (
              <span className="text-emerald-700 font-semibold flex items-center gap-1">
                ● Live Attendance: New gate entries/exits today appear automatically here
              </span>
            ) : dateFilter ? (
              <span>Viewing historical attendance records for <strong>{dateFilter}</strong></span>
            ) : (
              <span>Viewing all historical records across all dates</span>
            )}
          </span>
          <span className="font-mono text-stone-500">
            {records.length} of {total} record(s) on current page
          </span>
        </div>
      </div>

      {/* Secondary Search & Facet Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            className="input pl-9 text-xs py-2"
            placeholder="Search student ID or name…"
            value={searchId}
            onChange={e => { setSearchId(e.target.value); setPage(0) }}
          />
        </div>

        {/* Student Category Selector */}
        <div className="flex items-center gap-1.5 bg-white border border-stone-200 rounded-lg p-0.5 text-xs">
          {['all', 'Hosteller', 'Day Scholar'].map(cat => (
            <button
              key={cat}
              type="button"
              onClick={() => { setCategoryFilter(cat); setPage(0) }}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                categoryFilter === cat
                  ? 'bg-forest text-white shadow-sm'
                  : 'text-stone-600 hover:text-charcoal hover:bg-stone-50'
              }`}
            >
              {cat === 'all' ? 'All Categories' : cat}
            </button>
          ))}
        </div>

        {/* Gate Event Type Selector */}
        <div className="flex items-center gap-1.5 bg-white border border-stone-200 rounded-lg p-0.5 text-xs">
          {[
            { id: '', label: 'All Gates' },
            { id: 'entry', label: 'Entry Only' },
            { id: 'exit', label: 'Exit Only' },
          ].map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => { setTypeFilter(id); setPage(0) }}
              className={`px-3 py-1 rounded-md font-medium transition-all ${
                typeFilter === id
                  ? 'bg-forest text-white shadow-sm'
                  : 'text-stone-600 hover:text-charcoal hover:bg-stone-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Known/Unknown Selector */}
        <select
          className="input bg-white text-xs py-2 w-32"
          value={knownFilter}
          onChange={e => { setKnownFilter(e.target.value); setPage(0) }}
        >
          <option value="all">All Faces</option>
          <option value="known">Known Only</option>
          <option value="unknown">Unknown Only</option>
        </select>

        {(dateFilter || categoryFilter !== 'all' || knownFilter !== 'all' || typeFilter || searchId) && (
          <button onClick={clearFilters} className="btn-ghost text-xs text-rose-600 hover:bg-rose-50 px-2 py-1.5 rounded-lg">
            Reset Filters
          </button>
        )}
      </div>

      {/* Attendance Table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-stone-50 border-b border-stone-200 text-xs">
              <tr>
                <th className="th">Time (IST)</th>
                <th className="th">Student ID</th>
                <th className="th">Name</th>
                <th className="th">Category</th>
                <th className="th">Event Type</th>
                <th className="th">Gate ID</th>
                <th className="th">Confidence</th>
                <th className="th">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {loading ? (
                <tr><td colSpan={8} className="td text-center text-muted py-10">Loading attendance records…</td></tr>
              ) : !adminKey ? (
                <tr><td colSpan={8} className="td text-center text-muted py-10">Log in as administrator to view attendance logs.</td></tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={8} className="td text-center py-14">
                    <ClipboardList size={32} className="mx-auto text-muted opacity-25 mb-2" />
                    <p className="text-charcoal font-semibold text-sm">No attendance records found</p>
                    <p className="text-muted text-xs mt-1">
                      {dateFilter
                        ? `No entry or exit events were recorded on ${dateFilter}.`
                        : 'No events found matching current search criteria.'}
                    </p>
                  </td>
                </tr>
              ) : (
                records.map((r, i) => (
                  <tr key={r.id ?? i} className="tr-hover">
                    <td className="td text-xs font-mono text-muted whitespace-nowrap">
                      {toIST(r.captured_at)}
                    </td>
                    <td className="td font-mono text-xs text-forest font-semibold">
                      {r.student_id || '—'}
                    </td>
                    <td className="td font-semibold text-charcoal text-sm">
                      {r.full_name || 'Unknown Person'}
                    </td>
                    <td className="td">
                      {r.category ? (
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                          r.category === 'Hosteller'
                            ? 'bg-purple-100 text-purple-800 border border-purple-200'
                            : 'bg-stone-100 text-stone-700 border border-stone-200'
                        }`}>
                          {r.category}
                        </span>
                      ) : (
                        <span className="text-stone-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="td">
                      <EventTypeBadge type={r.event_type} />
                    </td>
                    <td className="td text-xs text-muted uppercase font-mono">
                      {r.gate_id ? `${r.gate_id} gate` : 'main gate'}
                    </td>
                    <td className="td font-mono text-xs text-muted">
                      {r.similarity != null ? `${(r.similarity * 100).toFixed(1)}%` : '—'}
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

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-stone-100 text-xs text-muted bg-stone-50/50">
            <span>Page {page + 1} of {totalPages} · {total} total records</span>
            <div className="flex gap-1.5">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-secondary py-1 px-2.5 disabled:opacity-40 text-xs"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="btn-secondary py-1 px-2.5 disabled:opacity-40 text-xs"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
