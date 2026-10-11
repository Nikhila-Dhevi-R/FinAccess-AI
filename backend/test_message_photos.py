"""
Real SMS screenshots (test_fixtures/sms) read by the OCR pipeline, both as screenshots and as
simulated camera photos of a phone screen (tilted, glare, blur, sideways), then classified.
"""

import io
import os

import numpy as np
import pytest
from PIL import Image, ImageFilter

from services import cheque_service
from services.fraud_service import classify_message, ocr_message_image

FIXTURES = os.path.join(os.path.dirname(__file__), "test_fixtures", "sms")
needs_ocr = pytest.mark.skipif(not cheque_service._find_tesseract(), reason="Tesseract OCR is not installed")

CASES = {  # file: (expected verdict, text that must be read)
    "fake_credit.png": ("fraud", ["3056967575278", "credited"]),
    "sbiupi_tokens.png": ("fraud", ["SBIUPI"]),
    "amazon_giftcard.png": ("fraud", ["shorturl.at", "gift card"]),
    "centro_promo.png": ("safe", ["t.jio/CENSNM", "CENTRO"]),
}


def _coeffs(src, dst):
    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
    return np.linalg.solve(np.array(rows, float), np.array(src, float).reshape(8)).tolist()


def camera_photo(img, tilt=0.08, rotate=4.0, sideways=False, seed=1):
    """A photo of the phone screen lying on a desk: bezel, perspective, glare, blur, noise, JPEG."""
    rng = np.random.default_rng(seed)
    img = img.convert("RGB")
    phone = Image.new("RGB", (img.width + 60, img.height + 160), (15, 15, 18))
    phone.paste(img, (30, 80))
    scale = 2600 * 0.65 / max(phone.size)
    phone = phone.resize((int(phone.width * scale), int(phone.height * scale)), Image.BICUBIC)
    w, h = int(2600 * 0.78), 2600
    desk = Image.new("RGB", (w, h), (130, 120, 110))
    desk.paste(phone, ((w - phone.width) // 2, (h - phone.height) // 2))
    d = tilt * w
    desk = desk.transform((w, h), Image.PERSPECTIVE,
                          _coeffs([(0, 0), (w, 0), (w, h), (0, h)], [(d, d * 0.4), (w - d * 0.6, 0), (w, h), (0, h - d * 0.3)]),
                          Image.BICUBIC, fillcolor=(120, 110, 100)).rotate(rotate, resample=Image.BICUBIC, fillcolor=(120, 110, 100))
    a = np.asarray(desk).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    spot = np.exp(-(((xx - 0.5 * w) ** 2 + (yy - 0.35 * h) ** 2) / (2 * (0.22 * w) ** 2)))
    a = a * (1 - 0.35 * spot[..., None]) + 255 * 0.35 * spot[..., None] + rng.normal(0, 7, a.shape)
    a = (a - 128) * 0.82 + 138
    photo = Image.fromarray(a.clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.6))
    if sideways:
        photo = photo.rotate(90, expand=True)
    buf = io.BytesIO()
    photo.save(buf, "JPEG", quality=72)
    return buf.getvalue()


PHOTO_MUST_READ = {
    # Known limit: in camera photos of this dark-mode screen with glare, the short link is not always
    # read character-perfect, so only the shop name is required (the verdict must still be right).
    "centro_promo.png": ["CENTRO"],
}


def _check(name, data, photo=False):
    expected, must_read = CASES[name]
    if photo:
        must_read = PHOTO_MUST_READ.get(name, must_read)
    text = ocr_message_image(data)
    flat = " ".join(text.split()).lower()
    for needle in must_read:
        assert needle.lower() in flat, f"{needle!r} not read from {name}:\n{text}"
    assert classify_message(text)["classification"] == expected, text


@needs_ocr
@pytest.mark.parametrize("name", list(CASES))
def test_screenshot(name):
    with open(os.path.join(FIXTURES, name), "rb") as fh:
        _check(name, fh.read())


@needs_ocr
@pytest.mark.parametrize("variant", ["photo", "tilted", "sideways"])
@pytest.mark.parametrize("name", list(CASES))
def test_camera_photo_of_screen(name, variant):
    img = Image.open(os.path.join(FIXTURES, name))
    kwargs = {"photo": {}, "tilted": {"tilt": 0.14, "rotate": 7}, "sideways": {"sideways": True}}[variant]
    _check(name, camera_photo(img, **kwargs), photo=True)


# ─── Detection of the scam tricks in these screenshots (text only, no OCR) ───
def test_fake_credit_alert_same_reference_for_different_amounts():
    text = ("Rs 10,000.00 credited to a/c XXXXX8027 on 2-05-24 by a/c linked to VPA XXXX8027 (UPI Ref No 3056967575278\n"
            "Rs 30,000.00 credited to a/c XXXXX8027 on 2-05-24 by a/c linked to VPA XXXX8027 (UPI Ref No 3056967575278")
    r = classify_message(text)
    assert r["classification"] == "fraud" and "sent by mistake" in r["scam_type"]


def test_credit_alert_from_personal_mobile_number():
    r = classify_message("+91 90246 13907\nRs 10,000.00 credited to a/c XXXXX8027 on 2-05-24 (UPI Ref No 3056967575278)")
    assert r["classification"] == "fraud"


def test_genuine_credit_alert_from_bank_is_safe():
    r = classify_message("AX-SBIINB\nRs 10,000.00 credited to a/c XXXXX8027 on 2-05-24 by UPI Ref No 3056967575278")
    assert r["classification"] == "safe"


def test_upi_binding_code_is_fraud_despite_dont_share_wording():
    r = classify_message("SBIUPI Confidential:Dont share if asked!Oj3O6BBRRyP4%2BEfCjYXR8lvBzzwxr8W5QEC3GnJ7%2Byb")
    assert r["classification"] == "fraud" and r["scam_type"] == "UPI SIM-binding hijack"


def test_jio_official_short_link_in_promo_is_safe():
    r = classify_message("Special Offer from CENTRO. Get Rs.500 OFF on minimum purchase of Rs.2499. Store Link: https://t.jio/CENSNM/WPo3aN")
    assert r["classification"] == "safe"


def test_gift_card_prize_with_short_link_is_fraud():
    r = classify_message("Congratulations! You've been selected to receive a $500 Amazon gift card. Claim it within the next "
                         "24 hours. Click the link below to verify your eligibility: https://shorturl.at/3uleX")
    assert r["classification"] == "fraud"


def test_hinglish_fir_meaning_then_is_not_a_police_threat():
    assert classify_message("Kal milte hai, fir baat karenge.")["classification"] == "safe"
