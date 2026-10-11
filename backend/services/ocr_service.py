"""
OCR / Document Parsing Service — Dynamic Form Extraction & Coordinate Mapping

Extracts actual field labels and blank space coordinates from uploaded PDF forms and images,
generating targeted field schemas with localized questions and precise (x, y, page) coordinates.
"""

import os
import uuid
import re
from pathlib import Path
from typing import Optional
from io import BytesIO
import pypdf

from config import get_settings
from services.voice_service import build_question_in_language
from services import cheque_service, bank_form_service

settings = get_settings()

# ─── Comprehensive Field Taxonomy & Patterns ──────────────────────────────────
# (Canonical Label, Regex Pattern, Field Type, Default question prompt)
KNOWN_FIELD_PATTERNS = [
    # Farmer & Agriculture
    ("Farmer Name", r"farmer\s*name|name\s*of\s*farmer|krishak\s*naam", "name"),
    ("Land Holding (Acres)", r"land\s*area|land\s*holding|acres|khasra|khata|holding\s*size", "number"),
    ("Survey / Khasra Number", r"khasra\s*no|survey\s*no|dag\s*no", "text"),
    ("Crop Type", r"crop\s*type|main\s*crop|cultivated\s*crop", "text"),

    # Personal Identity
    ("Full Name", r"(?:1\.\s*|2\.\s*|3\.\s*|4\.\s*|5\.\s*)?full\s*name|applicant\s*name|name\s*of\s*applicant|name\s*in\s*full|^name\s*:", "name"),
    ("Father's Name", r"father'?s?\s*name|father\s*name", "name"),
    ("Mother's Name", r"mother'?s?\s*name|mother\s*name", "name"),
    ("Spouse's Name", r"spouse'?s?\s*name|husband'?s?\s*name|wife'?s?\s*name", "name"),
    ("Father / Mother / Spouse Name", r"father.*spouse.*name|father.*mother.*spouse|parent.*spouse", "name"),
    ("Date of Birth", r"date\s*of\s*birth|d\.?o\.?b\.?|birth\s*date", "date"),
    ("Age", r"\bage\b|current\s*age|years\s*old", "number"),
    ("Gender", r"\bgender\b|\bsex\b", "text"),
    ("Marital Status", r"marital\s*status|married|single", "text"),

    # Government & Tax IDs
    ("Aadhaar Number", r"aadhaar|adhar|uidai|unique\s*id", "number"),
    ("PAN Number", r"pan\s*card|pan\s*number|pan\s*no|tax\s*id", "text"),
    ("Voter ID / EPIC", r"voter\s*id|epic\s*no|election\s*card", "text"),
    ("Ration Card Number", r"ration\s*card|ration\s*no|bpl\s*card\s*no", "text"),
    ("Disability Certificate Number", r"disability\s*no|udid\s*no|udid", "text"),

    # Contact & Address
    ("Mobile Number", r"mobile\s*no|mobile\s*number|phone\s*number|cell\s*no|contact\s*no", "phone"),
    ("Alternate Mobile Number", r"alternate\s*number|alternate\s*mobile|alternate\s*phone", "phone"),
    ("Email Address", r"email\s*address|e-?mail", "text"),
    ("Village Name", r"village\s*name|\bvillage\b|gram\s*panchayat", "text"),
    ("Block / Tehsil", r"block|tehsil|taluk|mandal", "text"),
    ("City / Town", r"city\s*/?\s*town|\bcity\b|\btown\b", "text"),
    ("District", r"\bdistrict\b|zilla", "text"),
    ("State", r"\bstate\b|state\s*/\s*ut", "text"),
    ("PIN / Postal Code", r"pin\s*code|postal\s*code|pincode|zip\s*code", "number"),
    ("Residential Address", r"residential\s*address|permanent\s*address|home\s*address|communication\s*address|complete\s*address", "address"),
    ("House / Flat / Building", r"house\s*/?\s*flat|flat\s*no|building\s*no|door\s*no", "address"),
    ("Street / Area / Locality", r"street\s*/?\s*area|\blocality\b|street\s*name", "address"),

    # Socio-Economic
    ("Occupation", r"occupation|profession|employment|work", "text"),
    ("Annual Family Income", r"annual\s*income|family\s*income|monthly\s*income|income\s*per\s*year", "number"),
    ("Caste / Social Category", r"caste|category|sc/st|obc|general\s*category", "text"),

    # Banking
    ("Bank Account Number", r"bank\s*account\s*number|account\s*no|savings\s*a/c|a/c\s*no", "number"),
    ("IFSC Code", r"ifsc\s*code|\bifsc\b", "text"),
    ("Bank Name & Branch", r"bank\s*name|branch\s*name|bank\s*&\s*branch", "text"),
    ("Nominee Name", r"nominee\s*name|name\s*of\s*nominee|nominee", "name"),
    ("Nominee Relationship", r"nominee\s*relationship|relation\s*with\s*nominee", "text"),
]

