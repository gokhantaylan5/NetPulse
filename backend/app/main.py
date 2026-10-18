import sqlite3
from app.database import DB_PATH, init_db, add_target, get_targets
from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import IPvAnyAddress
from app.monitoring.ping import measure_ping
from app.monitoring.network import detect_networks


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
