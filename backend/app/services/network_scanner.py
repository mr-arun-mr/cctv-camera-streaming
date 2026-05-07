import asyncio
import logging
import socket
import netifaces

logger = logging.getLogger(__name__)

_scan_jobs: dict[str, dict] = {}  # job_id -> {status, results}


def _get_local_subnet() -> str:
    gws = netifaces.gateways()
    default = gws.get("default", {})
    iface = None
    for af, gw_info in default.items():
        if isinstance(gw_info, (list, tuple)) and len(gw_info) >= 2:
            iface = gw_info[1]
            break
    if iface is None:
        ifaces = netifaces.interfaces()
        for i in ifaces:
            if i != "lo":
                iface = i
                break
    if iface is None:
        return "192.168.1.0/24"
    addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
    if not addrs:
        return "192.168.1.0/24"
    ip = addrs[0]["addr"]
    parts = ip.split(".")
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"


async def _probe_rtsp_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def _scan_host(ip: str) -> dict | None:
    rtsp_ports = [554, 8554, 8080, 80]
    open_ports = []
    tasks = {port: _probe_rtsp_port(ip, port) for port in rtsp_ports}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for port, result in zip(tasks.keys(), results):
        if result is True:
            open_ports.append(port)
    if not open_ports:
        return None
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except Exception:
        hostname = ""
    return {"ip": ip, "open_ports": open_ports, "hostname": hostname, "mac": ""}


async def _run_scan(job_id: str):
    _scan_jobs[job_id] = {"status": "running", "results": []}
    subnet = _get_local_subnet()
    base = ".".join(subnet.split(".")[:3])
    hosts = [f"{base}.{i}" for i in range(1, 255)]

    batch_size = 50
    found = []
    for i in range(0, len(hosts), batch_size):
        batch = hosts[i:i + batch_size]
        results = await asyncio.gather(*[_scan_host(ip) for ip in batch])
        found.extend(r for r in results if r is not None)

    _scan_jobs[job_id] = {"status": "done", "results": found}
    logger.info("Network scan %s complete: %d hosts found", job_id, len(found))


def start_scan(job_id: str):
    asyncio.create_task(_run_scan(job_id))


def get_scan(job_id: str) -> dict | None:
    return _scan_jobs.get(job_id)
