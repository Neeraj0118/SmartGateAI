import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [adminKey, setAdminKey] = useState(() => {
    try { return sessionStorage.getItem('sgai_key') || '' } catch { return '' }
  })

  const login = (key) => {
    setAdminKey(key)
    try { sessionStorage.setItem('sgai_key', key) } catch {}
  }

  const logout = () => {
    setAdminKey('')
    try { sessionStorage.removeItem('sgai_key') } catch {}
  }

  return (
    <AuthContext.Provider value={{ adminKey, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
