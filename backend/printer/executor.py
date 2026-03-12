"""
Print job executor with fallback chain.

Executes print jobs using the best available method:
  1. System driver (win32print / lp)
  2. TCP RAW (port 9100)
  3. USB direct (pyusb)
  4. Serial (pyserial / COM port)
  5. Simulation (save payload to file)
"""

from __future__ import annotations

import json
import base64
import os
import platform
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import (
    ConnectionType,
    ErrorClass,
    MAX_RETRIES,
    PrintMode,
    TCP_DEFAULT_PORT,
    TCP_TIMEOUT_S,
)
from .models import (
    DiagnosticInfo,
    LabelSpec,
    PrinterCandidate,
    PrintRequest,
    PrintResult,
    PrintStrategy,
)
from .renderer import generate_preview_base64, generate_raster_payload, render_label
from .logger import log_job


# ── Job ID generator ──────────────────────────────────────────────

_job_counter = 0


def _next_job_id() -> str:
    global _job_counter
    _job_counter += 1
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"job_{ts}_{_job_counter:04d}"


# ── Main executor ─────────────────────────────────────────────────


def execute_print(
    request: PrintRequest,
    candidates: list[PrinterCandidate],
) -> PrintResult:
    """
    Execute a print job based on the request mode and available printers.

    Flow:
      1. Render label to bitmap
      2. Select best printer candidate
      3. Choose print strategy
      4. Execute (or simulate) print
      5. Log the job
    """
    job_id = _next_job_id()
    warnings: list[str] = []
    mode = request.mode

    # ── 1. Render ─────────────────────────────────────────────────
    dpi = request.label.dpi
    try:
        render_result = render_label(request.label, dpi=dpi)
        image = render_result.image
        warnings.extend(render_result.warnings)
    except Exception as e:
        return _error_result(
            job_id, "render_label", ErrorClass.RENDERING_ERROR,
            f"Error al renderizar etiqueta: {e}", warnings,
        )

    preview_b64 = generate_preview_base64(image)

    # ── Preview-only mode ─────────────────────────────────────────
    if mode == PrintMode.PREVIEW_ONLY:
        result = PrintResult(
            success=True,
            action="preview_label",
            job_id=job_id,
            preview_generated=True,
            preview_base64=preview_b64,
            warnings=warnings,
            diagnostics=DiagnosticInfo(candidates_found=len(candidates)),
        )
        log_job(job_id, "preview_only", None, "preview", request.label, "none", "ok", warnings)
        return result

    # ── 2. Generate raster payload ────────────────────────────────
    try:
        payload = generate_raster_payload(image)
    except Exception as e:
        return _error_result(
            job_id, "generate_payload", ErrorClass.RENDERING_ERROR,
            f"Error al generar payload raster: {e}", warnings,
        )

    # ── Dry-run mode ──────────────────────────────────────────────
    if mode == PrintMode.DRY_RUN:
        payload_file, metadata_file = _save_diagnostics(
            job_id, payload, preview_b64, request, candidates[0] if candidates else None
        )
        result = PrintResult(
            success=True,
            action="dry_run",
            job_id=job_id,
            selected_printer=candidates[0] if candidates else None,
            print_strategy=PrintStrategy(method="dry_run", rasterized=True),
            preview_generated=True,
            preview_base64=preview_b64,
            payload_file=payload_file,
            warnings=warnings,
            diagnostics=DiagnosticInfo(
                candidates_found=len(candidates),
                transport_test="skipped",
                spool_submission="saved_to_file",
                metadata_file=metadata_file,
            ),
        )
        log_job(job_id, "dry_run", None, "file", request.label, "file", "ok", warnings)
        return result

    # ── 3. Select best candidate ──────────────────────────────────
    selected = _select_printer(candidates, request)

    if not selected:
        # No printers — simulate
        payload_file, metadata_file = _save_diagnostics(job_id, payload, preview_b64, request, None)
        warnings.append("No se encontró impresora. Resultado guardado en simulación.")
        result = PrintResult(
            success=True,
            action=request.action,
            job_id=job_id,
            print_strategy=PrintStrategy(method="simulation", rasterized=True),
            preview_generated=True,
            preview_base64=preview_b64,
            payload_file=payload_file,
            warnings=warnings,
            diagnostics=DiagnosticInfo(
                candidates_found=0,
                transport_test="no_printer",
                spool_submission="simulated",
                metadata_file=metadata_file,
            ),
        )
        log_job(job_id, request.action, None, "simulation", request.label, "none", "simulated", warnings)
        return result

    # ── 4. Execute print ──────────────────────────────────────────
    strategy, transport_result, error = _try_print(selected, payload, request.label)

    if error:
        payload_file, metadata_file = _save_diagnostics(job_id, payload, preview_b64, request, selected, error=error)
        warnings.append(f"Impresión falló: {error}. Payload guardado en {payload_file}.")
        result = PrintResult(
            success=False,
            action=request.action,
            job_id=job_id,
            selected_printer=selected,
            print_strategy=strategy,
            preview_generated=True,
            preview_base64=preview_b64,
            payload_file=payload_file,
            warnings=warnings,
            error_class=ErrorClass.SPOOLER_ERROR,
            error_message=error,
            diagnostics=DiagnosticInfo(
                candidates_found=len(candidates),
                transport_test="failed",
                spool_submission="failed",
                metadata_file=metadata_file,
            ),
        )
        log_job(job_id, request.action, selected.name, strategy.method, request.label, selected.connection_type.value, "error", warnings, ErrorClass.SPOOLER_ERROR.value)
        return result

    # ── Success ───────────────────────────────────────────────────
    payload_file, metadata_file = _save_diagnostics(job_id, payload, preview_b64, request, selected)
    result = PrintResult(
        success=True,
        action=request.action,
        job_id=job_id,
        selected_printer=selected,
        print_strategy=strategy,
        preview_generated=True,
        preview_base64=preview_b64,
        payload_file=payload_file,
        warnings=warnings,
        diagnostics=DiagnosticInfo(
            candidates_found=len(candidates),
            transport_test=transport_result,
            spool_submission="ok",
            metadata_file=metadata_file,
        ),
    )
    log_job(job_id, request.action, selected.name, strategy.method, request.label, selected.connection_type.value, "ok", warnings)
    return result


