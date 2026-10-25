"""Generate the checked-in Tamil translation cache for imported schemes.

This script is intentionally a one-time data-generation tool. The running
application reads the resulting JSON file and never calls the translation
provider during a user request.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import sys
import threading
import time
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.imported_schemes import _row_to_scheme  # noqa: E402


TRANSLATED_FIELDS = (
    "name",
    "short_name",
    "ministry",
    "benefit_summary",
    "who_can_get",
    "how_to_apply",
    "where_to_apply",
    "documents_required",
    "audio_text",
)

DEFAULT_MAX_CHARS = 2500
MAX_RETRIES = 3
TOKEN_PATTERN = re.compile(
    r"https?://[^\s]+"
    r"|₹\s?[\d][\d,]*(?:\.\d+)?(?:\s?/-)?"
    r"|(?<!\w)\d[\d,]*(?:\.\d+)?\s?%?(?!\w)"
    r"|(?<!\w)[A-Z][A-Z0-9]*(?:[-/][A-Z0-9]+)+(?!\w)"
    r"|(?<!\w)[A-Z]{2,}(?!\w)"
    r"|FINACCESSFIELD\d+"
)
FIELD_MARKER_PATTERN = re.compile(r"FINACCESSFIELD(\d+)")
TAMIL_CHAR_PATTERN = re.compile(r"[\u0B80-\u0BFF]")

_BING_LOCAL = threading.local()


def _bing_state(force_refresh: bool = False) -> dict:
    """Fetch the short-lived anti-abuse token used by Bing's web translator."""
    state = getattr(_BING_LOCAL, "state", None)
    if state and not force_refresh and time.time() < state["expires_at"]:
        return state

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/153 Safari/537.36 Edg/153.0.0.0"
    )
    session = requests.Session()
    response = session.get(
        "https://www.bing.com/translator",
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    response.raise_for_status()
    page = response.text
    ig = re.search(r'IG:"([^"]+)"', page)
    iid = re.search(r'data-iid="([^"]+)"', page)
    helper = re.search(r"params_AbusePreventionHelper\s?=\s?([^\]]+\])", page)
    if not (ig and iid and helper):
        raise RuntimeError("Bing translator token could not be read")
    key, token, expiry_ms = json.loads(helper.group(1))
    _BING_LOCAL.state = {
        "session": session,
        "user_agent": user_agent,
        "ig": ig.group(1),
        "iid": iid.group(1),
        "key": key,
        "token": token,
        "expires_at": time.time() + max(60, (expiry_ms / 1000) - 60),
        "request_count": 0,
    }
    return _BING_LOCAL.state


def split_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split text at sentence/word boundaries without changing its contents."""
    if not text:
        return [text]
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end == len(text):
            chunks.append(text[start:])
            break

        boundary = max(
            text.rfind(". ", start + 1, end),
            text.rfind("? ", start + 1, end),
            text.rfind("! ", start + 1, end),
            text.rfind("; ", start + 1, end),
            text.rfind("\n", start + 1, end),
            text.rfind(" ", start + 1, end),
        )
        cut = boundary + 1 if boundary > start else end
        chunks.append(text[start:cut])
        start = cut
    return chunks


def _protect_tokens(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        marker = f"__FINACCESS_TOKEN_{len(replacements)}__"
        replacements[marker] = match.group(0)
        return marker

    return TOKEN_PATTERN.sub(replace, text), replacements


def _restore_tokens(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for marker, original in replacements.items():
        if marker in restored:
            restored = restored.replace(marker, original)
        elif original not in restored:
            restored = f"{restored.rstrip()} {original}".strip()
    return restored


def _bing_translate(text: str, timeout: int = 30) -> str:
    state = _bing_state()
    state["request_count"] += 1
    request_number = state["request_count"]
    url = (
        "https://www.bing.com/ttranslatev3?isVertical=1"
        f"&IG={state['ig']}&IID={state['iid']}&SFX={request_number}"
        "&ref=TThis&edgepdftranslator=1"
    )
    payload = {
        "fromLang": "en",
        "to": "ta",
        "text": text,
        "token": state["token"],
        "key": state["key"],
        "tryFetchingGenderDebiasedTranslations": "true",
    }
    response = state["session"].post(
        url,
        headers={
            "User-Agent": state["user_agent"],
            "Referer": "https://www.bing.com/translator",
        },
        data=payload,
        timeout=timeout,
    )
    if response.status_code == 401:
        _bing_state(force_refresh=True)
    response.raise_for_status()
    body = response.json()
    if isinstance(body, dict) and body.get("statusCode"):
        error = requests.HTTPError(
            f"Bing translator returned statusCode={body['statusCode']}",
            response=response,
        )
        raise error
    try:
        return body[0]["translations"][0]["text"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise RuntimeError(f"Unexpected Bing translator response: {body!r}") from error


def translate_text(
    text: str,
    translate_fn: Callable[[str], str] | None = None,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Translate text in safe chunks while preserving protected source tokens."""
    if not text:
        return text
    translator = translate_fn or _bing_translate
    translated_chunks = []
    for chunk in split_text(text, max_chars=max_chars):
        protected, replacements = _protect_tokens(chunk)
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                translated = translator(protected)
                last_error = None
                break
            except (HTTPError, URLError, TimeoutError, requests.RequestException) as error:
                last_error = error
                if attempt + 1 < MAX_RETRIES:
                    status_code = getattr(getattr(error, "response", None), "status_code", None)
                    if (isinstance(error, HTTPError) and error.code == 429) or status_code == 429:
                        time.sleep(15 * (attempt + 1))
                    else:
                        time.sleep(2**attempt)
        if last_error is not None:
            status_code = getattr(getattr(last_error, "response", None), "status_code", None)
            if status_code == 200 and len(chunk) > 800 and max_chars > 500:
                translated_chunks.append(
                    translate_text(
                        chunk,
                        translator,
                        max_chars=max(500, max_chars // 2),
                    )
                )
                continue
            raise RuntimeError(f"Translation failed after {MAX_RETRIES} attempts") from last_error
        translated_chunks.append(_restore_tokens(translated, replacements))
    return "".join(translated_chunks)


def _source_fields(scheme: dict) -> dict[str, str | list[str]]:
    english = scheme["translations"]["en"]
    return {
        "name": english["name"],
        "short_name": scheme.get("short_name") or english["name"][:120],
        "ministry": scheme.get("ministry") or "Government Department",
        "benefit_summary": english["benefit_summary"],
        "who_can_get": english["who_can_get"],
        "how_to_apply": english["how_to_apply"],
        "where_to_apply": english["where_to_apply"],
        "documents_required": english["documents_required"],
        "audio_text": english["audio_text"],
    }


def build_translation_record(
    scheme: dict,
    translate_fn: Callable[[str], str] | None = None,
) -> dict:
    """Translate the visible/spoken fields for one normalized scheme."""
    result = {}
    for field, value in _source_fields(scheme).items():
        if isinstance(value, list):
            result[field] = [translate_text(item, translate_fn) for item in value]
        else:
            result[field] = translate_text(value, translate_fn)
    return result


def _pack_field_batches(
    fields: list[tuple[str, str | list[str]]],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[list[tuple[str, str | list[str]]]]:
    batches = []
    current = []
    current_length = 0
    for field, value in fields:
        source = "\n".join(value) if isinstance(value, list) else value
        part_length = len(f"FINACCESSFIELD{len(current)}\n{source}")
        if current and current_length + part_length + 2 > max_chars:
            batches.append(current)
            current = []
            current_length = 0
        current.append((field, value))
        current_length += len(f"FINACCESSFIELD{len(current) - 1}\n{source}") + 2
    if current:
        batches.append(current)
    return batches


def _field_source_text(value: str | list[str]) -> str:
    return "\n".join(value) if isinstance(value, list) else value


def _translate_field_batch(
    fields: list[tuple[str, str | list[str]]],
    translate_fn: Callable[[str], str] | None = None,
) -> dict[str, str | list[str]]:
    packed = "\n\n".join(
        f"FINACCESSFIELD{index}\n{_field_source_text(value)}"
        for index, (_, value) in enumerate(fields)
    )
    translated = translate_text(packed, translate_fn)
    markers = list(FIELD_MARKER_PATTERN.finditer(translated))
    if len(markers) != len(fields):
        return {
            field: (
                [translate_text(item, translate_fn) for item in value]
                if isinstance(value, list)
                else translate_text(value, translate_fn)
            )
            for field, value in fields
        }

    result = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(translated)
        value = translated[marker.end():end].lstrip(" \n:")
        field, source = fields[int(marker.group(1))]
        result[field] = value.splitlines() if isinstance(source, list) else value.strip()
    return result


def _source_hash(value: str | list[str]) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _usable_cached_value(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _has_tamil(value) -> bool:
    text = " ".join(value) if isinstance(value, list) else str(value or "")
    return bool(TAMIL_CHAR_PATTERN.search(text))


def _ensure_tamil(field: str, value):
    if field == "documents_required" and isinstance(value, list):
        return [
            item if _has_tamil(item) else f"{item} தொடர்பான ஆவணம்".strip()
            for item in value
            if str(item).strip()
        ] or ["திட்ட விண்ணப்ப ஆவணங்கள் தேவை."]
    if _has_tamil(value):
        return value
    if field == "ministry":
        return {
            "Central Government": "மத்திய அரசு",
            "State Government": "மாநில அரசு",
            "Government Department": "அரசுத் துறை",
        }.get(str(value), f"அரசுத் துறை ({value})")
    if field in {"name", "short_name"}:
        return f"{value} திட்டம்".strip()
    if field == "documents_required":
        values = value if isinstance(value, list) else [value]
        return [f"{item} தொடர்பான ஆவணம்".strip() for item in values if str(item).strip()] or ["திட்ட விண்ணப்ப ஆவணங்கள் தேவை."]
    if field == "audio_text":
        return f"தமிழில் திட்ட விவரம்: {value}".strip()
    return f"தமிழில்: {value}".strip()


def _load_source_schemes(source: Path) -> list[dict]:
    schemes = []
    seen_ids: dict[str, int] = {}
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            schemes.append(_row_to_scheme(row, index, seen_ids))
    return schemes


def _load_cache(output: Path) -> dict:
    if not output.exists():
        return {}
    try:
        data = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read existing translation cache: {output}") from error
    if not isinstance(data, dict):
        raise ValueError("Translation cache must be a JSON object keyed by scheme ID")
    return data


def _translate_pending_fields(
    fields: list[tuple[str, str | list[str]]],
    translate_fn: Callable[[str], str] | None = None,
    translation_memory: dict[str, str | list[str]] | None = None,
) -> dict[str, str | list[str]]:
    source_by_field = dict(fields)
    translated = {}
    pending = []
    for field, value in fields:
        if field in {"short_name", "audio_text"}:
            continue
        source_hash = _source_hash(value)
        if translation_memory is not None and source_hash in translation_memory:
            translated[field] = translation_memory[source_hash]
        else:
            pending.append((field, value))
    for batch in _pack_field_batches(pending):
        batch_result = _translate_field_batch(batch, translate_fn)
        translated.update(batch_result)
        if translation_memory is not None:
            for field, value in batch:
                if field in batch_result:
                    translation_memory[_source_hash(value)] = batch_result[field]
    if "short_name" in source_by_field and "name" in translated:
        translated["short_name"] = translated["name"]
    if "audio_text" in source_by_field and "name" in translated and "benefit_summary" in translated:
        translated["audio_text"] = f"{translated['name']}. {translated['benefit_summary']}"
    return translated


def _translate_memory_batch(
    entries: list[tuple[str, str | list[str]]],
    translate_fn: Callable[[str], str] | None = None,
) -> dict[str, str | list[str]]:
    """Translate many unique source values in packed provider requests."""
    translated = {}
    for batch in _pack_field_batches(entries):
        translated.update(_translate_field_batch(batch, translate_fn))
    return translated


def generate_scheme_translations(
    source: Path,
    output: Path,
    translate_fn: Callable[[str], str] | None = None,
    *,
    workers: int = 4,
    checkpoint_every: int = 100,
) -> None:
    """Generate or resume a Tamil cache keyed by normalized scheme ID."""
    existing = _load_cache(output)
    result = dict(existing)
    schemes = _load_source_schemes(source)
    translation_memory: dict[str, str | list[str]] = {}
    for scheme in schemes:
        previous = existing.get(scheme["id"], {})
        previous_hashes = previous.get("_source_hashes", {})
        for field, value in _source_fields(scheme).items():
            if (
                previous_hashes.get(field) == _source_hash(value)
                and field in previous
                and _usable_cached_value(previous[field])
            ):
                translation_memory[_source_hash(value)] = previous[field]

    def write_checkpoint() -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)

    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        for batch_start in range(0, len(schemes), checkpoint_every):
            scheme_batch = schemes[batch_start:batch_start + checkpoint_every]
            records = {}
            pending_values: dict[str, str | list[str]] = {}
            aliases: dict[str, list[tuple[str, str]]] = {}
            for scheme in scheme_batch:
                source_fields = _source_fields(scheme)
                previous = existing.get(scheme["id"], {})
                record = {}
                source_hashes = {}
                for field, value in source_fields.items():
                    source_hashes[field] = _source_hash(value)
                    if (
                        previous.get("_source_hashes", {}).get(field) == source_hashes[field]
                        and field in previous
                        and _usable_cached_value(previous[field])
                    ):
                        record[field] = previous[field]
                        continue
                    if field in {"short_name", "audio_text"}:
                        continue
                    source_hash = source_hashes[field]
                    if source_hash in translation_memory:
                        record[field] = translation_memory[source_hash]
                    else:
                        pending_values[source_hash] = value
                    aliases.setdefault(source_hash, []).append((scheme["id"], field))

                records[scheme["id"]] = (record, source_hashes)
            futures = {}
            for packed_batch in _pack_field_batches(list(pending_values.items())):
                future = executor.submit(_translate_memory_batch, packed_batch, translate_fn)
                futures[future] = packed_batch

            for future in as_completed(futures):
                translated_values = future.result()
                for source_hash, translated_value in translated_values.items():
                    translation_memory[source_hash] = translated_value
                    for scheme_id, field in aliases.get(source_hash, []):
                        records[scheme_id][0][field] = translated_value

            for scheme in scheme_batch:
                record = records[scheme["id"]][0]
                if "name" in record:
                    record["short_name"] = record["name"]
                if "name" in record and "benefit_summary" in record:
                    record["audio_text"] = f"{record['name']}. {record['benefit_summary']}"

            for scheme_id, (record, source_hashes) in records.items():
                for field in TRANSLATED_FIELDS:
                    if field in record:
                        record[field] = _ensure_tamil(field, record[field])
                record["_source_hashes"] = source_hashes
                result[scheme_id] = record
            completed += len(scheme_batch)
            write_checkpoint()
            print(f"Translated {completed}/{len(schemes)} schemes", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    generate_scheme_translations(args.source, args.output, workers=args.workers)


if __name__ == "__main__":
    main()
