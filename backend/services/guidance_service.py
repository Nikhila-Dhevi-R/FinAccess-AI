"""
Financial Guidance Service — a conversational money guide in English, Hindi and Tamil.

The server is stateless: every reply returns a small `context` (last topic, topics already discussed, pending
yes/no offer, calculator in progress, what the user told us about themselves, suggestion ids). The browser
keeps the conversation and sends `context` (and recent `history`) back with the next question, so the bot
can understand follow-ups like "what documents?", "yes", "2", or "5 lakh" without going round in circles.

Answers come from the curated knowledge base in finance_kb.py and, for named government schemes, from the
scheme catalogue used by the Schemes page.
"""

import math
import re
from typing import Optional

from services import finance_kb as kb
from services.schemes_data import SCHEMES_CATALOGUE
from services.scheme_finder import SCHEME_TAGS, search as search_schemes

LANGS = ("en", "hi", "ta")
MAX_DISCUSSED = 30
STRONG, WEAK = 3.0, 1.0
_SCHEMES_BY_ID = {s["id"]: s for s in SCHEMES_CATALOGUE}

_INDIC_DIGITS = str.maketrans("०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯", "01234567890123456789")


def _normalise(text: str) -> str:
    text = (text or "").translate(_INDIC_DIGITS).lower().replace("़", "")  # nukta: ज़ == ज
    text = re.sub(r"(?<=\d),(?=\d)", "", text)                                   # 50,000 → 50000
    text = re.sub(r"[^\wऀ-ॿ஀-௿%*#.₹ ]+", " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)                              # keep decimal points only
    return re.sub(r"\s+", " ", text).strip()


def _compile(keyword: str):
    k = _normalise(keyword)
    if not k:
        return None
    if k.isascii():
        return re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?:s|es)?(?![a-z0-9])")
    return k


def _hit(pattern, text: str) -> bool:
    return bool(pattern.search(text)) if hasattr(pattern, "search") else pattern in text


def _word_list(words):
    return [p for p in (_compile(w) for w in words) if p is not None]


_TOPIC_PATTERNS = {
    tid: [(p, STRONG + 0.5 * (len(w.split()) - 1), w) for w, p in ((w, _compile(w)) for w in t["strong"]) if p]
    + [(p, WEAK, w) for w, p in ((w, _compile(w)) for w in t["weak"]) if p]
    for tid, t in kb.TOPICS.items()
}
_FACETS = {name: _word_list(words) for name, words in kb.FACETS.items()}
_PROFILE = {key: _word_list(words) for key, words in kb.PROFILE_WORDS.items()}
_CALC_TRIGGERS = {key: _word_list(words) for key, words in kb.CALC_TEXT["triggers"].items()}
_SETS = {name: _word_list(getattr(kb, name)) for name in
         ("YES_WORDS", "NO_WORDS", "MORE_WORDS", "CANCEL_WORDS", "THANKS_WORDS", "BYE_WORDS", "GREET_WORDS", "HELP_WORDS", "HUMAN_WORDS")}
# ascii single-word strong keywords for typo tolerance ("pensoin", "insurence")
_TYPO_WORDS = [(w.lower(), tid) for tid, t in kb.TOPICS.items() for w in t["strong"] + t["weak"]
               if w.isascii() and " " not in w and len(w) >= 5]


def _any(name: str, text: str) -> bool:
    return any(_hit(p, text) for p in _SETS[name])


def _close(a: str, b: str) -> bool:
    """Edit distance ≤ 1 (one typo or swapped neighbours)."""
    if abs(len(a) - len(b)) > 1 or a == b:
        return a == b
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def _score_topics(text: str) -> dict:
    scores = {}
    for tid, patterns in _TOPIC_PATTERNS.items():
        score, seen = 0.0, set()
        for pattern, weight, word in patterns:
            if _hit(pattern, text):
                # a long keyword already counted covers its shorter parts ("lost card" vs "card")
                if any(word.lower() in s for s in seen):
                    continue
                score += weight
                seen.add(word.lower())
        if score:
            scores[tid] = score
    if not scores:
        for token in set(text.split()):
            if len(token) >= 5 and token.isascii():
                for word, tid in _TYPO_WORDS:
                    if _close(token, word):
                        scores[tid] = max(scores.get(tid, 0), 2.0)
    return scores


