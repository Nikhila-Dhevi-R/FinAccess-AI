"""
Cheque Detection, Voice Answer Parsing & Filled-Cheque Rendering

Cheques are usually scanned images (no text layer), so the regular PDF text
extractor finds nothing. This service:
- Renders the cheque (PDF page or image) to pixels and OCRs it with Tesseract
- Finds the printed anchors (PAY, OR BEARER, SUM OF / RUPEES, DATE, ACC NO)
- Finds the printed blank lines / boxes next to those anchors
- Returns form fields carrying exact PDF coordinates for each blank space
- Parses spoken amounts / dates and converts amounts to Indian-English words
- Writes the confirmed values onto the original cheque and saves a PDF
"""

import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from typing import Optional

try:
    import numpy as np
    from PIL import Image, ImageOps
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False

try:
    from reportlab.pdfbase.pdfmetrics import stringWidth
except ImportError:
    stringWidth = None

try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from config import get_settings

settings = get_settings()

RENDER_DPI = 200
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
INK_RGB = (0.05, 0.15, 0.55)  # Ball-pen blue

# ─── Field definitions (question text must contain the LOCALIZED_QUESTIONS key) ─
CHEQUE_FIELDS = {
    "date": {
        "label": "Cheque Date",
        "field_type": "cheque_date",
        "question_text": "What date should be written on the cheque? Please say the cheque date, or just say today.",
    },
    "payee": {
        "label": "Payee Name",
        "field_type": "name",
        "question_text": "Who should this cheque be paid to? Please say the payee name.",
    },
    "amount": {
        "label": "Cheque Amount",
        "field_type": "cheque_amount",
        "question_text": "How much money should this cheque be for? Please say the cheque amount in rupees.",
    },
    "account": {
        "label": "Account Number",
        "field_type": "number",
        "question_text": "What is the account number for this cheque? Please say the cheque account number.",
    },
}

ANCHOR_WORDS = {
    "pay": {"pay"},
    "bearer": {"bearer", "order"},
    "sum": {"sum", "rupees", "rupee"},
    "date": {"date"},
    "account": {"acc", "a/c", "ac", "account"},
}
LABEL_CONTINUATIONS = {"of", "no", "number"}


# ─── Tesseract / rendering helpers ───────────────────────────────────────────
def _find_tesseract() -> Optional[str]:
    cmd = shutil.which(settings.TESSERACT_CMD) or shutil.which("tesseract")
    if cmd:
        return cmd
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
    ]
    return next((c for c in candidates if os.path.isfile(c)), None)


