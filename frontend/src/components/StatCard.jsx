import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function StatCard({ title, value, icon: Icon, color = 'forest', subtitle, trend }) {
  const iconMap = {
    forest: 'bg-green-50 text-forest border border-green-100',
    amber:  'bg-amber-50 text-amber border border-amber-100',
    red:    'bg-red-50 text-errored border border-red-100',
    blue:   'bg-blue-50 text-blue-700 border border-blue-100',
    muted:  'bg-stone-100 text-muted border border-stone-200',
  }
  const cls = iconMap[color] || iconMap.forest

  return (
    <div className="card hover:shadow-elevated transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider truncate">{title}</p>
          <p className="text-3xl font-bold text-charcoal mt-2 tabular-nums">{value ?? '—'}</p>
          {subtitle && (
            <p className="text-xs text-muted mt-1.5">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-xl ${cls} ml-3 flex-shrink-0`}>
            <Icon size={20} />
          </div>
        )}
      </div>
    </div>
  )
}