def _facets(text: str) -> list:
    return [name for name, patterns in _FACETS.items() if any(_hit(p, text) for p in patterns)]


def _linked(tid: str, facets: list) -> Optional[str]:
    links = kb.TOPICS[tid]["links"]
    for name in reversed(facets):          # the more specific facets (claim, cost) are listed last
        if name in links:
            return links[name]
    return None


def _profile_from(text: str) -> list:
    found = [key for key, patterns in _PROFILE.items() if any(_hit(p, text) for p in patterns)]
    age = re.search(r"(?:age|umar|umra|उम्र|उमर|வயது)\D{0,12}(\d{2})|(\d{2})\s*(?:years? old|yrs? old|saal ka|saal ki|sal ka|sal ki|साल का|साल की|साल है|வயது)", text)
    if age:
        years = int(age.group(1) or age.group(2))
        if years >= 60 and "senior" not in found:
            found.append("senior")
    return found


# ─── Numbers for the calculators ──────────────────────────────────────────────

_MULT = [
    (r"crore|cr|करोड़|करोड|கோடி", 1e7),
    (r"lakhs?|lacs?|lac|lakh|लाख|லட்சம்|லட்ச", 1e5),
    (r"thousand|hazaa?r|k|हजार|ஆயிரம்", 1e3),
]
_RATE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent|pratishat|प्रतिशत|फीसदी|சதவீத|சதவிகித)(?![a-z])")
_YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|saal|sal|varsh|वर्ष|साल|ஆண்டு|வருட)(?![a-z])")
_MONTHS_RE = re.compile(r"(\d+)\s*(?:months?|mahine|mahina|महीने|महीना|மாத)(?![a-z])")
_AMOUNT_RE = re.compile(r"₹?\s*(\d+(?:\.\d+)?)\s*(" + "|".join(m for m, _ in _MULT) + r")?(?![\w%])")


def _extract_numbers(text: str, asking: Optional[str]) -> dict:
    """Pull amount / rate / months out of a message. Unit-less numbers fill the slot being asked."""
    found, rest = {}, text
    m = _RATE_RE.search(rest)
    if m:
        found["rate"] = float(m.group(1))
        rest = rest[:m.start()] + " " + rest[m.end():]
    m = _YEARS_RE.search(rest)
    if m:
        found["months"] = round(float(m.group(1)) * 12)
        rest = rest[:m.start()] + " " + rest[m.end():]
    else:
        m = _MONTHS_RE.search(rest)
        if m:
            found["months"] = int(m.group(1))
            rest = rest[:m.start()] + " " + rest[m.end():]
    for m in _AMOUNT_RE.finditer(rest):
        value = float(m.group(1))
        unit = m.group(2)
        if unit:
            mult = next(v for pat, v in _MULT if re.fullmatch(pat, unit))
            found.setdefault("amount", value * mult)
        elif asking == "rate" and "rate" not in found and 0 < value <= 50:
            found["rate"] = value
        elif asking == "years" and "months" not in found and 0 < value <= 480:
            found["months"] = round(value * 12) if value <= 40 else int(value)
        elif value >= 1000 or asking == "amount":
            found.setdefault("amount", value)
    if "amount" in found and not (1 <= found["amount"] <= 1e10):
        found.pop("amount")
    if "rate" in found and not (0 <= found["rate"] <= 60):
        found.pop("rate")
    if "months" in found and not (1 <= found["months"] <= 600):
        found.pop("months")
    return found


def _inr(value: float) -> str:
    n = int(round(value))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join(re.findall(r"\d{1,2}(?=(?:\d{2})*$)", head))
        s = head + "," + tail
    return ("-₹" if n < 0 else "₹") + s


def _period(months: int, li: int) -> str:
    if months % 12 == 0:
        years = months // 12
        return kb.CALC_TEXT["unit_year"][li] if years == 1 else kb.CALC_TEXT["unit_years"][li].format(n=years)
    return kb.CALC_TEXT["unit_months"][li].format(n=months)


def _rate_text(rate: float) -> str:
    return f"{rate:g}"


