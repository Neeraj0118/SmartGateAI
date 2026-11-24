import { useEffect, useState, useRef, useCallback } from 'react'
import { UserPlus, Trash2, Search, Upload, X, Eye, Users, Edit3, Building, Home } from 'lucide-react'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { listStudents, registerStudent, deleteStudent, updateStudent } from '../api/students'

const EMPTY_FORM = {
  student_id: '',
  full_name: '',
  department: '',
  email: '',
  phone: '',
  category: 'Day Scholar',
  hostel_name: '',
  hostel_block: '',
  room_number: '',
  consent_given: false,
}

export default function Students() {
  const { adminKey } = useAuth()
  const [students, setStudents] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [photos, setPhotos] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  // Profile modal & Edit modal
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [editingStudent, setEditingStudent] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [editError, setEditError] = useState(null)

  const fileRef = useRef()

  const fetchStudents = useCallback(async () => {
    if (!adminKey) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      const r = await listStudents(adminKey, { active_only: false })
      const items = r.data?.items || []
      setStudents(items)
      setTotal(r.data?.total ?? items.length)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load students. Check your admin key.')
    } finally { setLoading(false) }
  }, [adminKey])

  useEffect(() => { fetchStudents() }, [fetchStudents])

  const filtered = students.filter(s => {
    const q = search.toLowerCase()
    const matchesSearch = !q || s.full_name?.toLowerCase().includes(q) || s.student_id?.toLowerCase().includes(q)
    const matchesCategory = categoryFilter === 'all' || s.category === categoryFilter
    return matchesSearch && matchesCategory
  })

  const handleField = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const handleEditField = (k, v) => setEditForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.student_id.trim() || !form.full_name.trim()) {
      setFormError('Student ID and Full Name are required'); return
    }
    if (!form.consent_given) {
      setFormError('Biometric consent must be confirmed'); return
    }
    if (photos.length === 0) {
      setFormError('At least one face photo is required'); return
    }
    setSubmitting(true); setFormError(null)
    try {
      const fd = new FormData()
      fd.append('student_id', form.student_id.trim())
      fd.append('full_name', form.full_name.trim())
      fd.append('department', form.department.trim())
      fd.append('email', form.email.trim())
      fd.append('phone', form.phone.trim())
      fd.append('category', form.category)
      if (form.category === 'Hosteller') {
        fd.append('hostel_name', form.hostel_name.trim())
        fd.append('hostel_block', form.hostel_block.trim())
        fd.append('room_number', form.room_number.trim())
      }
      fd.append('consent_given', 'true')
      photos.forEach(f => fd.append('photos', f))

      await registerStudent(adminKey, fd)
      setShowModal(false); setForm(EMPTY_FORM); setPhotos([])
      fetchStudents()
    } catch (e) {
      if (e.response?.status === 409) setFormError('Student ID already exists')
      else setFormError(e.response?.data?.detail || 'Registration failed')
    } finally { setSubmitting(false) }
  }

  const handleStartEdit = (s) => {
    setEditingStudent(s)
    setEditForm({
      full_name: s.full_name || '',
      department: s.department || '',
      email: s.email || '',
      phone: s.phone || '',
      category: s.category || 'Day Scholar',
      hostel_name: s.hostel_name || '',
      hostel_block: s.hostel_block || '',
      room_number: s.room_number || '',
      is_active: s.is_active ?? true,
    })
    setEditError(null)
  }

  const handleSaveEdit = async (e) => {
    e.preventDefault()
    if (!editingStudent) return
    setEditSubmitting(true)
    setEditError(null)
    try {
      await updateStudent(adminKey, editingStudent.student_id, editForm)
      setEditingStudent(null)
      fetchStudents()
    } catch (err) {
      setEditError(err.response?.data?.detail || 'Failed to update student')
    } finally {
      setEditSubmitting(false)
    }
  }

  const handleDelete = async (s) => {
    if (!window.confirm(`Delete ${s.full_name} (${s.student_id})? This will remove all face embeddings permanently.`)) return
    try {
      await deleteStudent(adminKey, s.student_id)
      fetchStudents()
    } catch (e) {
      setError(e.response?.data?.detail || 'Delete failed')
    }
  }

  const handleToggleActive = async (s) => {
    try {
      await updateStudent(adminKey, s.student_id, { is_active: !s.is_active })
      fetchStudents()
    } catch (e) {
      setError('Update failed')
    }
  }

  return (
    <Layout
      title="Student Management"
      subtitle={`${total} students enrolled`}
      actions={
        adminKey && (
          <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2 text-sm">
            <UserPlus size={15} /> Add Student
          </button>
        )
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">
          {error} <button className="underline ml-2" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="relative max-w-sm flex-1 min-w-[240px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input pl-9" placeholder="Search by name or student ID…"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-muted">Category:</label>
          <div className="inline-flex rounded-lg border border-stone-200 bg-white p-0.5 text-xs">
            {['all', 'Hosteller', 'Day Scholar'].map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                  categoryFilter === cat
                    ? 'bg-forest text-white shadow-sm'
                    : 'text-stone-600 hover:text-charcoal'
                }`}
              >
                {cat === 'all' ? 'All' : cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                <th className="th">Student ID</th>
                <th className="th">Name</th>
                <th className="th">Category</th>
                <th className="th">Hostel / Room</th>
                <th className="th">Department</th>
                <th className="th">Photos</th>
                <th className="th">Status</th>
                <th className="th">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="td text-center text-muted py-10">Loading…</td></tr>
              ) : !adminKey ? (
                <tr><td colSpan={8} className="td text-center text-muted py-10">Log in to view students</td></tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="td text-center py-14">
                    <Users size={32} className="mx-auto text-muted opacity-30 mb-2" />
                    <p className="text-muted">No students found</p>
                  </td>
                </tr>
              ) : (
                filtered.map(s => (
                  <tr key={s.student_id} className="tr-hover">
                    <td className="td font-mono text-xs text-forest font-semibold">{s.student_id}</td>
                    <td className="td font-semibold text-charcoal">{s.full_name}</td>
                    <td className="td">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                        s.category === 'Hosteller'
                          ? 'bg-purple-50 text-purple-700 border border-purple-200'
                          : 'bg-stone-100 text-stone-700 border border-stone-200'
                      }`}>
                        {s.category || 'Day Scholar'}
                      </span>
                    </td>
                    <td className="td text-xs text-muted">
                      {s.category === 'Hosteller' ? (
                        <span>{s.hostel_name || 'Hostel'} {s.room_number ? `(${s.room_number})` : ''}</span>
                      ) : (
                        <span className="text-stone-400">—</span>
                      )}
                    </td>
                    <td className="td text-muted text-xs">{s.department || '—'}</td>
                    <td className="td">
                      <span className="badge-blue">{s.embeddings?.length ?? 0} photos</span>
                    </td>
                    <td className="td">
                      <StatusBadge status={s.is_active ? 'online' : 'offline'} label={s.is_active ? 'Active' : 'Inactive'} />
                    </td>
                    <td className="td">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setSelectedStudent(s)}
                          className="btn-ghost p-1.5 rounded-lg" title="View details"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          onClick={() => handleStartEdit(s)}
                          className="btn-ghost p-1.5 rounded-lg text-forest hover:bg-forest/10" title="Edit details"
                        >
                          <Edit3 size={14} />
                        </button>
                        <button
                          onClick={() => handleToggleActive(s)}
                          className="btn-ghost p-1.5 rounded-lg text-muted" title={s.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {s.is_active ? '⏸' : '▶'}
                        </button>
                        <button
                          onClick={() => handleDelete(s)}
                          className="btn-ghost p-1.5 rounded-lg text-errored hover:bg-red-50" title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Student Detail Modal */}
      {selectedStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-stone-200 w-full max-w-md shadow-elevated">
            <div className="flex items-center justify-between p-5 border-b border-stone-100">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-forest/10 rounded-lg text-forest">
                  <Building size={18} />
                </div>
                <div>
                  <h2 className="font-semibold text-charcoal">{selectedStudent.full_name}</h2>
                  <p className="text-xs text-muted font-mono">{selectedStudent.student_id}</p>
                </div>
              </div>
              <button onClick={() => setSelectedStudent(null)} className="text-muted hover:text-charcoal">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-3 text-sm">
              {[
                ['Category', selectedStudent.category || 'Day Scholar'],
                ...(selectedStudent.category === 'Hosteller' ? [
                  ['Hostel Name', selectedStudent.hostel_name || 'N/A'],
                  ['Hostel Block', selectedStudent.hostel_block || 'N/A'],
                  ['Room Number', selectedStudent.room_number || 'N/A'],
                ] : []),
                ['Department', selectedStudent.department || '—'],
                ['Email', selectedStudent.email || '—'],
                ['Phone', selectedStudent.phone || '—'],
                ['Face Photos', selectedStudent.embeddings?.length ?? 0],
                ['Status', selectedStudent.is_active ? 'Active' : 'Inactive'],
                ['Enrolled At', selectedStudent.created_at ? new Date(selectedStudent.created_at).toLocaleString() : '—'],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between py-1.5 border-b border-stone-50">
                  <span className="text-muted">{label}</span>
                  <span className="font-medium text-charcoal">{String(val)}</span>
                </div>
              ))}
            </div>
            <div className="p-4 bg-stone-50 rounded-b-2xl flex justify-end">
              <button onClick={() => setSelectedStudent(null)} className="btn-secondary text-sm">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Student Modal */}
      {editingStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-stone-200 w-full max-w-lg shadow-elevated">
            <div className="flex items-center justify-between p-5 border-b border-stone-100">
              <div>
                <h2 className="font-semibold text-charcoal">Edit Student Details</h2>
                <p className="text-xs text-muted font-mono">{editingStudent.student_id}</p>
              </div>
              <button onClick={() => setEditingStudent(null)} className="text-muted hover:text-charcoal">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="p-5 space-y-4">
              {editError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">{editError}</div>
              )}
              <div>
                <label className="text-xs text-muted mb-1 block font-medium">Full Name</label>
                <input className="input" value={editForm.full_name || ''}
                  onChange={e => handleEditField('full_name', e.target.value)} required />
              </div>
              <div>
                <label className="text-xs text-muted mb-1 block font-medium">Category</label>
                <select
                  className="input bg-white"
                  value={editForm.category || 'Day Scholar'}
                  onChange={e => handleEditField('category', e.target.value)}
                >
                  <option value="Day Scholar">Day Scholar</option>
                  <option value="Hosteller">Hosteller</option>
                </select>
              </div>

              {editForm.category === 'Hosteller' && (
                <div className="p-3 bg-purple-50/50 border border-purple-100 rounded-xl space-y-3">
                  <p className="text-xs font-semibold text-purple-900 flex items-center gap-1.5">
                    <Home size={13} /> Hostel Accommodation Details
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-muted mb-1 block font-medium">Hostel Name</label>
                      <input className="input bg-white" value={editForm.hostel_name || ''}
                        onChange={e => handleEditField('hostel_name', e.target.value)} placeholder="e.g. Kaveri Boys Hostel" />
                    </div>
                    <div>
                      <label className="text-xs text-muted mb-1 block font-medium">Block</label>
                      <input className="input bg-white" value={editForm.hostel_block || ''}
                        onChange={e => handleEditField('hostel_block', e.target.value)} placeholder="e.g. Block B" />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-muted mb-1 block font-medium">Room Number</label>
                    <input className="input bg-white" value={editForm.room_number || ''}
                      onChange={e => handleEditField('room_number', e.target.value)} placeholder="e.g. B-204" />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Department</label>
                  <input className="input" value={editForm.department || ''}
                    onChange={e => handleEditField('department', e.target.value)} />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Phone</label>
                  <input className="input" value={editForm.phone || ''}
                    onChange={e => handleEditField('phone', e.target.value)} />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={editSubmitting} className="btn-primary flex-1">
                  {editSubmitting ? 'Saving…' : 'Save Changes'}
                </button>
                <button type="button" onClick={() => setEditingStudent(null)} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Student Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl border border-stone-200 w-full max-w-lg shadow-elevated max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-stone-100 sticky top-0 bg-white z-10">
              <h2 className="font-semibold text-charcoal">Register New Student</h2>
              <button onClick={() => { setShowModal(false); setFormError(null); setForm(EMPTY_FORM); setPhotos([]) }}
                className="text-muted hover:text-charcoal"><X size={18} /></button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">{formError}</div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Student ID *</label>
                  <input className="input" value={form.student_id}
                    onChange={e => handleField('student_id', e.target.value)} placeholder="e.g. 230111472" />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Full Name *</label>
                  <input className="input" value={form.full_name}
                    onChange={e => handleField('full_name', e.target.value)} placeholder="Full legal name" />
                </div>
              </div>

              {/* Student Category Selector */}
              <div>
                <label className="text-xs text-muted mb-1 block font-medium">Student Category *</label>
                <div className="grid grid-cols-2 gap-2">
                  {['Day Scholar', 'Hosteller'].map(cat => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => handleField('category', cat)}
                      className={`p-2.5 rounded-xl border text-sm font-medium transition-all ${
                        form.category === cat
                          ? 'border-forest bg-forest/5 text-forest font-semibold'
                          : 'border-stone-200 text-stone-600 hover:bg-stone-50'
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              {/* Hostel Specific Fields (Shown only when Hosteller is selected) */}
              {form.category === 'Hosteller' && (
                <div className="p-3.5 bg-purple-50/50 border border-purple-100 rounded-xl space-y-3">
                  <p className="text-xs font-semibold text-purple-900 flex items-center gap-1.5">
                    <Home size={13} /> Hostel Accommodation Details
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-muted mb-1 block font-medium">Hostel Name</label>
                      <input className="input bg-white" value={form.hostel_name}
                        onChange={e => handleField('hostel_name', e.target.value)} placeholder="e.g. Kaveri Boys Hostel" />
                    </div>
                    <div>
                      <label className="text-xs text-muted mb-1 block font-medium">Hostel Block</label>
                      <input className="input bg-white" value={form.hostel_block}
                        onChange={e => handleField('hostel_block', e.target.value)} placeholder="e.g. Block B" />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-muted mb-1 block font-medium">Room Number</label>
                    <input className="input bg-white" value={form.room_number}
                      onChange={e => handleField('room_number', e.target.value)} placeholder="e.g. B-204" />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Department</label>
                  <input className="input" value={form.department}
                    onChange={e => handleField('department', e.target.value)} placeholder="e.g. Computer Science" />
                </div>
                <div>
                  <label className="text-xs text-muted mb-1 block font-medium">Phone</label>
                  <input className="input" value={form.phone}
                    onChange={e => handleField('phone', e.target.value)} placeholder="Phone number" />
                </div>
              </div>

              <div>
                <label className="text-xs text-muted mb-1 block font-medium">Email</label>
                <input className="input" type="email" value={form.email}
                  onChange={e => handleField('email', e.target.value)} placeholder="email@example.com" />
              </div>

              {/* Photo Upload */}
              <div>
                <label className="text-xs text-muted mb-1 block font-medium">Face Photos * (1–2 images)</label>
                <div onClick={() => fileRef.current?.click()}
                  className="border-2 border-dashed border-stone-300 hover:border-forest rounded-xl p-5 cursor-pointer text-center transition-colors">
                  <Upload size={20} className="mx-auto text-muted mb-1.5" />
                  <p className="text-sm text-muted">
                    {photos.length === 0 ? 'Click to upload face photos (JPG / PNG)' : `${photos.length} file(s) selected`}
                  </p>
                </div>
                <input ref={fileRef} type="file" accept="image/*" multiple className="hidden"
                  onChange={e => setPhotos(Array.from(e.target.files).slice(0, 2))} />
                {photos.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {photos.map((f, i) => (
                      <li key={i} className="text-xs text-muted flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-forest" /> {f.name}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Consent */}
              <label className="flex items-start gap-3 cursor-pointer">
                <input type="checkbox" checked={form.consent_given}
                  onChange={e => handleField('consent_given', e.target.checked)}
                  className="mt-0.5 w-4 h-4 accent-forest" />
                <span className="text-xs text-muted leading-relaxed">
                  I confirm this person has given written consent for facial recognition enrolment under applicable data protection regulations.
                </span>
              </label>

              <div className="flex gap-3 pt-1">
                <button type="submit" disabled={submitting} className="btn-primary flex-1">
                  {submitting ? 'Enrolling…' : 'Enroll Student'}
                </button>
                <button type="button" onClick={() => { setShowModal(false); setFormError(null) }} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  )
}
