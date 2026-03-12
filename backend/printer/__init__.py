"""
MCP Label Printer Agent for Ribetec printers.

Discovers printers (USB, Bluetooth, TCP/IP, system queues),
renders labels (text, QR, barcode), and executes print jobs
with safe fallback strategies.
"""

from .router import router as printer_router  # noqa: F401
from .router_rt420me import router as rt420me_router  # noqa: F401

__all__ = ["printer_router", "rt420me_router"]
