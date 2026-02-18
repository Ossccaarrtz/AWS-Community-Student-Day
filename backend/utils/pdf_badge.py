import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def _center_text(c: canvas.Canvas, y: float, text: str, font_name: str, font_size: int, page_width: float):
    c.setFont(font_name, font_size)
    text = text or ""
    text_width = c.stringWidth(text, font_name, font_size)
    x = (page_width - text_width) / 2.0
    c.drawString(x, y, text)


def _fit_center_text(c: canvas.Canvas, y: float, text: str, font_name: str, start_size: int, min_size: int, page_width: float, max_width: float):
    """
    Centra texto y baja el font-size si no cabe.
    max_width es el ancho máximo permitido (en puntos).
    """
    text = text or ""
    size = start_size
    while size > min_size and c.stringWidth(text, font_name, size) > max_width:
        size -= 1
    _center_text(c, y, text, font_name, size, page_width)


def build_badge_pdf(ticket_id: str, name: str, profession: str, checked_in_at: str) -> str:
    """
    PDF tipo etiqueta 4x2 pulgadas, retorna base64.
    """
    width, height = 4 * inch, 2 * inch
    margin = 0.18 * inch

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # --- Marco (borde suave) ---
    c.setLineWidth(1)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    # --- Header ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 0.08 * inch, height - margin - 0.22 * inch, "AWS Community Student Day")

    # Línea divisoria
    c.setLineWidth(0.5)
    c.line(margin, height - margin - 0.30 * inch, width - margin, height - margin - 0.30 * inch)

    # --- Nombre (grande, centrado, ajustable) ---
    safe_name = (name or "UNKNOWN").strip()
    _fit_center_text(
        c,
        y=height - margin - 0.85 * inch,
        text=safe_name,
        font_name="Helvetica-Bold",
        start_size=18,
        min_size=12,
        page_width=width,
        max_width=width - 2 * margin - 0.2 * inch,
    )

    # --- Profesión (centrado) ---
    safe_prof = (profession or "N/A").strip()
    _fit_center_text(
        c,
        y=height - margin - 1.15 * inch,
        text=safe_prof,
        font_name="Helvetica",
        start_size=11,
        min_size=8,
        page_width=width,
        max_width=width - 2 * margin - 0.2 * inch,
    )

    # --- Footer (ticket y checkin) ---
    c.setFont("Helvetica", 8)
    footer_y = margin + 0.22 * inch

    # Ticket a la izquierda
    c.drawString(margin + 0.08 * inch, footer_y + 0.18 * inch, f"Ticket: {ticket_id}")

    # CheckedInAt abajo
    c.drawString(margin + 0.08 * inch, footer_y, f"CheckedInAt: {checked_in_at}")

    # Mini firma (derecha)
    c.setFont("Helvetica-Oblique", 7)
    signature = "AWSQR"
    sig_w = c.stringWidth(signature, "Helvetica-Oblique", 7)
    c.drawString(width - margin - 0.08 * inch - sig_w, footer_y, signature)

    c.showPage()
    c.save()

    return base64.b64encode(buf.getvalue()).decode("utf-8")
