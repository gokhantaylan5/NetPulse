import { useEffect, useState } from 'react'

type IncidentStatus = 'open' | 'resolved'
type IncidentFilter = 'all' | IncidentStatus

interface Incident {
  id: number
  target_id: number
  target_name: string
  target_address: string
  status: IncidentStatus
  opened_at: string
  resolved_at: string | null
}

interface Props {
  refreshKey: number
}

const REFRESH_INTERVAL = 10_000

function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) return '—'

  // SQLite's CURRENT_TIMESTAMP values are UTC.
  const normalized = timestamp.replace(' ', 'T')
  const utcTimestamp = /(?:Z|[+-]\d\d:\d\d)$/.test(normalized)
    ? normalized
    : `${normalized}Z`
  const date = new Date(utcTimestamp)

  return Number.isNaN(date.getTime())
    ? timestamp
    : date.toLocaleString('tr-TR')
}

function IncidentsPanel({ refreshKey }: Props) {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [filter, setFilter] = useState<IncidentFilter>('open')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadIncidents() {
      try {
        const response = await fetch('/api/incidents', {
          signal: controller.signal
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: Incident[] = await response.json()

        if (!controller.signal.aborted) {
          setIncidents(data)
          setError(null)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Incident loading error:', err)
          setIncidents([])
          setError('Failed to load network incidents.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void loadIncidents()

    const interval = setInterval(() => {
      void loadIncidents()
    }, REFRESH_INTERVAL)

    return () => {
      clearInterval(interval)
      controller.abort()
    }
  }, [refreshKey])

  const openCount = incidents.filter(item => item.status === 'open').length
  const resolvedCount = incidents.filter(item => item.status === 'resolved').length
  const visibleIncidents = filter === 'all'
    ? incidents
    : incidents.filter(item => item.status === filter)

  return (
    <section className="targets-panel incidents-panel">
      <div className="panel-header incidents-header">
        <div>
          <h2>Network Incidents</h2>
          <p>
            Availability incidents · Auto-refresh every 10 seconds
          </p>
        </div>
        <span className="incident-open-counter">
          {error ? '—' : `${openCount} open`}
        </span>
      </div>

      <div className="incident-tabs" role="group" aria-label="Filter incidents">
        <button
          type="button"
          className={filter === 'open' ? 'incident-tab selected' : 'incident-tab'}
          aria-pressed={filter === 'open'}
          onClick={() => setFilter('open')}
        >
          Open ({openCount})
        </button>
        <button
          type="button"
          className={filter === 'resolved' ? 'incident-tab selected' : 'incident-tab'}
          aria-pressed={filter === 'resolved'}
          onClick={() => setFilter('resolved')}
        >
          Resolved ({resolvedCount})
        </button>
        <button
          type="button"
          className={filter === 'all' ? 'incident-tab selected' : 'incident-tab'}
          aria-pressed={filter === 'all'}
          onClick={() => setFilter('all')}
        >
          All ({incidents.length})
        </button>
      </div>

      {loading ? (
        <p className="empty-state">Loading incidents...</p>
      ) : error ? (
        <div className="error-message" role="alert">{error}</div>
      ) : visibleIncidents.length === 0 ? (
        <p className="empty-state">
          {filter === 'open'
            ? 'No active incidents.'
            : filter === 'resolved'
              ? 'No resolved incidents yet.'
              : 'No incidents recorded yet.'}
        </p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Device</th>
                <th>Status</th>
                <th>Opened At</th>
                <th>Resolved At</th>
              </tr>
            </thead>
            <tbody>
              {visibleIncidents.map(incident => (
                <tr key={incident.id}>
                  <td>
                    <div className="device-name">{incident.target_name}</div>
                    <div className="ip-address">{incident.target_address}</div>
                  </td>
                  <td>
                    <span className={`incident-status ${incident.status}`}>
                      {incident.status === 'open' ? 'OPEN' : 'RESOLVED'}
                    </span>
                  </td>
                  <td>{formatTimestamp(incident.opened_at)}</td>
                  <td>{formatTimestamp(incident.resolved_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default IncidentsPanel
