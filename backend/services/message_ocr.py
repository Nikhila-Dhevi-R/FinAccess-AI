"""
Reading the text of a message from a screenshot OR a camera photo of a phone screen.

Photos of a screen are much harder than screenshots: the phone may be sideways or tilted, the screen
is surrounded by a desk, and text may be light-on-dark (dark mode, coloured chat bubbles) next to
dark-on-light areas, with glare and blur. This module:

1. picks the right orientation (0 / 90 / 180 / 270) by trying them on a small cleaned copy,
2. straightens small tilts,
3. normalises contrast LOCALLY, so light-on-dark and dark-on-light text both become dark-on-white,
4. sizes the image so letters are the height Tesseract reads best,
5. reads it several ways (different clean-ups / page modes) and keeps the most confident reading,
6. removes phone UI text ("Tap to load preview", timestamps, "Text message") but keeps the sender.

Everything happens in memory; images are piped to Tesseract over stdin and never written to disk.
"""

import csv
import io
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageFilter, ImageOps

TARGET_TEXT_HEIGHT = 34      # px height of a typical word box that Tesseract reads most reliably
WORK_WIDTH = 1800            # first-pass working width


class OcrUnavailable(Exception):
    pass


# ─── Tesseract ───────────────────────────────────────────────────────────────
def _tesseract_tsv(cmd: str, img: Image.Image, psm: str) -> list[dict]:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    proc = subprocess.run([cmd, "stdin", "stdout", "--psm", psm, "tsv"],
                          input=buf.getvalue(), capture_output=True, timeout=60)
    if proc.returncode != 0:
        return []
    rows = []
    for r in csv.DictReader(io.StringIO(proc.stdout.decode("utf-8", errors="replace")), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (r.get("text") or "").strip()
        try:
            conf = float(r.get("conf") or -1)
        except ValueError:
            continue
        if not text or conf < 0:
            continue
        rows.append({"text": text, "conf": conf, "top": int(r["top"]), "left": int(r["left"]),
                     "height": int(r["height"]), "width": int(r["width"]),
                     "line": (int(r["block_num"]), int(r["par_num"]), int(r["line_num"]))})
    return rows


def _score(words: list[dict]) -> float:
    """Confident, word-like characters: rewards real text, ignores noise read off the background."""
    total = 0.0
    for w in words:
        alnum = len(re.sub(r"[^A-Za-z0-9]", "", w["text"]))
        if alnum < 2:
            continue
        weight = 1.0 if w["conf"] >= 80 else 0.6 if w["conf"] >= 60 else 0.15 if w["conf"] >= 40 else 0.0
        total += alnum * weight
    return total


# ─── Image clean-up ──────────────────────────────────────────────────────────
def _local_normalise(gray: Image.Image, radius: float, mode: str = "both") -> Image.Image:
    """
    Dark-on-white everywhere: where the local background is dark (dark mode, dark bubbles),
    flip the polarity there only, then stretch contrast against the local background.
    """
    g = np.asarray(gray).astype(np.float32)
    small = gray.resize((max(1, gray.width // 4), max(1, gray.height // 4)), Image.BILINEAR)
    bg_small = small.filter(ImageFilter.GaussianBlur(max(1.0, radius / 4)))
    bg = np.asarray(bg_small.resize(gray.size, Image.BILINEAR)).astype(np.float32)
    # Ink = strong difference from the local background in EITHER direction, so light-on-dark text,
    # dark-on-light text and glare-brightened dark screens all read the same way. Where the background
    # is clearly light, only darker pixels count (and vice versa) to avoid doubling stroke edges.
    diff = g - bg
    if mode == "flip":  # decide polarity from the background: robust for evenly lit screens
        ink = np.where(bg < 120, np.clip(diff, 0, None), np.clip(-diff, 0, None))
    else:               # either direction: robust when glare brightens part of a dark screen
        ink = np.where(bg >= 170, np.clip(-diff, 0, None), np.where(bg <= 80, np.clip(diff, 0, None), np.abs(diff)))
    scale = np.percentile(ink[ink > 4], 92) if np.any(ink > 4) else 1.0
    out = 255 - np.clip(ink / max(scale, 8.0) * 255, 0, 255)
    return Image.fromarray(out.astype("uint8"))


def _binarise(norm: Image.Image) -> Image.Image:
    a = np.asarray(norm)
    hist = np.bincount(a.ravel(), minlength=256).astype(np.float64)
    # Otsu threshold
    total, sum_all = a.size, np.dot(np.arange(256), hist)
    best_t, best_var, w_b, sum_b = 128, -1.0, 0.0, 0.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0 or w_b == total:
            continue
        sum_b += t * hist[t]
        m_b, m_f = sum_b / w_b, (sum_all - sum_b) / (total - w_b)
        var = w_b * (total - w_b) * (m_b - m_f) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return Image.fromarray(np.where(a > best_t, 255, 0).astype("uint8"))


def _estimate_skew(img: Image.Image, max_angle: float = 12.0) -> float:
    small = img.resize((600, max(1, int(img.height * 600 / img.width))))
    mask = Image.fromarray(np.where(np.asarray(small) < 128, 255, 0).astype("uint8"))

    def sharpness(angle):
        rows = np.asarray(mask.rotate(angle, resample=Image.NEAREST)).sum(axis=1).astype(np.float64)
        return float(np.sum(np.diff(rows) ** 2))

    coarse = max(np.arange(-max_angle, max_angle + 0.01, 1.0), key=sharpness)
    fine = max(np.arange(coarse - 1.0, coarse + 1.01, 0.2), key=sharpness)
    return float(fine)


def _resize_width(img: Image.Image, width: int) -> Image.Image:
    if img.width == width:
        return img
    return img.resize((width, max(1, int(img.height * width / img.width))), Image.LANCZOS)


# ─── Text assembly / UI clean-up ─────────────────────────────────────────────
UI_LINES = re.compile(
    r"^(tap to load preview|text message|rcs message|sms|mms|imessage|delivered|read|sent|edited|"
    r"today|yesterday|now|\d{1,2}:\d{2}\s*(am|pm)?|.*\b(today|yesterday)\b,?\s*\d{1,2}:\d{2}\s*(am|pm)?|"
    r"(mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s.*\d{1,2}:\d{2}\s*(am|pm)?|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s*\d{1,2}:\d{2}\s*(am|pm)?)$",
    re.IGNORECASE)


def _repair_url(line: str) -> str:
    """Undo common OCR damage inside links: 'https://t jio/X', 'https://t.jio(X', 'https: //bit.ly/ X'."""
    m = re.search(r"https?\s*:\s*/\s*/\s*(.*)$", line, re.IGNORECASE)
    if not m:
        return line
    rest = m.group(1).strip()
    host_match = re.match(r"([A-Za-z0-9.\- ]+?)([/(|\[{)\\].*|$)", rest)
    host, path = (host_match.group(1), host_match.group(2)) if host_match else (rest, "")
    host = re.sub(r"\s+", ".", host.strip()).strip(".")       # a gap inside a domain is a lost dot
    path = re.sub(r"^[(|\[{)\\]", "/", path).replace(" ", "")  # a bracket right after the domain is a slash
    scheme = "https://" if line[m.start():m.start() + 5].lower() == "https" else "http://"
    return line[:m.start()] + scheme + host + path


def _assemble(words: list[dict]) -> str:
    lines = {}
    for w in words:
        if w["conf"] < 30 and len(re.sub(r"[^A-Za-z0-9]", "", w["text"])) < 3:
            continue  # noise read off borders / background
        lines.setdefault(w["line"], []).append(w)
    ordered = sorted(lines.values(), key=lambda ws: (min(w["top"] for w in ws), min(w["left"] for w in ws)))
    out = []
    for ws in ordered:
        # a real line has at least one confidently read word; background texture gives "se hs jj fir"
        def alnum(w):
            return len(re.sub(r"[^A-Za-z0-9]", "", w["text"]))

        if not any((w["conf"] >= 50 and alnum(w) >= 3) or (w["conf"] >= 80 and alnum(w) >= 2) or alnum(w) >= 10 for w in ws):
            continue
        text = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["left"])).strip()
        text = re.sub(r"\s*\(SMS/MMS\)\s*$", "", text, flags=re.IGNORECASE)
        sender = re.match(r"(?i)^texting with\s+(.*)$", text)
        if sender:
            text = sender.group(1).strip()
            if not re.search(r"\d{3}", text):
                continue  # "Texting with Payment" — a contact name, not a number
        if UI_LINES.match(text) or len(re.sub(r"[^A-Za-z0-9]", "", text)) < 2:
            continue
        out.append(_repair_url(text))
    return "\n".join(out)


# ─── Pipeline ────────────────────────────────────────────────────────────────
def read_text(img: Image.Image, cmd: str) -> str:
    img = ImageOps.exif_transpose(img).convert("L")
    work = _resize_width(img, WORK_WIDTH) if img.width > WORK_WIDTH or img.width < 900 else img

    with ThreadPoolExecutor(max_workers=4) as pool:
        # 1. Orientation: whichever rotation reads the most confident text
        norm = _local_normalise(work, radius=work.width * 0.04)
        probe = _resize_width(norm, 900)
        rotations = [0, 90, 270, 180]
        scores = list(pool.map(lambda a: _score(_tesseract_tsv(cmd, probe.rotate(a, expand=True), "11")), rotations))
        angle = rotations[int(np.argmax(scores))]
        if angle and scores[0] >= 0.8 * max(scores):
            angle = 0  # only rotate when clearly better
        if angle:
            img = img.rotate(angle, expand=True)
            work = _resize_width(img, WORK_WIDTH) if img.width > WORK_WIDTH or img.width < 900 else img
            norm = _local_normalise(work, radius=work.width * 0.04)

        # 2. Straighten
        skew = _estimate_skew(norm)
        if abs(skew) >= 0.6:
            img = img.rotate(skew, resample=Image.BICUBIC, expand=True, fillcolor=int(np.median(np.asarray(img))))
            work = _resize_width(img, WORK_WIDTH) if img.width > WORK_WIDTH or img.width < 900 else img
            norm = _local_normalise(work, radius=work.width * 0.04)

        # 3. Scale so that text is the size Tesseract likes (measured from a first reading)
        first = _tesseract_tsv(cmd, norm, "11")
        heights = [w["height"] for w in first if w["conf"] >= 60 and len(re.sub(r"[^A-Za-z0-9]", "", w["text"])) >= 3]
        if heights:
            factor = TARGET_TEXT_HEIGHT / float(np.median(heights))
            factor = min(3.0, max(0.5, factor))
            if abs(factor - 1) > 0.15:
                width = int(work.width * factor)
                src = img if img.width >= width else img
                work = _resize_width(src, width)
                norm = _local_normalise(work, radius=work.width * 0.04)

        # 4. Several readings; keep the most confident
        flip = _local_normalise(work, radius=work.width * 0.04, mode="flip")
        binary = _binarise(flip)
        gray = ImageOps.autocontrast(work.filter(ImageFilter.MedianFilter(3)), cutoff=1)
        if np.median(np.asarray(gray)) < 110:
            gray = ImageOps.invert(gray)
        candidates = [(norm, "6"), (flip, "6"), (norm, "4"), (flip, "4"), (binary, "6"), (norm, "11"), (gray, "6")]
        readings = list(pool.map(lambda c: _tesseract_tsv(cmd, c[0], c[1]), candidates))

    best = max(readings, key=_score)
    return _assemble(best)