# Standard fallback bank fields only used if an uploaded image is completely blank / unreadable
DEFAULT_BANK_FIELDS = [
    {"label": "Full Name", "field_type": "name", "x": 180, "y": 720, "page": 1},
    {"label": "Date of Birth", "field_type": "date", "x": 180, "y": 670, "page": 1},
    {"label": "Father's Name", "field_type": "name", "x": 180, "y": 620, "page": 1},
    {"label": "Mobile Number", "field_type": "phone", "x": 180, "y": 570, "page": 1},
    {"label": "Aadhaar Number", "field_type": "number", "x": 180, "y": 520, "page": 1},
    {"label": "Residential Address", "field_type": "address", "x": 180, "y": 470, "page": 1},
    {"label": "PIN / Postal Code", "field_type": "number", "x": 180, "y": 420, "page": 1},
    {"label": "Nominee Name", "field_type": "name", "x": 180, "y": 370, "page": 1},
]


def extract_fields_with_coordinates_from_pdf(file_path: str) -> list[dict]:
    """
    Parse text from an uploaded PDF and extract exact fields and (x, y, page) coordinates
    where the input answer should be stamped.
    """
    detected_fields = []
    seen_labels = set()

    try:
        reader = pypdf.PdfReader(file_path)
        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            page_height = float(page.mediabox.height) if page.mediabox else 842.0

            # Collect raw text fragments with positioning
            text_blocks = []

            def visitor(text, cm, tm, font_dict, font_size):
                clean = text.strip()
                if clean:
                    text_blocks.append({
                        "text": clean,
                        "x": float(tm[4]),
                        "y": float(tm[5]),
                        "font_size": float(font_size) if font_size else 11.0,
                    })

            try:
                page.extract_text(visitor_text=visitor)
            except Exception:
                # Fallback to plain line extraction if visitor fails
                plain_text = page.extract_text() or ""
                for line_idx, line in enumerate(plain_text.splitlines()):
                    if line.strip():
                        text_blocks.append({
                            "text": line.strip(),
                            "x": 60.0,
                            "y": max(60.0, page_height - 100 - (line_idx * 35)),
                            "font_size": 11.0,
                        })

            # Sort blocks top-to-bottom, left-to-right
            # (In PDF, higher y is near the top)
            text_blocks.sort(key=lambda b: (-b["y"], b["x"]))

            # Match form field patterns
            for block in text_blocks:
                line_text = block["text"]
                if len(line_text) < 2:
                    continue

                for label, pattern, f_type in KNOWN_FIELD_PATTERNS:
                    if label in seen_labels:
                        continue

                    match = re.search(pattern, line_text, re.IGNORECASE)
                    if match:
                        # Estimate width of the label to place answer directly after it
                        approx_label_len = len(line_text)
                        # ~6 points per char for standard 11pt font
                        est_label_width = min(220, max(60, approx_label_len * 6.5))

                        target_x = block["x"] + est_label_width + 12
                        target_y = block["y"]  # Align baseline with label

                        detected_fields.append({
                            "label": label,
                            "field_type": f_type,
                            "page": page_num,
                            "x": round(target_x, 1),
                            "y": round(target_y, 1),
                            "width": 260,
                            "height": 24,
                        })
                        seen_labels.add(label)
                        break

    except Exception as e:
        print(f"[OCR] Error in PDF coordinate extraction: {e}")

    return detected_fields


