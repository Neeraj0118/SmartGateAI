import { useEffect, useRef, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Camera, CameraOff, Zap, Users, Eye, AlertTriangle, RefreshCw, Loader2, LogIn, LogOut } from 'lucide-react'
import Layout from '../components/Layout'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { startCamera, stopCamera, getCameraStatus, reloadEmbeddings, setCameraMode } from '../api/camera'
import { STREAM_URL } from '../api/client'

export default function Monitoring() {
  const { adminKey } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryMode = searchParams.get('mode')

  const [running, setRunning] = useState(false)
  const [threadAlive, setThreadAlive] = useState(false)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [streamKey, setStreamKey] = useState(0)
  const [streamLoaded, setStreamLoaded] = useState(false)
  const [reloadMsg, setReloadMsg] = useState(null)
  const [reloading, setReloading] = useState(false)
  const [gateMode, setGateMode] = useState(queryMode === 'exit' ? 'exit' : 'entry')
  const pollRef = useRef(null)
  const imgRef = useRef(null)

  const fetchStatus = useCallback(async () => {
    try {
      const r = await getCameraStatus()
      const d = r.data
      setStatus(d)
      setRunning(d?.running || false)
      setThreadAlive(d?.thread_alive || false)
      // Sync gate mode from server if running
      if (d?.running && d?.gate_mode) {
        setGateMode(d.gate_mode)
      }
      if (d?.error && !d?.running) {
        setError(`Camera thread stopped: ${d.error}`)
      }
    } catch {}
  }, [])

  useEffect(() => {
    fetchStatus()
    pollRef.current = setInterval(fetchStatus, 2000)
    return () => clearInterval(pollRef.current)
  }, [fetchStatus])

  // Handle URL mode query param change
  useEffect(() => {
    if (queryMode === 'entry' || queryMode === 'exit') {
      setGateMode(queryMode)
    }
  }, [queryMode])

  const handleModeChange = async (newMode) => {
    setGateMode(newMode)
    setSearchParams({ mode: newMode })
    // If running, switch mode dynamically on backend
    if (running && adminKey) {
      try {
        await setCameraMode(adminKey, newMode)
        await fetchStatus()
      } catch (e) {
        setError(e.response?.data?.detail || 'Failed to switch camera gate mode')
      }
    }
  }

  const handleStart = async () => {
    if (!adminKey) { setError('Admin key required — log in first'); return }
    setLoading(true); setError(null); setStreamLoaded(false)
    try {
      await startCamera(adminKey, gateMode)
      setTimeout(() => {
        setStreamKey(k => k + 1)
        setRunning(true)
      }, 1200)
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || 'Failed to start camera'
      setError(detail)
    } finally { setLoading(false) }
  }

  const handleStop = async () => {
    if (!adminKey) { setError('Admin key required'); return }
    setLoading(true); setError(null)
    try {
      await stopCamera(adminKey)
      setRunning(false)
      setThreadAlive(false)
      setStreamLoaded(false)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to stop camera')
    } finally { setLoading(false) }
  }

  const handleReload = async () => {
    if (!adminKey) return
    setReloading(true); setReloadMsg(null)
    try {
      const r = await reloadEmbeddings(adminKey)
      setReloadMsg(r.data?.message || 'Embeddings reloaded')
      setTimeout(() => setReloadMsg(null), 5000)
    } catch (e) {
      setReloadMsg(`Reload failed: ${e.response?.data?.detail || e.message}`)
    } finally { setReloading(false) }
  }

  const fps = status?.fps ?? 0
  const faceCount = status?.faces_detected ?? 0
  const knownCount = status?.known_count ?? 0
  const unknownCount = status?.unknown_count ?? 0
  const faces = status?.results || []
  const activeGateMode = status?.running && status?.gate_mode ? status.gate_mode : gateMode
  const isActuallyRunning = running && threadAlive

  return (
    <Layout
      title="Live Monitor"
      subtitle="Real-time webcam face recognition stream"
      actions={
        <button
          onClick={handleReload}
          disabled={reloading || !adminKey}
          className="btn-secondary flex items-center gap-2 text-sm"
          title="Reload student embeddings from database into recognition cache"
        >
          {reloading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Reload Embeddings
        </button>
      }
    >
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-errored text-sm flex items-start gap-2">
          <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-errored/60 hover:text-errored">✕</button>
        </div>
      )}
      {reloadMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl text-forest text-sm">
          {reloadMsg}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        {/* Camera Feed Column */}
        <div className="xl:col-span-2 space-y-4">

          {/* Controls */}
          <div className="card flex flex-wrap items-center gap-3 py-3">
            {/* Gate mode toggle buttons */}
            <div className="flex items-center bg-stone-100 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => handleModeChange('entry')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  gateMode === 'entry'
                    ? 'bg-forest text-white shadow-sm'
                    : 'text-stone-600 hover:text-charcoal'
                }`}
              >
                <LogIn size={13} /> Entry Gate
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('exit')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  gateMode === 'exit'
                    ? 'bg-amber text-white shadow-sm'
                    : 'text-stone-600 hover:text-charcoal'
                }`}
              >
                <LogOut size={13} /> Exit Gate
              </button>
            </div>

            <StatusBadge
              status={isActuallyRunning ? 'running' : 'stopped'}
              label={
                isActuallyRunning
                  ? `Live (${activeGateMode.toUpperCase()})`
                  : running && !threadAlive ? 'Thread Dead' : 'Stopped'
              }
            />

            <span className="text-sm text-charcoal flex-1 min-w-0">
              {isActuallyRunning
                ? `${activeGateMode.toUpperCase()} gate active · ${faceCount} face${faceCount !== 1 ? 's' : ''} detected`
                : running && !threadAlive
                  ? 'Camera thread died — click Stop then Start again'
                  : `Camera stopped · Mode: ${gateMode.toUpperCase()}`}
            </span>

            {!isActuallyRunning ? (
              <button
                onClick={handleStart}
                disabled={loading || !adminKey}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                {loading
                  ? <><Loader2 size={15} className="animate-spin" /> Starting…</>
                  : gateMode === 'entry'
                    ? <><LogIn size={15} /> Start Entry Camera</>
                    : <><LogOut size={15} /> Start Exit Camera</>}
              </button>
            ) : (
              <button
                onClick={handleStop}
                disabled={loading}
                className="btn-danger flex items-center gap-2 text-sm"
              >
                {loading
                  ? <><Loader2 size={15} className="animate-spin" /> Stopping…</>
                  : <><CameraOff size={15} /> Stop Camera</>}
              </button>
            )}
          </div>

          {/* Stream window */}
          <div className="relative bg-charcoal rounded-2xl overflow-hidden" style={{ minHeight: '340px' }}>
            {isActuallyRunning ? (
              <>
                <img
                  key={streamKey}
                  ref={imgRef}
                  src={STREAM_URL}
                  alt="Live face recognition stream"
                  className="w-full block object-contain"
                  style={{ maxHeight: '480px', display: streamLoaded ? 'block' : 'none' }}
                  onLoad={() => setStreamLoaded(true)}
                  onError={() => {
                    setStreamLoaded(false)
                    setError('Stream disconnected — camera may have stopped')
                  }}
                />
                {!streamLoaded && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-white/40">
                    <Loader2 size={36} className="animate-spin mb-3" />
                    <p className="text-sm">Connecting to {activeGateMode.toUpperCase()} stream…</p>
                  </div>
                )}
                {streamLoaded && (
                  <>
                    <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-sm px-2.5 py-1 rounded-lg text-xs text-green-400 font-mono flex items-center gap-1.5">
                      <Zap size={11} /> {typeof fps === 'number' ? fps.toFixed(1) : fps} FPS
                    </div>
                    <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm px-2.5 py-1 rounded-lg text-xs text-white font-mono">
                      {faceCount} face{faceCount !== 1 ? 's' : ''} · {knownCount} known · {unknownCount} unknown
                    </div>
                    <div className="absolute bottom-3 left-3 bg-black/70 backdrop-blur-sm px-2.5 py-1 rounded-lg text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5"
                      style={{ color: activeGateMode === 'entry' ? '#4ade80' : '#fbbf24' }}>
                      {activeGateMode === 'entry' ? <LogIn size={13} /> : <LogOut size={13} />}
                      {activeGateMode} gate monitoring
                    </div>
                  </>
                )}
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-80 text-white/20 select-none">
                <CameraOff size={52} className="mb-3" />
                <p className="text-sm font-medium">Camera Offline</p>
                <p className="text-xs mt-1 text-white/20">Select gate mode and click Start Camera above</p>
              </div>
            )}
          </div>

          <div className="card-inset text-xs text-muted">
            ⚠️ The browser MJPEG stream and <code className="font-mono bg-stone-200 px-1 rounded">webcam_recognition.py</code> cannot
            share the webcam simultaneously. Only one process should be active at a time.
          </div>
        </div>

        {/* Recognition Panel */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'FPS', value: typeof fps === 'number' ? fps.toFixed(1) : fps,
                cls: 'bg-amber-50 border-amber-100 text-amber' },
              { label: 'Faces', value: faceCount,
                cls: 'bg-blue-50 border-blue-100 text-blue-700' },
              { label: 'Known', value: knownCount,
                cls: 'bg-green-50 border-green-100 text-forest' },
              { label: 'Unknown', value: unknownCount,
                cls: 'bg-red-50 border-red-100 text-errored' },
            ].map(({ label, value, cls }) => (
              <div key={label} className={`rounded-xl border p-3 text-center ${cls}`}>
                <p className="text-2xl font-bold tabular-nums leading-tight">{value}</p>
                <p className="text-xs font-semibold mt-0.5 uppercase tracking-wider">{label}</p>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <Users size={15} className="text-muted" />
              <h3 className="text-sm font-semibold text-charcoal">Detected in Frame</h3>
            </div>
            {faces.length === 0 ? (
              <div className="text-center py-7 text-muted">
                <Users size={28} className="mx-auto mb-2 opacity-20" />
                <p className="text-sm">
                  {isActuallyRunning ? 'No faces in frame' : 'Camera not running'}
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-stone-100">
                {faces.map((f, i) => (
                  <li key={i} className="py-3 flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-charcoal truncate">
                        {f.name || 'UNKNOWN'}
                      </p>
                      {f.person_id && (
                        <p className="text-xs text-muted font-mono mt-0.5">{f.person_id}</p>
                      )}
                      <p className="text-xs text-muted mt-0.5">
                        sim: {f.similarity != null ? (f.similarity * 100).toFixed(1) + '%' : '—'}
                      </p>
                    </div>
                    <StatusBadge status={f.is_known ? 'known' : 'unknown_face'} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card-inset text-xs text-muted space-y-1">
            <p className="font-semibold text-charcoal">Gate Event Logging</p>
            <p>
              Recognised faces are logged as <strong>{activeGateMode.toUpperCase()}</strong> records (30s cooldown per student).
            </p>
            <p>
              View real-time history under <strong>Gate Activity</strong> and <strong>Attendance</strong>.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
