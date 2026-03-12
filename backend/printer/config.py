"""
Configuration constants and enums for the MCP Label Printer Agent.
"""

from enum import Enum


# ── Label defaults ────────────────────────────────────────────────
DEFAULT_DPI = 203
DEFAULT_LABEL_WIDTH_IN = 3.0
DEFAULT_LABEL_HEIGHT_IN = 2.0
SAFETY_MARGIN_MM = 2.0          # margin on each side
SAFETY_MARGIN_IN = SAFETY_MARGIN_MM / 25.4

# ── Ribetec RT-420ME Profile ──────────────────────────────────────
RT420ME_PROFILE = {
    "dpi": 203,
    "label_width_in": 3.0,
    "label_height_in": 2.0,
    "print_mode": "thermal_direct",
    "default_render_mode": "raster",
    "connection_priority": ["system_queue", "usb", "tcp"]
}

# ── Network defaults ─────────────────────────────────────────────
TCP_DEFAULT_PORT = 9100
TCP_TIMEOUT_S = 5
USB_TIMEOUT_MS = 3000
SERIAL_TIMEOUT_S = 3
SERIAL_BAUDRATE = 9600

# ── Job execution ─────────────────────────────────────────────────
MAX_RETRIES = 2
JOB_LOG_FILE = "print_jobs.log"

# ── Vendor keywords for discovery ─────────────────────────────────
RIBETEC_KEYWORDS = [
    "ribetec", "rib-etec", "label printer", "thermal printer",
    "etiquetas", "barcode printer",
]

# ── Supported command languages ───────────────────────────────────
KNOWN_LANGUAGES = ["zpl", "tspl", "epl", "escpos"]


class PrintMode(str, Enum):
    """Supported print modes."""
    PREVIEW_ONLY = "preview_only"
    DRY_RUN = "dry_run"
    TEST_PRINT = "test_print"
    ACTUAL_PRINT = "actual_print"


class ConnectionType(str, Enum):
    """Printer connection types."""
    USB = "usb"
    BLUETOOTH = "bluetooth"
    TCP = "tcp"
    SYSTEM_QUEUE = "system_queue"
    SERIAL = "serial"
    SIMULATION = "simulation"


class ErrorClass(str, Enum):
    """Classifiable error types."""
    DETECTION_ERROR = "detection_error"
    PERMISSION_ERROR = "permission_error"
    USB_TRANSPORT_ERROR = "usb_transport_error"
    BLUETOOTH_TRANSPORT_ERROR = "bluetooth_transport_error"
    TCP_TRANSPORT_ERROR = "tcp_transport_error"
    SPOOLER_ERROR = "spooler_error"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    RENDERING_ERROR = "rendering_error"
    LABEL_OVERFLOW = "label_overflow"
    UNCERTAIN_COMPATIBILITY = "uncertain_compatibility"
    SERIAL_TRANSPORT_ERROR = "serial_transport_error"
    NONE = "none"