# ── Printer selection ─────────────────────────────────────────────


def _select_printer(
    candidates: list[PrinterCandidate],
    request: PrintRequest,
) -> Optional[PrinterCandidate]:
    """Select the best printer candidate, optionally filtered by hints."""
    if not candidates:
        return None

    hint = request.printer_hint
    filtered = candidates

    if hint.name:
        name_lower = hint.name.lower()
        filtered = [c for c in filtered if name_lower in c.name.lower()]

    if hint.connection_type:
        filtered = [c for c in filtered if c.connection_type.value == hint.connection_type]

    if hint.ip:
        filtered = [c for c in filtered if hint.ip in c.transport_details]

    return filtered[0] if filtered else candidates[0]


# ── Print methods with fallback chain ─────────────────────────────


def _try_print(
    printer: PrinterCandidate,
    payload: bytes,
    label: LabelSpec,
) -> tuple[PrintStrategy, str, Optional[str]]:
    """
    Attempt to print using the best method for the selected printer.

    Returns (strategy, transport_result, error_message | None).
    """
    methods = _get_method_chain(printer)

    for method_name, method_fn in methods:
        strategy = PrintStrategy(method=method_name, rasterized=True)
        try:
            result = method_fn(printer, payload)
            return strategy, result, None
        except Exception as e:
            continue  # try next method

    # All methods failed
    return (
        PrintStrategy(method="all_failed", rasterized=True),
        "failed",
        "Todos los métodos de impresión fallaron.",
    )


def _get_method_chain(printer: PrinterCandidate) -> list[tuple[str, callable]]:
    """Return ordered list of (method_name, method_fn) to try."""
    chain = []

    if printer.can_print_via_system_driver:
        chain.append(("system_driver", _print_via_system_driver))

    if printer.connection_type == ConnectionType.TCP and printer.can_print_raw:
        chain.append(("tcp_raw", _print_via_tcp_raw))

    if printer.connection_type == ConnectionType.USB and printer.can_print_raw:
        chain.append(("usb_raw", _print_via_usb_raw))

    if printer.connection_type in (ConnectionType.SERIAL, ConnectionType.BLUETOOTH):
        chain.append(("serial", _print_via_serial))

    # Always have system driver as final fallback
    if not any(m[0] == "system_driver" for m in chain):
        chain.append(("system_driver", _print_via_system_driver))

    return chain


# ── Print method implementations ─────────────────────────────────


def _print_via_system_driver(printer: PrinterCandidate, payload: bytes) -> str:
    """Print using the OS print system (win32print on Windows, lp on Unix)."""
    system = platform.system()

    if system == "Windows":
        return _win32_print(printer.name, payload)
    else:
        return _unix_lp_print(printer.name, payload)


def _win32_print(printer_name: str, payload: bytes) -> str:
    """Print via win32print on Windows."""
    try:
        import win32print

        hprinter = win32print.OpenPrinter(printer_name)
        try:
            job_info = win32print.StartDocPrinter(hprinter, 1, ("MCP Label", None, "RAW"))
            try:
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, payload)
                win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
        return "ok"
    except ImportError:
        raise RuntimeError("pywin32 no está instalado. Instale con: pip install pywin32")
    except Exception as e:
        raise RuntimeError(f"Error win32print: {e}")


