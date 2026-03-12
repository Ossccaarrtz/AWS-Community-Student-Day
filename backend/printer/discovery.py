"""
Printer discovery engine.

Discovers printers connected via USB, Bluetooth, TCP/IP, and system queues.
All functions return structured data and never throw — errors are captured
in the candidate's fields or as warnings.
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
from typing import Optional

from .config import (
    ConnectionType,
    RIBETEC_KEYWORDS,
    TCP_DEFAULT_PORT,
    TCP_TIMEOUT_S,
    DEFAULT_DPI,
)
from .models import PrinterCandidate, DiscoverResult


def _keyword_score(text: str) -> float:
    """Return a confidence boost based on how many Ribetec keywords match."""
    text_lower = text.lower()
    hits = sum(1 for kw in RIBETEC_KEYWORDS if kw in text_lower)
    return min(hits * 0.15, 0.45)


def _run_cmd(cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
    """Run a subprocess command and return (success, stdout)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, result.stdout
    except FileNotFoundError:
        return False, ""
    except subprocess.TimeoutExpired:
        return False, ""
    except Exception as e:
        return False, str(e)


# ── System queue discovery ────────────────────────────────────────


def discover_system_printers() -> list[PrinterCandidate]:
    """List printers installed in the OS print system."""
    system = platform.system()
    candidates: list[PrinterCandidate] = []

    if system == "Windows":
        candidates = _discover_windows_system_printers()
    elif system == "Darwin":
        candidates = _discover_macos_system_printers()
    elif system == "Linux":
        candidates = _discover_linux_system_printers()

    return candidates


def _discover_windows_system_printers() -> list[PrinterCandidate]:
    """Discover printers via wmic / PowerShell on Windows."""
    candidates: list[PrinterCandidate] = []

    # Try PowerShell first (wmic is deprecated)
    ok, output = _run_cmd([
        "powershell", "-NoProfile", "-Command",
        "Get-Printer | Select-Object Name, DriverName, PortName, PrinterStatus | Format-List"
    ])

    if ok and output.strip():
        blocks = re.split(r"\n\s*\n", output.strip())
        for block in blocks:
            fields: dict[str, str] = {}
            for line in block.strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    fields[key.strip()] = val.strip()

            name = fields.get("Name", "")
            driver = fields.get("DriverName", "")
            port = fields.get("PortName", "")
            if not name:
                continue

            full_text = f"{name} {driver} {port}"
            score = 0.3 + _keyword_score(full_text)

            # Infer connection type from port name
            conn = ConnectionType.SYSTEM_QUEUE
            transport = f"port={port}"
            if port and re.match(r"^USB\d+", port, re.IGNORECASE):
                conn = ConnectionType.USB
                score += 0.05
            elif port and re.match(r"^(COM\d+|/dev/tty)", port, re.IGNORECASE):
                conn = ConnectionType.SERIAL
            elif port and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", port):
                conn = ConnectionType.TCP
                transport = f"ip={port}"

            candidates.append(PrinterCandidate(
                name=name,
                connection_type=conn,
                vendor=_guess_vendor(full_text),
                driver_name=driver or "unknown",
                transport_details=transport,
                dpi_estimate=DEFAULT_DPI,
                can_print_via_system_driver=True,
                can_print_raw=conn in (ConnectionType.USB, ConnectionType.TCP),
                confidence_score=round(min(score, 1.0), 2),
            ))
    else:
        # Fallback: wmic
        ok2, output2 = _run_cmd([
            "wmic", "printer", "get",
            "Name,DriverName,PortName,Status", "/format:csv"
        ])
        if ok2 and output2.strip():
            for line in output2.strip().splitlines()[1:]:
                parts = line.strip().split(",")
                if len(parts) < 4:
                    continue
                # CSV: Node, DriverName, Name, PortName, Status
                driver = parts[1] if len(parts) > 1 else ""
                name = parts[2] if len(parts) > 2 else ""
                port = parts[3] if len(parts) > 3 else ""
                if not name:
                    continue

                full_text = f"{name} {driver} {port}"
                score = 0.25 + _keyword_score(full_text)
                candidates.append(PrinterCandidate(
                    name=name,
                    connection_type=ConnectionType.SYSTEM_QUEUE,
                    vendor=_guess_vendor(full_text),
                    driver_name=driver or "unknown",
                    transport_details=f"port={port}",
                    dpi_estimate=DEFAULT_DPI,
                    can_print_via_system_driver=True,
                    confidence_score=round(min(score, 1.0), 2),
                ))

    return candidates


