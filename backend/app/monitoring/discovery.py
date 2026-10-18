
import ipaddress

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable

from app.monitoring.ping import PingResult, measure_ping


PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

MAX_ADDRESSES = 256
MAX_WORKERS = 16


def discover_hosts(
    cidr: str,
    ping_fn: Callable[[str], PingResult] = measure_ping
) -> list[PingResult]:

    network = ipaddress.ip_network(cidr, strict=True)

    if network.version != 4:
        raise ValueError("Only IPv4 networks are supported.")

    if not any(
        network.subnet_of(private)
        for private in PRIVATE_NETWORKS
    ):
        raise ValueError("Only private IPv4 networks are allowed.")

    if network.num_addresses > MAX_ADDRESSES:
        raise ValueError("Network exceeds the scan size limit.")

    addresses = [
        str(ip) for ip in network.hosts()
    ]

    if not addresses:
        return []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        results = executor.map(ping_fn, addresses)

        discovered = [
            result
            for result in results
            if result.reachable
        ]

    return discovered
