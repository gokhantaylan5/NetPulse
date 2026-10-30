import { useEffect, useState } from 'react'

interface AvailabilityResult {
  target_id: number
  target_name: string
  target_address: string
  window_hours: number
  window_start: string
  window_end: string
  total_checks: number
  successful_checks: number
  failed_checks: number
  check_success_rate_percent: number | null
  measurement_coverage_percent: number
  observed_seconds: number
  unknown_seconds: number
  gaps_detected: number
  max_gap_seconds: number
}

interface Props {
  targetId: number
  refreshKey: number
}

type WindowHours = 1 | 24 | 168

const REFRESH_INTERVAL_MS = 10_000

const WINDOWS: { hours: WindowHours; label: string }[] = [
  { hours: 1, label: '1 Hour' },
  { hours: 24, label: '24 Hours' },
  { hours: 168, label: '7 Days' }
]

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—'

  const total = Math.floor(seconds)
  const days = Math.floor(total / 86_400)
  const hours = Math.floor((total % 86_400) / 3_600)
  const minutes = Math.floor((total % 3_600) / 60)
  const remainingSeconds = total % 60

  if (days > 0) return `${days}d ${hours}h ${minutes}m`
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${remainingSeconds}s`
  return `${remainingSeconds}s`
}

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(2)}%`
}

function AvailabilityAnalytics({ targetId, refreshKey }: Props) {
  const [hours, setHours] = useState<WindowHours>(24)
  const [data, setData] = useState<AvailabilityResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let inFlight = false

    setData(null)
    setError(null)
    setLoading(true)

    async function loadAvailability() {
      if (inFlight || controller.signal.aborted) return
      inFlight = true

      try {
        const response = await fetch(
          `/api/targets/${targetId}/availability?hours=${hours}`,
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const next: AvailabilityResult = await response.json()

        if (!controller.signal.aborted) {
          setData(next)
          setError(null)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Availability request failed:', err)
          setError('Failed to load availability statistics.')
        }
      } finally {
        inFlight = false
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    void loadAvailability()
    const timer = window.setInterval(
      () => { void loadAvailability() },
      REFRESH_INTERVAL_MS
    )

    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [targetId, hours, refreshKey])

  return (
    <div className="availability-section">
      <div className="availability-heading">
        <div>
          <h3>Availability Analytics</h3>
          <p>Recorded ping checks and observation coverage</p>
        </div>

        <div className="availability-periods" role="group" aria-label="Availability time window">
          {WINDOWS.map(option => (
            <button
              key={option.hours}
              type="button"
              className={hours === option.hours
                ? 'availability-period selected'
                : 'availability-period'}
              aria-pressed={hours === option.hours}
              onClick={() => setHours(option.hours)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <p className="availability-message" role="status">
          Loading availability statistics...
        </p>
      )}

      {!loading && error && (
        <div className="availability-error" role="alert">
          {error} Check that the backend API is running.
        </div>
      )}

      {!loading && !error && data && (
        <>
          <div className="availability-grid">
            <div className="availability-card">
              <p>Check Success Rate</p>
              <strong>{formatPercent(data.check_success_rate_percent)}</strong>
              <span>Successful recorded ping checks</span>
            </div>
            <div className="availability-card">
              <p>Measurement Coverage</p>
              <strong>{formatPercent(data.measurement_coverage_percent)}</strong>
              <span>Time supported by consecutive measurements</span>
            </div>
            <div className="availability-card">
              <p>Successful / Failed</p>
              <strong>{data.successful_checks.toLocaleString('tr-TR')} / {data.failed_checks.toLocaleString('tr-TR')}</strong>
              <span>{data.total_checks.toLocaleString('tr-TR')} checks in selected window</span>
            </div>
            <div className="availability-card">
              <p>Unknown Time</p>
              <strong>{formatDuration(data.unknown_seconds)}</strong>
              <span>{formatDuration(data.observed_seconds)} observed</span>
            </div>
          </div>

          {data.total_checks === 0 && (
            <p className="availability-message">
              No measurements recorded in this time window. A success rate cannot be calculated.
            </p>
          )}

          <p className="availability-note">
            Coverage uses intervals between consecutive measurements up to {data.max_gap_seconds}s apart.
            {' '}Longer gaps are unknown, not downtime. Detected gaps: {data.gaps_detected}.
            {' '}Check success rate is not a verified 24/7 uptime percentage.
          </p>
        </>
      )}
    </div>
  )
}

export default AvailabilityAnalytics
