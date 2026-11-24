import { useEffect, useRef, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Camera, CameraOff, Zap, Users, Eye, AlertTriangle, RefreshCw, Loader2, LogIn, LogOut,
  ShieldAlert, ShieldCheck, Volume2, VolumeX, Home, UserCheck, AlertOctagon
} from 'lucide-react'
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

  // Alert states
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [alertDismissed, setAlertDismissed] = useState(false)
  const [exitAlertDismissed, setExitAlertDismissed] = useState(false)
  const lastBeepRef = useRef(0)
  const prevUnknownCountRef = useRef(0)

  const pollRef = useRef(null)
  const imgRef = useRef(null)

  // Web Audio API alert sound
  const playAlertSound = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      if (!AudioCtx) return
      const ctx = new AudioCtx()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sawtooth'
      const now = ctx.currentTime
      osc.frequency.setValueAtTime(850, now)
      osc.frequency.setValueAtTime(650, now + 0.1)
      osc.frequency.setValueAtTime(850, now + 0.2)
      gain.gain.setValueAtTime(0.2, now)
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now)
      osc.stop(now + 0.35)
    } catch (e) {
      // Audio autoplay policy
    }
  }, [])

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
  const activeAlert = status?.active_alert
  const activeGateMode = status?.running && status?.gate_mode ? status.gate_mode : gateMode
  const isActuallyRunning = running && threadAlive

  // Check if any recognized face in the current frame is denied exit
  const deniedFace = faces.find(f => f.permission_status === 'denied')
  const grantedFace = faces.find(f => f.permission_status === 'granted' && f.category === 'Hosteller')

  // Sound and banner alert trigger when unknown face or exit denial is detected
  useEffect(() => {
    if (isActuallyRunning) {
      const isExitDeniedAlert = activeGateMode === 'exit' && (deniedFace || activeAlert?.type === 'HOSTEL_EXIT_DENIED')
      const isUnknownAlert = unknownCount > 0

      if (isUnknownAlert && unknownCount > prevUnknownCountRef.current) {
        setAlertDismissed(false)
      }
      if (isExitDeniedAlert) {
        setExitAlertDismissed(false)
      }

      if (soundEnabled && (isUnknownAlert || isExitDeniedAlert)) {
        const now = Date.now()
        if (now - lastBeepRef.current > 3500) {
          playAlertSound()
          lastBeepRef.current = now
        }
      }
    }
    prevUnknownCountRef.current = unknownCount
  }, [isActuallyRunning, unknownCount, activeGateMode, deniedFace, activeAlert, soundEnabled, playAlertSound])

  return (
    <Layout
      title="Live Monitor"
      subtitle="Real-time webcam face recognition & gate permission stream"
      actions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`btn-secondary flex items-center gap-1.5 text-xs ${soundEnabled ? 'text-forest font-semibold' : 'text-muted'}`}
            title={soundEnabled ? 'Mute alert sound' : 'Enable alert sound'}
          >
            {soundEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
            {soundEnabled ? 'Alert Sound ON' : 'Alert Sound MUTED'}
          </button>
          <button
            onClick={handleReload}
            disabled={reloading || !adminKey}
            className="btn-secondary flex items-center gap-2 text-sm"
            title="Reload student embeddings from database into recognition cache"
          >
            {reloading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Reload Embeddings
          </button>
        </div>
      }
    >
      {/* SECURITY ALERT BANNER: Unknown Person Detected */}
      {isActuallyRunning && unknownCount > 0 && !alertDismissed && (
        <div className="mb-4 p-4 bg-gradient-to-r from-red-600 to-rose-600 border-2 border-red-700 text-white rounded-2xl shadow-xl flex flex-wrap items-center justify-between gap-3 animate-pulse">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-white/20 rounded-xl flex-shrink-0 animate-bounce">
              <ShieldAlert size={28} className="text-yellow-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-black tracking-wide uppercase">
                  Security Alert: Unknown Person Detected!
                </h2>
                <span className="bg-white text-red-700 text-xs px-2.5 py-0.5 rounded-full font-black shadow-sm">
                  {unknownCount} Unknown
                </span>
              </div>
              <p className="text-xs text-red-100 mt-0.5">
                Unregistered face detected at <strong className="text-white font-bold">{activeGateMode.toUpperCase()} GATE</strong>. Immediate identity verification required.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAlertDismissed(true)}
              className="px-3 py-1.5 rounded-lg bg-black/20 hover:bg-black/30 text-white text-xs font-semibold transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* SECURITY ALERT BANNER: Hostel Exit Denied (EXIT CAMERA ONLY) */}
      {isActuallyRunning && activeGateMode === 'exit' && (deniedFace || activeAlert?.type === 'HOSTEL_EXIT_DENIED') && !exitAlertDismissed && (
        <div className="mb-4 p-4 bg-gradient-to-r from-red-700 to-rose-800 border-2 border-red-900 text-white rounded-2xl shadow-2xl flex flex-wrap items-center justify-between gap-3 animate-pulse">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-white/20 rounded-xl flex-shrink-0 animate-bounce">
              <AlertOctagon size={28} className="text-amber-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-black tracking-wide uppercase">
                  ⛔ HOSTEL EXIT DENIED - SECURITY ALERT
                </h2>
                <span className="bg-red-900 text-white border border-red-400 text-xs px-2 py-0.5 rounded-full font-bold">
                  {deniedFace?.status_message || activeAlert?.message || "NO VALID PASS"}
                </span>
              </div>
              <p className="text-xs text-red-100 mt-0.5">
                Hostel Student <strong className="text-white font-bold underline">{deniedFace?.name || activeAlert?.student_name}</strong> ({deniedFace?.person_id || activeAlert?.student_id}) cannot exit without an approved valid pass within scheduled timing.
                {deniedFace?.room_number && ` Room: ${deniedFace.room_number}.`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setExitAlertDismissed(true)}
              className="px-3 py-1.5 rounded-lg bg-black/30 hover:bg-black/40 text-white text-xs font-semibold transition-colors"
            >
              Acknowledge
            </button>
          </div>
        </div>
      )}

      {/* EXIT PASS GRANTED NOTIFICATION (EXIT CAMERA ONLY) */}
      {isActuallyRunning && activeGateMode === 'exit' && grantedFace && (
        <div className="mb-4 p-3.5 bg-gradient-to-r from-emerald-600 to-teal-700 text-white rounded-xl shadow-lg flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-white/20 rounded-lg">
              <ShieldCheck size={22} className="text-emerald-200" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-emerald-100">Exit Granted — Pass Permitted</p>
              <p className="text-sm font-semibold">
                Pass #{grantedFace.permission_id} Permitted for {grantedFace.name} ({grantedFace.person_id})
                {grantedFace.room_number && ` · Room ${grantedFace.room_number}`}
              </p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-full bg-white/20 text-xs font-bold text-white uppercase tracking-wider border border-white/20">
            PASS USED · OUTING LOGGED
          </span>
        </div>
      )}

      {/* HOSTEL STUDENT ENTERED NOTIFICATION (ENTRY CAMERA ONLY) */}
      {isActuallyRunning && activeAlert?.type === 'HOSTEL_OUTING_RETURNED' && (
        <div className="mb-4 p-3.5 bg-gradient-to-r from-blue-700 to-indigo-800 text-white rounded-xl shadow-lg flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-white/20 rounded-lg">
              <UserCheck size={22} className="text-blue-200" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-blue-200">Hostel Student Re-entry</p>
              <p className="text-sm font-semibold">
                Hostel student <strong className="underline">{activeAlert.student_name}</strong> entered — Outing closed & Pass is now invalid!
              </p>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full bg-white/20 text-xs font-bold text-white uppercase tracking-wider border border-white/30">
            PASS INVALIDATED
          </span>
        </div>
      )}

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

                    {/* Flashing overlay badge on live video when unknown face is detected */}
                    {unknownCount > 0 && (
                      <div className="absolute top-12 left-3 bg-red-600/95 text-white border-2 border-white/80 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider flex items-center gap-1.5 animate-bounce shadow-xl">
                        <ShieldAlert size={15} className="text-yellow-300" />
                        <span>⚠️ UNKNOWN DETECTED ({unknownCount})</span>
                      </div>
                    )}

                    {/* Flashing overlay badge when hosteller is denied exit */}
                    {activeGateMode === 'exit' && deniedFace && (
                      <div className="absolute top-12 right-3 bg-red-700 text-white border-2 border-white/80 backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider flex items-center gap-1.5 shadow-xl">
                        <AlertOctagon size={15} className="text-amber-300" />
                        <span>⛔ HOSTEL EXIT DENIED</span>
                      </div>
                    )}

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
            ℹ️ <strong>Hostel Permission Rule:</strong> Permission verification operates on the <strong>EXIT camera only</strong>. Hostellers require an approved active pass to leave. The <strong>ENTRY camera</strong> automatically records arrivals and returns hostellers from outings without permission checks.
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
                cls: unknownCount > 0 ? 'bg-red-600 border-red-700 text-white font-bold animate-pulse' : 'bg-red-50 border-red-100 text-errored' },
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
                {faces.map((f, i) => {
                  const isDenied = (activeGateMode === 'exit' && f.permission_status === 'denied')
                  const isGrantedHostel = (activeGateMode === 'exit' && f.permission_status === 'granted' && f.category === 'Hosteller')

                  return (
                    <li key={i} className={`py-3 flex items-start justify-between gap-2 px-2.5 rounded-lg transition-colors ${
                      !f.is_known ? 'bg-red-50/90 border border-red-300' :
                      isDenied ? 'bg-red-50/90 border border-red-400' :
                      isGrantedHostel ? 'bg-emerald-50/70 border border-emerald-200' : ''
                    }`}>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <p className={`text-sm font-bold truncate ${
                            !f.is_known || isDenied ? 'text-red-700' : 'text-charcoal'
                          }`}>
                            {f.name || 'UNKNOWN PERSON'}
                          </p>
                          {!f.is_known && (
                            <span className="bg-red-600 text-white text-[10px] px-1.5 py-0.2 rounded font-black tracking-wide uppercase">
                              ALERT
                            </span>
                          )}
                          {f.category && (
                            <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                              f.category === 'Hosteller' ? 'bg-purple-100 text-purple-800' : 'bg-stone-200 text-stone-700'
                            }`}>
                              {f.category}
                            </span>
                          )}
                        </div>

                        {f.person_id && (
                          <p className="text-xs text-muted font-mono mt-0.5">{f.person_id}</p>
                        )}

                        {/* Hostel details if available */}
                        {f.room_number && (
                          <p className="text-xs text-stone-500 flex items-center gap-1 mt-0.5">
                            <Home size={11} /> Room {f.room_number} {f.hostel_name ? `(${f.hostel_name})` : ''}
                          </p>
                        )}

                        {/* Exit permission or entry return status message */}
                        {f.status_message && (
                          <p className={`text-xs font-semibold mt-1 ${
                            isDenied ? 'text-red-600' : 'text-emerald-700'
                          }`}>
                            {f.status_message}
                          </p>
                        )}

                        <p className="text-[11px] text-muted mt-0.5">
                          sim: {f.similarity != null ? (f.similarity * 100).toFixed(1) + '%' : '—'}
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-1">
                        <StatusBadge status={f.is_known ? 'known' : 'unknown_face'} />
                        {activeGateMode === 'exit' && f.is_known && (
                          <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wide ${
                            isDenied ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
                          }`}>
                            {isDenied ? 'EXIT DENIED' : 'EXIT ALLOWED'}
                          </span>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          <div className="card-inset text-xs text-muted space-y-1">
            <p className="font-semibold text-charcoal">Gate Security Protocols</p>
            <p>
              • <strong>Day Scholars:</strong> Authorized for exit anytime during gate operating hours.
            </p>
            <p>
              • <strong>Hostellers:</strong> Must have an approved, currently valid exit pass created by authorized staff.
            </p>
            <p>
              • <strong>Entry Gate:</strong> Face recognition records arrival and automatically closes active outings.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
