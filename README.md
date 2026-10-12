# NetPulse

**A modular, self-hosted network monitoring dashboard built with FastAPI, React, and TypeScript.**

NetPulse is a personal software engineering project focused on network monitoring, device management, and network discovery.

The goal is to develop a lightweight monitoring platform that can be used in home and small-office networks, while exploring networking concepts, backend development, and modern web technologies.

> **Project Status:** Early development (v0.1.0). Core backend functionality and the initial dashboard are implemented. Automated device discovery and continuous monitoring are planned.

## Features

### Currently Implemented

- **ICMP Ping Monitoring:** Check the reachability of IPv4/IPv6 targets using the Windows ping utility.
- **Latency Extraction:** Parse response times from supported Windows ping output formats.
- **Target Management:** Register and retrieve monitored targets through REST API endpoints.
- **SQLite Storage:** Persist registered targets locally.
- **Network Interface Detection:** Identify active IPv4 interfaces and calculate their private network ranges.
- **Web Dashboard:** View registered targets through a React-based interface.
- **Automated Backend Tests:** Unit and API tests using Pytest.

### Planned Features

- Automatic local network device discovery
- ARP-assisted device identification
- Device selection and registration through the dashboard
- Periodic background monitoring
- Historical latency and availability measurements
- Interactive monitoring charts
- Packet loss and jitter statistics
- Network outage alerts
- SNMP-based monitoring for supported devices
- Additional operating system support

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, TypeScript, Vite |
| Database | SQLite |
| Network Utilities | ICMP Ping, psutil, ipaddress |
| Backend Testing | Pytest, HTTPX |
| API Documentation | Swagger UI / OpenAPI |

## Project Structure

```text
NetPulse/
├── backend/
│   ├── app/
│   │   ├── monitoring/
│   │   │   ├── ping.py
│   │   │   └── network.py
│   │   ├── database.py
│   │   └── main.py
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── index.css
│   ├── package.json
│   └── vite.config.ts
│
└── .gitignore
```

## Getting Started

The current development setup is designed for Windows.

### Prerequisites

- Python 3.14
- Node.js (LTS)
- npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/gokhantaylan5/NetPulse.git
cd NetPulse
```

### 2. Set Up the Backend

Open PowerShell:

```powershell
cd backend

py -m venv .venv

.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" pytest httpx psutil
```

Start the FastAPI server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The backend will be available at:

- API: http://127.0.0.1:8000
- Swagger Documentation: http://127.0.0.1:8000/docs

The SQLite database is automatically initialized when the application starts.

### 3. Set Up the Frontend

Open another terminal in the project root:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the development URL displayed in your terminal, typically:

http://localhost:5173

The Vite development server proxies `/api` requests to the FastAPI backend.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Check backend health |
| GET | `/api/monitor/ping` | Perform an on-demand ping check |
| GET | `/api/targets` | List registered targets |
| POST | `/api/targets` | Register a new target |

### Example: Ping a Target

```http
GET /api/monitor/ping?host=8.8.8.8
```

Example response:

```json
{
  "host": "8.8.8.8",
  "reachable": true,
  "latency_ms": 25.0
}
```

Latency values depend on actual network conditions.

## Testing

Backend tests cover API responses, ping behavior, latency parsing, database operations, and network calculations.

From the `backend` directory:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The project currently has 23 passing backend tests in the local development environment.

Frontend production build:

```powershell
cd frontend
npm.cmd run build
```

## Development Roadmap

- [x] FastAPI backend initialization
- [x] Basic ICMP monitoring
- [x] Latency parsing
- [x] SQLite target storage
- [x] Target management API
- [x] Initial React dashboard
- [x] Local network interface detection
- [ ] Automatic local network discovery
- [ ] Device discovery interface
- [ ] Periodic monitoring engine
- [ ] Measurement history
- [ ] Real-time dashboard updates
- [ ] Alerts and monitoring statistics
- [ ] SNMP monitoring

## Current Limitations

NetPulse is still an experimental development project.

- Continuous background monitoring is not yet implemented.
- The dashboard currently displays registered targets, not live device status.
- Network discovery can identify interface information, but automatic host scanning is not yet implemented.
- Ping execution and output parsing are currently Windows-oriented.
- Authentication and access control are not yet implemented.

Use network monitoring and discovery functionality only on networks you own or are authorized to manage. The development server is intended for local use.

## Project Goals

NetPulse is being developed to gain practical experience in network programming, API development, database design, automated testing, and frontend engineering.

The long-term goal is to build an extensible monitoring application that provides useful insights into network availability and performance.

---

**Built as a personal learning and software engineering project.**