def _calc_result(kind: str, slots: dict, li: int) -> str:
    p, rate, months = slots["amount"], slots["rate"], slots["months"]
    if kind == "emi":
        r = rate / 12 / 100
        emi = p / months if r == 0 else p * r * (1 + r) ** months / ((1 + r) ** months - 1)
        total = emi * months
        return kb.CALC_TEXT["emi"]["result"][li].format(
            p=_inr(p), r=_rate_text(rate), n=_period(months, li), emi=_inr(emi), total=_inr(total), interest=_inr(total - p))
    total = p * (1 + rate / 400) ** (4 * months / 12)
    return kb.CALC_TEXT["fd"]["result"][li].format(
        p=_inr(p), r=_rate_text(rate), n=_period(months, li), total=_inr(total), interest=_inr(total - p))


def _next_slot(slots: dict) -> Optional[str]:
    if "amount" not in slots:
        return "amount"
    if "rate" not in slots:
        return "rate"
    if "months" not in slots:
        return "years"
    return None


# ─── Helpers for building replies ─────────────────────────────────────────────

def _title(tid: str, li: int) -> str:
    if tid in kb.TOPICS:
        return kb.TOPICS[tid]["title"][LANGS[li]]
    if tid in kb.CALC_TEXT["title"]:
        return kb.CALC_TEXT["title"][tid][li]
    return tid


def _first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?।])(\s|$)", text)
    return m.group(1) if m else text


def _scheme_name(sid: str, lang: str) -> str:
    s = _SCHEMES_BY_ID[sid]
    return s["translations"].get(lang, s["translations"]["en"])["name"]


def _schemes_for_profile(profile: list, lang: str, limit: int = 4) -> list:
    names = []
    for audience in profile:
        for sid, (audiences, _needs) in SCHEME_TAGS.items():
            if audience in audiences and sid in _SCHEMES_BY_ID:
                name = _scheme_name(sid, lang)
                if name not in names:
                    names.append(name)
            if len(names) >= limit:
                return names
    return names


def _profile_label(profile: list, li: int) -> str:
    return ", ".join(kb.PROFILE_LABELS[p][li] for p in profile if p in kb.PROFILE_LABELS)


