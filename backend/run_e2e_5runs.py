"""
FinAccess AI — Real End-to-End Execution Script
Executes:
1. 5 full runs in Hindi (hi) across 5 distinct financial forms
2. 5 full runs in Tamil (ta) across 5 distinct financial forms
3. 1 full run on a real phone photo of a bank deposit slip
Records:
- Pass / Fail status
- Total time (seconds)
- Form name and field count
- Localized prompt question
- Generated stamped PDF file path and byte size
"""

import time
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

FORMS_TO_TEST = [
    ("uploads/0068adc1392f435a8c9d66c1eb9e3463.pdf", "PMJDY Basic Savings Account Form"),
    ("uploads/01c0c45206124740b69d3c082e725d89.pdf", "PM-Kisan Samman Nidhi Form"),
    ("uploads/05b4b392c69544f8b75bf68cd93da88e.pdf", "National Pension (NSAP) Form"),
    ("uploads/011eb3c2deb0439aa0def684faea6e9d.pdf", "Standard KYC Verification Form"),
    ("uploads/905065c108f24c289462bed092ce1f6e.pdf", "PM SVANidhi Micro-Credit Form"),
]

PHOTO_FORM = ("uploads/880fba20bf844e90aa45d446687912dc.jpg", "PNB Cash Deposit Slip (Real Phone Photo)")

SAMPLE_ANSWERS_HI = {
    "name": "रमेश कुमार",
    "number": "987654321012",
    "date": "15/08/1980",
    "cheque_date": "10 October 2026",
    "cheque_amount": "पांच हजार रुपये",
    "phone": "9876543210",
    "address": "गाँव रामपुर, वाराणसी, उत्तर प्रदेश",
    "text": "भारतीय स्टेट बैंक",
}

SAMPLE_ANSWERS_TA = {
    "name": "முருகன் குமார்",
    "number": "987654321012",
    "date": "15/08/1980",
    "cheque_date": "10 October 2026",
    "cheque_amount": "ஐந்தாயிரம் ரூபாய்",
    "phone": "9876543210",
    "address": "கிராமம் ராம்புரம், மதுரை, தமிழ்நாடு",
    "text": "ஸ்டேட் பாங்க் ஆப் இந்தியா",
}


