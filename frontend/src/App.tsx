
import { useEffect, useState, type FormEvent } from 'react'
import TargetStatus from './components/TargetStatus'
import LatencyHistory from './components/LatencyHistory'
import './App.css'
import NetworkDiscovery from './components/NetworkDiscovery'

interface Target {
  id: number
  name: string
  address: string
  created_at: string
}

interface MonitoringSummary {
  total_targets: number
  online_devices: number
  offline_devices: number
  unknown_devices: number
  average_latency_ms: number | null
}

function App() {
  // Registered targets
  const [targets, setTargets] = useState<Target[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  // Monitoring statistics
  const [summary, setSummary] =
    useState<MonitoringSummary | null>(null)
  const [summaryError, setSummaryError] = useState(false)

  // Latency history selection
  const [selectedTargetId, setSelectedTargetId] =
    useState<number | null>(null)

  // Target management
  const [newName, setNewName] = useState('')
  const [newAddress, setNewAddress] = useState('')
  const [addingTarget, setAddingTarget] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const [deletingTargetId, setDeletingTargetId] =
    useState<number | null>(null)
  const [deleteError, setDeleteError] =
    useState<string | null>(null)

  // Load registered targets
  useEffect(() => {
    const controller = new AbortController()

    async function fetchTargets() {
      setLoading(true)
      setError(null)

      try {
        const response = await fetch('/api/targets', {
          signal: controller.signal
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
          console.error('Target loading error:', err)
          setError('Failed to load targets.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void fetchTargets()

    return () => controller.abort()
  }, [refreshKey])

  // Refresh monitoring summary every 10 seconds
  useEffect(() => {
    const controller = new AbortController()

    async function fetchSummary() {
      try {
        const response = await fetch(
          '/api/monitor/summary',
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: MonitoringSummary =
          await response.json()

        if (!controller.signal.aborted) {
          setSummary(data)
          setSummaryError(false)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Monitoring summary error:', err)
          setSummary(null)
          setSummaryError(true)
        }
      }
    }

    void fetchSummary()

    const interval = setInterval(() => {
      void fetchSummary()
    }, 10_000)

    return () => {
      clearInterval(interval)
      controller.abort()
    }
  }, [refreshKey])

  // Add a new monitoring target
  async function handleAddTarget(
    event: FormEvent<HTMLFormElement>
  ) {
    event.preventDefault()

    if (addingTarget) return

    const name = newName.trim()
    const address = newAddress.trim()

    if (!name || !address) {
      setAddError('Device name and IP address are required.')
      return
    }

    setAddingTarget(true)
    setAddError(null)

    try {
      const response = await fetch('/api/targets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name,
          address
        })
      })

      if (!response.ok) {
        if (response.status === 409) {
          throw new Error(
            'This IP address is already registered.'
          )
        }

        if (response.status === 422) {
          throw new Error(
            'Please enter a valid IP address and device name.'
          )
        }

        throw new Error(
          `Failed to add target (HTTP ${response.status}).`
        )
      }

      // Reset form after successful creation
      setNewName('')
      setNewAddress('')

      // Reload targets and summary
      setRefreshKey(key => key + 1)
    } catch (err) {
      setAddError(
        err instanceof Error
          ? err.message
          : 'Failed to add target.'
      )
    } finally {
      setAddingTarget(false)
    }
  }

  // Delete a target and its history
  async function handleDeleteTarget(target: Target) {
    if (deletingTargetId !== null) return

    const confirmed = window.confirm(
      `Delete "${target.name}" (${target.address})?\n\n` +
      'All measurement history for this target will also be ' +
      'permanently deleted.\n\n' +
      'This action cannot be undone.'
    )

    if (!confirmed) return

    setDeletingTargetId(target.id)
    setDeleteError(null)

    try {
      const response = await fetch(
        `/api/targets/${target.id}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Target not found.')
        }

        throw new Error(
          `Failed to delete target (HTTP ${response.status}).`
        )
      }

      // Close history if the selected target was deleted
      if (selectedTargetId === target.id) {
        setSelectedTargetId(null)
      }

      // Reload targets and summary
      setRefreshKey(key => key + 1)
    } catch (err) {
      setDeleteError(
        err instanceof Error
          ? err.message
          : 'Failed to delete target.'
      )
    } finally {
      setDeletingTargetId(null)
    }
  }

  const selectedTarget = targets.find(
    target => target.id === selectedTargetId
  )

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">◈</span>
          <span>NetPulse</span>
        </div>

        <nav className="navigation">
          <div className="nav-item active">Dashboard</div>
          <div className="nav-item disabled">
            Monitoring (Soon)
          </div>
          <div className="nav-item disabled">
            Settings (Soon)
          </div>
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

        {/* Monitoring statistics */}
        <section className="stats-grid">
          <div className="stat-card">
            <p>Total Targets</p>
            <h2>{loading ? '—' : targets.length}</h2>
            <span>Registered network targets</span>
          </div>

          <div className="stat-card">
            <p>Online Devices</p>
            <h2>{summary?.online_devices ?? '—'}</h2>
            <span>
              {summaryError
                ? 'Unable to load monitoring data'
                : summary
                  ? `${summary.offline_devices} offline · ${summary.unknown_devices} unknown`
                  : 'Loading monitoring data...'}
            </span>
          </div>

          <div className="stat-card">
            <p>Average Latency</p>
            <h2>
              {summary?.average_latency_ms != null
                ? `${summary.average_latency_ms} ms`
                : '—'}
            </h2>
            <span>
              {summaryError
                ? 'Unable to load monitoring data'
                : 'Average of latest reachable measurements'}
            </span>
          </div>
        </section>

        {/* Target management */}
        <section className="targets-panel">
          <div className="panel-header">
            <div>
              <h2>Monitored Targets</h2>
              <p>
                Add devices, manage targets and view latency history.
              </p>
            </div>
            <NetworkDiscovery
            registeredAddresses={targets.map(target => target.address)}
            onTargetAdded={() => setRefreshKey(key => key + 1)}
            />
          </div>

          {/* Add target form */}
          <form
            className="target-form"
            onSubmit={handleAddTarget}
          >
            <div className="target-field">
              <label htmlFor="target-name">
                Device Name
              </label>

              <input
                id="target-name"
                type="text"
                value={newName}
                onChange={event =>
                  setNewName(event.target.value)
                }
                placeholder="e.g. Home Router"
                maxLength={80}
                required
              />
            </div>

            <div className="target-field">
              <label htmlFor="target-address">
                IP Address
              </label>

              <input
                id="target-address"
                type="text"
                value={newAddress}
                onChange={event =>
                  setNewAddress(event.target.value)
                }
                placeholder="e.g. 192.168.1.1"
                required
              />
            </div>

            <button
              type="submit"
              className="add-target-button"
              disabled={addingTarget}
            >
              {addingTarget ? 'Adding...' : '+ Add Target'}
            </button>
          </form>

          {addError && (
            <div className="error-message" role="alert">
              {addError}
            </div>
          )}

          {deleteError && (
            <div className="error-message" role="alert">
              {deleteError}
            </div>
          )}

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {/* Target table */}
          {loading ? (
            <p className="empty-state">
              Loading targets...
            </p>
          ) : targets.length === 0 ? (
            <p className="empty-state">
              No targets registered yet.
              Add a device above to start monitoring.
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
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {targets.map(target => (
                    <tr key={target.id}>
                      <td className="device-name">
                        <button
                          type="button"
                          className="device-select"
                          aria-pressed={
                            selectedTargetId === target.id
                          }
                          onClick={() =>
                            setSelectedTargetId(target.id)
                          }
                        >
                          {target.name}
                        </button>
                      </td>

                      <td className="ip-address">
                        {target.address}
                      </td>

                      <td>
                        <TargetStatus
                          targetId={target.id}
                        />
                      </td>

                      <td>{target.created_at}</td>

                      <td>
                        <button
                          type="button"
                          className="delete-target-button"
                          disabled={deletingTargetId !== null}
                          onClick={() =>
                            void handleDeleteTarget(target)
                          }
                          aria-label={`Delete ${target.name}`}
                        >
                          {deletingTargetId === target.id
                            ? 'Deleting...'
                            : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Selected target's latency history */}
        <NetworkDiscovery
          registeredAddresses={targets.map(target => target.address)}
          onTargetAdded={() => setRefreshKey(key => key + 1)}
        />
        {selectedTarget && (
          <LatencyHistory
            key={selectedTarget.id}
            targetId={selectedTarget.id}
            targetName={selectedTarget.name}
            refreshKey={refreshKey}
            onClose={() => setSelectedTargetId(null)}
          />
        )}
      </main>
    </div>
  )
}

export default App