def _ocr_words(image, psm: str = "11", offset: tuple = (0, 0)) -> list[dict]:
    """Run Tesseract directly (no global pytesseract config) and return word boxes."""
    cmd = _find_tesseract()
    if not cmd:
        print("[CHEQUE] Tesseract not found; cheque detection skipped")
        return []

    fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        image.save(tmp_path)
        proc = subprocess.run(
            [cmd, tmp_path, "stdout", "--psm", psm, "tsv"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
    finally:
        os.remove(tmp_path)

    words = []
    for row in csv.DictReader(io.StringIO(proc.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        try:
            conf = float(row.get("conf") or -1)
        except ValueError:
            continue
        if not text or conf < 30:
            continue
        left, top = int(row["left"]) + offset[0], int(row["top"]) + offset[1]
        width, height = int(row["width"]), int(row["height"])
        words.append({
            "text": text,
            "norm": re.sub(r"[^a-z/]", "", text.lower()),
            "x0": left, "y0": top, "x1": left + width, "y1": top + height,
            "h": height, "conf": conf,
        })
    return words


def _ink_threshold(gray) -> int:
    return min(170, int(np.median(gray)) - 70)


def _ocr_page(img, gray) -> list[dict]:
    """
    OCR the cheque twice (binarized to strip the security pattern, and plain grayscale)
    and merge the words, since either pass alone can miss a printed label.
    """
    binary = Image.fromarray(np.where(gray < _ink_threshold(gray), 0, 255).astype("uint8"))
    words = _ocr_words(binary)
    for w in _ocr_words(img.convert("L")):
        overlaps = any(
            w["norm"] == o["norm"] and w["x0"] < o["x1"] and o["x0"] < w["x1"] and w["y0"] < o["y1"] and o["y0"] < w["y1"]
            for o in words
        )
        if not overlaps:
            words.append(w)
    return words


def _find_boxes(lines, img_w) -> list[tuple]:
    """Pairs of rules with matching left/right ends, i.e. printed rectangles."""
    boxes = []
    for top in lines:
        for bottom in lines:
            dy = bottom["y0"] - top["y1"]
            if not (img_w * 0.012 <= dy <= img_w * 0.09):
                continue
            if abs(top["x0"] - bottom["x0"]) > img_w * 0.02 or abs(top["x1"] - bottom["x1"]) > img_w * 0.02:
                continue
            if any(m is not top and m is not bottom and top["y1"] < m["y0"] < bottom["y0"]
                   and m["x0"] <= top["x0"] + 5 and m["x1"] >= top["x1"] - 5 for m in lines):
                continue
            boxes.append((top, bottom))
    return boxes


def _account_anchor_from_boxes(img, lines) -> Optional[dict]:
    """Labels printed inside a box (e.g. "ACC. NO |") are often missed by page OCR; read each box alone."""
    gray_img = img.convert("L")
    for top, bottom in _find_boxes(lines, img.width):
        x0, x1 = max(top["x0"], bottom["x0"]) + 4, min(top["x1"], bottom["x1"]) - 4
        y0, y1 = top["y1"] + 3, bottom["y0"] - 2
        if x1 - x0 < 20 or y1 - y0 < 8:
            continue
        words = _ocr_words(gray_img.crop((x0, y0, x1, y1)), psm="7", offset=(x0, y0))
        anchor = _find_anchor(words, "account")
        if anchor:
            return anchor
    return None


def _load_page_image(file_path: str, is_pdf: bool, dpi: int = RENDER_DPI):
    """
    Returns (PIL image, px_to_pdf transform dict) where the transform maps image pixels
    to the coordinate space used when stamping the output PDF.
    """
    if is_pdf:
        if not PYMUPDF_AVAILABLE:
            print("[CHEQUE] PyMuPDF not installed; cannot rasterize PDF cheque")
            return None, None
        import pypdf
        crop = pypdf.PdfReader(file_path).pages[0].cropbox  # PDF space, bottom-left origin
        doc = pymupdf.open(file_path)
        try:
            page = doc[0]
            page.set_rotation(0)  # render in unrotated user space, same space the overlay uses
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        finally:
            doc.close()
        return img, {
            "kind": "pdf",
            "scale": float(crop.width) / img.width,
            "left": float(crop.left),
            "top": float(crop.top),
            "page_width": float(crop.width),
            "page_height": float(crop.height),
        }

    img = ImageOps.exif_transpose(Image.open(file_path)).convert("RGB")
    scale = 72.0 / 150  # treat images as 150 dpi when building the output PDF page
    return img, {
        "kind": "image",
        "scale": scale,
        "left": 0.0,
        "top": img.height * scale,
        "page_width": img.width * scale,
        "page_height": img.height * scale,
    }


def _horizontal_lines(gray) -> list[dict]:
    """Find printed horizontal rules (blank lines and box edges)."""
    height, width = gray.shape
    dark = gray < _ink_threshold(gray)
    min_run = int(width * 0.06)

    raw = []
    for y in np.where(dark.sum(axis=1) >= min_run)[0]:
        row = dark[y].astype(np.int8)
        edges = np.diff(np.concatenate([[0], row, [0]]))
        runs = []
        for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
            if runs and s - runs[-1][1] <= 40:  # bridge gaps from watermarks
                runs[-1][1] = e
            else:
                runs.append([s, e])
        raw.extend((int(y), int(s), int(e)) for s, e in runs if e - s >= min_run)

    merged = []
    for y, s, e in raw:
        for m in merged:
            if y - m["y1"] <= 3 and s < m["x1"] and e > m["x0"]:
                m["y1"] = y
                m["x0"], m["x1"] = min(m["x0"], s), max(m["x1"], e)
                break
        else:
            merged.append({"y0": y, "y1": y, "x0": s, "x1": e})
    return merged


def _find_anchor(words: list[dict], key: str) -> Optional[dict]:
    matches = [w for w in words if w["norm"] in ANCHOR_WORDS[key]]
    if key == "account":
        matches += [w for w in words if w["text"].lower().startswith(("a/c", "acc"))]
    if not matches:
        return None
    anchor = dict(min(matches, key=lambda w: (w["y0"], w["x0"])))

    # Extend label with neighbouring words on the same row ("SUM OF", "ACC. NO", "OR BEARER")
    for w in sorted(words, key=lambda w: w["x0"]):
        same_row = abs((w["y0"] + w["y1"]) / 2 - (anchor["y0"] + anchor["y1"]) / 2) < anchor["h"] * 0.6
        if not same_row:
            continue
        if w["norm"] in LABEL_CONTINUATIONS and 0 <= w["x0"] - anchor["x1"] < anchor["h"] * 1.5:
            anchor["x1"] = w["x1"]
        if key == "bearer" and w["norm"] == "or" and 0 <= anchor["x0"] - w["x1"] < anchor["h"] * 1.5:
            anchor["x0"] = w["x0"]
    return anchor


def _line_under(lines, anchor, min_x1=None):
    """Nearest rule just below an anchor that extends to the right of it."""
    h = anchor["h"]
    candidates = [
        l for l in lines
        if anchor["y1"] - h * 0.5 <= l["y0"] <= anchor["y1"] + h * 2.5
        and l["x1"] > (min_x1 or anchor["x1"] + h * 2)
        and l["x0"] < anchor["x1"] + h * 4
    ]
    return min(candidates, key=lambda l: l["y0"]) if candidates else None


def _ink_clusters(gray, x0, x1, y0, y1, gap=6):
    band = gray[max(0, y0):y1, x0:x1] < _ink_threshold(gray)
    clusters = []
    for x in np.where(band.any(axis=0))[0]:
        if clusters and x - clusters[-1][1] <= gap:
            clusters[-1][1] = x
        else:
            clusters.append([x, x])
    return [(int(a) + x0, int(b) + x0) for a, b in clusters]


# ─── Detection ───────────────────────────────────────────────────────────────
def looks_like_cheque(file_path: str, filename: str, is_pdf: bool) -> bool:
    """Cheap pre-check for text-based documents that are clearly cheques."""
    if re.search(r"cheque|\bcheck\b", (filename or "").lower()):
        return True
    if not is_pdf:
        return False
    try:
        import pypdf
        text = (pypdf.PdfReader(file_path).pages[0].extract_text() or "").lower()
        return bool(re.search(r"\bpay\b", text) and re.search(r"\bbearer\b|\bor order\b", text))
    except Exception:
        return False


def detect_cheque_fields(file_path: str, is_pdf: bool) -> list[dict]:
    """
    Detect a cheque and return field dicts (label, field_type, question_text, page, x, y,
    width, height, cheque). Returns [] when the document does not look like a cheque.
    """
    if not IMAGING_AVAILABLE:
        return []
    try:
        img, tf = _load_page_image(file_path, is_pdf)
        if img is None:
            return []
        gray = np.asarray(img.convert("L")).astype(np.int16)
        words = _ocr_page(img, gray)
        anchors = {k: _find_anchor(words, k) for k in ANCHOR_WORDS}
        if not anchors["pay"] or not anchors["bearer"]:  # every cheque prints "or Bearer" / "or Order"
            return []
        lines = _horizontal_lines(gray)
        if not anchors["account"]:
            anchors["account"] = _account_anchor_from_boxes(img, lines)
        return _build_fields(gray, anchors, lines, tf)
    except Exception as e:
        print(f"[CHEQUE] Detection notice: {e}")
        return []


def _build_fields(gray, anchors, lines, tf) -> list[dict]:
    img_h, img_w = gray.shape
    scale = tf["scale"]
    pay = anchors["pay"]
    text_h = pay["h"]  # cap-height of printed labels, used as a size reference
    gap = text_h * 0.6

    def to_pdf(x0, x1, baseline, size_px):
        return {
            "x0": round(tf["left"] + x0 * scale, 2),
            "x1": round(tf["left"] + x1 * scale, 2),
            "baseline": round(tf["top"] - baseline * scale, 2),
            "size": round(max(7.0, min(16.0, size_px * scale)), 2),
        }

    slots = {}

    # Payee: rule under "PAY", up to "OR BEARER"
    pay_line = _line_under(lines, pay)
    stop = anchors["bearer"]
    x_end = stop["x0"] - gap if stop and stop["x0"] > pay["x1"] else (pay_line["x1"] if pay_line else img_w * 0.9)
    base = pay_line["y0"] - text_h * 0.25 if pay_line else pay["y1"]
    slots["payee"] = {"area": to_pdf(pay["x1"] + gap, x_end, base, text_h * 1.45)}

    # Amount in words: rule under "SUM OF"/"RUPEES" plus the continuation rule below it
    sum_anchor = anchors["sum"]
    words_lines = []
    if sum_anchor:
        first = _line_under(lines, sum_anchor)
        if first:
            words_lines.append(to_pdf(sum_anchor["x1"] + gap, first["x1"] - gap,
                                      first["y0"] - text_h * 0.25, text_h * 1.3))
            below = [l for l in lines
                     if text_h * 1.5 <= l["y0"] - first["y1"] <= text_h * 5
                     and l["x0"] < sum_anchor["x1"] and l["x1"] > first["x1"] - text_h * 4]
            if below:
                second = min(below, key=lambda l: l["y0"])
                words_lines.append(to_pdf(second["x0"] + gap, second["x1"] - gap,
                                          second["y0"] - text_h * 0.25, text_h * 1.3))
        else:
            words_lines.append(to_pdf(sum_anchor["x1"] + gap, img_w * 0.65, sum_anchor["y1"], text_h * 1.1))

    # Amount in figures: a box (two matching rules) on the right of the words lines
    box_area = None
    region_top = (sum_anchor or pay)["y0"] - text_h * 3
    region_bottom = (sum_anchor or pay)["y1"] + text_h * 8
    acc = anchors["account"]
    boxes = []
    for top, bottom in _find_boxes(lines, img_w):
        width = top["x1"] - top["x0"]
        if width > img_w * 0.45 or (top["x0"] + top["x1"]) / 2 < img_w * 0.5:
            continue
        if not (region_top <= top["y0"] <= region_bottom):
            continue
        if acc and top["x0"] <= acc["x0"] <= top["x1"] and top["y0"] <= acc["y0"] <= bottom["y0"]:
            continue
        boxes.append((top, bottom))
    if boxes:
        top, bottom = min(boxes, key=lambda b: b[0]["y0"])
        mid = (top["y1"] + bottom["y0"]) / 2
        box_text = min(text_h * 1.5, (bottom["y0"] - top["y1"]) * 0.55)
        box_area = to_pdf(max(top["x0"], bottom["x0"]) + gap * 1.5, min(top["x1"], bottom["x1"]) - gap,
                          mid + box_text * 0.36, box_text)
    elif words_lines:
        last = words_lines[-1]
        box_area = {**last, "x0": round(tf["left"] + img_w * 0.70 * scale, 2),
                    "x1": round(tf["left"] + img_w * 0.95 * scale, 2)}
    if sum_anchor or box_area:
        slots["amount"] = {
            "box": box_area,
            "words_lines": words_lines,
            "words_prefix": bool(sum_anchor and sum_anchor["norm"] == "sum"),
        }

    # Date: rule right of "DATE" (split around printed "/ /20" marks if present)
    date_anchor = anchors["date"]
    if date_anchor:
        date_line = _line_under(lines, date_anchor, min_x1=date_anchor["x1"] + text_h)
        if date_line:
            x0 = max(date_line["x0"], date_anchor["x1"] + gap * 0.5)
            x1 = date_line["x1"]
            base = date_line["y0"] - text_h * 0.25
            marks = _ink_clusters(gray, int(x0), int(x1), int(date_line["y0"] - text_h * 1.7), int(date_line["y0"] - 3))
            date_slot = {"area": to_pdf(x0, x1, base, text_h * 1.1)}
            slashes = [m for m in marks if (m[1] - m[0]) < text_h * 0.8]
            if len(slashes) >= 2:
                s1, s2 = slashes[0], slashes[1]
                after = [m for m in marks if m[0] > s2[1]]
                year_start = after[-1][1] if after else s2[1]
                date_slot["parts"] = [
                    to_pdf(x0, s1[0], base, text_h * 1.1),
                    to_pdf(s1[1], s2[0], base, text_h * 1.1),
                    to_pdf(year_start, x1, base, text_h * 1.1),
                ]
                date_slot["year_digits"] = 2 if after else 4
            slots["date"] = date_slot
        else:
            slots["date"] = {"area": to_pdf(date_anchor["x1"] + gap, min(img_w * 0.97, date_anchor["x1"] + text_h * 14),
                                            date_anchor["y1"], text_h * 1.1)}
    else:
        # Indian CTS cheques often print only DDMMYYYY boxes at top-right
        base = pay["y0"] - text_h * 1.5
        slots["date"] = {"area": to_pdf(img_w * 0.70, img_w * 0.95, base, text_h * 1.1)}

    # Account number: box around "ACC NO" (text goes after the vertical divider)
    if acc:
        a_h = acc["h"]
        tops = [l for l in lines if acc["y0"] - a_h * 2 <= l["y0"] <= acc["y0"] and l["x0"] <= acc["x0"] + a_h <= l["x1"]]
        bottoms = [l for l in lines if acc["y1"] <= l["y0"] <= acc["y1"] + a_h * 2 and l["x0"] <= acc["x0"] + a_h <= l["x1"]]
        if tops and bottoms:
            top = max(tops, key=lambda l: l["y0"])
            bottom = min(bottoms, key=lambda l: l["y0"])
            interior = gray[top["y1"] + 3:bottom["y0"] - 2, :] < _ink_threshold(gray)
            start = acc["x1"]
            col_ratio = interior[:, int(acc["x1"]):int(acc["x1"] + a_h * 3)].mean(axis=0) if interior.size else []
            dividers = [i for i, v in enumerate(col_ratio) if v > 0.7]
            if dividers:
                start = acc["x1"] + dividers[-1]
            mid = (top["y1"] + bottom["y0"]) / 2
            size = min(text_h * 1.4, (bottom["y0"] - top["y1"]) * 0.55)
            slots["account"] = {"area": to_pdf(start + gap, min(top["x1"], bottom["x1"]) - gap, mid + size * 0.36, size)}
        else:
            line = _line_under(lines, acc)
            base = line["y0"] - text_h * 0.25 if line else acc["y1"]
            slots["account"] = {"area": to_pdf(acc["x1"] + gap, line["x1"] if line else img_w * 0.5, base, text_h * 1.1)}

    page_info = {
        "kind": tf["kind"],
        "page_width": tf["page_width"],
        "page_height": tf["page_height"],
    }

    fields = []
    for role in ("date", "payee", "amount", "account"):
        if role not in slots:
            continue
        spec = CHEQUE_FIELDS[role]
        ref = slots[role].get("area") or slots[role].get("box") or (slots[role].get("words_lines") or [{}])[0]
        fields.append({
            "label": spec["label"],
            "field_type": spec["field_type"],
            "question_text": spec["question_text"],
            "page": 1,
            "x": ref.get("x0", 180),
            "y": ref.get("baseline", 700),
            "width": round(ref.get("x1", 440) - ref.get("x0", 180), 2),
            "height": ref.get("size", 12),
            "cheque": {"role": role, "page": page_info, **slots[role]},
        })
    return fields


# ─── Spoken answer parsing ───────────────────────────────────────────────────
UNIT_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "a": 1, "an": 1,
    # Hindi (Devanagari + transliterated)
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7,
    "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "पंद्रह": 15, "बीस": 20, "पच्चीस": 25,
    "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhah": 6,
    "saat": 7, "aath": 8, "nau": 9, "das": 10, "bees": 20, "pachees": 25, "tees": 30,
    "chalees": 40, "pachaas": 50, "pachas": 50, "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
    "dedh": 1.5, "dhai": 2.5, "डेढ़": 1.5, "ढाई": 2.5,
    # Tamil
    "ஒன்று": 1, "ஒரு": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5, "ஆறு": 6,
    "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10,
}
MULTIPLIERS = {
    "hundred": 100, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000,
    "crore": 10000000, "crores": 10000000, "million": 1000000,
    "sau": 100, "so": 100, "hazaar": 1000, "hazar": 1000, "hajar": 1000, "karod": 10000000, "karor": 10000000,
    "सौ": 100, "हजार": 1000, "हज़ार": 1000, "लाख": 100000, "करोड़": 10000000, "करोड": 10000000,
    "நூறு": 100, "ஆயிரம்": 1000, "லட்சம்": 100000, "கோடி": 10000000,
}
FILLER_WORDS = {
    "rs", "rupees", "rupee", "rupaye", "rupay", "rupaiye", "inr", "only", "and", "aur", "the", "of",
    "रुपये", "रुपए", "रुपया", "और", "ரூபாய்", "மட்டும்",
}
PAISE_WORDS = {"paise", "paisa", "पैसे", "पैसा", "பைசா"}


def _words_to_number(tokens: list[str]) -> Optional[float]:
    total, current, seen = 0.0, 0.0, False
    for tok in tokens:
        if re.fullmatch(r"\d+(\.\d+)?", tok):
            current += float(tok)
            seen = True
        elif tok in UNIT_WORDS:
            current += UNIT_WORDS[tok]
            seen = True
        elif tok in MULTIPLIERS:
            mult = MULTIPLIERS[tok]
            if mult == 100:
                current = (current or 1) * 100
            else:
                total += (current or 1) * mult
                current = 0
            seen = True
    return total + current if seen else None


def parse_spoken_amount(text: str) -> Optional[float]:
    """'5000', '₹5,000', 'five thousand', 'do lakh pachaas hazaar', '5 हजार' → rupee amount."""
    from services.voice_service import normalize_digits

    t = normalize_digits(text.lower())
    t = re.sub(r"\(.*?\)", " ", t)  # an edited readback like "₹5,000 (Rupees Five Thousand Only)"
    explicit = re.search(r"(?:₹|\brs\.?)\s*(\d[\d,]*(?:\.\d+)?)", t)
    if explicit:
        return round(float(explicit.group(1).replace(",", "")), 2)
    t = t.replace("₹", " ")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    t = re.sub(r"(\d)\s*(k)\b", r"\1 thousand", t)
    t = re.sub(r"[^\w\s.\u0900-\u097F\u0B80-\u0BFF]", " ", t)
    t = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", t)
    raw_tokens = t.split()

    paise = 0.0
    paise_idx = next((i for i, tok in enumerate(raw_tokens) if tok in PAISE_WORDS), None)
    if paise_idx is not None:
        # "<rupees> rupees and <paise> paise": split at the last rupee/and word before "paise"
        head = raw_tokens[:paise_idx]
        split = next((i for i in range(len(head) - 1, -1, -1) if head[i] in FILLER_WORDS), None)
        if split is None:
            # No separator spoken: paise are the number words after the last multiplier
            split = len(head)
            while split > 0 and head[split - 1] not in MULTIPLIERS:
                split -= 1
            paise_tokens, raw_tokens = head[split:], head[:split]
        else:
            paise_tokens, raw_tokens = head[split + 1:], head[:split]
        paise = _words_to_number([tok for tok in paise_tokens if tok not in FILLER_WORDS]) or 0.0

    tokens = [tok for tok in raw_tokens if tok not in FILLER_WORDS]

    # Pure digits spoken one by one ("5 0 0 0") → join them
    if tokens and all(re.fullmatch(r"\d", tok) for tok in tokens) and len(tokens) > 1:
        return float("".join(tokens)) + min(paise, 99) / 100.0

    rupees = _words_to_number(tokens)
    if rupees is None and not paise:
        return None
    return round((rupees or 0) + min(paise, 99) / 100.0, 2)


ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digits(n: int) -> str:
    if n < 20:
        return ONES[n]
    return (TENS[n // 10] + " " + ONES[n % 10]).strip()


def _three_digits(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(ONES[hundreds] + " Hundred")
    if rest:
        parts.append(_two_digits(rest))
    return " ".join(parts)


def number_to_indian_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    crore, n = divmod(n, 10000000)
    lakh, n = divmod(n, 100000)
    thousand, n = divmod(n, 1000)
    if crore:
        parts.append(number_to_indian_words(crore) + " Crore")
    if lakh:
        parts.append(_two_digits(lakh) + " Lakh")
    if thousand:
        parts.append(_two_digits(thousand) + " Thousand")
    if n:
        parts.append(_three_digits(n))
    return " ".join(parts)


def amount_to_words(amount: float, prefix: bool = True, suffix: bool = True) -> str:
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    words = number_to_indian_words(rupees)
    if paise:
        words += f" and {_two_digits(paise)} Paise"
    if prefix:
        words = f"Rupees {words}"
    return f"{words} Only" if suffix else words


def format_indian_amount(amount: float) -> str:
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"{s}.{paise:02d}" if paise else s


def interpret_amount(text: str) -> str:
    amount = parse_spoken_amount(text)
    if amount is None or amount <= 0:
        return text.strip()
    return f"₹{format_indian_amount(amount)} ({amount_to_words(amount)})"


def _amount_from_value(value: str) -> Optional[float]:
    """Recover the numeric amount from a confirmed value like '₹5,000 (Rupees Five Thousand Only)'."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    if m:
        return float(m.group(0).replace(",", ""))
    return parse_spoken_amount(value)


TODAY_WORDS = {"today", "aaj", "आज", "இன்று", "indru", "inru"}
TOMORROW_WORDS = {"tomorrow", "kal", "कल", "நாளை", "naalai"}


def interpret_date(text: str, today: Optional[date] = None) -> str:
    """'today', '10 October 2026', 'October 10th 2026', '10/10/26', 'दस अक्टूबर 2026' → DD/MM/YYYY."""
    from services.voice_service import normalize_digits, MONTHS_MAP

    today = today or date.today()
    t = normalize_digits(text.lower()).strip()
    tokens = re.findall(r"[\w\u0900-\u097F\u0B80-\u0BFF]+", t)
    if any(tok in TODAY_WORDS for tok in tokens):
        return today.strftime("%d/%m/%Y")
    if any(tok in TOMORROW_WORDS for tok in tokens):
        return (today + timedelta(days=1)).strftime("%d/%m/%Y")

    def build(d, m, y):
        if y < 100:
            y += 2000
        try:
            return date(y, m, d).strftime("%d/%m/%Y")
        except ValueError:
            return None

    m = re.search(r"\b(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{2,4})\b", t)
    if m:
        result = build(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if result:
            return result

    month_idx, month_num = None, None
    for i, tok in enumerate(tokens):
        if tok in MONTHS_MAP:
            month_idx, month_num = i, MONTHS_MAP[tok]
            break
    if month_num is not None:
        def num(toks):
            cleaned = [re.sub(r"(st|nd|rd|th)$", "", x) for x in toks if x not in ("the", "of", "on")]
            return _words_to_number(cleaned)

        before, after = tokens[:month_idx], tokens[month_idx + 1:]
        year_match = re.search(r"\b(\d{4})\b", " ".join(after)) or re.search(r"\b(\d{4})\b", " ".join(before))
        year = int(year_match.group(1)) if year_match else None
        if year_match:
            before = [x for x in before if x != year_match.group(1)]
            after = [x for x in after if x != year_match.group(1)]
        day = num(before) if before else None
        if day is None and after:
            day = num(after[:1])
            after = after[1:]
        if year is None and after:
            if len(after) >= 2 and after[0] == "twenty" and after[1] in UNIT_WORDS:
                year = 2000 + int(_words_to_number(after[1:]) or 0)
            else:
                year = int(_words_to_number(after) or 0) or None
        year = year or today.year
        if day:
            result = build(int(day), month_num, year)
            if result:
                return result

    return text.strip()


def validate_cheque_field(field_type: str, value: str) -> tuple[bool, str]:
    if field_type == "cheque_amount":
        if value.startswith("₹"):
            return True, "Valid"
        return False, "Please say the amount in rupees, for example five thousand."
    if field_type == "cheque_date":
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
            return True, "Valid"
        return False, "Please say a date like 10 October 2026, or say today."
    return True, "Valid"


# ─── Rendering ───────────────────────────────────────────────────────────────
def is_cheque_fields(fields: list[dict]) -> bool:
    return any((f.get("position") or {}).get("cheque") for f in fields)


_INDIC_FONT = None
INDIC_FONT_PATHS = [
    ("C:/Windows/Fonts/Nirmala.ttc", 0), ("C:/Windows/Fonts/Nirmala.ttf", None),
    ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", None),
]


def _font_for(text: str, font: str) -> str:
    """Helvetica has no Devanagari / Tamil glyphs: switch to an Indic-capable font for such answers."""
    global _INDIC_FONT
    if all(ord(ch) < 0x0250 for ch in text):
        return font
    if _INDIC_FONT is None:
        _INDIC_FONT = font
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for path, index in INDIC_FONT_PATHS:
            if os.path.isfile(path):
                try:
                    kwargs = {"subfontIndex": index} if index is not None else {}
                    pdfmetrics.registerFont(TTFont("IndicFont", path, **kwargs))
                    _INDIC_FONT = "IndicFont"
                    break
                except Exception as e:
                    print(f"[CHEQUE] Indic font notice: {e}")
    return _INDIC_FONT


def _fit_size(text: str, font: str, size: float, max_width: float, min_size: float = 6.0) -> float:
    while size > min_size and stringWidth(text, font, size) > max_width:
        size -= 0.25
    return size


def _draw_in(c, text: str, area: dict, font: str = "Helvetica-Bold"):
    font = _font_for(text, font)
    if not text or not area:
        return
    width = max(10.0, area["x1"] - area["x0"])
    size = _fit_size(text, font, area["size"], width)
    c.setFont(font, size)
    c.drawString(area["x0"], area["baseline"], text)


def _draw_words(c, words_text: str, lines: list[dict], font: str = "Helvetica-Bold"):
    font = _font_for(words_text, font)
    if not lines:
        return
    words = words_text.split()
    size = min(l["size"] for l in lines)
    while True:
        out, idx = [[] for _ in lines], 0
        for w in words:
            trial = " ".join(out[idx] + [w])
            if stringWidth(trial, font, size) <= lines[idx]["x1"] - lines[idx]["x0"] or not out[idx]:
                out[idx].append(w)
            elif idx + 1 < len(lines):
                idx += 1
                out[idx].append(w)
            else:
                out[idx].append(w)
        fits = all(stringWidth(" ".join(o), font, size) <= l["x1"] - l["x0"] for o, l in zip(out, lines))
        if fits or size <= 6:
            break
        size -= 0.25
    c.setFont(font, size)
    for o, l in zip(out, lines):
        if o:
            c.drawString(l["x0"], l["baseline"], " ".join(o))


def _draw_centered(c, text: str, area: dict, font: str = "Helvetica-Bold"):
    font = _font_for(text, font)
    size = _fit_size(text, font, area["size"], max(4.0, area["x1"] - area["x0"]), min_size=4.0)
    x = area["x0"] + max(0.0, (area["x1"] - area["x0"] - stringWidth(text, font, size)) / 2)
    c.setFont(font, size)
    c.drawString(x, area["baseline"], text)


def _comb_chars(value: str, field_type: str, n_cells: int) -> list[str]:
    if field_type == "cheque_date" and re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        digits = value.replace("/", "")
        return list(digits if n_cells >= 8 else digits[:4] + digits[-2:])
    if field_type in ("name", "text", "address", "payee"):
        return list(re.sub(r"\s+", " ", value.upper()))
    return list(re.sub(r"[^A-Za-z0-9]", "", value).upper())


def _draw_placement(c, value: str, field_type: str, p: dict):
    kind = p.get("type")
    if kind == "choice":
        for option in p.get("options", []):
            if option["label"].lower() == value.lower():
                box = option["box"]
                w = box["x1"] - box["x0"]
                x, y = box["x0"], box["baseline"] - w * 0.05  # baseline sits near the box bottom
                c.saveState()
                c.setStrokeColorRGB(*INK_RGB)
                c.setLineWidth(max(1.0, w * 0.13))
                c.setLineCap(1)
                c.setLineJoin(1)
                path = c.beginPath()  # a hand-drawn style tick mark
                path.moveTo(x + w * 0.2, y + w * 0.5)
                path.lineTo(x + w * 0.42, y + w * 0.25)
                path.lineTo(x + w * 0.85, y + w * 0.85)
                c.drawPath(path, stroke=1, fill=0)
                c.restoreState()
        return
    if kind == "comb":
        chars = _comb_chars(value, field_type, len(p["cells"]))
        if len(chars) > len(p["cells"]):
            _draw_in(c, "".join(chars), p.get("fallback") or p["cells"][0])
            return
        for ch, cell in zip(chars, p["cells"]):
            if ch.strip():
                _draw_centered(c, ch, cell)
    elif kind == "date_parts" and re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        day, month, year = value.split("/")
        if p.get("year_digits") == 2:
            year = year[-2:]
        for text, area in zip((day, month, year), p["parts"]):
            _draw_centered(c, text, area)
    elif kind == "date_prefix" and re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        # Form prints "Date ........ 20 ....": day/month before "20", last two year digits after it
        _draw_in(c, value[:6], p["lines"][0])
        _draw_in(c, value[-2:], p["year"])
    elif kind in ("amount_figures", "amount_words"):
        amount = _amount_from_value(value)
        if amount is None:
            if kind == "amount_figures":
                _draw_in(c, value, p["area"])
            return
        if kind == "amount_words":
            words = amount_to_words(amount, prefix=p.get("prefix", True), suffix=p.get("suffix", True))
            _draw_words(c, words, p["lines"])
        elif p.get("paise"):
            rupees = int(amount)
            _draw_in(c, format_indian_amount(rupees), p["area"])
            _draw_centered(c, f"{int(round((amount - rupees) * 100)):02d}", p["paise"])
        else:
            figures = format_indian_amount(amount)
            _draw_in(c, figures if "." in figures else f"{figures}/-", p["area"])
    else:
        lines = p.get("lines") or []
        if len(lines) > 1:
            _draw_words(c, value, lines)
        elif lines:
            _draw_in(c, value, lines[0])


def _draw_field(c, field: dict):
    value = str(field.get("confirmed_value") or "").strip()
    meta = (field.get("position") or {}).get("cheque") or {}
    if not value or not meta:
        return
    role = meta.get("role")

    if meta.get("placements"):
        for p in meta["placements"]:
            _draw_placement(c, value, field.get("field_type") or "text", p)
    elif role == "amount":
        amount = _amount_from_value(value)
        if amount is None:
            _draw_in(c, value, meta.get("box") or (meta.get("words_lines") or [None])[0])
            return
        figures = format_indian_amount(amount)
        _draw_in(c, f"{figures}/-" if "." not in figures else figures, meta.get("box"))
        _draw_words(c, amount_to_words(amount, prefix=meta.get("words_prefix", True)), meta.get("words_lines") or [])
    elif role == "date" and meta.get("parts") and re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        day, month, year = value.split("/")
        year = year[-2:] if meta.get("year_digits") == 2 else year
        for text, area in zip((day, month, year), meta["parts"]):
            area = dict(area)
            # Centre each part inside its slot
            size = _fit_size(text, "Helvetica-Bold", area["size"], area["x1"] - area["x0"])
            area["x0"] = area["x0"] + max(0.0, (area["x1"] - area["x0"] - stringWidth(text, "Helvetica-Bold", size)) / 2)
            _draw_in(c, text, area)
    else:
        _draw_in(c, value, meta.get("area"))


def render_filled_cheque(original_path: str, output_path: str, fields: list[dict]) -> bool:
    """Write confirmed values onto the original cheque (PDF or image) and save as PDF."""
    import pypdf
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader

    page_info = next(((f.get("position") or {}).get("cheque") or {}).get("page") for f in fields
                     if (f.get("position") or {}).get("cheque"))
    is_pdf = original_path.lower().endswith(".pdf")

    def draw_overlay(c):
        # Only the values go on a cheque: no stamps or watermarks
        c.setFillColorRGB(*INK_RGB)
        for f in fields:
            _draw_field(c, f)

    if is_pdf:
        reader = pypdf.PdfReader(original_path)
        writer = pypdf.PdfWriter(clone_from=reader)
        first = writer.pages[0]
        mb = first.mediabox
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=(float(mb.right), float(mb.top)))
        draw_overlay(c)
        c.save()
        buf.seek(0)
        first.merge_page(pypdf.PdfReader(buf).pages[0])
        with open(output_path, "wb") as fh:
            writer.write(fh)
        return True

    page_w, page_h = page_info["page_width"], page_info["page_height"]
    c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
    c.drawImage(ImageReader(ImageOps.exif_transpose(Image.open(original_path)).convert("RGB")), 0, 0, width=page_w, height=page_h)
    draw_overlay(c)
    c.save()
    return True