def execute_flow(form_path_str: str, form_title: str, language: str, run_id: int):
    t_start = time.perf_counter()
    form_path = Path(form_path_str)
    if not form_path.exists():
        return {"run_id": run_id, "form_title": form_title, "status": "FAIL", "error": f"File not found: {form_path}"}

    # 1. Create Session
    s_res = requests.post(f"{BASE_URL}/api/v1/sessions", json={"preferred_language": language})
    assert s_res.status_code == 200, f"Session creation failed: {s_res.text}"
    session_id = s_res.json()["id"]

    # 2. Upload Form
    with open(form_path, "rb") as f:
        media_type = "image/jpeg" if form_path.suffix.lower() in [".jpg", ".jpeg"] else "application/pdf"
        up_res = requests.post(
            f"{BASE_URL}/api/v1/forms/upload",
            data={"session_id": session_id, "form_type": "standard"},
            files={"file": (form_path.name, f, media_type)},
        )
    assert up_res.status_code == 200, f"Upload failed: {up_res.text}"
    up_data = up_res.json()
    form_id = up_data["form_id"]
    detected_fields = up_data.get("fields", [])

    answers_dict = SAMPLE_ANSWERS_HI if language == "hi" else SAMPLE_ANSWERS_TA
    questions_recorded = []

    # 3. Step through fields: Answer + Nonce Confirm each field
    for field in detected_fields:
        f_id = field.get("id")
        f_type = field.get("field_type", "text")
        q_text = field.get("question_text") or field.get("label") or "Field prompt"
        questions_recorded.append(q_text)

        val = answers_dict.get(f_type, "9876543210" if f_type == "phone" else "रमेश कुमार")
        
        # Submit answer
        ans_res = requests.post(
            f"{BASE_URL}/api/v1/forms/{form_id}/fields/{f_id}/answer",
            json={"transcribed_text": val, "preferred_language": language},
        )
        assert ans_res.status_code == 200, f"Answer failed: {ans_res.text}"
        ans_data = ans_res.json()

        # If confirmation nonce is issued, respond with challenge digits
        nonce_id = ans_data.get("nonce_id")
        digits = ans_data.get("challenge_digits")
        if nonce_id and digits:
            conf_res = requests.post(
                f"{BASE_URL}/api/v1/confirmations/{nonce_id}/respond",
                json={"session_id": session_id, "transcribed_text": digits},
            )
            assert conf_res.status_code == 200, f"Field confirm failed: {conf_res.text}"

    # 4. Final Confirmation Nonce for submitting form
    ch_res = requests.post(
        f"{BASE_URL}/api/v1/confirmations",
        json={"session_id": session_id, "bound_action": "submit_form", "bound_target_id": form_id},
    )
    assert ch_res.status_code == 200, f"Final challenge creation failed: {ch_res.text}"
    final_nonce_id = ch_res.json()["nonce_id"]
    final_digits = ch_res.json()["challenge_digits"]

    fin_conf = requests.post(
        f"{BASE_URL}/api/v1/confirmations/{final_nonce_id}/respond",
        json={"session_id": session_id, "transcribed_text": final_digits},
    )
    assert fin_conf.status_code == 200, f"Final confirmation failed: {fin_conf.text}"

    # 5. Finalize Form (Generates filled PDF)
    fin_res = requests.post(f"{BASE_URL}/api/v1/forms/{form_id}/finalize")
    assert fin_res.status_code == 200, f"Finalize failed: {fin_res.text}"
    fin_data = fin_res.json()
    stamped_pdf_url = fin_data.get("pdf_url") or fin_data.get("download_url")

    # 6. Download Stamped PDF
    dl_res = requests.get(f"{BASE_URL}{stamped_pdf_url}")
    assert dl_res.status_code == 200, f"Download failed: {dl_res.status_code}"
    pdf_bytes = len(dl_res.content)
    assert pdf_bytes > 500, f"PDF too small: {pdf_bytes} bytes"

    # Save to disk as proof
    out_dir = Path("stamped_demo_output")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"run_{language}_{run_id}_{form_path.stem}.pdf"
    out_file.write_bytes(dl_res.content)

    t_total = time.perf_counter() - t_start
    return {
        "run_id": run_id,
        "language": language,
        "form_title": form_title,
        "fields_count": len(detected_fields),
        "status": "PASS",
        "total_time_sec": round(t_total, 2),
        "pdf_size_bytes": pdf_bytes,
        "output_pdf": str(out_file),
        "sample_question": questions_recorded[0] if questions_recorded else "N/A",
    }


def main():
    print("=" * 110)
    print("FINACCESS AI — 10 END-TO-END DEMO RUNS (5 HINDI + 5 TAMIL) + 1 REAL PHONE PHOTO RUN")
    print("=" * 110)

    # 5 Hindi Runs
    print("\n--- HINDI (hi) END-TO-END RUNS ---")
    hi_results = []
    for idx, (fpath, ftitle) in enumerate(FORMS_TO_TEST, 1):
        res = execute_flow(fpath, ftitle, "hi", idx)
        hi_results.append(res)
        print(f"Run {idx:2} [HI]: {ftitle:36} | Status: {res['status']} | Time: {res['total_time_sec']:5.2f}s | "
              f"Fields: {res['fields_count']:2} | PDF: {res['pdf_size_bytes']:6}B | Saved: {res['output_pdf']}")

    # 5 Tamil Runs
    print("\n--- TAMIL (ta) END-TO-END RUNS ---")
    ta_results = []
    for idx, (fpath, ftitle) in enumerate(FORMS_TO_TEST, 1):
        res = execute_flow(fpath, ftitle, "ta", idx)
        ta_results.append(res)
        print(f"Run {idx:2} [TA]: {ftitle:36} | Status: {res['status']} | Time: {res['total_time_sec']:5.2f}s | "
              f"Fields: {res['fields_count']:2} | PDF: {res['pdf_size_bytes']:6}B | Saved: {res['output_pdf']}")

    # Real Phone Photo Run
    print("\n--- REAL PHONE PHOTO OF A FORM RUN ---")
    photo_res = execute_flow(PHOTO_FORM[0], PHOTO_FORM[1], "hi", 1)
    print(f"Photo Run: {PHOTO_FORM[1]:36} | Status: {photo_res['status']} | Time: {photo_res['total_time_sec']:5.2f}s | "
          f"Fields: {photo_res['fields_count']:2} | PDF: {photo_res['pdf_size_bytes']:6}B | Saved: {photo_res['output_pdf']}")

    print("\n" + "=" * 110)
    print("ALL 11 RUNS COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
    print("=" * 110)


if __name__ == "__main__":
    main()
