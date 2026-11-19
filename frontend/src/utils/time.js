/**
 * Timestamp utilities for SmartGateAI frontend.
 * All API timestamps are UTC (stored with Z suffix or +00:00).
 * Historical records may be naive strings — we treat them as UTC.
 * All display is in Asia/Kolkata (IST, UTC+5:30).
 */

/** Ensure a raw API timestamp string is treated as UTC. */
function asUTC(raw) {
  if (!raw) return null
  if (typeof raw !== 'string') return raw
  // If no timezone indicator at all, append Z to treat as UTC
  if (!raw.match(/[Zz]$/) && !raw.match(/[+-]\d{2}:\d{2}$/)) {
    return raw.replace(' ', 'T') + 'Z'
  }
  return raw.replace(' ', 'T')
}

/** Format as full IST datetime: "19 Nov 2026, 10:47:59 AM" */
export function toIST(raw) {
  if (!raw) return '—'
  try {
    const d = new Date(asUTC(raw))
    if (isNaN(d.getTime())) return raw
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })
  } catch {
    return raw
  }
}

/** Format as IST date only: "19 Nov 2026" */
export function toISTDate(raw) {
  if (!raw) return '—'
  try {
    const d = new Date(asUTC(raw))
    if (isNaN(d.getTime())) return raw
    return d.toLocaleDateString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return raw
  }
}

/** Format as IST time only: "10:47:59 AM" */
export function toISTTime(raw) {
  if (!raw) return '—'
  try {
    const d = new Date(asUTC(raw))
    if (isNaN(d.getTime())) return raw
    return d.toLocaleTimeString('en-IN', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    })
  } catch {
    return raw
  }
}

/** Return today's date in IST as YYYY-MM-DD string (for date filter defaults). */
export function todayIST() {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })
}
