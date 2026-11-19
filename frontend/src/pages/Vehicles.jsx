import { useEffect, useState, useCallback } from 'react'
import { Car, Plus, Trash2, Search, RefreshCw, Info, X } from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { listVehicles, registerVehicle, deleteVehicle } from '../api/vehicles'

const VEHICLE_TYPES = ['car', 'motorcycle', 'bicycle', 'bus', 'truck', 'auto', 'other']

const EMPTY_FORM = {
  vehicle_number: '',
  owner_name: '',
  vehicle_type: 'car',
  vehicle_make: '',
  vehicle_color: '',
  associated_student_id: '',
  notes: '',
}

function fmt(dt) {
  if (!dt) return '-'
  try { return new Date(dt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) }
  catch { return dt }
}

export default function Vehicles() {
  const { adminKey } = useAuth()
  const [vehicles, setVehicles] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  const fetchVehicles = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      const r = await listVehicles(adminKey, { active_only: true })
      setVehicles(r.data?.items || [])
      setTotal(r.data?.total ?? 0)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load vehicles')
    } finally { setLoading(false) }
  }, [adminKey])

  useEffect(() => { fetchVehicles() }, [fetchVehicles])

  const filtered = vehicles.filter(v => {
    const q = search.toLowerCase()
    return !q || v.vehicle_number?.toLowerCase().includes(q) || v.owner_name?.toLowerCase().includes(q)
  })

  const handleField = (k, val) => setForm(f => ({ ...f, [k]: val }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError(null)
    if (!form.vehicle_number.trim()) { setFormError('Vehicle number is required'); return }
    if (!form.owner_name.trim()) { setFormError('Owner name is required'); return }
    setSubmitting(true)
    try {
      await registerVehicle(adminKey, {
        vehicle_number: form.vehicle_number.trim(),
        owner_name: form.owner_name.trim(),
        vehicle_type: form.vehicle_type,
        vehicle_make: form.vehicle_make.trim() || null,
        vehicle_color: form.vehicle_color.trim() || null,
        associated_student_id: form.associated_student_id.trim() || null,
        notes: form.notes.trim() || null,
      })
      setShowModal(false)
      setForm(EMPTY_FORM)
      fetchVehicles()
    } catch (e) {
      setFormError(e.response?.data?.detail || 'Failed to register vehicle')
    } finally { setSubmitting(false) }
  }

  const handleDelete = async (id, number) => {
    if (!window.confirm(`Remove vehicle ${number}?`)) return
    try {
      await deleteVehicle(adminKey, id)
      fetchVehicles()
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to remove vehicle')
    }
  }

  return (
    <Layout
      title="Vehicle Management"
      subtitle="Register and manage campus vehicles"
      actions={
        <div className="flex items-center gap-2">
          <button onClick={fetchVehicles} className="btn-secondary flex items-center gap-2 text-sm">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          {adminKey && (
            <button
              onClick={() => { setShowModal(true); setFormError(null); setForm(EMPTY_FORM) }}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus size={14} /> Register Vehicle
            </button>
          )}
        </div>
      }
    >
      {/* Info banner */}
      <div className="card mb-5 border-l-4 border-amber">
        <div className="flex items-start gap-3">
          <Info size={18} className="text-amber mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-semibold text-charcoal text-sm">Manual Registration Mode</h3>
            <p className="text-xs text-muted mt-1 leading-relaxed">
              Vehicles are registered manually. Automatic number-plate recognition (ANPR) is a
              planned future module requiring YOLOv8 + OCR integration.
            </p>
          </div>
        </div>
      </div>

      {/* Search + stats row */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search by number plate or owner..."
            className="input pl-9 w-full text-sm"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Car size={15} className="text-forest" />
          <span>{total} registered vehicle{total !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">
          {error}
        </div>
      )}

      {/* Table / empty state */}
      {loading ? (
        <div className="card flex items-center justify-center h-32 text-muted">
          <RefreshCw size={18} className="animate-spin mr-2" /> Loading vehicles...
        </div>
      ) : filtered.length === 0 ? (
        <div className="card flex flex-col items-center justify-center h-40 text-muted gap-3">
          <Car size={32} className="opacity-30" />
          <div className="text-center">
            <p className="font-medium text-charcoal">No vehicles registered</p>
            <p className="text-sm mt-1">
              {adminKey ? 'Click "Register Vehicle" to add one.' : 'Please log in to manage vehicles.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-stone-200 bg-stone-50">
                  <th className="text-left px-4 py-3 font-semibold text-muted">Number Plate</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted">Owner</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted">Type</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted">Make / Colour</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted">Student ID</th>
                  <th className="text-left px-4 py-3 font-semibold text-muted">Registered</th>
                  {adminKey && <th className="px-4 py-3"></th>}
                </tr>
              </thead>
              <tbody>
                {filtered.map((v, i) => (
                  <tr key={v.id} className={`border-b border-stone-100 hover:bg-stone-50 transition-colors ${i % 2 === 1 ? 'bg-stone-50/40' : ''}`}>
                    <td className="px-4 py-3">
                      <span className="font-mono font-bold text-charcoal tracking-wider text-sm bg-stone-100 px-2 py-0.5 rounded">
                        {v.vehicle_number}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-charcoal">{v.owner_name}</td>
                    <td className="px-4 py-3">
                      <span className="badge-forest capitalize">{v.vehicle_type}</span>
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {[v.vehicle_make, v.vehicle_color].filter(Boolean).join(' / ') || '-'}
                    </td>
                    <td className="px-4 py-3 text-muted font-mono text-xs">
                      {v.associated_student_id || '-'}
                    </td>
                    <td className="px-4 py-3 text-muted text-xs">{fmt(v.created_at)}</td>
                    {adminKey && (
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleDelete(v.id, v.vehicle_number)}
                          className="text-muted hover:text-errored transition-colors p-1"
                          title="Remove vehicle"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Register Vehicle Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-ivory rounded-xl shadow-2xl w-full max-w-lg max-h-screen overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-stone-200">
              <h2 className="font-bold text-charcoal flex items-center gap-2">
                <Car size={18} className="text-forest" /> Register Vehicle
              </h2>
              <button onClick={() => setShowModal(false)} className="text-muted hover:text-charcoal">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-charcoal mb-1">
                    Number Plate <span className="text-errored">*</span>
                  </label>
                  <input
                    type="text"
                    className="input w-full font-mono uppercase tracking-wider"
                    placeholder="e.g. UP32AB1234"
                    value={form.vehicle_number}
                    onChange={e => handleField('vehicle_number', e.target.value)}
                    required
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-charcoal mb-1">
                    Owner Name <span className="text-errored">*</span>
                  </label>
                  <input
                    type="text"
                    className="input w-full"
                    placeholder="Full name of owner"
                    value={form.owner_name}
                    onChange={e => handleField('owner_name', e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-charcoal mb-1">Vehicle Type</label>
                  <select
                    className="input w-full"
                    value={form.vehicle_type}
                    onChange={e => handleField('vehicle_type', e.target.value)}
                  >
                    {VEHICLE_TYPES.map(t => (
                      <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-charcoal mb-1">Colour</label>
                  <input
                    type="text"
                    className="input w-full"
                    placeholder="e.g. Silver"
                    value={form.vehicle_color}
                    onChange={e => handleField('vehicle_color', e.target.value)}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-charcoal mb-1">Make / Model</label>
                  <input
                    type="text"
                    className="input w-full"
                    placeholder="e.g. Honda Activa"
                    value={form.vehicle_make}
                    onChange={e => handleField('vehicle_make', e.target.value)}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-charcoal mb-1">
                    Associated Student ID <span className="text-muted text-xs">(optional)</span>
                  </label>
                  <input
                    type="text"
                    className="input w-full font-mono"
                    placeholder="e.g. 230111472"
                    value={form.associated_student_id}
                    onChange={e => handleField('associated_student_id', e.target.value)}
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-charcoal mb-1">Notes</label>
                  <textarea
                    className="input w-full resize-none"
                    rows={2}
                    placeholder="Optional notes..."
                    value={form.notes}
                    onChange={e => handleField('notes', e.target.value)}
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                >
                  {submitting
                    ? <><RefreshCw size={14} className="animate-spin" /> Registering...</>
                    : <><Plus size={14} /> Register Vehicle</>
                  }
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  )
}
