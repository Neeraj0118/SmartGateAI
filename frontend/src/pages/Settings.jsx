import { useEffect, useState, useCallback } from 'react'
import { Server, Database, Cpu, Camera, Users, Key, RefreshCw, CheckCircle, XCircle } from 'lucide-react'
import Layout from '../components/Layout'
import { useAuth } from '../context/AuthContext'
import { getHealth, getApiHealth } from '../api/health'
import { getCameraStatus } from '../api/camera'
import { listStudents } from '../api/students'

function StatusRow({ icon: Icon, label, detail, ok, loading }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-stone-100 last:border-0">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-stone-100 rounded-lg">
          <Icon size={15} className="text-muted" />
        </div>
        <div>
          <p className="text-sm font-medium text-charcoal">{label}</p>
          {detail && <p className="text-xs text-muted mt-0.5">{detail}</p>}
        </div>
      </div>
      {loading ? (
        <span className="text-xs text-muted">Checking…</span>
      ) : ok ? (
        <CheckCircle size={16} className="text-forest" />
      ) : (
        <XCircle size={16} className="text-errored" />
      )}
    </div>
  )
}

export default function Settings() {
  const { adminKey, login, logout } = useAuth()
  const [health, setHealth] = useState(null)
  const [apiHealth, setApiHealth] = useState(null)
  const [camStatus, setCamStatus] = useState(null)
  const [studentCount, setStudentCount] = useState(null)
  const [loading, setLoading] = useState(true)
  const [newKey, setNewKey] = useState('')
  const [keyMsg, setKeyMsg] = useState(null)

  const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    const [h, ah, cam] = await Promise.allSettled([
      getHealth(),
      getApiHealth(),
      getCameraStatus(),
    ])
    if (h.status === 'fulfilled') setHealth(h.value.data)
    else setHealth(null)
    if (ah.status === 'fulfilled') setApiHealth(ah.value.data)
    else setApiHealth(null)
    if (cam.status === 'fulfilled') setCamStatus(cam.value.data)
    else setCamStatus(null)

    if (adminKey) {
      try {
        const r = await listStudents(adminKey, { active_only: true })
        setStudentCount(r.data?.total ?? r.data?.items?.length ?? null)
      } catch {}
    }
    setLoading(false)
  }, [adminKey])

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 8000)
    return () => clearInterval(id)
  }, [fetchStatus])

  const handleUpdateKey = (e) => {
    e.preventDefault()
    if (!newKey.trim()) { setKeyMsg({ type: 'error', text: 'Key cannot be empty' }); return }
    login(newKey.trim())
    setNewKey('')
    setKeyMsg({ type: 'success', text: 'Admin key updated for this session' })
    setTimeout(() => setKeyMsg(null), 4000)
  }

  const backendOk = health?.status === 'healthy' || health?.status === 'ok'
  const dbOk = health?.database_connected === true || apiHealth?.database === 'connected'
  const modelsOk = health?.models_ready === true || apiHealth?.ai_engine === 'loaded'
  const camRunning = camStatus?.running

  return (
    <Layout title="Settings & System Status" subtitle="Backend health and session configuration">
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* System Status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-charcoal">System Status</h2>
            <button onClick={fetchStatus} disabled={loading}
              className="btn-ghost p-1.5 rounded-lg text-muted" title="Refresh">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>

          <StatusRow icon={Server} label="Backend Server" detail={BASE}
            ok={backendOk} loading={loading} />
          <StatusRow icon={Database} label="Database (SQLite)" detail="smartgate.db"
            ok={dbOk} loading={loading} />
          <StatusRow icon={Cpu} label="AI Models (YuNet + SFace 128-D)" detail="Face detection & recognition"
            ok={modelsOk} loading={loading} />
          <StatusRow icon={Camera} label="Camera Stream" detail={camRunning ? 'Streaming active' : 'Not streaming'}
            ok={!!camRunning} loading={loading} />
          <StatusRow icon={Users} label="Enrolled Students"
            detail={studentCount != null ? `${studentCount} active student(s)` : 'Log in to check'}
            ok={studentCount != null && studentCount > 0} loading={loading} />
        </div>

        {/* Config + Key */}
        <div className="space-y-4">
          {/* Config */}
          <div className="card">
            <h2 className="text-sm font-semibold text-charcoal mb-4">Configuration</h2>
            <div className="space-y-0 divide-y divide-stone-100 text-sm">
              {[
                ['Backend URL', BASE],
                ['Swagger UI', null, `${BASE}/docs`],
                ['Auth Header', 'X-Admin-API-Key'],
                ['Recognition Threshold', '0.637 cosine similarity'],
                ['Admin Key (session)', adminKey ? '●●●●●●●●●●●● (set)' : 'Not set'],
                ['Enrolled Students', studentCount != null ? String(studentCount) : '—'],
              ].map(([label, val, link]) => (
                <div key={label} className="flex justify-between items-center py-2.5">
                  <span className="text-muted">{label}</span>
                  {link ? (
                    <a href={link} target="_blank" rel="noreferrer"
                      className="text-forest hover:underline font-mono text-xs">
                      {link.replace('http://127.0.0.1:8000', '')} ↗
                    </a>
                  ) : (
                    <span className="font-medium text-charcoal text-xs font-mono">{val}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Update Key */}
          <div className="card">
            <h2 className="text-sm font-semibold text-charcoal mb-1">Update Admin Key</h2>
            <p className="text-xs text-muted mb-4">
              Stored in session memory only — never logged or saved to disk.
            </p>
            {keyMsg && (
              <div className={`mb-3 p-2.5 rounded-lg text-xs ${keyMsg.type === 'success'
                ? 'bg-green-50 border border-green-200 text-forest'
                : 'bg-red-50 border border-red-200 text-errored'}`}>
                {keyMsg.text}
              </div>
            )}
            <form onSubmit={handleUpdateKey} className="flex gap-2">
              <input type="password" className="input flex-1 text-sm"
                placeholder="Paste admin key…" value={newKey}
                onChange={e => setNewKey(e.target.value)} autoComplete="off" />
              <button type="submit" className="btn-primary flex items-center gap-2 text-sm whitespace-nowrap">
                <Key size={14} /> Set Key
              </button>
            </form>
            {adminKey && (
              <button onClick={logout} className="mt-3 text-xs text-errored hover:underline">
                Clear session key
              </button>
            )}
          </div>

          {/* Notes */}
          <div className="card-inset text-xs text-muted space-y-1.5">
            <p className="font-semibold text-charcoal text-xs mb-2">Security Notes</p>
            <p>• Backend bound to <code className="font-mono bg-stone-200 px-1 rounded">127.0.0.1</code> — not publicly accessible</p>
            <p>• Do not run <code className="font-mono bg-stone-200 px-1 rounded">webcam_recognition.py</code> while the browser camera stream is active</p>
            <p>• Face embeddings stored as encrypted binary blobs in SQLite — never exposed via API</p>
            <p>• Admin key never stored in source code, localStorage, or server logs</p>
            <p>• Adjust recognition threshold in <code className="font-mono bg-stone-200 px-1 rounded">backend/app/config.py → FACE_SIMILARITY_THRESHOLD</code></p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
