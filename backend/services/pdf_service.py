"""
PDF Generation & Document Overlay Service

Overlays confirmed field values directly onto the original uploaded form document
at the exact detected coordinates (x, y, page).
"""

import os
import uuid
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional
import pypdf

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def generate_filled_form_pdf(
    form_id: str,
    form_title: str,
    fields: list[dict],
    original_file_path: Optional[str] = None,
    output_dir: str = "./uploads",
) -> str:
    """
    Generate a filled form PDF.
    If original_file_path is provided and exists, overlays answers onto the original document.
    Otherwise generates a clean styled form document.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"form_{form_id}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(output_dir, filename)

    # 0. Cheques: write each value into its detected blank line / box
    if original_file_path and os.path.exists(original_file_path):
        from services import cheque_service
        if cheque_service.is_cheque_fields(fields):
            try:
                if cheque_service.render_filled_cheque(original_file_path, filepath, fields):
                    return filepath
            except Exception as e:
                print(f"[PDF_SERVICE] Notice: cheque overlay fallback ({e})")

    # 1. Try true PDF overlay if base file is a valid PDF
    if original_file_path and os.path.exists(original_file_path) and original_file_path.lower().endswith(".pdf"):
        try:
            success = _overlay_on_original_pdf(original_file_path, filepath, fields)
            if success:
                return filepath
        except Exception as e:
            print(f"[PDF_SERVICE] Notice: PDF merge overlay fallback ({e})")

    # 2. Try Image overlay if base file is an image (PNG, JPG)
    if original_file_path and os.path.exists(original_file_path) and PIL_AVAILABLE and any(original_file_path.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
        try:
            success = _overlay_on_original_image(original_file_path, filepath, fields)
            if success:
                return filepath
        except Exception as e:
            print(f"[PDF_SERVICE] Notice: Image overlay fallback ({e})")

    # 3. Standard fallback generator
    if REPORTLAB_AVAILABLE:
        _generate_with_reportlab(filepath, form_title, fields)
    else:
        _generate_simple_text(filepath, form_title, fields)

    return filepath


def _overlay_on_original_pdf(original_pdf_path: str, output_pdf_path: str, fields: list[dict]) -> bool:
    """
    Reads the original PDF and stamps user answers in dark navy ink directly at each field's
    exact (x, y) coordinates using ReportLab and PyPDF merge_page.
    """
    base_reader = pypdf.PdfReader(original_pdf_path)
    if len(base_reader.pages) == 0:
        return False

    writer = pypdf.PdfWriter()

    # Group field values by page number (1-indexed)
    fields_by_page = {}
    for f in fields:
        pos = f.get("position") or {}
        p_num = pos.get("page", 1)
        fields_by_page.setdefault(p_num, []).append(f)

    for page_idx, base_page in enumerate(base_reader.pages):
        page_num = page_idx + 1
        page_width = float(base_page.mediabox.width)
        page_height = float(base_page.mediabox.height)

        page_fields = fields_by_page.get(page_num, [])

        if page_fields and REPORTLAB_AVAILABLE:
            # Build overlay canvas for this page
            overlay_buf = BytesIO()
            c = rl_canvas.Canvas(overlay_buf, pagesize=(page_width, page_height))

            # Professional dark blue filled-form ink
            c.setFillColorRGB(0.04, 0.16, 0.58)

            for f in page_fields:
                val = str(f.get("confirmed_value") or "").strip()
                if not val:
                    continue

                pos = f.get("position") or {}
                x = float(pos.get("x", 180))
                y = float(pos.get("y", 700))

                # Font styling for entry values
                c.setFont("Helvetica-Bold", 11)
                c.drawString(x, y, val)

            # Verification watermark stamp in top corner
            c.setFillColorRGB(0.12, 0.65, 0.35)
            c.setFont("Helvetica-Bold", 8)
            c.drawRightString(page_width - 30, page_height - 20, "Voice Confirmed ✓ FinAccess AI")

            c.save()
            overlay_buf.seek(0)

            # Merge overlay on original page
            overlay_reader = pypdf.PdfReader(overlay_buf)
            base_page.merge_page(overlay_reader.pages[0])

        writer.add_page(base_page)

    with open(output_pdf_path, "wb") as f_out:
        writer.write(f_out)

    return True


def _overlay_on_original_image(image_path: str, output_pdf_path: str, fields: list[dict]) -> bool:
    """
    Renders text directly onto an uploaded form image and converts to PDF.
    """
    img = Image.open(image_path).convert("RGB")
    img_w, img_h = img.size
    draw = ImageDraw.Draw(img)

    for f in fields:
        val = str(f.get("confirmed_value") or "").strip()
        if not val:
            continue

        pos = f.get("position") or {}
        # Convert PDF points (595 x 842) back to image pixels
        scale_x = img_w / 595.0
        scale_y = img_h / 842.0

        pdf_x = float(pos.get("x", 180))
        pdf_y = float(pos.get("y", 700))

        img_x = pdf_x * scale_x
        img_y = (842.0 - pdf_y) * scale_y - 10

        # Draw text in navy blue
        draw.text((img_x, img_y), val, fill=(10, 40, 150))

    img.save(output_pdf_path, "PDF", resolution=100.0)
    return True


def _generate_with_reportlab(filepath: str, title: str, fields: list[dict]):
    """Clean fallback table layout."""
    c = rl_canvas.Canvas(filepath, pagesize=A4)
    width, height = A4  # 595 x 842 pt

    # Header bar
    c.setFillColorRGB(0.043, 0.573, 0.694)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 45, "FinAccess AI — Completed Form")
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 65, f"Form: {title}")
    c.drawString(40, height - 78, f"Generated: {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}")

    # Confidence badge
    c.setFillColorRGB(0.18, 0.80, 0.44)
    c.roundRect(width - 160, height - 65, 120, 30, 8, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width - 100, height - 46, "Voice Confirmed ✓")

    # Fields
    y = height - 110
    row = 0
    for field in fields:
        if y < 80:
            c.showPage()
            y = height - 60

        if row % 2 == 0:
            c.setFillColorRGB(0.97, 0.98, 1.0)
            c.rect(30, y - 10, width - 60, 36, fill=1, stroke=0)

        # Label
        c.setFillColorRGB(0.3, 0.35, 0.45)
        c.setFont("Helvetica", 9)
        c.drawString(40, y + 16, field.get("label", ""))

        # Value
        value = field.get("confirmed_value") or "—"
        c.setFillColorRGB(0.05, 0.05, 0.15)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y + 2, value)

        # Checkmark
        c.setFillColorRGB(0.18, 0.80, 0.44)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(width - 50, y + 6, "✓")

        c.setStrokeColorRGB(0.88, 0.90, 0.95)
        c.setLineWidth(0.5)
        c.line(30, y - 10, width - 30, y - 10)

        y -= 46
        row += 1

    # Footer
    c.setFillColorRGB(0.6, 0.65, 0.75)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 40, "Generated by FinAccess AI | Voice-Confirmed | All fields verified by user")

    c.save()


def _generate_simple_text(filepath: str, title: str, fields: list[dict]):
    """Fallback text writer."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"FinAccess AI — Completed Form\n")
        f.write(f"Form: {title}\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        for field in fields:
            f.write(f"{field.get('label', 'Field')}: {field.get('confirmed_value', '—')}\n")
        f.write("\n[Voice Confirmed — FinAccess AI]\n")
