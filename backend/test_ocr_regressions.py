"""Regression coverage for document field extraction and OCR handoff."""

import os

from services.ocr_service import extract_fields_from_image, process_form_image


ROOT = os.path.dirname(os.path.dirname(__file__))


def _labels(filename: str) -> list[str]:
    path = os.path.join(ROOT, filename)
    result = process_form_image(path, filename)
    return [field["label"] for field in result["fields"]]


def test_text_layer_kisan_form_keeps_every_document_field():
    assert _labels("test_kisan_form.pdf") == [
        "Farmer Name",
        "Aadhaar Number",
        "Mobile Number",
        "State / District",
        "Land Holding (Acres)",
        "Bank Account Number",
        "IFSC Code",
    ]


def test_text_layer_acme_form_keeps_common_application_fields():
    labels = _labels("temp_acme_check.pdf")

    for label in (
        "Full Name",
        "Date of Birth",
        "Mobile Number",
        "Email Address",
        "Residential Address",
        "Loan Type",
        "Loan Amount Requested",
        "Loan Purpose",
        "Employer Name",
        "Job Title",
        "Monthly Income",
    ):
        assert label in labels


def test_scanned_form_ocr_uses_the_discovered_tesseract_command():
    from PIL import Image, ImageDraw, ImageFont

    font_path = "C:/Windows/Fonts/arial.ttf"
    font = ImageFont.truetype(font_path, 64) if os.path.exists(font_path) else ImageFont.load_default()
    image = Image.new("RGB", (1800, 320), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 40), "Full Name:", fill="black", font=font)
    draw.text((60, 180), "Mobile Number:", fill="black", font=font)
    path = os.path.join(os.path.dirname(__file__), "_ocr_regression_form.png")
    try:
        image.save(path)
        labels = [field["label"] for field in extract_fields_from_image(path)]

        assert "Full Name" in labels
        assert "Mobile Number" in labels
    finally:
        if os.path.exists(path):
            os.unlink(path)