def _discover_macos_system_printers() -> list[PrinterCandidate]:
    """Discover printers via lpstat on macOS."""
    ok, output = _run_cmd(["lpstat", "-p", "-d"])
    candidates: list[PrinterCandidate] = []
    if not ok:
        return candidates

    for line in output.splitlines():
        m = re.match(r"printer\s+(\S+)", line)
        if m:
            name = m.group(1)
            score = 0.25 + _keyword_score(name)
            candidates.append(PrinterCandidate(
                name=name,
                connection_type=ConnectionType.SYSTEM_QUEUE,
                vendor=_guess_vendor(name),
                transport_details="cups",
                dpi_estimate=DEFAULT_DPI,
                can_print_via_system_driver=True,
                confidence_score=round(min(score, 1.0), 2),
            ))
    return candidates


def _discover_linux_system_printers() -> list[PrinterCandidate]:
    """Discover printers via lpstat on Linux."""
    return _discover_macos_system_printers()  # Same CUPS-based logic


# ── USB discovery ─────────────────────────────────────────────────


def discover_usb_printers() -> list[PrinterCandidate]:
    """Discover USB-connected printers."""
    candidates: list[PrinterCandidate] = []
    system = platform.system()

    if system == "Windows":
        ok, output = _run_cmd([
            "powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -Class Printer -Status OK | Select-Object FriendlyName, InstanceId | Format-List"
        ])
        if ok and output.strip():
            blocks = re.split(r"\n\s*\n", output.strip())
            for block in blocks:
                fields: dict[str, str] = {}
                for line in block.strip().splitlines():
                    if ":" in line:
                        key, _, val = line.partition(":")
                        fields[key.strip()] = val.strip()

                name = fields.get("FriendlyName", "")
                instance = fields.get("InstanceId", "")
                if not name or "USB" not in instance.upper():
                    continue

                score = 0.4 + _keyword_score(name)
                candidates.append(PrinterCandidate(
                    name=name,
                    connection_type=ConnectionType.USB,
                    vendor=_guess_vendor(name),
                    transport_details=f"instance={instance}",
                    dpi_estimate=DEFAULT_DPI,
                    can_print_raw=True,
                    can_print_via_system_driver=True,
                    confidence_score=round(min(score, 1.0), 2),
                ))

    elif system in ("Linux", "Darwin"):
        ok, output = _run_cmd(["lsusb"])
        if ok:
            for line in output.splitlines():
                low = line.lower()
                if any(kw in low for kw in ["printer", "label", "ribetec", "thermal"]):
                    score = 0.35 + _keyword_score(line)
                    candidates.append(PrinterCandidate(
                        name=line.strip(),
                        connection_type=ConnectionType.USB,
                        vendor=_guess_vendor(line),
                        transport_details="lsusb",
                        dpi_estimate=DEFAULT_DPI,
                        can_print_raw=True,
                        confidence_score=round(min(score, 1.0), 2),
                    ))

    return candidates


# ── Bluetooth discovery ───────────────────────────────────────────


def discover_bluetooth_printers() -> list[PrinterCandidate]:
    """Discover paired Bluetooth devices that might be printers."""
    candidates: list[PrinterCandidate] = []
    system = platform.system()

    if system == "Windows":
        ok, output = _run_cmd([
            "powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -Class Bluetooth -Status OK | Select-Object FriendlyName, InstanceId | Format-List"
        ])
        if ok and output.strip():
            blocks = re.split(r"\n\s*\n", output.strip())
            for block in blocks:
                fields: dict[str, str] = {}
                for line in block.strip().splitlines():
                    if ":" in line:
                        key, _, val = line.partition(":")
                        fields[key.strip()] = val.strip()

                name = fields.get("FriendlyName", "")
                if not name:
                    continue

                low = name.lower()
                if any(kw in low for kw in RIBETEC_KEYWORDS + ["print", "label"]):
                    score = 0.3 + _keyword_score(name)
                    candidates.append(PrinterCandidate(
                        name=name,
                        connection_type=ConnectionType.BLUETOOTH,
                        vendor=_guess_vendor(name),
                        transport_details="bluetooth",
                        dpi_estimate=DEFAULT_DPI,
                        can_print_raw=True,
                        confidence_score=round(min(score, 1.0), 2),
                    ))

    elif system == "Linux":
        ok, output = _run_cmd(["bluetoothctl", "paired-devices"])
        if ok:
            for line in output.splitlines():
                low = line.lower()
                if any(kw in low for kw in RIBETEC_KEYWORDS + ["print", "label"]):
                    score = 0.25 + _keyword_score(line)
                    candidates.append(PrinterCandidate(
                        name=line.strip(),
                        connection_type=ConnectionType.BLUETOOTH,
                        vendor=_guess_vendor(line),
                        transport_details="bluetooth",
                        dpi_estimate=DEFAULT_DPI,
                        can_print_raw=True,
                        confidence_score=round(min(score, 1.0), 2),
                    ))

    return candidates


