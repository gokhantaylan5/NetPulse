# NetPulse

**An agentless, self-hosted network monitoring and observability dashboard built with FastAPI, React, TypeScript, and SQLite.**

NetPulse is a personal software engineering project for monitoring network reachability, exploring local networks, investigating outages, and understanding network performance through historical data. It is designed primarily for home labs and small networks, with an emphasis on transparent monitoring logic and practical network engineering.

> **Status:** Active development · **Version:** v0.1.0 · **Primary development platform:** Windows
>
> NetPulse is an educational prototype, not a production-ready monitoring or alerting service.

## Features

### Network discovery and target management

- Detect active local IPv4 interfaces and their associated private subnets.
- Scan an eligible local private IPv4 subnet for ICMP-responsive hosts.
- Add discovered hosts to monitoring directly from the dashboard.
- Register and delete monitoring targets with IP address validation and duplicate prevention.
- Limit discovery to a connected local private subnet and at most 256 addresses per scan.

### Continuous ICMP monitoring

- Run a **separate monitoring worker** that periodically checks registered targets (10-second configured interval).
- Record reachability, measured latency when available, and timestamps in SQLite.
- Display **Online**, **Offline**, and **Unknown** states, treating measurements older than 45 seconds as stale.
- View recent latency measurements in an interactive chart with minimum, maximum, average, and successful-check statistics.
- Isolate individual ping and persistence errors so other targets can still be checked.

### Incident detection and history

- Automatically open an incident after **three consecutive failed recorded checks** with no gap exceeding 30 seconds between adjacent failures.
- Maintain at most one open incident per target; resolve it after a successful recorded check.
- View **Open**, **Resolved**, and **All** incidents with timestamps and incident duration.
- Preserve incident history in SQLite until its target is deleted.

### Availability analytics

- Query statistics over the last **1 hour**, **24 hours**, or **7 days**.
- Compare successful and failed recorded checks.
- Show **Check Success Rate**, **Measurement Coverage**, **Observed Time**, and **Unknown Time**.
- Treat observation gaps longer than 30 seconds as unknown rather than assuming a host was online or offline.
- Refresh dashboard data periodically without reloading the page.

