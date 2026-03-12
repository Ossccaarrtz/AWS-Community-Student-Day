"""
Label renderer — renders labels to monochrome bitmaps with
text, QR codes, barcodes, and structured fields.
"""

from __future__ import annotations

import base64
import io
import math
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .config import DEFAULT_DPI, SAFETY_MARGIN_IN
from .models import LabelSpec


# ── QR / Barcode helpers (lazy imports) ───────────────────────────


def _render_qr(data: str, box_size: int = 4) -> Image.Image:
    """Render a QR code to a PIL Image."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("1")


def _render_barcode(data: str, width_px: int, height_px: int) -> Image.Image:
    """Render a Code128 barcode to a PIL Image."""
    try:
        import barcode
        from barcode.writer import ImageWriter

        writer = ImageWriter()
        writer.set_options({
            "module_width": 0.3,
            "module_height": max(height_px / 10, 8),
            "quiet_zone": 2,
            "write_text": True,
            "font_size": 8,
        })
        code = barcode.get("code128", data, writer=writer)
        buf = io.BytesIO()
        code.write(buf)
        buf.seek(0)
        img = Image.open(buf).convert("1")
        # Resize to fit target
        if img.width > width_px:
            ratio = width_px / img.width
            new_h = int(img.height * ratio)
            img = img.resize((width_px, new_h), Image.NEAREST)
        return img
    except Exception:
        # Fallback: create a placeholder
        img = Image.new("1", (width_px, height_px), 1)
        draw = ImageDraw.Draw(img)
        draw.text((4, 4), f"[BARCODE: {data}]", fill=0)
        return img


# ── Font helper ───────────────────────────────────────────────────


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font; fall back to default."""
    font_names = (
        ["arialbd.ttf", "Arial Bold.ttf"] if bold
        else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    )
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _text_fits(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> bool:
    """Check if text fits within max_width."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0]) <= max_width


def _fit_font_size(draw: ImageDraw.ImageDraw, text: str, bold: bool, start_size: int, min_size: int, max_width: int) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, int]:
    """Find the largest font size that fits the text within max_width."""
    size = start_size
    font = _get_font(size, bold)
    while size > min_size:
        if _text_fits(draw, text, font, max_width):
            return font, size
        size -= 1
        font = _get_font(size, bold)
    return font, size


def _center_x(draw: ImageDraw.ImageDraw, text: str, font, page_width: int) -> int:
    """Calculate x coordinate to center text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    return max(0, (page_width - text_w) // 2)


# ── Main renderer ─────────────────────────────────────────────────


class RenderResult:
    """Result of a label render operation."""

    def __init__(
        self,
        image: Image.Image,
        warnings: list[str] | None = None,
    ):
        self.image = image
        self.warnings = warnings or []


def render_label(label: LabelSpec, dpi: Optional[int] = None) -> RenderResult:
    """
    Render a label specification to a monochrome PIL Image.

    Returns a RenderResult with the image and any warnings
    (e.g., content overflow).
    """
    effective_dpi = dpi or label.dpi or DEFAULT_DPI
    warnings: list[str] = []

    if not dpi and not label.dpi:
        warnings.append(
            f"No se pudo confirmar el DPI exacto; se usó {DEFAULT_DPI} dpi por defecto."
        )

    # ── Dimensions in pixels ──────────────────────────────────────
    width_px = int(label.width_in * effective_dpi)
    height_px = int(label.height_in * effective_dpi)
    margin_px = int(SAFETY_MARGIN_IN * effective_dpi)
    usable_w = width_px - 2 * margin_px
    usable_h = height_px - 2 * margin_px

    # ── Create canvas ─────────────────────────────────────────────
    img = Image.new("1", (width_px, height_px), 1)  # white
    draw = ImageDraw.Draw(img)

    content = label.content
    y_cursor = margin_px

    # ── 1. Header band ────────────────────────────────────────────
    header_h = int(0.28 * effective_dpi)
    draw.rectangle(
        [margin_px, y_cursor, width_px - margin_px, y_cursor + header_h],
        fill=0,  # black
    )
    header_font = _get_font(max(10, int(effective_dpi * 0.045)), bold=True)
    header_text = "RIBETEC LABEL"
    hx = margin_px + int(0.05 * effective_dpi)
    hy = y_cursor + (header_h - 12) // 2
    draw.text((hx, hy), header_text, fill=1, font=header_font)  # white on black
    y_cursor += header_h + int(0.08 * effective_dpi)

    # ── 2. Title (large, centered) ────────────────────────────────
    if content.title:
        title_font, _ = _fit_font_size(
            draw, content.title, bold=True,
            start_size=int(effective_dpi * 0.11),
            min_size=int(effective_dpi * 0.06),
            max_width=usable_w,
        )
        tx = _center_x(draw, content.title, title_font, width_px)
        draw.text((tx, y_cursor), content.title, fill=0, font=title_font)
        bbox = draw.textbbox((tx, y_cursor), content.title, font=title_font)
        y_cursor = bbox[3] + int(0.04 * effective_dpi)

    # ── 3. Subtitle ───────────────────────────────────────────────
    if content.subtitle:
        sub_font, _ = _fit_font_size(
            draw, content.subtitle, bold=False,
            start_size=int(effective_dpi * 0.07),
            min_size=int(effective_dpi * 0.04),
            max_width=usable_w,
        )
        sx = _center_x(draw, content.subtitle, sub_font, width_px)
        draw.text((sx, y_cursor), content.subtitle, fill=0, font=sub_font)
        bbox = draw.textbbox((sx, y_cursor), content.subtitle, font=sub_font)
        y_cursor = bbox[3] + int(0.04 * effective_dpi)

    # ── 4. Fields ─────────────────────────────────────────────────
    if content.fields:
        field_font = _get_font(int(effective_dpi * 0.045))
        for field in content.fields:
            text = f"{field.label}: {field.value}"
            fx = margin_px + int(0.05 * effective_dpi)
            if y_cursor + int(effective_dpi * 0.06) > height_px - margin_px:
                warnings.append(f"Campo '{field.label}' recortado por falta de espacio.")
                break
            draw.text((fx, y_cursor), text, fill=0, font=field_font)
            y_cursor += int(effective_dpi * 0.06)

    # ── 5. Separator line ─────────────────────────────────────────
    sep_y = height_px - margin_px - int(0.45 * effective_dpi)
    if sep_y > y_cursor:
        draw.line(
            [margin_px + 4, sep_y, width_px - margin_px - 4, sep_y],
            fill=0, width=1,
        )

    # ── 6. QR code (bottom-right) ─────────────────────────────────
    if content.qr:
        try:
            qr_target_size = int(min(usable_h * 0.35, usable_w * 0.25))
            box_size = max(2, qr_target_size // 25)
            qr_img = _render_qr(content.qr, box_size=box_size)
            # Position bottom-right
            qr_x = width_px - margin_px - qr_img.width - 4
            qr_y = height_px - margin_px - qr_img.height - 4
            if qr_y < y_cursor:
                warnings.append("QR code recortado parcialmente.")
            img.paste(qr_img, (qr_x, max(qr_y, y_cursor)))
        except Exception as e:
            warnings.append(f"Error al renderizar QR: {e}")

    # ── 7. Barcode (bottom-left) ──────────────────────────────────
    if content.barcode:
        try:
            bc_w = int(usable_w * 0.55)
            bc_h = int(effective_dpi * 0.3)
            bc_img = _render_barcode(content.barcode, bc_w, bc_h)
            bc_x = margin_px + 4
            bc_y = height_px - margin_px - bc_img.height - 4
            if bc_y < y_cursor:
                warnings.append("Barcode recortado parcialmente.")
            img.paste(bc_img, (bc_x, max(bc_y, y_cursor)))
        except Exception as e:
            warnings.append(f"Error al renderizar barcode: {e}")

    # ── Overflow check ────────────────────────────────────────────
    if y_cursor > height_px - margin_px:
        warnings.append(
            "El contenido excede el área imprimible. Considere reducir campos."
        )

    return RenderResult(image=img, warnings=warnings)


# ── Output helpers ────────────────────────────────────────────────


def generate_preview_base64(image: Image.Image) -> str:
    """Convert a PIL Image to a base64-encoded PNG string."""
    buf = io.BytesIO()
    # Convert to grayscale for better preview quality
    preview = image.convert("L")
    preview.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_raster_payload(image: Image.Image) -> bytes:
    """
    Convert a PIL Image to a 1-bit monochrome raw byte payload.

    Layout: row-major, MSB first, each row padded to full bytes.
    """
    mono = image.convert("1")
    width, height = mono.size
    row_bytes = math.ceil(width / 8)
    payload = bytearray()

    pixels = mono.load()
    for y in range(height):
        row = bytearray(row_bytes)
        for x in range(width):
            # In mode "1": 0 = black, 255 = white
            if pixels[x, y] == 0:  # black pixel
                byte_idx = x // 8
                bit_idx = 7 - (x % 8)
                row[byte_idx] |= (1 << bit_idx)
        payload.extend(row)

    return bytes(payload)
