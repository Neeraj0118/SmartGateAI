import { useEffect, useState, useCallback } from 'react'
import {
  ShieldCheck, PlusCircle, CheckCircle, XCircle, Clock, AlertTriangle,
  Search, Filter, UserCheck, Calendar, ArrowRight, Eye, RefreshCw,
  LogOut, Building, User, Check
} from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import {
  listPermissions, createPermission, approvePermission, rejectPermission,
  listActiveOutings, listSecurityAlerts, resolveSecurityAlert, getHostelStats
} from '../api/hostelPermissions'

const EMPTY_REQUEST = {
  student_id: '',
  student_name: '',
  reason: '',
  departure_date: new Date().toISOString().split('T')[0],
  departure_time: '17:00',
  expected_return_date: new Date().toISOString().split('T')[0],
  expected_return_time: '21:00',
}

export default function HostelPermissions() {
  const { adminKey } = useAuth()

  // Active view tab: 'permissions' | 'outings' | 'alerts'
  const [activeTab, setActiveTab] = useState('permissions')
  const [statusFilter, setStatusFilter] = useState('All')
  const [search, setSearch] = useState('')

  // Data states
  const [permissions, setPermissions] = useState([])
  const [totalPermissions, setTotalPermissions] = useState(0)
  const [outings, setOutings] = useState([])
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState({
    total_permissions: 0,
    pending_count: 0,
    approved_count: 0,
    used_count: 0,
    rejected_count: 0,
    expired_count: 0,
    active_outings_count: 0,
    late_returns_count: 0,
  })

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [form, setForm] = useState(EMPTY_REQUEST)
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  const [rejectingId, setRejectingId] = useState(null)
  const [rejectionReason, setRejectionReason] = useState('')
  const [rejectSubmitting, setRejectSubmitting] = useState(false)

  const [selectedPermission, setSelectedPermission] = useState(null)

  const fetchData = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      // 1. Fetch Stats
      const statsRes = await getHostelStats(adminKey)
      setStats(statsRes.data)

      // 2. Fetch Permissions
      const permParams = {
        skip: 0,
        limit: 100,
        search: search.trim() || undefined,
        status: statusFilter === 'All' ? undefined : statusFilter,
      }
      const permRes = await listPermissions(adminKey, permParams)
      setPermissions(permRes.data.items || [])
      setTotalPermissions(permRes.data.total || 0)

      // 3. Fetch Active Outings
      const outRes = await listActiveOutings(adminKey)
      setOutings(outRes.data.items || [])

      // 4. Fetch Security Alerts
      const alertRes = await listSecurityAlerts(adminKey, { unresolved_only: false })
      setAlerts(alertRes.data.items || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load hostel permissions data')
    } finally {
      setLoading(false)
    }
  }, [adminKey, statusFilter, search])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleCreateSubmit = async (e) => {
    e.preventDefault()
    if (!form.student_id.trim() || !form.reason.trim()) {
      setFormError('Student ID and Reason are required')
      return
    }
    setFormSubmitting(true); setFormError(null)
    try {
      await createPermission(adminKey, {
        student_id: form.student_id.trim(),
        student_name: form.student_name.trim() || undefined,
        reason: form.reason.trim(),
        departure_date: form.departure_date,
        departure_time: form.departure_time,
        expected_return_date: form.expected_return_date,
        expected_return_time: form.expected_return_time,
      })
      setShowCreateModal(false)
      setForm(EMPTY_REQUEST)
      setSuccessMsg('Exit permission request submitted successfully!')
      setTimeout(() => setSuccessMsg(null), 4000)
      fetchData()
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to create permission request')
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleApprove = async (id) => {
    try {
      await approvePermission(adminKey, id)
      setSuccessMsg(`Permission #${id} approved!`)
      setTimeout(() => setSuccessMsg(null), 3000)
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to approve permission')
    }
  }

  const handleConfirmReject = async (e) => {
    e.preventDefault()
    if (!rejectingId) return
    setRejectSubmitting(true)
    try {
      await rejectPermission(adminKey, rejectingId, rejectionReason)
      setRejectingId(null)
      setRejectionReason('')
      setSuccessMsg(`Permission #${rejectingId} rejected.`)
      setTimeout(() => setSuccessMsg(null), 3000)
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reject permission')
    } finally {
      setRejectSubmitting(false)
    }
  }

  const handleResolveAlert = async (alertId) => {
    try {
      await resolveSecurityAlert(adminKey, alertId)
      fetchData()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to resolve alert')
    }
  }

  const formatIST = (isoString) => {
    if (!isoString) return '—'
    try {
      return new Date(isoString).toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      })
    } catch {
      return isoString
    }
  }

  const getStatusBadge = (st) => {
    switch (st) {
      case 'Approved':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1"><CheckCircle size={12} /> Approved</span>
      case 'Pending':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1"><Clock size={12} /> Pending</span>
      case 'Used':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1"><LogOut size={12} /> Used</span>
      case 'Rejected':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-1"><XCircle size={12} /> Rejected</span>
      case 'Expired':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-stone-100 text-stone-600 border border-stone-200 flex items-center gap-1"><Clock size={12} /> Expired</span>
      default:
        return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-stone-100 text-stone-700">{st}</span>
    }
  }

  return (
    <Layout
      title="Hostel Exit Permissions"
      subtitle="Digital Pass Verification, Outing Tracking & Security Authorization"
      actions={
        adminKey && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchData()}
              className="btn-secondary flex items-center gap-1.5 text-xs py-2 px-3"
              title="Refresh Data"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <PlusCircle size={15} /> Create Exit Pass
            </button>
          </div>
        )
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-errored text-sm flex items-center justify-between">
          <span>{error}</span>
          <button className="underline text-xs" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {successMsg && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle size={16} className="text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* High-Level Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-6">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-3 bg-amber-500/10 text-amber-600 rounded-xl">
            <Clock size={20} />
          </div>
          <div>
            <p className="text-xs text-muted font-medium">Pending Approval</p>
            <p className="text-2xl font-bold text-charcoal">{stats.pending_count}</p>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-3">
          <div className="p-3 bg-emerald-500/10 text-emerald-600 rounded-xl">
            <ShieldCheck size={20} />
          </div>
          <div>
            <p className="text-xs text-muted font-medium">Approved Passes</p>
            <p className="text-2xl font-bold text-charcoal">{stats.approved_count}</p>
          </div>
        </div>

        <div className="card p-4 flex items-center gap-3">
          <div className="p-3 bg-blue-500/10 text-blue-600 rounded-xl">
            <LogOut size={20} />
          </div>
          <div>
            <p className="text-xs text-muted font-medium">Active Outings</p>
            <p className="text-2xl font-bold text-charcoal">{stats.active_outings_count}</p>
          </div>
        </div>

        <div className={`card p-4 flex items-center gap-3 ${stats.late_returns_count > 0 ? 'border-red-300 bg-red-50/20' : ''}`}>
          <div className={`p-3 rounded-xl ${stats.late_returns_count > 0 ? 'bg-red-500/20 text-red-600 animate-pulse' : 'bg-stone-100 text-stone-600'}`}>
            <AlertTriangle size={20} />
          </div>
          <div>
            <p className="text-xs text-muted font-medium">Late / Overdue</p>
            <p className={`text-2xl font-bold ${stats.late_returns_count > 0 ? 'text-errored' : 'text-charcoal'}`}>
              {stats.late_returns_count}
            </p>
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="flex border-b border-stone-200 mb-5 gap-6">
        <button
          onClick={() => setActiveTab('permissions')}
          className={`pb-3 text-sm font-semibold transition-all relative ${
            activeTab === 'permissions'
              ? 'text-forest border-b-2 border-forest'
              : 'text-stone-500 hover:text-charcoal'
          }`}
        >
          Exit Permission Passes ({totalPermissions})
        </button>
        <button
          onClick={() => setActiveTab('outings')}
          className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${
            activeTab === 'outings'
              ? 'text-forest border-b-2 border-forest'
              : 'text-stone-500 hover:text-charcoal'
          }`}
        >
          Active Outings ({outings.length})
          {stats.active_outings_count > 0 && (
            <span className="w-2 h-2 rounded-full bg-blue-500" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-3 text-sm font-semibold transition-all relative flex items-center gap-1.5 ${
            activeTab === 'alerts'
              ? 'text-forest border-b-2 border-forest'
              : 'text-stone-500 hover:text-charcoal'
          }`}
        >
          Security Alerts ({alerts.filter(a => !a.is_resolved).length} Unresolved)
          {stats.late_returns_count > 0 && (
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
          )}
        </button>
      </div>

      {/* TAB 1: PERMISSION REQUESTS */}
      {activeTab === 'permissions' && (
        <>
          {/* Filters & Search */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div className="relative max-w-sm flex-1 min-w-[240px]">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                className="input pl-9"
                placeholder="Search by student ID, name, reason…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto p-1 bg-white border border-stone-200 rounded-xl text-xs">
              {['All', 'Pending', 'Approved', 'Used', 'Expired', 'Rejected'].map(st => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                    statusFilter === st
                      ? 'bg-forest text-white shadow-sm'
                      : 'text-stone-600 hover:text-charcoal hover:bg-stone-50'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          {/* Permissions Table */}
          <div className="card overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-stone-50 border-b border-stone-200 text-xs">
                  <tr>
                    <th className="th">Pass #</th>
                    <th className="th">Student</th>
                    <th className="th">Reason</th>
                    <th className="th">Departure Window</th>
                    <th className="th">Expected Return</th>
                    <th className="th">Status</th>
                    <th className="th">Approval / Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {loading ? (
                    <tr><td colSpan={7} className="td text-center py-10 text-muted">Loading permissions…</td></tr>
                  ) : permissions.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="td text-center py-12 text-muted">
                        <Clock size={32} className="mx-auto text-muted opacity-30 mb-2" />
                        No permission requests matching filter.
                      </td>
                    </tr>
                  ) : (
                    permissions.map(p => (
                      <tr key={p.id} className="tr-hover">
                        <td className="td font-mono font-semibold text-xs text-forest">#{p.id}</td>
                        <td className="td">
                          <p className="font-semibold text-charcoal text-sm">{p.student_name}</p>
                          <p className="font-mono text-xs text-muted">{p.student_id}</p>
                        </td>
                        <td className="td text-xs text-stone-600 max-w-[200px] truncate" title={p.reason}>
                          {p.reason}
                        </td>
                        <td className="td text-xs font-mono">
                          {p.departure_date} <span className="text-forest font-semibold">{p.departure_time}</span>
                        </td>
                        <td className="td text-xs font-mono">
                          {p.expected_return_date} <span className="text-amber-700 font-semibold">{p.expected_return_time}</span>
                        </td>
                        <td className="td">
                          {getStatusBadge(p.status)}
                        </td>
                        <td className="td">
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => setSelectedPermission(p)}
                              className="btn-ghost p-1.5 rounded-lg text-stone-600"
                              title="View Pass Details"
                            >
                              <Eye size={15} />
                            </button>

                            {p.status === 'Pending' && (
                              <>
                                <button
                                  onClick={() => handleApprove(p.id)}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm flex items-center gap-1"
                                  title="Approve Exit Pass"
                                >
                                  <Check size={13} /> Approve
                                </button>
                                <button
                                  onClick={() => setRejectingId(p.id)}
                                  className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold"
                                  title="Reject Request"
                                >
                                  Reject
                                </button>
                              </>
                            )}

                            {p.status === 'Approved' && (
                              <button
                                onClick={() => setRejectingId(p.id)}
                                className="px-2 py-1 rounded-lg text-stone-400 hover:text-rose-600 text-xs"
                                title="Revoke Approval"
                              >
                                Revoke
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* TAB 2: ACTIVE OUTINGS */}
      {activeTab === 'outings' && (
        <div className="card overflow-hidden p-0">
          <div className="p-4 bg-stone-50 border-b border-stone-200 flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-charcoal text-sm">Students Currently Outside Campus</h3>
              <p className="text-xs text-muted">Automatically created on EXIT gate authorization; cleared on ENTRY recognition.</p>
            </div>
            <span className="badge-blue text-xs font-semibold">{outings.length} Active</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-stone-100/60 border-b border-stone-200 text-xs">
                <tr>
                  <th className="th">Student</th>
                  <th className="th">Hostel & Room</th>
                  <th className="th">Actual Exit Time</th>
                  <th className="th">Expected Return</th>
                  <th className="th">Status</th>
                  <th className="th">Pass Ref</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {outings.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="td text-center py-12 text-muted">
                      All hostellers are currently inside campus. Zero active outings.
                    </td>
                  </tr>
                ) : (
                  outings.map(o => (
                    <tr key={o.id} className={`tr-hover ${o.status === 'Late' ? 'bg-red-50/40' : ''}`}>
                      <td className="td">
                        <p className="font-semibold text-charcoal text-sm">{o.student_name}</p>
                        <p className="font-mono text-xs text-muted">{o.student_id}</p>
                      </td>
                      <td className="td text-xs">
                        <span className="font-medium text-stone-700">{o.hostel_name || 'Hostel'}</span>
                        {o.room_number && <span className="ml-1 text-muted">({o.room_number})</span>}
                      </td>
                      <td className="td font-mono text-xs text-forest">
                        {formatIST(o.actual_exit_time)}
                      </td>
                      <td className="td font-mono text-xs">
                        {formatIST(o.expected_return_time)}
                      </td>
                      <td className="td">
                        {o.status === 'Late' ? (
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700 border border-red-300 flex items-center gap-1 animate-pulse">
                            <AlertTriangle size={12} /> OVERDUE / LATE
                          </span>
                        ) : (
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                            <LogOut size={12} /> Outside Campus
                          </span>
                        )}
                      </td>
                      <td className="td font-mono text-xs text-muted">
                        #{o.permission_id}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SECURITY ALERTS */}
      {activeTab === 'alerts' && (
        <div className="card overflow-hidden p-0">
          <div className="p-4 bg-stone-50 border-b border-stone-200 flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-charcoal text-sm">Gate Security Alerts & Verification Incidents</h3>
              <p className="text-xs text-muted">Tracks exit denials without passes, late returns, and unverified attempts.</p>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-stone-200 text-stone-800">
              {alerts.length} Total Alerts
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-stone-100/60 border-b border-stone-200 text-xs">
                <tr>
                  <th className="th">Alert Type</th>
                  <th className="th">Severity</th>
                  <th className="th">Student</th>
                  <th className="th">Description</th>
                  <th className="th">Timestamp</th>
                  <th className="th">Status & Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="td text-center py-12 text-muted">
                      No security alerts recorded.
                    </td>
                  </tr>
                ) : (
                  alerts.map(a => (
                    <tr key={a.id} className={`tr-hover ${!a.is_resolved ? 'bg-amber-50/20' : ''}`}>
                      <td className="td font-mono font-semibold text-xs">
                        <span className={`px-2 py-0.5 rounded-md ${
                          a.alert_type === 'HOSTEL_EXIT_DENIED' ? 'bg-red-100 text-red-800' :
                          a.alert_type === 'LATE_RETURN' ? 'bg-amber-100 text-amber-800' : 'bg-stone-100 text-stone-700'
                        }`}>
                          {a.alert_type}
                        </span>
                      </td>
                      <td className="td">
                        <span className={`text-xs font-bold ${a.severity === 'HIGH' ? 'text-red-600' : 'text-amber-600'}`}>
                          {a.severity}
                        </span>
                      </td>
                      <td className="td">
                        <p className="font-semibold text-charcoal text-sm">{a.student_name || 'N/A'}</p>
                        <p className="font-mono text-xs text-muted">{a.student_id || '—'}</p>
                      </td>
                      <td className="td text-xs text-stone-600 max-w-xs">{a.description}</td>
                      <td className="td font-mono text-xs text-muted">{formatIST(a.created_at)}</td>
                      <td className="td">
                        {a.is_resolved ? (
                          <span className="text-xs text-muted font-medium flex items-center gap-1">
                            <Check size={13} className="text-emerald-600" /> Resolved ({a.resolved_by})
                          </span>
                        ) : (
                          <button
                            onClick={() => handleResolveAlert(a.id)}
                            className="btn-secondary text-xs py-1 px-2.5 font-semibold text-forest hover:bg-forest/10"
                          >
                            Mark Resolved
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE EXIT PASS MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-stone-200 w-full max-w-lg shadow-elevated max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-stone-100 sticky top-0 bg-white z-10">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-forest/10 rounded-lg text-forest">
                  <ShieldCheck size={18} />
                </div>
                <div>
                  <h2 className="font-semibold text-charcoal">Create Hostel Exit Pass</h2>
                  <p className="text-xs text-muted">Authorizes hosteller outing through the EXIT gate</p>
                </div>
              </div>
              <button
                onClick={() => { setShowCreateModal(false); setFormError(null) }}
                className="text-muted hover:text-charcoal"
              >
                <XCircle size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-5 space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Student ID *</label>
                  <input
                    className="input"
                    value={form.student_id}
                    onChange={e => setForm({ ...form, student_id: e.target.value })}
                    placeholder="e.g. 230111472"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Student Name (Optional)</label>
                  <input
                    className="input"
                    value={form.student_name}
                    onChange={e => setForm({ ...form, student_name: e.target.value })}
                    placeholder="Defaults to registered name"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-muted mb-1 block font-medium">Reason for Leaving *</label>
                <textarea
                  className="input min-h-[70px] resize-none"
                  value={form.reason}
                  onChange={e => setForm({ ...form, reason: e.target.value })}
                  placeholder="e.g. Family Function, Medical Emergency, Project Work, Weekend Outing"
                  required
                />
              </div>

              {/* Scheduled Departure Window */}
              <div className="p-3.5 bg-stone-50 border border-stone-200 rounded-xl space-y-3">
                <p className="text-xs font-semibold text-charcoal flex items-center gap-1.5">
                  <Calendar size={13} className="text-forest" /> Scheduled Departure Window
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-muted mb-1 block font-medium">Departure Date</label>
                    <input
                      type="date"
                      className="input bg-white"
                      value={form.departure_date}
                      onChange={e => setForm({ ...form, departure_date: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted mb-1 block font-medium">Departure Time (IST)</label>
                    <input
                      type="time"
                      className="input bg-white"
                      value={form.departure_time}
                      onChange={e => setForm({ ...form, departure_time: e.target.value })}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Expected Return Window */}
              <div className="p-3.5 bg-amber-50/50 border border-amber-200 rounded-xl space-y-3">
                <p className="text-xs font-semibold text-amber-900 flex items-center gap-1.5">
                  <Clock size={13} className="text-amber-700" /> Expected Return Window
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-muted mb-1 block font-medium">Return Date</label>
                    <input
                      type="date"
                      className="input bg-white"
                      value={form.expected_return_date}
                      onChange={e => setForm({ ...form, expected_return_date: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted mb-1 block font-medium">Return Time (IST)</label>
                    <input
                      type="time"
                      className="input bg-white"
                      value={form.expected_return_time}
                      onChange={e => setForm({ ...form, expected_return_time: e.target.value })}
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="btn-primary flex-1 font-semibold"
                >
                  {formSubmitting ? 'Submitting…' : 'Submit Permission Request'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REJECTION REASON MODAL */}
      {rejectingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-stone-200 w-full max-w-sm shadow-elevated p-5">
            <h3 className="font-semibold text-charcoal mb-1">Reject Permission #{rejectingId}</h3>
            <p className="text-xs text-muted mb-3">Provide an administrative reason for denying this pass.</p>

            <form onSubmit={handleConfirmReject} className="space-y-3">
              <textarea
                className="input min-h-[80px] resize-none"
                placeholder="Reason for rejection (e.g. Incomplete parent consent, curfew hours)…"
                value={rejectionReason}
                onChange={e => setRejectionReason(e.target.value)}
                required
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={rejectSubmitting}
                  className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-sm font-semibold flex-1"
                >
                  {rejectSubmitting ? 'Rejecting…' : 'Confirm Rejection'}
                </button>
                <button
                  type="button"
                  onClick={() => setRejectingId(null)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VIEW PASS DETAILS MODAL */}
      {selectedPermission && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-stone-200 w-full max-w-md shadow-elevated p-5">
            <div className="flex items-center justify-between pb-3 border-b border-stone-100 mb-4">
              <div className="flex items-center gap-2">
                <ShieldCheck size={18} className="text-forest" />
                <h3 className="font-semibold text-charcoal">Exit Pass #{selectedPermission.id}</h3>
              </div>
              <button onClick={() => setSelectedPermission(null)} className="text-muted hover:text-charcoal">
                <XCircle size={18} />
              </button>
            </div>

            <div className="space-y-2.5 text-sm">
              <div className="flex justify-between py-1 border-b border-stone-50">
                <span className="text-muted">Student Name</span>
                <span className="font-semibold text-charcoal">{selectedPermission.student_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-stone-50">
                <span className="text-muted">Student ID</span>
                <span className="font-mono text-forest">{selectedPermission.student_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-stone-50">
                <span className="text-muted">Status</span>
                <span>{getStatusBadge(selectedPermission.status)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-stone-50">
                <span className="text-muted">Departure Window</span>
                <span className="font-mono text-xs">{selectedPermission.departure_date} {selectedPermission.departure_time}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-stone-50">
                <span className="text-muted">Return Window</span>
                <span className="font-mono text-xs text-amber-800">{selectedPermission.expected_return_date} {selectedPermission.expected_return_time}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-stone-50">
                <span className="text-muted">Reason</span>
                <span className="text-right text-stone-700 text-xs max-w-[220px]">{selectedPermission.reason}</span>
              </div>
              {selectedPermission.approved_by && (
                <div className="flex justify-between py-1 border-b border-stone-50">
                  <span className="text-muted">Approved By</span>
                  <span className="font-medium text-emerald-700">{selectedPermission.approved_by}</span>
                </div>
              )}
              {selectedPermission.rejection_reason && (
                <div className="flex justify-between py-1 border-b border-stone-50">
                  <span className="text-muted">Rejection Note</span>
                  <span className="text-rose-700 text-xs">{selectedPermission.rejection_reason}</span>
                </div>
              )}
              {selectedPermission.used_at && (
                <div className="flex justify-between py-1 border-b border-stone-50">
                  <span className="text-muted">Actual Exit Time</span>
                  <span className="font-mono text-xs text-blue-700">{formatIST(selectedPermission.used_at)}</span>
                </div>
              )}
            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setSelectedPermission(null)}
                className="btn-secondary text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