**Not implemented yet:** notifications, SNMP, TCP port checks, packet-loss/jitter reporting, worker heartbeat, and authentication. See the [Development Roadmap](#development-roadmap).

## Technology stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI, Pydantic |
| Monitoring | ICMP via Windows `ping`, Python scheduler and worker |
| Network discovery | `psutil`, `ipaddress`, `ThreadPoolExecutor` |
| Persistence | SQLite |
| Frontend | React, TypeScript, Vite |
| Charts | Recharts |
| Testing | Pytest, FastAPI TestClient / HTTPX |
| API documentation | OpenAPI / Swagger UI |

## Architecture

```text
                  +-------------------------+
                  |   React / TypeScript    |
                  |  Dashboard (Vite dev)   |
                  +------------+------------+
                               |
                         /api requests
                               |
                  +------------v------------+
                  |       FastAPI API        |
                  | targets, scans, history, |
                  | incidents, availability  |
                  +------------+------------+
                               |
                               v
                       +-------+-------+
                       |    SQLite     |
                       | targets       |
                       | measurements  |
                       | incidents     |
                       +-------^-------+
                               |
                  +------------+------------+
                  |  Monitoring Worker       |
                  |  scheduler + ICMP ping   |
                  |  incident state updates  |
                  +------------+------------+
                               |
                               v
                       Monitored devices
```

The FastAPI server, monitoring worker, and frontend development server are **three separate processes**. Starting the API alone does **not** start periodic monitoring.

## Getting started (Windows)

### Prerequisites

- Python 3.14 (current development environment)
- Node.js and npm compatible with the project's Vite version
- Git
- Network access to devices you are authorized to monitor

### 1. Clone the repository

```powershell
git clone https://github.com/gokhantaylan5/NetPulse.git
cd NetPulse
```

### 2. Install backend dependencies

In **terminal 1**:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" pytest httpx psutil
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- API: <http://127.0.0.1:8000>
- Interactive API docs: <http://127.0.0.1:8000/docs>

The backend initializes the SQLite database at `backend/data/netpulse.db` on startup.

### 3. Start the monitoring worker

In **terminal 2**, from the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.monitoring.worker
```

The worker runs periodic checks against registered targets and writes measurements and incident state changes to the same local SQLite database. Stop it with `Ctrl+C`.

### 4. Start the frontend

In **terminal 3**, from the repository root:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the Vite URL shown in the terminal (typically <http://localhost:5173>). The development server proxies `/api` requests to FastAPI at `http://127.0.0.1:8000`.

### 5. Try NetPulse

1. Add a target by name and IP address, or choose a private network interface and run **Network Discovery**.
2. Add a discovered responding host to monitoring.
3. Keep the monitoring worker running and watch device status and latency history update.
4. Select a target to view its latency chart and availability statistics.
5. Open **Network Incidents** to inspect active and resolved monitoring incidents.

> **Tip:** For a local test, monitor a reachable device you control. ICMP requests may be blocked by a host firewall even when the host is otherwise available.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API health check (not worker health) |
| `GET` | `/api/monitor/ping?host=8.8.8.8` | One on-demand ICMP measurement |
| `GET` | `/api/targets` | List registered monitoring targets |
| `POST` | `/api/targets` | Register a target |
| `DELETE` | `/api/targets/{target_id}` | Delete a target and its history |
| `GET` | `/api/targets/{target_id}/measurements?limit=100` | Recent measurements (limit: 1–1000) |
| `GET` | `/api/monitor/summary` | Latest target-status summary |
| `GET` | `/api/network/interfaces` | Eligible local private IPv4 interfaces |
| `POST` | `/api/network/discover` | Scan a permitted local private IPv4 subnet |
| `GET` | `/api/incidents` | List all incidents |
| `GET` | `/api/incidents?status=open` | Filter active incidents (`resolved` is also accepted) |
| `GET` | `/api/targets/{target_id}/availability?hours=24` | Availability analytics (1–168 hours) |

**Example: register a target**

```http
POST /api/targets
Content-Type: application/json

{
  "name": "Home Router",
  "address": "192.168.1.1"
}
```

**Example: scan a permitted local subnet**

```http
POST /api/network/discover
Content-Type: application/json

{
  "network": "192.168.1.0/24"
}
```

Only scan a subnet actually associated with one of your active local interfaces. Network discovery currently uses ICMP reachability; it is not ARP-based device identification.

## Understanding monitoring results

### Device status

The dashboard uses the most recent stored result for a target. If no result exists, the API fails, or the last measurement is stale, the device cannot be confidently described as online or offline. A recent failed ICMP check indicates **no ICMP response**, which does not necessarily mean every service on the host is unavailable.

### Incident lifecycle

```text
3 consecutive recorded ping failures (each gap <= 30s)
                         |
                         v
                    Incident OPEN
                         |
                 Successful ping
                         |
                         v
                  Incident RESOLVED
```

Incident duration is measured from the **incident opening timestamp**, not necessarily from the first instant of an actual network outage. A stopped worker does not currently have a heartbeat or independent service-health state.

### Check success rate vs. coverage

- **Check Success Rate** = successful recorded checks / total recorded checks in the selected time window.
- **Measurement Coverage** = portion of the selected time window supported by consecutive observations separated by no more than 30 seconds.
- **Unknown Time** = time not covered by those observation intervals.

A 100% check success rate does **not** imply 100% uptime across the whole time window. Likewise, coverage is an estimate based on stored measurements, not a service-level agreement (SLA) guarantee.

## Project structure

```text
NetPulse/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI routes
│   │   ├── database.py                # SQLite data and incident lifecycle
│   │   └── monitoring/
│   │       ├── availability.py        # Check and coverage analytics
│   │       ├── discovery.py           # Private subnet host discovery
│   │       ├── network.py             # Local network interfaces
│   │       ├── ping.py                # ICMP and latency parsing
│   │       ├── scheduler.py           # Periodic monitoring orchestration
│   │       └── worker.py              # Independent monitoring process
│   ├── data/                          # Local database (ignored by Git)
│   └── tests/                         # Backend tests
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── components/
│   │       ├── AvailabilityAnalytics.tsx
│   │       ├── IncidentsPanel.tsx
│   │       ├── LatencyHistory.tsx
│   │       ├── NetworkDiscovery.tsx
│   │       └── TargetStatus.tsx
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Testing

Run the backend tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Build and type-check the frontend from `frontend/`:

```powershell
npm.cmd run build
```

Tests cover network calculations and discovery restrictions, ping parsing, target/database operations, scheduler behavior, incident transitions and stale-failure handling, API validation, incident duration, and availability calculations. New monitoring features should include regression tests.

## Development roadmap

### Completed

- [x] FastAPI backend and SQLite persistence
- [x] ICMP reachability checks and Windows latency parsing
- [x] Target registration, listing, and deletion
- [x] Local IPv4 interface detection
- [x] Restricted private-network device discovery and dashboard registration
- [x] Independent periodic monitoring worker and historical measurements
- [x] Auto-refreshing target status and latency charts
- [x] Incident creation, resolution, history, and duration
- [x] Stale-failure protection for incident creation
- [x] Availability check success rate and measurement-coverage API
- [x] Availability analytics dashboard (1 hour / 24 hours / 7 days)
- [x] Automated backend tests

### Next priorities — monitoring reliability

- [ ] **Worker heartbeat and health status** (distinguish worker outages from target outages)
- [ ] **Concurrent monitoring with controlled limits** for larger target sets
- [ ] Monitoring session awareness and better outage/unknown-time semantics
- [ ] More robust scheduling, error reporting, and performance testing

### Planned — deeper network observability

- [ ] TCP port and service reachability monitoring
- [ ] Packet loss and jitter statistics
- [ ] SNMP monitoring (device/interface metrics)
- [ ] ARP-assisted host identification and discovery improvements
- [ ] Incident notifications, recovery notifications, and alert suppression
- [ ] Retention policies, reporting, and longer-term trend analysis
- [ ] Additional operating system support
- [ ] Authentication, authorization, and deployment hardening

## Current limitations and security

- **Windows-oriented:** ICMP execution and latency parsing currently depend on Windows `ping` behavior.
- **Agentless and ICMP-based:** An unanswered ping does not prove a device is powered off or all services are unreachable.
- **Sequential periodic checks:** Monitoring targets are currently checked one after another; a large set of targets can lengthen the cycle.
- **No worker heartbeat:** `/api/health` checks the API, not the background monitoring worker.
- **No notification delivery:** Incidents appear in the dashboard but do not send email, webhook, or other alerts yet.
- **No access controls:** The application has no login, role-based authorization, or secured multi-user deployment setup.
- **Development only:** The built-in development servers are not intended to be directly exposed to untrusted networks or the public internet.
- **Local data:** SQLite data is stored locally and excluded from version control. Deleting a monitored target also deletes its measurement and incident history.

Only scan or monitor networks and devices that you own or have explicit authorization to access.

## Project purpose

NetPulse is being developed as a hands-on project combining network engineering, backend and frontend development, persistence, testing, and monitoring-system design. The longer-term goal is an extensible self-hosted platform for small-network observability.

---

**NetPulse — built for learning, experimentation, and practical network monitoring.**
