
import { useEffect, useRef, useState } from 'react'

interface NetworkInterface {
  interface: string
  ip: string
  netmask: string
  network: string
  is_primary: boolean
}

interface DiscoveredDevice {
  ip: string
  reachable: boolean
  latency_ms: number | null
}

interface DiscoveryResult {
  network: string
  discovered_count: number
  devices: DiscoveredDevice[]
}

interface Props {
  registeredAddresses: string[]
  onTargetAdded: () => void
}

function NetworkDiscovery({
  registeredAddresses,
  onTargetAdded
}: Props) {
  const [interfaces, setInterfaces] =
    useState<NetworkInterface[]>([])

  const [selectedNetwork, setSelectedNetwork] =
    useState('')

  const [result, setResult] =
    useState<DiscoveryResult | null>(null)

  const [loadingNetworks, setLoadingNetworks] =
    useState(true)

  const [scanning, setScanning] = useState(false)

  const [error, setError] =
    useState<string | null>(null)

  const [addingAddress, setAddingAddress] =
    useState<string | null>(null)

  const [addError, setAddError] =
    useState<string | null>(null)

  const [addedAddresses, setAddedAddresses] =
    useState<string[]>([])

  const scanController =
    useRef<AbortController | null>(null)

  // Load available local network interfaces
  useEffect(() => {
    const controller = new AbortController()

    async function loadNetworks() {
      try {
        const response = await fetch(
          '/api/network/interfaces',
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: NetworkInterface[] =
          await response.json()

        if (controller.signal.aborted) return

        setInterfaces(data)

        const primary = data.find(
          item => item.is_primary
        )

        setSelectedNetwork(
          primary?.network ?? data[0]?.network ?? ''
        )
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error(err)
          setError('Failed to load network interfaces.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingNetworks(false)
        }
      }
    }

    void loadNetworks()

    return () => {
      controller.abort()
      scanController.current?.abort()
    }
  }, [])

  // Scan the selected local network
  async function handleScan() {
    if (!selectedNetwork || scanning) return

    const controller = new AbortController()
    scanController.current = controller

    setScanning(true)
    setError(null)
    setAddError(null)
    setResult(null)

    try {
      const response = await fetch(
        '/api/network/discover',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            network: selectedNetwork
          }),
          signal: controller.signal
        }
      )

      if (!response.ok) {
        throw new Error(
          `Network scan failed (HTTP ${response.status}).`
        )
      }

      const data: DiscoveryResult =
        await response.json()

      if (!controller.signal.aborted) {
        setResult(data)
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        console.error(err)

        setError(
          err instanceof Error
            ? err.message
            : 'Network scan failed.'
        )
      }
    } finally {
      if (!controller.signal.aborted) {
        setScanning(false)
      }

      if (scanController.current === controller) {
        scanController.current = null
      }
    }
  }

  // Register a discovered device for monitoring
  async function handleAddDevice(ip: string) {
    if (addingAddress !== null) return

    const alreadyRegistered =
      registeredAddresses.includes(ip) ||
      addedAddresses.includes(ip)

    if (alreadyRegistered) return

    setAddingAddress(ip)
    setAddError(null)

    try {
      const response = await fetch('/api/targets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: `Discovered Device (${ip})`,
          address: ip
        })
      })

      // Another request may have registered it already.
      if (response.status === 409) {
        setAddedAddresses(previous =>
          previous.includes(ip)
            ? previous
            : [...previous, ip]
        )

        onTargetAdded()
        return
      }

      if (!response.ok) {
        throw new Error(
          `Failed to add ${ip} (HTTP ${response.status}).`
        )
      }

      // Immediately update the discovery table
      setAddedAddresses(previous =>
        previous.includes(ip)
          ? previous
          : [...previous, ip]
      )

      // Refresh the main dashboard
      onTargetAdded()

    } catch (err) {
      console.error('Add discovered device error:', err)

      setAddError(
        err instanceof Error
          ? err.message
          : 'Failed to add discovered device.'
      )
    } finally {
      setAddingAddress(null)
    }
  }

  const monitoredAddresses = new Set([
    ...registeredAddresses,
    ...addedAddresses
  ])

  return (
    <section className="targets-panel discovery-panel">

      {/* Panel header */}
      <div className="panel-header">
        <h2>Network Discovery</h2>
        <p>
          Discover responding devices on your local network
          and add them to monitoring.
        </p>
      </div>

      {/* Network selection */}
      <div className="discovery-controls">
        <div className="target-field">
          <label htmlFor="network-select">
            Network Interface
          </label>

          <select
            id="network-select"
            value={selectedNetwork}
            disabled={loadingNetworks || scanning}
            onChange={event => {
              setSelectedNetwork(event.target.value)
              setResult(null)
              setError(null)
              setAddError(null)
            }}
          >
            {interfaces.length === 0 && (
              <option value="">
                No available networks
              </option>
            )}

            {interfaces.map((item, index) => (
              <option
                key={`${item.interface}-${index}`}
                value={item.network}
              >
                {item.interface} — {item.network}
                {item.is_primary ? ' (Primary)' : ''}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className="add-target-button"
          onClick={() => void handleScan()}
          disabled={
            loadingNetworks ||
            scanning ||
            !selectedNetwork
          }
        >
          {scanning ? 'Scanning...' : 'Scan Network'}
        </button>
      </div>

      {/* Errors */}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {addError && (
        <div className="error-message" role="alert">
          {addError}
        </div>
      )}

      {/* Scanning indicator */}
      {scanning && (
        <p className="discovery-message">
          Scanning {selectedNetwork}.
          This may take a while...
        </p>
      )}

      {/* Scan results */}
      {!scanning && result && (
        <>
          <div className="discovery-summary">
            <strong>{result.discovered_count}</strong>
            <span>
              responding devices found on {result.network}
            </span>
          </div>

          {result.devices.length === 0 ? (
            <p className="empty-state">
              No devices responded to the scan.
            </p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {result.devices.map(device => {
                    const isMonitored =
                      monitoredAddresses.has(device.ip)

                    const isAdding =
                      addingAddress === device.ip

                    return (
                      <tr key={device.ip}>
                        <td className="ip-address">
                          {device.ip}
                        </td>

                        <td>
                          <span className="status-badge online">
                            Responding
                          </span>
                        </td>

                        <td>
                          {device.latency_ms === null
                            ? '—'
                            : `${device.latency_ms} ms`}
                        </td>

                        <td>
                          {isMonitored ? (
                            <span className="discovery-monitored">
                              Already Monitored
                            </span>
                          ) : (
                            <button
                              type="button"
                              className="discovery-add-button"
                              disabled={
                                addingAddress !== null
                              }
                              onClick={() =>
                                void handleAddDevice(device.ip)
                              }
                            >
                              {isAdding
                                ? 'Adding...'
                                : '+ Add to Monitoring'}
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default NetworkDiscovery