# ── TCP/IP discovery ──────────────────────────────────────────────


def discover_tcp_printer(
    ip: str,
    port: int = TCP_DEFAULT_PORT,
    timeout: float = TCP_TIMEOUT_S,
) -> Optional[PrinterCandidate]:
    """Test TCP connection to a raw-print port and return candidate if reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()

        return PrinterCandidate(
            name=f"TCP Printer @ {ip}:{port}",
            connection_type=ConnectionType.TCP,
            vendor="unknown",
            transport_details=f"ip={ip}, port={port}",
            dpi_estimate=DEFAULT_DPI,
            can_print_raw=True,
            can_print_via_system_driver=False,
            confidence_score=0.55,
        )
    except (socket.timeout, ConnectionRefusedError, OSError):
        return None


# ── Aggregated discovery ──────────────────────────────────────────


def discover_all(
    tcp_ip: Optional[str] = None,
    tcp_port: int = TCP_DEFAULT_PORT,
) -> DiscoverResult:
    """
    Run all discovery methods and return a sorted list of candidates.

    Priority order (by confidence_score, highest first):
      1. Ribetec system printers
      2. USB label printers
      3. TCP/IP reachable printers
      4. Bluetooth printers
      5. Generic system printers
    """
    warnings: list[str] = []
    candidates: list[PrinterCandidate] = []

    # System queue
    try:
        candidates.extend(discover_system_printers())
    except Exception as e:
        warnings.append(f"System printer discovery failed: {e}")

    # USB
    try:
        candidates.extend(discover_usb_printers())
    except Exception as e:
        warnings.append(f"USB printer discovery failed: {e}")

    # Bluetooth
    try:
        candidates.extend(discover_bluetooth_printers())
    except Exception as e:
        warnings.append(f"Bluetooth printer discovery failed: {e}")

    # TCP/IP (if IP provided)
    if tcp_ip:
        try:
            tcp_candidate = discover_tcp_printer(tcp_ip, tcp_port)
            if tcp_candidate:
                candidates.append(tcp_candidate)
            else:
                warnings.append(f"TCP printer at {tcp_ip}:{tcp_port} not reachable.")
        except Exception as e:
            warnings.append(f"TCP printer discovery failed: {e}")

    # De-duplicate by name (keep highest confidence)
    seen: dict[str, PrinterCandidate] = {}
    for c in candidates:
        key = c.name.lower().strip()
        if key not in seen or c.confidence_score > seen[key].confidence_score:
            seen[key] = c
    candidates = list(seen.values())

    # Sort by confidence (descending)
    candidates.sort(key=lambda c: c.confidence_score, reverse=True)

    if not candidates:
        warnings.append(
            "No printers discovered. The agent will operate in simulation mode."
        )

    return DiscoverResult(
        success=True,
        candidates=candidates,
        warnings=warnings,
    )


# ── Helpers ───────────────────────────────────────────────────────


def _guess_vendor(text: str) -> str:
    """Guess vendor name from a text string."""
    low = text.lower()
    vendors = {
        "ribetec": "Ribetec",
        "zebra": "Zebra",
        "tsc": "TSC",
        "brother": "Brother",
        "dymo": "DYMO",
        "epson": "Epson",
        "honeywell": "Honeywell",
        "bixolon": "Bixolon",
        "citizen": "Citizen",
        "sato": "SATO",
        "godex": "Godex",
        "datamax": "Datamax",
    }
    for keyword, vendor_name in vendors.items():
        if keyword in low:
            return vendor_name
    return "unknown"