def _clean_slots(slots) -> dict:
    clean = {}
    for key in ("amount", "rate", "months"):
        value = (slots or {}).get(key) if isinstance(slots, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            clean[key] = value
    return clean


def _clean_awaiting(awaiting):
    if not isinstance(awaiting, dict):
        return None
    if awaiting.get("type") == "yes_no" and (awaiting.get("yes") in kb.TOPICS or awaiting.get("yes") in kb.CALC_TEXT["title"]):
        return {"type": "yes_no", "yes": awaiting["yes"]}
    if awaiting.get("type") == "calc" and awaiting.get("calc") in ("emi", "fd"):
        ask = awaiting.get("ask") if awaiting.get("ask") in ("amount", "rate", "years") else None
        return {"type": "calc", "calc": awaiting["calc"], "slots": _clean_slots(awaiting.get("slots")), "ask": ask}
    return None


def _fresh_context(context: Optional[dict], history: Optional[list]) -> dict:
    ctx = dict(context) if isinstance(context, dict) else {}
    clean = {
        "last_topic": ctx.get("last_topic") if ctx.get("last_topic") in kb.TOPICS else None,
        "discussed": [t for t in (ctx.get("discussed") or []) if t in kb.TOPICS][-MAX_DISCUSSED:],
        "suggestions": [t for t in (ctx.get("suggestions") or []) if t in kb.TOPICS or t in kb.CALC_TEXT["title"]][:6],
        "awaiting": _clean_awaiting(ctx.get("awaiting")),
        "profile": [p for p in (ctx.get("profile") or []) if p in kb.PROFILE_WORDS],
        "misses": int(ctx.get("misses") or 0) if str(ctx.get("misses") or 0).isdigit() else 0,
        "last_scheme": ctx.get("last_scheme") if ctx.get("last_scheme") in _SCHEMES_BY_ID else None,
    }
    # No context sent (older client, or restored chat): recover the thread from the history
    if not clean["last_topic"] and history:
        for msg in reversed(history[-20:]):
            topic = msg.get("topic") if isinstance(msg, dict) else None
            if topic in kb.TOPICS:
                clean["last_topic"] = clean["last_topic"] or topic
                if topic not in clean["discussed"]:
                    clean["discussed"].insert(0, topic)
    return clean


def _pick_suggestions(ctx: dict, li: int, around: Optional[str] = None, first: Optional[str] = None) -> list:
    ids = []
    if first:
        ids.append(first)
    pool = []
    profile_topics = [t for p in ctx["profile"] for t in kb.PROFILE_TOPICS.get(p, [])]
    if around == "schemes_general":
        pool += profile_topics
    if around and around in kb.TOPICS:
        pool += kb.TOPICS[around]["related"]
    pool += profile_topics
    pool += kb.MENU_TOPICS
    for tid in pool:
        if tid not in ids and tid not in ctx["discussed"] and tid != around:
            ids.append(tid)
        if len(ids) >= 3:
            break
    ctx["suggestions"] = ids
    return [_title(t, li) for t in ids]


def _reply(text: str, ctx: dict, li: int, intent: str, topic: Optional[str] = None, suggestions=None, sources=None) -> dict:
    return {
        "answer": text.strip(),
        "answer_audio_text": text.strip(),
        "intent": intent,
        "topic": topic,
        "sources": sources if sources is not None else (["FinAccess AI Knowledge Base"] if topic else []),
        "follow_up_suggestions": suggestions or [],
        "context": ctx,
    }


def _answer_topic(tid: str, ctx: dict, li: int, prefix: str = "") -> dict:
    lang = LANGS[li]
    topic = kb.TOPICS[tid]
    base = topic["answer"][lang]
    ctx["misses"] = 0
    ctx["awaiting"] = None
    ctx["last_scheme"] = None

    if tid == "schemes_general" and ctx["profile"]:
        names = _schemes_for_profile(ctx["profile"], lang)
        if names:
            base = kb.PHRASES["schemes_for_you"][li].format(p=_profile_label(ctx["profile"], li), list=", ".join(names))

    offer_target = None
    if tid == ctx["last_topic"]:
        # Asked the same thing again: don't repeat the whole answer — summarise and move the conversation on
        nxt = next((r for r in topic["related"] if r not in ctx["discussed"]), topic["related"][0] if topic["related"] else None)
        text = kb.PHRASES["again_short"][li] + _first_sentence(base)
        if nxt:
            text += " " + kb.PHRASES["next_offer"][li].format(t=_title(nxt, li))
            offer_target = nxt
    else:
        text = (kb.PHRASES["as_mentioned"][li] if tid in ctx["discussed"] else "") + base
        offer = topic.get("offer")
        if offer and offer[0] not in ctx["discussed"]:
            text += " " + offer[1][li]
            offer_target = offer[0]

    if offer_target:
        ctx["awaiting"] = {"type": "yes_no", "yes": offer_target}
    if tid in ctx["discussed"]:
        ctx["discussed"].remove(tid)
    ctx["discussed"] = (ctx["discussed"] + [tid])[-MAX_DISCUSSED:]
    ctx["last_topic"] = tid
    first = offer_target if offer_target in kb.CALC_TEXT["title"] else None
    suggestions = _pick_suggestions(ctx, li, around=tid, first=first)
    return _reply(prefix + text, ctx, li, intent=topic["cat"], topic=tid, suggestions=suggestions)


def _start_calc(kind: str, ctx: dict, li: int, text: str, prefix: str = "") -> dict:
    slots = _extract_numbers(text, None)
    ctx["awaiting"] = {"type": "calc", "calc": kind, "slots": slots}
    ctx["misses"] = 0
    return _continue_calc(ctx, li, prefix + kb.CALC_TEXT[kind]["start"][li])


def _continue_calc(ctx: dict, li: int, prefix: str = "") -> dict:
    state = ctx["awaiting"]
    kind, slots = state["calc"], state["slots"]
    slot = _next_slot(slots)
    if slot is None:
        ctx["awaiting"] = None
        # keep the numbers so "what about 5 years?" can recalculate
        ctx["last_calc"] = {"calc": kind, "slots": slots}
        text = prefix + _calc_result(kind, slots, li)
        topic = "emi" if kind == "emi" else "fd"
        if topic not in ctx["discussed"]:
            ctx["discussed"] = (ctx["discussed"] + [topic])[-MAX_DISCUSSED:]
        ctx["last_topic"] = topic
        return _reply(text, ctx, li, intent="calculator", topic=topic,
                      suggestions=_pick_suggestions(ctx, li, around=topic), sources=["FinAccess AI calculator"])
    state["ask"] = slot
    return _reply(prefix + kb.CALC_TEXT[kind][slot][li], ctx, li, intent="calculator",
                  topic="emi" if kind == "emi" else "fd", suggestions=[], sources=[])


def _menu(ctx: dict, li: int, text: str, intent: str = "general") -> dict:
    ctx["awaiting"] = None
    ids = [t for t in kb.MENU_TOPICS if t not in ctx["discussed"]][:6] or kb.MENU_TOPICS[:6]
    ctx["suggestions"] = ids
    return _reply(text, ctx, li, intent=intent, suggestions=[_title(t, li) for t in ids])


def _scheme_answer(sid: str, ctx: dict, li: int) -> dict:
    lang = LANGS[li]
    s = _SCHEMES_BY_ID[sid]
    tr = s["translations"].get(lang, s["translations"]["en"])
    parts = [f"{tr['name']}: {tr.get('benefit_summary', '')}"]
    if tr.get("who_can_get"):
        parts.append(kb.PHRASES["scheme_who"][li] + tr["who_can_get"])
    if tr.get("how_to_apply"):
        parts.append(kb.PHRASES["scheme_how"][li] + tr["how_to_apply"])
    if s.get("helpline"):
        parts.append(kb.PHRASES["scheme_help"][li] + s["helpline"])
    text = " ".join(p.strip().rstrip(".।") + ("।" if lang == "hi" else ".") for p in parts if p.strip())
    ctx["awaiting"] = None
    ctx["misses"] = 0
    ctx["last_topic"] = None
    ctx["last_scheme"] = sid
    return _reply(text, ctx, li, intent="schemes", topic=None,
                  suggestions=_pick_suggestions(ctx, li, around="schemes_general"), sources=["Government scheme catalogue"])


_SCHEME_FACET_FIELDS = {"docs": ["documents_required"], "how": ["how_to_apply", "where_to_apply"], "eligibility": ["who_can_get"],
                        "cost": ["benefit_summary"], "claim": ["how_to_apply"]}


def _scheme_followup(sid: str, facets: list, ctx: dict, li: int) -> Optional[dict]:
    lang = LANGS[li]
    s = _SCHEMES_BY_ID[sid]
    tr = s["translations"].get(lang, s["translations"]["en"])
    for name in reversed(facets):
        values = []
        for field in _SCHEME_FACET_FIELDS.get(name, []):
            value = tr.get(field)
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            if value:
                values.append(str(value).strip())
        if values:
            ctx["awaiting"] = None
            ctx["misses"] = 0
            text = kb.PHRASES["about_that"][li].format(t=tr["name"]) + " ".join(values)
            return _reply(text, ctx, li, intent="schemes", topic=None,
                          suggestions=_pick_suggestions(ctx, li, around="schemes_general"), sources=["Government scheme catalogue"])
    return None


_GENERIC_SCHEME_WORDS = {"pm", "pradhan", "mantri", "yojana", "yojna", "scheme", "national", "card", "pension", "bima", "kisan", "mission",
                         "the", "for", "and", "of", "india", "bharat", "rashtriya", "abhiyan", "programme", "program", "loan", "credit", "insurance",
                         "savings", "account", "women", "woman", "girl", "child", "senior", "citizen", "citizens", "health", "house", "housing",
                         "farmer", "farmers", "employment", "guarantee", "free", "fund", "nidhi", "samman", "suraksha", "jeevan", "atal", "life"}


def _scheme_words(s: dict) -> set:
    names = [s["id"].replace("_", " "), s.get("short_name", "")] + [t.get("name", "") for t in s["translations"].values()]
    words = set()
    for name in names:
        for w in _normalise(re.sub(r"[()]", " ", name)).split():
            if len(w) >= 4 and w not in _GENERIC_SCHEME_WORDS and not w.isdigit():
                words.add(w)
    return words


_SCHEME_WORDS = {sid: _scheme_words(s) for sid, s in _SCHEMES_BY_ID.items()}
# words shared by several scheme names (योजना, திட்டம், प्रधानमंत्री …) don't identify a scheme
_WORD_DF = {}
for _words in _SCHEME_WORDS.values():
    for _w in _words:
        _WORD_DF[_w] = _WORD_DF.get(_w, 0) + 1
# …and only proper names identify a scheme — ordinary words (more, help, इलाज, வீடு) must not
_SCHEME_NAME_WORDS = set("""
aicte antyodaya arogya atmanirbhar aushadhi awaas ayushman bachao bhartiya bijli bocw cgtmse dayal dbtl deen dialysis drip eshram
fasal garib grameen gramin gramodyog ignoaps ignwps indira indradhanush janaushadhi jyoti kalyan kaushalya krishi kusum kvic lakhpati
maan mahatma matric matru maternity mgnrega mssc mudra niwas nmms nsap padhao pahal pariyojana pmay pmbjp pmegp pmfby pmgkay pmjay
pmjjby pmkisan pmksy pmmvy pmmy pmsby pmsvanidhi pmuy pmvv poshan pragati pucca rooftop sakhi samriddhi scss shram sinchayee sprinkler
sukanya surya svanidhi ujjwala upadhyaya vaccines vandana vaya vayoshri vishwakarma yogi
अंत्योदय आयुष्मान इंदिरा इंद्रधनुष उज्ज्वला उपाध्याय एपीवाई कुसुम केसीसी कौशल्य दयाल मनरेगा मानधन मुद्रा योगी लखपति वयोश्री विश्वकर्मा
सुकन्या स्वनिधि प्रगति समृद्धि वंदना डायलिसिस रूफटॉप ड्रिप फव्वारा टीकाकरण गर्भावस्था मातृ पोषण ग्रामोद्योग एआईसीटीई मैट्रिक मृदा सिंचाई चश्मा
அந்தியோதயா ஆயுஷ்மான் இந்திரதனுஷ் இலட்சாதிபதி உஜ்வாலா உபாத்யாய குசும் கல்யாண் தயாள் தீன் முத்ரா யோகி வந்தனா வயோஸ்ரீ விஸ்வகர்மா
ஸ்வாநிதி சுகன்யா செல்வமகள் சம்ரிதி பிரகதி டயாலிசிஸ் தடுப்பூசி மாத்ரு சொட்டு ஷ்ரம் நிவாஸ் பஹல் அவுஷதி
""".split())
_SCHEME_WORDS = {sid: {w for w in words if _WORD_DF[w] < 3 and w in _SCHEME_NAME_WORDS} for sid, words in _SCHEME_WORDS.items()}


def _match_scheme(text: str) -> Optional[str]:
    """A scheme named in the question by a distinctive word of its name (Ujjwala, Vishwakarma, उज्ज्वला …)."""
    tokens = set(text.split())
    best, best_hits = None, 0
    for sid, words in _SCHEME_WORDS.items():
        hits = len(tokens & words)
        if hits > best_hits:
            best, best_hits = sid, hits
    return best


_TITLE_INDEX = {_normalise(_title(tid, li)): tid for tid in list(kb.TOPICS) + list(kb.CALC_TEXT["title"]) for li in range(3)}


def _title_lookup(text: str) -> Optional[str]:
    return _TITLE_INDEX.get(text)


_ORDINALS = {
    1: ["1", "one", "first", "pehla", "pahla", "पहला", "पहले", "एक", "ஒன்று", "முதல்"],
    2: ["2", "two", "second", "dusra", "doosra", "दूसरा", "दो", "இரண்டு", "இரண்டாவது"],
    3: ["3", "three", "third", "teesra", "tisra", "तीसरा", "तीन", "மூன்று", "மூன்றாவது"],
}


def _ordinal(text: str) -> Optional[int]:
    words = text.replace("number", "").replace("option", "").replace("नंबर", "").strip()
    for n, forms in _ORDINALS.items():
        if words in forms:
            return n
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

def detect_intent(question: str) -> str:
    """Category of the best-matching topic (kept for callers that only need the intent)."""
    scores = _score_topics(_normalise(question))
    if not scores:
        return "general"
    return kb.TOPICS[max(scores, key=scores.get)]["cat"]


def get_guidance(question: str, language: str = "en", history: Optional[list] = None, context: Optional[dict] = None) -> dict:
    """
    Answer a money question in the user's language, using the conversation so far.
    Returns answer, audio text, intent (category), topic, sources, follow-up suggestions and the new context.
    """
    lang = language if language in LANGS else "en"
    li = LANGS.index(lang)
    last_calc = (context or {}).get("last_calc") if isinstance(context, dict) else None
    ctx = _fresh_context(context, history)
    text = _normalise(question)
    words = text.split()
    short = len(words) <= 4

    new_profile = [p for p in _profile_from(text) if p not in ctx["profile"]]
    ctx["profile"] = ctx["profile"] + new_profile
    profile_prefix = kb.PHRASES["profile_ack"][li].format(p=_profile_label(new_profile, li)) if new_profile else ""

    scores = _score_topics(text)
    best = max(scores, key=scores.get) if scores else None
    best_score = scores.get(best, 0)
    awaiting = ctx["awaiting"] or {}

    # 1. A calculation in progress: the next message is most likely the number we asked for
    if awaiting.get("type") == "calc" and awaiting.get("calc") in ("emi", "fd"):
        if _any("CANCEL_WORDS", text) and not _extract_numbers(text, awaiting.get("ask")):
            ctx["awaiting"] = None
            return _menu(ctx, li, kb.PHRASES["calc_cancel"][li] + kb.PHRASES["ok_no"][li])
        numbers = _extract_numbers(text, awaiting.get("ask"))
        if numbers:
            awaiting.setdefault("slots", {}).update(numbers)
            ctx["awaiting"] = awaiting
            return _continue_calc(ctx, li)
        if best and best_score >= STRONG:
            ctx["awaiting"] = None
            return _answer_topic(best, ctx, li, prefix=kb.PHRASES["calc_leave"][li])
        return _continue_calc(ctx, li, prefix=kb.PHRASES["calc_retry"][li])

    # 2. Asked to calculate (or new numbers right after a calculation)
    for kind, patterns in _CALC_TRIGGERS.items():
        if any(_hit(p, text) for p in patterns):
            return _start_calc("emi" if kind == "calc_emi" else "fd", ctx, li, text, prefix=profile_prefix)
    if isinstance(last_calc, dict) and last_calc.get("calc") in ("emi", "fd") and (not best or best_score < STRONG):
        numbers = _extract_numbers(text, None)
        if numbers:
            slots = _clean_slots(last_calc.get("slots"))
            slots.update(numbers)
            ctx["awaiting"] = {"type": "calc", "calc": last_calc["calc"], "slots": slots}
            return _continue_calc(ctx, li)

    # 3. Reply to our yes/no offer
    if awaiting.get("type") == "yes_no" and short and not (best and best_score >= STRONG):
        target = awaiting.get("yes")
        if _any("NO_WORDS", text):
            ctx["awaiting"] = None
            ctx["misses"] = 0
            return _reply(kb.PHRASES["ok_no"][li], ctx, li, intent="general",
                          suggestions=_pick_suggestions(ctx, li, around=ctx["last_topic"]))
        if _any("YES_WORDS", text):
            if target in ("calc_emi", "calc_fd"):
                return _start_calc("emi" if target == "calc_emi" else "fd", ctx, li, text)
            if target in kb.TOPICS:
                return _answer_topic(target, ctx, li)

    if short and not best and not awaiting:
        if _any("NO_WORDS", text):
            return _reply(kb.PHRASES["ok_no"][li], ctx, li, intent="general",
                          suggestions=_pick_suggestions(ctx, li, around=ctx["last_topic"]))
        if _any("YES_WORDS", text) and not _ordinal(text):
            return _menu(ctx, li, kb.PHRASES["yes_what"][li])

    # 4. "2" / "the second one" → a suggestion we just offered
    pick = _ordinal(text) if short else None
    if pick and len(ctx["suggestions"]) >= pick:
        chosen = ctx["suggestions"][pick - 1]
        if chosen in ("calc_emi", "calc_fd"):
            return _start_calc("emi" if chosen == "calc_emi" else "fd", ctx, li, "")
        return _answer_topic(chosen, ctx, li)

    # 5. A suggestion chip was tapped (its exact title)
    chip = _title_lookup(text)
    if chip in ("calc_emi", "calc_fd"):
        return _start_calc("emi" if chip == "calc_emi" else "fd", ctx, li, "")
    if chip:
        return _answer_topic(chip, ctx, li)

    # 6. Small talk
    if short and not best:
        if _any("THANKS_WORDS", text):
            return _reply(kb.PHRASES["thanks"][li], ctx, li, intent="general",
                          suggestions=_pick_suggestions(ctx, li, around=ctx["last_topic"]))
        if _any("BYE_WORDS", text):
            ctx["awaiting"] = None
            return _reply(kb.PHRASES["bye"][li], ctx, li, intent="general")
        if _any("GREET_WORDS", text):
            if ctx["last_topic"]:
                ctx["awaiting"] = {"type": "yes_no", "yes": ctx["last_topic"]}
                return _reply(kb.PHRASES["greet_again"][li].format(t=_title(ctx["last_topic"], li)), ctx, li, intent="general",
                              suggestions=_pick_suggestions(ctx, li, around=ctx["last_topic"]))
            return _menu(ctx, li, profile_prefix + kb.PHRASES["greet"][li])
    if _any("HUMAN_WORDS", text) and best_score < STRONG:
        return _reply(kb.PHRASES["human"][li], ctx, li, intent="complaints",
                      suggestions=_pick_suggestions(ctx, li, around="bank_complaint"))
    if _any("HELP_WORDS", text) and best_score < STRONG:
        return _menu(ctx, li, profile_prefix + kb.PHRASES["help"][li])

    facets = _facets(text)

    # 7a. The user only told us about themselves ("I am a farmer", "meri umar 65 saal hai")
    if new_profile and (not best or kb.TOPICS[best]["cat"] == "schemes" and best_score < STRONG):
        ids = []
        for p in new_profile:
            ids += [t for t in kb.PROFILE_TOPICS.get(p, []) if t not in ids]
        ctx["suggestions"] = ids[:3]
        ctx["awaiting"] = None
        ctx["misses"] = 0
        listing = ", ".join(_title(t, li) for t in ids[:3])
        return _reply(profile_prefix + kb.PHRASES["profile_suggest"][li].format(list=listing), ctx, li, intent="general",
                      suggestions=[_title(t, li) for t in ids[:3]])

    # 7b. A named government scheme from the catalogue (beats the generic 'schemes' topic)
    sid = _match_scheme(text)
    if sid and (not best or best == "schemes_general" or best_score < STRONG):
        return _scheme_answer(sid, ctx, li)

    # 7c. A clear topic in the question
    if best and best_score >= 2.0:
        target = _linked(best, facets) or best
        return _answer_topic(target, ctx, li, prefix=profile_prefix)

    # 8. A follow-up about what we were just discussing ("what documents?", "how do I apply?", "tell me more")
    if ctx["last_scheme"] and facets and not best:
        follow = _scheme_followup(ctx["last_scheme"], facets, ctx, li)
        if follow:
            return follow
    last = ctx["last_topic"]
    if last and facets and not best:
        linked = _linked(last, facets)
        if linked and linked != last:
            return _answer_topic(linked, ctx, li, prefix=profile_prefix)
        return _answer_topic(last, ctx, li, prefix=kb.PHRASES["about_that"][li].format(t=_title(last, li)) + profile_prefix)
    if last and _any("MORE_WORDS", text) and short and not best:
        nxt = next((r for r in kb.TOPICS[last]["related"] if r not in ctx["discussed"]), None)
        if nxt:
            return _answer_topic(nxt, ctx, li, prefix=kb.PHRASES["related_to"][li].format(t=_title(nxt, li)))

    # 9. Weak topic match (single generic word like "account" or "card")
    if best:
        return _answer_topic(best, ctx, li, prefix=profile_prefix)

    # 10. Not understood — vary the reply instead of repeating the same fallback
    ctx["misses"] += 1
    if ctx["misses"] == 1:
        suggestions = _pick_suggestions(ctx, li, around=last)
        return _reply(kb.PHRASES["miss1"][li] + "; ".join(suggestions) + ".", ctx, li, intent="general", suggestions=suggestions)
    if ctx["misses"] == 2:
        return _menu(ctx, li, kb.PHRASES["miss2"][li])
    ctx["misses"] = 0
    return _menu(ctx, li, kb.PHRASES["miss3"][li] + kb.PHRASES["human"][li])
