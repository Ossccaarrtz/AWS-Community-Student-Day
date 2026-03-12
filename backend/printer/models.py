"""
Pydantic models for the MCP Label Printer Agent request/response contracts.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from .config import (
    ConnectionType,
    ErrorClass,
    PrintMode,
    DEFAULT_DPI,
    DEFAULT_LABEL_HEIGHT_IN,
    DEFAULT_LABEL_WIDTH_IN,
)


# ── Request models ────────────────────────────────────────────────


class PrinterHint(BaseModel):
    """Optional hints to help select a printer."""
    name: Optional[str] = None
    connection_type: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None


class LabelField(BaseModel):
    """A key-value field on a label."""
    label: str
    value: str


class LabelContent(BaseModel):
    """Content to print on a label."""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    qr: Optional[str] = None
    barcode: Optional[str] = None
    fields: list[LabelField] = Field(default_factory=list)


class LabelSpec(BaseModel):
    """Label dimensions and content specification."""
    width_in: float = DEFAULT_LABEL_WIDTH_IN
    height_in: float = DEFAULT_LABEL_HEIGHT_IN
    dpi: Optional[int] = None
    copies: int = 1
    orientation: str = "landscape"
    content: LabelContent = Field(default_factory=LabelContent)


class PrintRequest(BaseModel):
    """Top-level print request."""
    action: str = "print_label"
    printer_hint: PrinterHint = Field(default_factory=PrinterHint)
    label: LabelSpec = Field(default_factory=LabelSpec)
    mode: PrintMode = PrintMode.PREVIEW_ONLY


# ── Printer candidate models ─────────────────────────────────────


class PrinterCandidate(BaseModel):
    """A discovered printer with inferred capabilities."""
    name: str = "Unknown Printer"
    connection_type: ConnectionType = ConnectionType.SIMULATION
    vendor: str = "unknown"
    model: str = "unknown"
    driver_name: str = "unknown"
    transport_details: str = ""
    dpi_estimate: int = DEFAULT_DPI
    max_width_mm: Optional[float] = None
    supported_media_type: str = "unknown"
    likely_command_language: str = "unknown"
    can_print_raw: bool = False
    can_print_via_system_driver: bool = False
    confidence_score: float = 0.0


# ── Response models ───────────────────────────────────────────────


class PrintStrategy(BaseModel):
    """The strategy chosen for printing."""
    method: str = "simulation"
    language: str = "unknown"
    rasterized: bool = True


class DiagnosticInfo(BaseModel):
    """Diagnostic details from a print job."""
    candidates_found: int = 0
    transport_test: str = "skipped"
    spool_submission: str = "skipped"
    metadata_file: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class PrintResult(BaseModel):
    """Result of a print action."""
    success: bool = True
    action: str = "print_label"
    job_id: str = ""
    selected_printer: Optional[PrinterCandidate] = None
    print_strategy: PrintStrategy = Field(default_factory=PrintStrategy)
    preview_generated: bool = False
    preview_base64: Optional[str] = None
    payload_file: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    diagnostics: DiagnosticInfo = Field(default_factory=DiagnosticInfo)
    error_class: ErrorClass = ErrorClass.NONE
    error_message: Optional[str] = None


class DiscoverResult(BaseModel):
    """Result of printer discovery."""
    success: bool = True
    candidates: list[PrinterCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ConnectionTestResult(BaseModel):
    """Result of a connection test."""
    success: bool = True
    printer: Optional[PrinterCandidate] = None
    method: str = "unknown"
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
