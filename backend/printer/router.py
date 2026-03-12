"""
FastAPI router for the MCP Label Printer Agent.

Endpoints:
  POST /printer/discover       — discover available printers
  POST /printer/capabilities   — get capabilities for a specific printer
  POST /printer/preview        — render a label preview
  POST /printer/test_connection — test connectivity to a printer
  POST /printer/print          — full print workflow
  POST /printer/save_job       — save rendered job to file
  GET  /printer/jobs           — list recent job logs
"""

from __future__ import annotations

import socket
import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .config import ConnectionType, PrintMode, TCP_DEFAULT_PORT, TCP_TIMEOUT_S
from .discovery import discover_all, discover_tcp_printer
from .executor import execute_print
from .logger import read_recent_jobs
from .models import (
    ConnectionTestResult,
    DiscoverResult,
    LabelSpec,
    PrinterCandidate,
    PrinterHint,
    PrintRequest,
    PrintResult,
    PrintStrategy,
)
from .renderer import generate_preview_base64, render_label

router = APIRouter(prefix="/printer", tags=["printer"])


# ── Request schemas for specific endpoints ────────────────────────


class DiscoverRequest(BaseModel):
    """Optional hints for discovery."""
    tcp_ip: Optional[str] = None
    tcp_port: int = TCP_DEFAULT_PORT


class PreviewRequest(BaseModel):
    """Request to render a label preview only."""
    label: LabelSpec = Field(default_factory=LabelSpec)


class TestConnectionRequest(BaseModel):
    """Request to test connectivity to a specific printer."""
    ip: Optional[str] = None
    port: int = TCP_DEFAULT_PORT
    printer_name: Optional[str] = None


class SaveJobRequest(BaseModel):
    """Request to render and save a job to file."""
    label: LabelSpec = Field(default_factory=LabelSpec)
    format: str = "prn"  # prn, bin, txt


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/discover", response_model=DiscoverResult)
def discover_printers(req: DiscoverRequest = None):
    """
    Discover all available printers.

    Inspects system queues, USB, Bluetooth, and optionally TCP/IP.
    Returns candidates sorted by confidence score.
    """
    if req is None:
        req = DiscoverRequest()

    return discover_all(tcp_ip=req.tcp_ip, tcp_port=req.tcp_port)


@router.post("/capabilities")
def get_printer_capabilities(req: DiscoverRequest = None):
    """
    Get capabilities for discovered printers.

    Returns each candidate with its inferred capabilities.
    """
    if req is None:
        req = DiscoverRequest()

    result = discover_all(tcp_ip=req.tcp_ip, tcp_port=req.tcp_port)

    capabilities = []
    for candidate in result.candidates:
        capabilities.append({
            "printer": candidate.model_dump(),
            "inferred_capabilities": {
                "can_print_raw": candidate.can_print_raw,
                "can_print_via_system_driver": candidate.can_print_via_system_driver,
                "likely_command_language": candidate.likely_command_language,
                "dpi_estimate": candidate.dpi_estimate,
                "max_width_mm": candidate.max_width_mm,
                "connection_type": candidate.connection_type.value,
                "confidence_score": candidate.confidence_score,
            },
        })

    return {
        "success": True,
        "printers": capabilities,
        "warnings": result.warnings,
    }


@router.post("/preview")
def preview_label(req: PreviewRequest):
    """
    Render a label preview without printing.

    Returns a base64-encoded PNG image.
    """
    render_result = render_label(req.label)
    preview_b64 = generate_preview_base64(render_result.image)

    return {
        "success": True,
        "preview_base64": preview_b64,
        "label_size": f"{req.label.width_in}x{req.label.height_in}in",
        "dpi_used": req.label.dpi or 203,
        "warnings": render_result.warnings,
    }


@router.post("/test_connection", response_model=ConnectionTestResult)
def test_connection(req: TestConnectionRequest):
    """
    Test connectivity to a printer.

    Supports TCP/IP (direct socket test) and system queue (name check).
    """
    if req.ip:
        start = time.time()
        candidate = discover_tcp_printer(req.ip, req.port)
        elapsed_ms = round((time.time() - start) * 1000, 1)

        if candidate:
            return ConnectionTestResult(
                success=True,
                printer=candidate,
                method="tcp",
                latency_ms=elapsed_ms,
            )
        else:
            return ConnectionTestResult(
                success=False,
                method="tcp",
                latency_ms=elapsed_ms,
                error_message=f"No se pudo conectar a {req.ip}:{req.port}",
            )

    elif req.printer_name:
        # Check if the printer exists in the system
        result = discover_all()
        match = next(
            (c for c in result.candidates if req.printer_name.lower() in c.name.lower()),
            None,
        )
        if match:
            return ConnectionTestResult(
                success=True,
                printer=match,
                method="system_queue",
            )
        else:
            return ConnectionTestResult(
                success=False,
                method="system_queue",
                error_message=f"Impresora '{req.printer_name}' no encontrada en el sistema.",
            )

    return ConnectionTestResult(
        success=False,
        method="unknown",
        error_message="Debe proporcionar 'ip' o 'printer_name'.",
    )


@router.post("/print", response_model=PrintResult)
def print_label(req: PrintRequest):
    """
    Full print workflow: discover → select → render → execute.

    Respects the print mode:
      - preview_only: render and return preview
      - dry_run: render, save payload, no printing
      - test_print: print with extra safety checks
      - actual_print: full print execution
    """
    # Discover printers
    tcp_ip = req.printer_hint.ip
    tcp_port = req.printer_hint.port or TCP_DEFAULT_PORT

    discovery = discover_all(tcp_ip=tcp_ip, tcp_port=tcp_port)

    # Execute the print job
    result = execute_print(req, discovery.candidates)

    # Add discovery warnings
    if discovery.warnings:
        result.warnings = discovery.warnings + result.warnings

    return result


@router.post("/save_job")
def save_job(req: SaveJobRequest):
    """
    Render a label and save the print job payload to a file.

    Useful for offline printing preparation or debugging.
    """
    from .renderer import generate_raster_payload
    from .executor import _save_payload, _next_job_id

    render_result = render_label(req.label)
    payload = generate_raster_payload(render_result.image)
    preview_b64 = generate_preview_base64(render_result.image)

    job_id = _next_job_id()
    filepath = _save_payload(job_id, payload)

    return {
        "success": True,
        "job_id": job_id,
        "payload_file": filepath,
        "payload_size_bytes": len(payload),
        "preview_base64": preview_b64,
        "warnings": render_result.warnings,
    }


@router.get("/jobs")
def list_jobs(count: int = 20):
    """List recent print job logs."""
    jobs = read_recent_jobs(count=count)
    return {
        "success": True,
        "total": len(jobs),
        "jobs": jobs,
    }
