
import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'

interface Measurement {
  id: number
  target_id: number
  reachable: number
  latency_ms: number | null
  timestamp: string
}

interface Props {
  targetId: number
  targetName: string
  refreshKey: number
  onClose: () => void
}

const REFRESH_INTERVAL = 10_000

// SQLite timestamps are stored in UTC.
function parseTimestamp(timestamp: string): Date {
  return new Date(timestamp.replace(' ', 'T') + 'Z')
}

function formatTime(timestamp: string): string {
  return parseTimestamp(timestamp).toLocaleTimeString(
    'tr-TR',
    {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }
  )
}

function formatDateTime(timestamp: string): string {
  return parseTimestamp(timestamp).toLocaleString('tr-TR')
}

function formatLatency(value: number | null): string {
  return value === null
    ? '—'
    : `${value.toFixed(1)} ms`
}

function LatencyHistory({
  targetId,
  targetName,
  refreshKey,
  onClose
}: Props) {
  const [measurements, setMeasurements] =
    useState<Measurement[]>([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch measurement history.
  useEffect(() => {
    const controller = new AbortController()

    setLoading(true)
    setMeasurements([])
    setError(null)

    async function fetchMeasurements() {
      try {
        const response = await fetch(
          `/api/targets/${targetId}/measurements?limit=100`,
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: Measurement[] = await response.json()

        if (!controller.signal.aborted) {
          setMeasurements(data)
          setError(null)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error('Measurement history error:', err)
          setMeasurements([])
          setError('Failed to load measurement history.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    void fetchMeasurements()

    const interval = setInterval(() => {
      void fetchMeasurements()
    }, REFRESH_INTERVAL)

    return () => {
      clearInterval(interval)
      controller.abort()
    }
  }, [targetId, refreshKey])

  // API returns newest measurements first.
  // The chart displays oldest to newest.
  const chartData = [...measurements]
    .reverse()
    .map(measurement => ({
      timestamp: measurement.timestamp,
      latency_ms:
        measurement.reachable === 1
          ? measurement.latency_ms
          : null
    }))

  // Monitoring statistics.
  const totalChecks = measurements.length

  const successfulCount = measurements.filter(
    measurement => measurement.reachable === 1
  ).length

  const offlineCount = measurements.filter(
    measurement => measurement.reachable === 0
  ).length

  const missingLatencyCount = measurements.filter(
    measurement =>
      measurement.reachable === 1 &&
      measurement.latency_ms === null
  ).length

  // Ignore missing latency values.
  const validLatencies = measurements.flatMap(
    measurement =>
      measurement.reachable === 1 &&
      measurement.latency_ms !== null
        ? [measurement.latency_ms]
        : []
  )

  const averageLatency =
    validLatencies.length > 0
      ? validLatencies.reduce(
          (sum, value) => sum + value,
          0
        ) / validLatencies.length
      : null

  const minLatency =
    validLatencies.length > 0
      ? Math.min(...validLatencies)
      : null

  const maxLatency =
    validLatencies.length > 0
      ? Math.max(...validLatencies)
      : null

  const successfulChecks =
    totalChecks > 0
      ? (successfulCount / totalChecks) * 100
      : null

  const hasLatencyData = validLatencies.length > 0

  return (
    <section className="targets-panel history-panel">

      {/* Header */}
      <div className="panel-header history-header">
        <div>
          <h2>Latency History — {targetName}</h2>
          <p>
            Last 100 measurements · Auto-refresh every 10s
          </p>
        </div>

        <button
          type="button"
          className="history-close"
          onClick={onClose}
        >
          Close
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <p className="empty-state">
          Loading measurement history...
        </p>
      )}

      {/* API error */}
      {!loading && error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {/* Empty history */}
      {!loading && !error && totalChecks === 0 && (
        <p className="empty-state">
          No measurements recorded for this target yet.
        </p>
      )}

      {/* Measurements */}
      {!loading && !error && totalChecks > 0 && (
        <>

          {/* Measurement information */}
          <div className="history-meta">
            <span>{totalChecks} measurements</span>
            <span>{offlineCount} offline checks</span>
            <span>{missingLatencyCount} without latency</span>
          </div>

          {/* Performance statistics */}
          <div className="performance-grid">

            <div className="performance-card">
              <p>Average Latency</p>
              <h3>{formatLatency(averageLatency)}</h3>
            </div>

            <div className="performance-card">
              <p>Successful Checks</p>
              <h3>
                {successfulChecks === null
                  ? '—'
                  : `${successfulChecks.toFixed(1)}%`}
              </h3>
            </div>

            <div className="performance-card">
              <p>Minimum Latency</p>
              <h3>{formatLatency(minLatency)}</h3>
            </div>

            <div className="performance-card">
              <p>Maximum Latency</p>
              <h3>{formatLatency(maxLatency)}</h3>
            </div>

          </div>

          {/* Latency chart */}
          {hasLatencyData ? (
            <div className="history-chart">

              <LineChart
                data={chartData}
                responsive
                style={{
                  width: '100%',
                  height: 320
                }}
                margin={{
                  top: 12,
                  right: 24,
                  bottom: 8,
                  left: 0
                }}
              >

                <CartesianGrid
                  stroke="#263244"
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatTime}
                  tick={{
                    fill: '#94a3b8',
                    fontSize: 11
                  }}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={30}
                />

                <YAxis
                  domain={[0, 'auto']}
                  tick={{
                    fill: '#94a3b8',
                    fontSize: 11
                  }}
                  tickLine={false}
                  axisLine={false}
                  width={60}
                  tickFormatter={
                    value => `${value} ms`
                  }
                />

                <Tooltip
                  labelFormatter={
                    label => formatDateTime(String(label))
                  }
                  formatter={
                    value => [`${value} ms`, 'Latency']
                  }
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: '1px solid #334155',
                    borderRadius: 8
                  }}
                  labelStyle={{
                    color: '#cbd5e1'
                  }}
                  itemStyle={{
                    color: '#38bdf8'
                  }}
                />

                <Line
                  type="linear"
                  dataKey="latency_ms"
                  name="Latency"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  activeDot={{ r: 5 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />

              </LineChart>

            </div>
          ) : (
            <p className="empty-state">
              Measurements exist, but no numeric latency
              values are available.
            </p>
          )}

        </>
      )}

    </section>
  )
}

export default LatencyHistory
