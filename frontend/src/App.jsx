import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { Shield } from 'lucide-react'

import Dashboard  from './pages/Dashboard'
import Monitoring from './pages/Monitoring'
import Students   from './pages/Students'
import Attendance from './pages/Attendance'
import Gate       from './pages/Gate'
import Visitors   from './pages/Visitors'
import Vehicles   from './pages/Vehicles'
import Settings   from './pages/Settings'

/* ── Login overlay ─────────────────────────────────────────── */
function LoginOverlay() {
  const { login } = useAuth()
  const [key, setKey] = useState('')
  const [err, setErr] = useState(null)

  const submit = (e) => {
    e.preventDefault()
    if (!key.trim()) { setErr('Please enter the admin API key'); return }
    login(key.trim())
  }

  return (
    <div className="fixed inset-0 z-[100] bg-ivory flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-forest/10 border border-forest/20 mb-4">
            <Shield size={28} className="text-forest" />
          </div>
          <h1 className="text-2xl font-bold text-charcoal">SmartGateAI</h1>
          <p className="text-sm text-muted mt-1">Campus Security Management System</p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-2xl border border-stone-200 p-6 shadow-elevated">
          <h2 className="text-base font-semibold text-charcoal mb-1">Administrator Sign In</h2>
          <p className="text-xs text-muted mb-5">Enter your admin API key to access the security dashboard.</p>

          {err && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-errored text-sm">{err}</div>
          )}

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted mb-1 block">Admin API Key</label>
              <input
                type="password"
                className="input"
                placeholder="Paste your admin key…"
                value={key}
                onChange={e => setKey(e.target.value)}
                autoComplete="off"
                autoFocus
              />
            </div>
            <button type="submit" className="btn-primary w-full py-2.5 font-semibold">
              Sign In
            </button>
          </form>

          <p className="text-xs text-stone-400 text-center mt-5">
            Key stored in session memory only · Not persisted to disk
          </p>
        </div>

        <p className="text-xs text-stone-400 text-center mt-4">
          SmartGateAI v1.0 · Secure Localhost Deployment · 127.0.0.1:8000
        </p>
      </div>
    </div>
  )
}

/* ── App shell ─────────────────────────────────────────────── */
function AppRoutes() {
  const { adminKey } = useAuth()
  return (
    <>
      {!adminKey && <LoginOverlay />}
      <BrowserRouter>
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/students"   element={<Students />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/gate"       element={<Gate />} />
          <Route path="/visitors"   element={<Visitors />} />
          <Route path="/vehicles"   element={<Vehicles />} />
          <Route path="/settings"   element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
