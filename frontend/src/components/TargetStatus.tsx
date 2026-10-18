
import { useEffect, useState } from 'react'

interface Measurement {
  id: number
  target_id: number
  reachable: number
  latency_ms: number | null
  timestamp: string
}

interface Props {
  targetId: number
}

const REFRESH_INTERVAL = 10_000
const STALE_AFTER = 45_000

function TargetStatus({ targetId }: Props) {
  const [measurement, setMeasurement] =
    useState<Measurement | null>(null)

  const [error, setError] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    async function refresh() {
      try {
        const response = await fetch(
          `/api/targets/${targetId}/measurements?limit=1`,
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: Measurement[] = await response.json()

        if (!controller.signal.aborted) {
          setMeasurement(data[0] ?? null)
          setError(false)
        }
      } catch {
        if (!controller.signal.aborted) {
          setError(true)
        }
      }
    }

    void refresh()

    const timer = setInterval(() => {
      void refresh()
    }, REFRESH_INTERVAL)

    return () => {
      clearInterval(timer)
      controller.abort()
    }
  }, [targetId])

  if (error) {
    return <span className="status-badge">API Error</span>
  }

  if (!measurement) {
    return <span className="status-badge">Unknown</span>
  }

  // SQLite CURRENT_TIMESTAMP is UTC.
  const timestamp = new Date(
    measurement.timestamp.replace(' ', 'T') + 'Z'
  ).getTime()

  const age = Date.now() - timestamp

  if (
    !Number.isFinite(age) ||
    age < 0 ||
    age > STALE_AFTER
  ) {
    return <span className="status-badge">Unknown</span>
  }

  if (measurement.reachable !== 1) {
    return (
      <span className="status-badge offline">
        Offline
      </span>
    )
  }

  return (
    <span className="status-badge online">
      Online
      {measurement.latency_ms !== null &&
        ` · ${measurement.latency_ms} ms`}
    </span>
  )
}

export default TargetStatus