def _unix_lp_print(printer_name: str, payload: bytes) -> str:
    """Print via lp command on Linux/macOS."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".prn", delete=False) as f:
        f.write(payload)
        tmp = f.name

    try:
        result = subprocess.run(
            ["lp", "-d", printer_name, "-o", "raw", tmp],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError(f"lp error: {result.stderr}")
        return "ok"
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _print_via_tcp_raw(printer: PrinterCandidate, payload: bytes) -> str:
    """Send raw data to printer via TCP (port 9100)."""
    # Parse IP and port from transport_details
    ip, port = _parse_tcp_details(printer.transport_details)

    for attempt in range(MAX_RETRIES + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TCP_TIMEOUT_S)
            sock.connect((ip, port))
            sock.sendall(payload)
            sock.close()
            return "ok"
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"TCP print falló después de {MAX_RETRIES + 1} intentos: {e}")
            time.sleep(0.5)

    return "ok"


def _print_via_usb_raw(printer: PrinterCandidate, payload: bytes) -> str:
    """Send raw data via USB (pyusb)."""
    try:
        import usb.core
        import usb.util

        dev = usb.core.find(find_all=False)
        if dev is None:
            raise RuntimeError("No se encontró dispositivo USB.")

        cfg = dev.get_active_configuration()
        intf = cfg[(0, 0)]
        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        if ep_out is None:
            raise RuntimeError("No se encontró endpoint USB de salida.")

        ep_out.write(payload)
        return "ok"
    except ImportError:
        raise RuntimeError("pyusb no está instalado.")
    except Exception as e:
        raise RuntimeError(f"USB print error: {e}")


def _print_via_serial(printer: PrinterCandidate, payload: bytes) -> str:
    """Send raw data via serial port (Bluetooth COM or USB serial)."""
    try:
        import serial as pyserial

        # Try to extract port from transport_details
        port = _extract_serial_port(printer.transport_details)
        if not port:
            raise RuntimeError("No se encontró puerto serial en los detalles de transporte.")

        ser = pyserial.Serial(port, 9600, timeout=5)
        ser.write(payload)
        ser.flush()
        ser.close()
        return "ok"
    except ImportError:
        raise RuntimeError("pyserial no está instalado.")
    except Exception as e:
        raise RuntimeError(f"Serial print error: {e}")


# ── Helpers ───────────────────────────────────────────────────────


def _parse_tcp_details(transport: str) -> tuple[str, int]:
    """Extract IP and port from transport_details string."""
    import re
    ip_match = re.search(r"ip=([^\s,]+)", transport)
    port_match = re.search(r"port=(\d+)", transport)

    ip = ip_match.group(1) if ip_match else "127.0.0.1"
    port = int(port_match.group(1)) if port_match else TCP_DEFAULT_PORT
    return ip, port


def _extract_serial_port(transport: str) -> Optional[str]:
    """Extract COM port or /dev/tty path from transport details."""
    import re
    m = re.search(r"(COM\d+|/dev/tty\S+)", transport, re.IGNORECASE)
    return m.group(1) if m else None


def _save_payload(job_id: str, payload: bytes) -> str:
    """Save a payload to a .prn file and return the path."""
    jobs_dir = Path("printer_jobs")
    jobs_dir.mkdir(exist_ok=True)
    filepath = jobs_dir / f"{job_id}.prn"
    filepath.write_bytes(payload)
    return str(filepath)


def _save_diagnostics(
    job_id: str,
    payload: bytes,
    preview_b64: str,
    request: PrintRequest,
    printer: Optional[PrinterCandidate],
    error: Optional[str] = None,
) -> tuple[str, str]:
    """
    Save .prn, .png, and .json metadata for thorough printer diagnostic testing.
    Returns (payload_file_path, metadata_file_path).
    """
    jobs_dir = Path("printer_jobs")
    jobs_dir.mkdir(exist_ok=True)

    # 1. Save .prn
    prn_path = jobs_dir / f"{job_id}.prn"
    prn_path.write_bytes(payload)

    # 2. Save .png
    png_path = jobs_dir / f"{job_id}_preview.png"
    try:
        if preview_b64.startswith("data:image"):
            b64_data = preview_b64.split(",")[1]
        else:
            b64_data = preview_b64
        png_path.write_bytes(base64.b64decode(b64_data))
    except Exception:
        pass

    # 3. Save .json
    meta_path = jobs_dir / f"{job_id}_metadata.json"
    
    # Try reading the used profile matching config
    from .config import RT420ME_PROFILE
    
    metadata = {
        "job_id": job_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "printer_name": printer.name if printer else "simulated",
        "printer_vendor": printer.vendor if printer else "unknown",
        "mode": request.mode.value,
        "label_size": f"{request.label.width_in}x{request.label.height_in}",
        "dpi": request.label.dpi or 203,
        "bytes_sent": len(payload),
        "render_mode": "raster",
        "error": error,
        "assumed_profile": "printer_profile_rt420me" if request.label.width_in == 3.0 and request.label.dpi == 203 else "generic",
    }
    
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    return str(prn_path), str(meta_path)


def _error_result(
    job_id: str,
    action: str,
    error_class: ErrorClass,
    message: str,
    warnings: list[str],
) -> PrintResult:
    """Build an error PrintResult."""
    return PrintResult(
        success=False,
        action=action,
        job_id=job_id,
        error_class=error_class,
        error_message=message,
        warnings=warnings,
        diagnostics=DiagnosticInfo(),
    )