def extract_fields_from_image(file_path: str) -> list[dict]:
    """
    Attempt OCR on uploaded image files using pytesseract if available.
    """
    detected_fields = []
    seen_labels = set()

    try:
        import pytesseract
        from PIL import Image
        img = Image.open(file_path)
        img_w, img_h = img.size

        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        n_boxes = len(ocr_data['text'])

        # Combine words into lines
        lines_dict = {}
        for i in range(n_boxes):
            txt = ocr_data['text'][i].strip()
            if not txt:
                continue
            line_id = (ocr_data['page_num'][i], ocr_data['block_num'][i], ocr_data['par_num'][i], ocr_data['line_num'][i])
            if line_id not in lines_dict:
                lines_dict[line_id] = {
                    "text": txt,
                    "x": ocr_data['left'][i],
                    "y": ocr_data['top'][i],
                    "w": ocr_data['width'][i],
                    "h": ocr_data['height'][i],
                }
            else:
                lines_dict[line_id]["text"] += " " + txt
                lines_dict[line_id]["w"] += ocr_data['width'][i]

        for _, line_info in lines_dict.items():
            line_str = line_info["text"]
            for label, pattern, f_type in KNOWN_FIELD_PATTERNS:
                if label in seen_labels:
                    continue
                if re.search(pattern, line_str, re.IGNORECASE):
                    # Invert Y for PDF coordinates: PDF origin is bottom-left
                    # Normalizing to standard A4 (595 x 842 pt)
                    scale_x = 595.0 / max(img_w, 1)
                    scale_y = 842.0 / max(img_h, 1)

                    pdf_x = (line_info["x"] + line_info["w"]) * scale_x + 10
                    pdf_y = 842.0 - ((line_info["y"] + line_info["h"]) * scale_y)

                    detected_fields.append({
                        "label": label,
                        "field_type": f_type,
                        "page": 1,
                        "x": round(pdf_x, 1),
                        "y": round(pdf_y, 1),
                        "width": 250,
                        "height": 24,
                    })
                    seen_labels.add(label)
                    break
    except Exception as e:
        print(f"[OCR] Image OCR pass notice: {e}")

    return detected_fields


def process_form_image(file_path: str, filename: str) -> dict:
    """
    Process uploaded form document (PDF or image).
    Extracts ONLY actual fields present in the document along with exact entry coordinates.
    """
    fields_raw = []

    is_pdf = filename.lower().endswith(".pdf") or file_path.lower().endswith(".pdf")

    if is_pdf:
        fields_raw = extract_fields_with_coordinates_from_pdf(file_path)
    else:
        fields_raw = extract_fields_from_image(file_path)

    # Cheques and bank slips are usually scanned (no text layer): detect their blank spaces via OCR
    scanned = not is_pdf or not fields_raw
    cheque_fields = []
    if scanned or cheque_service.looks_like_cheque(file_path, filename, is_pdf):
        cheque_fields = cheque_service.detect_cheque_fields(file_path, is_pdf)
        if cheque_fields:
            fields_raw = cheque_fields
    if not cheque_fields and (scanned or bank_form_service.looks_like_bank_form(file_path, filename, is_pdf)):
        form_fields = bank_form_service.detect_form_fields(file_path, is_pdf)
        if len(form_fields) >= 2:
            fields_raw = form_fields

    # Fallback to standard template only if zero fields could be parsed (e.g. blank test stub)
    if not fields_raw:
        fields_raw = DEFAULT_BANK_FIELDS

    # Enrich fields with unique IDs, position geometry, and localized questions
    enriched = []
    for idx, f in enumerate(fields_raw):
        label = f["label"]
        f_type = f.get("field_type", "text")

        pos_x = f.get("x", 180)
        pos_y = f.get("y", 700 - (idx * 45))
        page_num = f.get("page", 1)

        position = {
            "x": pos_x,
            "y": pos_y,
            "width": f.get("width", 260),
            "height": f.get("height", 24),
            "page": page_num,
        }
        if f.get("cheque"):
            position["cheque"] = f["cheque"]

        enriched.append({
            "id": str(uuid.uuid4()),
            "label": label,
            "field_type": f_type,
            "question_text": f.get("question_text") or build_question_in_language(label, "en"),
            "order_index": idx,
            "position": position,
        })

    return {
        "template": "extracted_form",
        "fields": enriched,
    }


