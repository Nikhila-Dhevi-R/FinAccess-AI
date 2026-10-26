"""
FinAccess AI — Check Missed Labels on Pension and Photographic Forms
Compares extracted fields against expected domain taxonomy and reports exact missed labels.
"""

import os
import sys
import fitz
from services.tesseract_finder import configure_tesseract
from services import ocr_service, bank_form_service

configure_tesseract()

print("=" * 80)
print("FINACCESS AI — MISSED LABEL DETECTION REPORT")
print("=" * 80)

# ─────────────────────────────────────────────────────────────────────────────
# 1. PENSION FORM (NSAP / IGNOAPS APPLICATION)
# ─────────────────────────────────────────────────────────────────────────────
pension_pdf = "uploads/05b4b392c69544f8b75bf68cd93da88e.pdf"

# Standard comprehensive taxonomy for Indian Social Welfare Pension Forms:
EXPECTED_PENSION_TAXONOMY = [
    "Full Name",
    "Father's / Husband's Name",
    "Date of Birth",
    "Age",
    "Gender",
    "Aadhaar Number",
    "Mobile Number",
    "Residential Address",
    "Annual Family Income",
    "Bank Account Number",
    "Bank Branch / IFSC Code",
    "BPL Card Number / Ration Card Number",
    "Nominee Name",
    "Nominee Relationship",
    "Signature / Thumb Impression",
]

print("\n--- 1. NATIONAL OLD AGE PENSION SCHEME (NSAP) FORM ---")
print(f"Target Document: {pension_pdf}")

# (A) Digital Vector Extraction
res_pension_vector = ocr_service.process_form_image(pension_pdf, "pension.pdf")
detected_vector_labels = [f["label"] for f in res_pension_vector["fields"]]
print(f"\n[A] Native Vector Text Pipeline:")
print(f"    Source: {res_pension_vector.get('extraction_source')}")
print(f"    Total Extracted: {len(detected_vector_labels)}")
print(f"    Detected Labels: {detected_vector_labels}")

missed_vector = [lbl for lbl in EXPECTED_PENSION_TAXONOMY if lbl not in detected_vector_labels]
print(f"    Missed Labels ({len(missed_vector)}): {missed_vector}")

# (B) Scanned Raster Image Extraction (Tesseract OCR Pass)
doc = fitz.open(pension_pdf)
pix = doc[0].get_pixmap(dpi=300)
temp_scan_path = "uploads/temp_pension_scan_300dpi.png"
pix.save(temp_scan_path)

try:
    res_pension_ocr = ocr_service.extract_fields_from_image(temp_scan_path)
    detected_ocr_labels = [f["label"] for f in res_pension_ocr]
    print(f"\n[B] Scanned Raster OCR Pipeline (300 DPI Tesseract):")
    print(f"    Total Extracted: {len(detected_ocr_labels)}")
    print(f"    Detected Labels: {detected_ocr_labels}")
    
    missed_ocr = [lbl for lbl in EXPECTED_PENSION_TAXONOMY if lbl not in detected_ocr_labels]
    print(f"    Missed Labels ({len(missed_ocr)}): {missed_ocr}")
finally:
    if os.path.exists(temp_scan_path):
        os.remove(temp_scan_path)

# Detailed reason report for pension form
print("\nMissed Pension Labels Analysis:")
pension_reasons = {
    "Father's / Husband's Name": "Template design choice: NSAP demo template prioritizes applicant 'Age' and 'Gender' over parent name to match elderly eligibility criteria.",
    "Bank Branch / IFSC Code": "Template design omission: Account number is present, but separate IFSC code entry field was omitted from single-page layout.",
    "BPL Card Number / Ration Card Number": "Omitted from single-page demo form: captured under general Annual Family Income rather than explicit BPL ID.",
    "Nominee Relationship": "Single nominee name line is provided without secondary relationship dropdown field.",
    "Signature / Thumb Impression": "Voice-assist filtering: Biometric/handwritten signature lines are intentionally ignored (cannot be filled via voice API).",
}
for lbl in missed_vector:
    print(f"  • {lbl}: {pension_reasons.get(lbl, 'Not matched by known regex patterns.')}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. PHOTOGRAPHIC FORM (PNB CASH DEPOSIT SLIP)
# ─────────────────────────────────────────────────────────────────────────────
photo_path = "uploads/880fba20bf844e90aa45d446687912dc.jpg"

# Standard comprehensive taxonomy for Commercial Bank Cash Deposit Slips (PNB):
EXPECTED_DEPOSIT_TAXONOMY = [
    "Date",
    "Branch Name",
    "Account Number",
    "Account Holder Name",
    "Amount in Words",
    "Amount in Figures",
    "Mobile Number",
    "PAN Number",
    "Cash Denomination Breakdown",
    "Signature of Depositor",
]

print("\n" + "=" * 80)
print("--- 2. REAL PHONE PHOTO: PUNJAB NATIONAL BANK CASH DEPOSIT SLIP ---")
print(f"Target Document: {photo_path}")

res_photo = ocr_service.process_form_image(photo_path, "pnb_deposit_photo.jpg")
detected_photo_labels = [f["label"] for f in res_photo["fields"]]

print(f"\nPipeline Extraction Result:")
print(f"  Extraction Source: {res_photo.get('extraction_source')}")
print(f"  Is Fallback: {res_photo.get('is_fallback')}")
print(f"  Total Extracted: {len(detected_photo_labels)}")
print(f"  Detected Labels: {detected_photo_labels}")

missed_photo = [lbl for lbl in EXPECTED_DEPOSIT_TAXONOMY if lbl not in detected_photo_labels]
# Note: "Amount" in pipeline covers both words and figures
if "Amount" in detected_photo_labels:
    missed_photo = [l for l in missed_photo if l not in ("Amount in Words", "Amount in Figures")]

print(f"\nMissed Labels ({len(missed_photo)}): {missed_photo}")

print("\nMissed Photographic Form Labels Analysis:")
photo_reasons = {
    "PAN Number": "Physical framing / crop: PAN card box is located on the right-hand counterfoil, which is cropped out of this single-camera photo.",
    "Cash Denomination Breakdown": "Tabular structure limitation: The grid rows (2000x, 500x, 100x notes) are not individual key-value text pairs, so the OCR line segmenter merges them or ignores non-text boxes.",
    "Signature of Depositor": "Explicitly ignored in bank_form_service.py line 100 (_ignore key): signatures cannot be captured via voice and must be physically signed.",
}
for lbl in missed_photo:
    print(f"  • {lbl}: {photo_reasons.get(lbl, 'Not matched by bank form vocabulary.')}")

print("\n" + "=" * 80)
