"""
Comprehensive automated tests for FinAccess AI OCR, document field extraction,
PDF text visitor/coordinates, bank-form detection, cheque detection, span extraction,
full form-filling workflow, and missing OCR simulations.
"""

import io
import os
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw, ImageFont
import pypdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from services import tesseract_finder
from services import ocr_service
from services import bank_form_service
from services import cheque_service
from services import pdf_service


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────────────────────────────────────

def create_sample_text_pdf(path: str):
    """Generate a clean text-based PDF containing form labels with underlines."""
    c = canvas.Canvas(path, pagesize=letter)
    c.drawString(100, 700, "Full Name: ____________________________")
    c.drawString(100, 650, "Mobile Number: ________________________")
    c.drawString(100, 600, "Date of Birth: ________________________")
    c.drawString(100, 550, "Aadhaar Number: _______________________")
    c.save()


def create_sample_image(path: str, text_lines: list[str]):
    """Generate an image with crisp black text on white background."""
    img = Image.new("RGB", (1000, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y = 50
    for line in text_lines:
        draw.text((60, y), line, fill=(0, 0, 0))
        y += 60
    img.save(path)


def create_sample_cheque_pdf(path: str):
    """Generate a PDF containing cheque anchor terms (pay, rupees, bearer, ac no)."""
    c = canvas.Canvas(path, pagesize=(600, 260))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(420, 230, "DATE: D D M M Y Y Y Y")
    c.drawString(50, 190, "PAY  ________________________________________  OR BEARER")
    c.drawString(50, 150, "RUPEES  _______________________________________________")
    c.drawString(400, 140, "Rs. [                  ]")
    c.drawString(80, 80, "A/C NO.  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |")
    c.drawString(400, 40, "Authorised Signatory")
    c.save()


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Tesseract Discovery Service
# ─────────────────────────────────────────────────────────────────────────────

def test_tesseract_finder_active():
    """Verify that tesseract_finder identifies an available binary and configures pytesseract."""
    assert tesseract_finder.is_tesseract_available() is True
    cmd = tesseract_finder.find_tesseract_cmd()
    assert cmd is not None
    assert os.path.exists(cmd)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Text-based PDF extraction and coordinate calculation
# ─────────────────────────────────────────────────────────────────────────────

def test_text_pdf_extraction_and_coordinates(tmp_path):
    """Text-based PDF should extract fields via pypdf text visitor with positive coordinates."""
    pdf_path = str(tmp_path / "test_form.pdf")
    create_sample_text_pdf(pdf_path)

    result = ocr_service.process_form_image(pdf_path, "test_form.pdf")
    assert result["is_fallback"] is False
    assert result["extraction_source"] == "pdf_text"
    assert len(result["fields"]) >= 4

    labels = [f["label"].lower() for f in result["fields"]]
    assert any("name" in l for l in labels)
    assert any("mobile" in l or "number" in l for l in labels)

    for field in result["fields"]:
        pos = field.get("position")
        assert pos is not None
        assert pos["x"] > 0
        assert pos["y"] > 0
        assert pos["page"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Cheque detection and layout parsing
# ─────────────────────────────────────────────────────────────────────────────

def test_cheque_detection_and_fields(tmp_path):
    """Cheque documents should be detected as cheque layouts with date, payee, and amount."""
    cheque_path = str(tmp_path / "cheque.pdf")
    create_sample_cheque_pdf(cheque_path)

    result = ocr_service.process_form_image(cheque_path, "cheque.pdf")
    assert result["is_fallback"] is False
    assert result["extraction_source"] == "cheque"
    labels = [f["label"] for f in result["fields"]]
    assert "Payee Name" in labels or "Cheque Amount" in labels


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Image OCR extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_image_ocr_extraction(tmp_path):
    """Image files (PNG/JPG) should undergo OCR using Tesseract and extract labeled fields."""
    img_path = str(tmp_path / "form_card.png")
    create_sample_image(img_path, [
        "Applicant Name: Rajesh Kumar",
        "Date of Birth: 15/08/1985",
        "Mobile Number: 9876543210",
        "Father Name: Ramesh Kumar",
    ])

    result = ocr_service.process_form_image(img_path, "form_card.png")
    assert result["is_fallback"] is False
    assert result["extraction_source"] == "image_ocr"
    assert len(result["fields"]) >= 3

    labels = [f["label"].lower() for f in result["fields"]]
    assert any("name" in l for l in labels)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Scanned / Raster PDF extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_scanned_pdf_raster_ocr(tmp_path):
    """A PDF containing only a rasterized image of a form should trigger OCR."""
    img_path = str(tmp_path / "temp_page.png")
    create_sample_image(img_path, [
        "PENSION APPLICATION FORM",
        "Beneficiary Name: Sunita Devi",
        "Age: 62",
        "Village: Rampur",
        "Monthly Income: 5000",
    ])

    # Convert the image into a scanned PDF with no native text layer
    pdf_path = str(tmp_path / "scanned_form.pdf")
    im = Image.open(img_path).convert("RGB")
    im.save(pdf_path, "PDF")

    result = ocr_service.process_form_image(pdf_path, "scanned_form.pdf")
    assert result["is_fallback"] is False
    # Depending on whether bank vocabulary matches or image OCR triggers:
    assert result["extraction_source"] in ("bank_form", "image_ocr")
    assert len(result["fields"]) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Robustness of PDF span splitting
# ─────────────────────────────────────────────────────────────────────────────

def test_bank_form_span_splitting():
    """Verify bank_form_service._split_span handles edge cases (empty chars, no bbox)."""
    # Empty chars
    span_empty = {"text": "Hello World", "size": 12, "chars": [], "bbox": [10, 20, 100, 35]}
    words, leaders = bank_form_service._split_span(span_empty)
    assert len(words) == 1
    assert words[0]["text"] == "Hello World"

    # Dot leaders
    span_leader = {
        "text": "Name ..........",
        "size": 10,
        "chars": [
            {"c": "N", "bbox": [10, 10, 20, 20], "origin": [10, 20]},
            {"c": "a", "bbox": [20, 10, 30, 20], "origin": [20, 20]},
            {"c": "m", "bbox": [30, 10, 40, 20], "origin": [30, 20]},
            {"c": "e", "bbox": [40, 10, 50, 20], "origin": [40, 20]},
            {"c": " ", "bbox": [50, 10, 55, 20], "origin": [50, 20]},
            {"c": ".", "bbox": [55, 10, 60, 20], "origin": [55, 20]},
            {"c": ".", "bbox": [60, 10, 65, 20], "origin": [60, 20]},
            {"c": ".", "bbox": [65, 10, 70, 20], "origin": [65, 20]},
            {"c": ".", "bbox": [70, 10, 75, 20], "origin": [70, 20]},
        ],
    }
    words, leaders = bank_form_service._split_span(span_leader)
    assert len(words) == 1
    assert words[0]["text"] == "Name"
    assert len(leaders) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: PDF Stamping Overlay
# ─────────────────────────────────────────────────────────────────────────────

def test_pdf_overlay_stamping(tmp_path):
    """Ensure answers are stamped onto the original PDF at exact coordinates."""
    original_pdf = str(tmp_path / "orig.pdf")
    create_sample_text_pdf(original_pdf)

    fields = [
        {"label": "Full Name", "confirmed_value": "Ramesh Patel", "position": {"x": 160, "y": 700, "page": 1}},
        {"label": "Mobile Number", "confirmed_value": "9988776655", "position": {"x": 180, "y": 650, "page": 1}},
    ]

    out_pdf = pdf_service.generate_filled_form_pdf(
        form_id="test1234",
        form_title="Test Application",
        fields=fields,
        original_file_path=original_pdf,
        output_dir=str(tmp_path / "output"),
    )

    assert os.path.exists(out_pdf)
    reader = pypdf.PdfReader(out_pdf)
    text = reader.pages[0].extract_text()
    assert "Ramesh Patel" in text
    assert "9988776655" in text


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: End-to-End Form Filling Workflow via API
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_form_filling_flow(client, tmp_path):
    """Test full cycle: upload -> next-field -> answer -> finalize -> download."""
    # 1. Start a session
    sess_res = client.post("/api/v1/sessions", json={"preferred_language": "en"})
    assert sess_res.status_code == 200
    session_id = sess_res.json()["id"]

    # 2. Upload text PDF form
    pdf_path = str(tmp_path / "kisan.pdf")
    create_sample_text_pdf(pdf_path)

    with open(pdf_path, "rb") as f:
        up_res = client.post(
            "/api/v1/forms/upload",
            data={"session_id": session_id, "language": "en"},
            files={"file": ("kisan.pdf", f, "application/pdf")},
        )
    assert up_res.status_code == 200
    up_data = up_res.json()
    form_id = up_data["form_id"]
    fields = up_data["fields"]
    assert len(fields) >= 4
    assert up_data["is_fallback"] is False
    assert up_data["extraction_source"] == "pdf_text"

    # 3. Iterate fields and submit answers with confirmation challenge
    val_map = {
        "name": "Ramesh Kumar",
        "phone": "9876543210",
        "date": "15th August 1985",
        "number": "123456789012",
        "text": "Sample text entry",
    }
    for field in fields:
        f_type = field.get("field_type", "text")
        valid_input = val_map.get(f_type, "Sample answer")
        ans_res = client.post(
            f"/api/v1/forms/{form_id}/fields/{field['id']}/answer",
            json={"transcribed_text": valid_input, "language": "en"},
        )
        assert ans_res.status_code == 200
        ans_data = ans_res.json()
        assert ans_data["validation_passed"] is True, f"Validation failed for {field['label']}: {ans_data.get('validation_message')}"
        nid = ans_data["nonce_id"]
        ndig = ans_data["challenge_digits"]
        conf_res = client.post(
            f"/api/v1/confirmations/{nid}/respond",
            json={"session_id": session_id, "transcribed_text": ndig},
        )
        assert conf_res.status_code == 200
        assert conf_res.json()["action_committed"] is True

    # Final voice submission challenge
    final_nonce_res = client.post("/api/v1/confirmations", json={
        "session_id": session_id,
        "bound_action": "submit_form",
        "bound_target_id": form_id,
    })
    assert final_nonce_res.status_code == 200
    fn = final_nonce_res.json()
    final_conf = client.post(
        f"/api/v1/confirmations/{fn['nonce_id']}/respond",
        json={"session_id": session_id, "transcribed_text": fn["challenge_digits"]},
    )
    assert final_conf.status_code == 200
    assert final_conf.json()["action_committed"] is True

    # 4. Finalize
    fin_res = client.post(f"/api/v1/forms/{form_id}/finalize")
    assert fin_res.status_code == 200
    fin_data = fin_res.json()
    assert fin_data["confirmed_fields"] == len(fields)

    # 5. Download filled PDF
    dl_res = client.get(f"/api/v1/forms/{form_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 1000


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Missing OCR Simulation (Honest Fallback)
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_ocr_honest_fallback(monkeypatch, tmp_path):
    """When OCR cannot run or extract anything, honest fallback is returned with is_fallback=True."""
    # Force tesseract to be unavailable
    monkeypatch.setattr(tesseract_finder, "is_tesseract_available", lambda: False)

    blank_img = str(tmp_path / "blank.png")
    im = Image.new("RGB", (100, 100), color=(255, 255, 255))
    im.save(blank_img)

    result = ocr_service.process_form_image(blank_img, "blank.png")
    assert result["is_fallback"] is True
    assert result["extraction_source"] == "fallback"
    assert len(result["fields"]) > 0
