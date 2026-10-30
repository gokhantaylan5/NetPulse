import sqlite3
import ipaddress
from app.database import DB_PATH, init_db, add_target, get_targets
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import IPvAnyAddress
from app.monitoring.ping import measure_ping
from app.monitoring.network import detect_networks
from fastapi import Query, Path
from app.database import get_measurements
from app.database import get_monitoring_summary
from app.database import delete_target
from typing import Literal
from app.database import get_incidents
from app.monitoring.availability import get_target_availability

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database when the application starts
    init_db(DB_PATH)

    yield

    # Future shutdown operations can go here


app = FastAPI(
    title="NetPulse API",
    description="A modular network monitoring platform",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "NetPulse API"
    }


@app.get("/api/monitor/ping")
def ping_target(host: IPvAnyAddress):
    result = measure_ping(str(host))

    return {
        "host": result.host,
        "reachable": result.reachable,
        "latency_ms": result.latency_ms
    }


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    address: IPvAnyAddress


@app.post("/api/targets", status_code=status.HTTP_201_CREATED)
def create_target(target: TargetCreate):
    try:
        target_id = add_target(
            name=target.name,
            address=str(target.address),
            db_path=DB_PATH
        )

        return {
            "id": target_id,
            "name": target.name,
            "address": str(target.address)
        }

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="This IP address is already registered."
        )



@app.get("/api/targets")
def list_targets():
    return get_targets(db_path=DB_PATH)



@app.get("/api/network/interfaces")
def list_network_interfaces():
    return detect_networks()


from app.monitoring.discovery import (
    discover_hosts,
    MAX_ADDRESSES,
    PRIVATE_NETWORKS,
)


class NetworkScanRequest(BaseModel):
    network: str = Field(min_length=1, max_length=43)


@app.post("/api/network/discover")
def scan_network(request: NetworkScanRequest):
    try:
        network = ipaddress.ip_network(
            request.network,
            strict=True
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid network CIDR."
        ) from exc

    if not isinstance(network, ipaddress.IPv4Network):
        raise HTTPException(
            status_code=422,
            detail="Only IPv4 networks are supported."
        )

    if network.num_addresses > MAX_ADDRESSES:
        raise HTTPException(
            status_code=400,
            detail="Network exceeds scan size limit."
        )

    if not any(
        network.subnet_of(private)
        for private in PRIVATE_NETWORKS
    ):
        raise HTTPException(
            status_code=403,
            detail="Only private networks can be scanned."
        )

    interfaces = detect_networks()

    allowed = any(
        network.subnet_of(
            ipaddress.ip_network(item["network"])
        )
        for item in interfaces
    )

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Network is not on an active local interface."
        )

    results = discover_hosts(str(network))

    return {
        "network": str(network),
        "discovered_count": len(results),
        "devices": [
            {
                "ip": result.host,
                "reachable": result.reachable,
                "latency_ms": result.latency_ms
            }
            for result in results
        ]
    }


@app.get("/api/targets/{target_id}/measurements")
def list_target_measurements(
    target_id: int = Path(gt=0),
    limit: int = Query(default=100, ge=1, le=1000)
):
    return get_measurements(
        target_id=target_id,
        limit=limit,
        db_path=DB_PATH
    )


@app.get("/api/monitor/summary")
def monitoring_summary():
    return get_monitoring_summary(
        db_path=DB_PATH
    )



@app.delete(
    "/api/targets/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def remove_target(target_id: int = Path(gt=0)):
    deleted = delete_target(
        target_id=target_id,
        db_path=DB_PATH
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Target not found."
        )



@app.get("/api/incidents")
def list_incidents(
    status: Literal["open", "resolved"] | None = Query(
        default=None,
        description="Filter incidents by status."
    )
):
    """
    Retrieve network monitoring incidents.

    Without a status parameter, return all incidents.

    Supported filters:
        open
        resolved
    """

    return get_incidents(
        status=status,
        db_path=DB_PATH
    )



@app.get("/api/targets/{target_id}/availability")
def target_availability(
    target_id: int = Path(gt=0),
    hours: int = Query(default=24, ge=1, le=168)
):
    """
    Return monitoring check statistics and coverage
    for a selected target and time window.
    """

    result = get_target_availability(
        target_id=target_id,
        hours=hours,
        db_path=DB_PATH
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Target not found."
        )

    return result