# ─── Built-in Demo Template Generator Helper ──────────────────────────────────
def generate_sample_form_pdf(template_type: str = "pm_kisan") -> bytes:
    """
    Generates realistic official-looking sample form PDFs for frontend demo buttons.
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Outer border
    c.setStrokeColorRGB(0.2, 0.3, 0.4)
    c.setLineWidth(1)
    c.rect(30, 30, width - 60, height - 60)

    if template_type == "pm_kisan":
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(width / 2, height - 65, "PM-KISAN SAMMAN NIDHI — ENROLMENT FORM")
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, height - 82, "Ministry of Agriculture & Farmers Welfare, Govt of India")
        c.line(40, height - 90, width - 40, height - 90)

        fields = [
            ("1. Farmer Name:", 160, height - 130),
            ("2. Father's Name:", 160, height - 175),
            ("3. Aadhaar Number:", 170, height - 220),
            ("4. Mobile Number:", 165, height - 265),
            ("5. Village Name:", 160, height - 310),
            ("6. District:", 130, height - 355),
            ("7. State:", 120, height - 400),
            ("8. Land Holding (Acres):", 195, height - 445),
            ("9. Bank Account Number:", 200, height - 490),
            ("10. IFSC Code:", 145, height - 535),
        ]
    elif template_type == "pension":
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(width / 2, height - 65, "NATIONAL OLD AGE PENSION SCHEME (NSAP) APPLICATION")
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, height - 82, "Social Welfare Department, Government of India")
        c.line(40, height - 90, width - 40, height - 90)

        fields = [
            ("1. Full Name:", 145, height - 130),
            ("2. Date of Birth:", 155, height - 175),
            ("3. Age:", 115, height - 220),
            ("4. Gender:", 125, height - 265),
            ("5. Aadhaar Number:", 170, height - 310),
            ("6. Mobile Number:", 165, height - 355),
            ("7. Residential Address:", 190, height - 400),
            ("8. Annual Family Income:", 195, height - 445),
            ("9. Bank Account Number:", 200, height - 490),
            ("10. Nominee Name:", 165, height - 535),
        ]
    else:  # Standard Zero-Balance Bank Form
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(width / 2, height - 65, "PRADHAN MANTRI JAN DHAN YOJANA (PMJDY) ACCOUNT FORM")
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, height - 82, "Application for Opening Basic Savings Bank Deposit Account")
        c.line(40, height - 90, width - 40, height - 90)

        fields = [
            ("1. Full Name:", 145, height - 130),
            ("2. Date of Birth:", 155, height - 175),
            ("3. Father's Name:", 160, height - 220),
            ("4. Mobile Number:", 165, height - 265),
            ("5. Aadhaar Number:", 170, height - 310),
            ("6. PAN Number:", 150, height - 355),
            ("7. Residential Address:", 190, height - 400),
            ("8. PIN / Postal Code:", 175, height - 445),
            ("9. Occupation:", 150, height - 490),
            ("10. Nominee Name:", 165, height - 535),
        ]

    c.setFont("Helvetica-Bold", 11)
    for label, line_x, y in fields:
        c.drawString(55, y, label)
        # Draw underline for blank space
        c.setStrokeColorRGB(0.7, 0.75, 0.8)
        c.line(line_x, y - 2, width - 60, y - 2)

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, 45, "FinAccess AI Form Template — Voice Assisted Document Enrolment")

    c.save()
    buf.seek(0)
    return buf.getvalue()
