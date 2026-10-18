import TargetStatus from './components/TargetStatus'
import { useEffect, useState } from 'react'
import './App.css'

interface Target {
  id: number
  name: string
  address: string
  created_at: string
}

function App() {
  const [targets, setTargets] = useState<Target[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function fetchTargets() {
      setLoading(true)
      setError(null)

      try {
        const response = await fetch('/api/targets', {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: Target[] = await response.json()

        if (!controller.signal.aborted) {
          setTargets(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError('Failed to load targets.')
          console.error(err)
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    fetchTargets()

    return () => controller.abort()
  }, [refreshKey])

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">◈</span>
          <span>NetPulse</span>
        </div>

        <nav className="navigation">
          <div className="nav-item active">Dashboard</div>
          <div className="nav-item disabled">Monitoring (Soon)</div>
          <div className="nav-item disabled">Settings (Soon)</div>
        </nav>

        <div className="sidebar-footer">
          NetPulse v0.1.0
        </div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div>
            <p className="eyebrow">NETWORK OVERVIEW</p>
            <h1>Dashboard</h1>
            <p className="subtitle">
              Manage and monitor your network targets.
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={() => setRefreshKey(key => key + 1)}
            disabled={loading}
          >
            {loading ? 'Loading...' : '↻ Refresh'}
          </button>
        </header>

        <section className="stats-grid">
          <div className="stat-card">
            <p>Total Targets</p>
            <h2>{loading ? '—' : targets.length}</h2>
            <span>Registered network targets</span>
          </div>

          <div className="stat-card">
            <p>Online Devices</p>
            <h2>—</h2>
            <span>Monitoring not started</span>
          </div>

          <div className="stat-card">
            <p>Average Latency</p>
            <h2>—</h2>
            <span>No measurements yet</span>
          </div>
        </section>

        <section className="targets-panel">
          <div className="panel-header">
            <div>
              <h2>Monitored Targets</h2>
              <p>Devices registered in NetPulse</p>
            </div>
          </div>

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {loading ? (
            <p className="empty-state">Loading targets...</p>
          ) : targets.length === 0 ? (
            <p className="empty-state">
              No targets registered yet.
            </p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Device</th>
                    <th>IP Address</th>
                    <th>Status</th>
                    <th>Added At</th>
                  </tr>
                </thead>

                <tbody>
                  {targets.map(target => (
                    <tr key={target.id}>
                      <td className="device-name">
                        {target.name}
                      </td>
                      <td className="ip-address">
                        {target.address}
                      </td>
                      <td>
                         <TargetStatus targetId={target.id} />
                      </td>
                      <td>{target.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
