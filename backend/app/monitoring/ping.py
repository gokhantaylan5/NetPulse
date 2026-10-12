import subprocess
import re
from dataclasses import dataclass

def ping_host(host: str) -> bool:
    result = subprocess.run(
        ["ping", "-n", "1", "-w", "1000", host],
        capture_output=True,
        text=True,
        timeout=3,
        check=False
    )

    return result.returncode == 0



def parse_latency(output: str) -> float | None:
    pattern = r"\b(?:time|süre)\s*=\s*(\d+(?:[.,]\d+)?)\s*ms\b"

    match = re.search(pattern, output, re.IGNORECASE)

    if match is None:
        return None

    value = match.group(1).replace(",", ".")
    return float(value)



@dataclass
class PingResult:
    host: str
    reachable: bool
    latency_ms: float | None


def measure_ping(host: str) -> PingResult:
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", host],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=3,
            check=False
        )

        latency = parse_latency(result.stdout)

        reachable = (
            result.returncode == 0
            and (
                latency is not None
                or "ttl=" in result.stdout.lower()
            )
        )

        return PingResult(
            host=host,
            reachable=reachable,
            latency_ms=latency if reachable else None
        )

    except subprocess.TimeoutExpired:
        return PingResult(
            host=host,
            reachable=False,
            latency_ms=None
        )
