import Sidebar from './Sidebar'

export default function Layout({ children, title, subtitle, actions }) {
  return (
    <div className="flex min-h-screen bg-stone-100">
      <Sidebar />
      <div className="flex-1 ml-56 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-40 bg-white border-b border-stone-200 px-6 py-4 flex items-center justify-between shadow-sm">
          <div>
            <h1 className="text-lg font-bold text-charcoal leading-tight">{title}</h1>
            {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>

        {/* Main content */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
