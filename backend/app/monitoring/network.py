
import ipaddress
import socket

import psutil


PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


def calculate_network(ip: str, netmask: str) -> str | None:
    try:
        address = ipaddress.ip_address(ip)

        if not any(address in net for net in PRIVATE_NETWORKS):
            return None

        interface = ipaddress.ip_interface(
            f"{ip}/{netmask}"
        )

        return str(interface.network)

    except ValueError:
        return None


def get_primary_ip() -> str | None:
    try:
        with socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        ) as sock:
            sock.connect(("1.1.1.1", 53))
            return sock.getsockname()[0]

    except OSError:
        return None


def detect_networks() -> list[dict]:
    networks = []
    primary_ip = get_primary_ip()
    stats = psutil.net_if_stats()

    for name, addresses in psutil.net_if_addrs().items():
        adapter = stats.get(name)

        if adapter is None or not adapter.isup:
            continue

        for addr in addresses:
            if addr.family != socket.AF_INET:
                continue

            if not addr.netmask:
                continue

            network = calculate_network(
                addr.address,
                addr.netmask
            )

            if network is None:
                continue

            networks.append({
                "interface": name,
                "ip": addr.address,
                "netmask": addr.netmask,
                "network": network,
                "is_primary": addr.address == primary_ip
            })

    return sorted(
        networks,
        key=lambda item: not item["is_primary"]
    )
