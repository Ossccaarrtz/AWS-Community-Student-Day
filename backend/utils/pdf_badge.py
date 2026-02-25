import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor


# ── Palette (black & white only) ──────────────────────────────────
_BLACK = HexColor("#000000")
_DARK = HexColor("#1A1A1A")
_MID_GRAY = HexColor("#555555")
_LIGHT_GRAY = HexColor("#CCCCCC")
_WHITE = HexColor("#FFFFFF")


def _center_text(c: canvas.Canvas, y: float, text: str, font_name: str, font_size: int, page_width: float):
    c.setFont(font_name, font_size)
    text = text or ""
    text_width = c.stringWidth(text, font_name, font_size)
    x = (page_width - text_width) / 2.0
    c.drawString(x, y, text)


def _fit_center_text(c: canvas.Canvas, y: float, text: str, font_name: str,
                     start_size: int, min_size: int, page_width: float, max_width: float):
    """Centra texto y baja el font-size si no cabe."""
    text = text or ""
    size = start_size
    while size > min_size and c.stringWidth(text, font_name, size) > max_width:
        size -= 1
    _center_text(c, y, text, font_name, size, page_width)


def build_badge_pdf(ticket_id: str, name: str, profession: str, checked_in_at: str) -> str:
    """PDF tipo etiqueta 4 × 2 pulgadas, retorna base64."""
    width, height = 4 * inch, 2 * inch
    margin = 0.18 * inch
    pad = 0.10 * inch                   # padding interno extra
    usable_w = width - 2 * margin
    usable_text_w = usable_w - 2 * pad  # ancho máximo de texto

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # ── 1. Borde redondeado fino ──────────────────────────────────
    c.setStrokeColor(_LIGHT_GRAY)
    c.setLineWidth(0.75)
    c.roundRect(margin, margin, usable_w, height - 2 * margin, radius=6)

    # ── 2. Header: franja negra con texto blanco ──────────────────
    header_h = 0.32 * inch
    header_y = height - margin - header_h
    c.setFillColor(_BLACK)
    c.roundRect(margin, header_y, usable_w, header_h, radius=6, stroke=0, fill=1)
    # Tapar las esquinas inferiores redondeadas de la franja
    c.rect(margin, header_y, usable_w, header_h / 2, stroke=0, fill=1)

    c.setFillColor(_WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin + pad, header_y + 0.10 * inch, "AWS Community Student Day")

    # ── 3. Nombre (grande, centrado, ajustable) ───────────────────
    safe_name = (name or "UNKNOWN").strip()
    c.setFillColor(_DARK)
    _fit_center_text(
        c,
        y=height - margin - 0.82 * inch,
        text=safe_name,
        font_name="Helvetica-Bold",
        start_size=18,
        min_size=12,
        page_width=width,
        max_width=usable_text_w,
    )

    # ── 4. Profesión (centrada, gris medio) ───────────────────────
    safe_prof = (profession or "N/A").strip()
    c.setFillColor(_MID_GRAY)
    _fit_center_text(
        c,
        y=height - margin - 1.12 * inch,
        text=safe_prof,
        font_name="Helvetica",
        start_size=11,
        min_size=8,
        page_width=width,
        max_width=usable_text_w,
    )

    # ── 5. Línea separadora fina antes del footer ─────────────────
    sep_y = margin + 0.48 * inch
    c.setStrokeColor(_LIGHT_GRAY)
    c.setLineWidth(0.5)
    c.line(margin + pad, sep_y, width - margin - pad, sep_y)

    # ── 6. Footer ─────────────────────────────────────────────────
    c.setFillColor(_MID_GRAY)
    c.setFont("Helvetica", 7)
    footer_y = margin + 0.24 * inch

    c.drawString(margin + pad, footer_y + 0.14 * inch, f"Ticket: {ticket_id}")
    c.drawString(margin + pad, footer_y, f"CheckedInAt: {checked_in_at}")

    # Firma AWSQR (derecha, negrita)
    c.setFillColor(_BLACK)
    c.setFont("Helvetica-Bold", 7)
    signature = "AWSQR"
    sig_w = c.stringWidth(signature, "Helvetica-Bold", 7)
    c.drawString(width - margin - pad - sig_w, footer_y, signature)

    c.showPage()
    c.save()

    return base64.b64encode(buf.getvalue()).decode("utf-8")
