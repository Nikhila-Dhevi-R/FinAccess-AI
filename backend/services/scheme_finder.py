"""
Finding the right government scheme quickly, in English, Hindi or Tamil.

Every scheme is tagged with WHO it is for (farmer, woman, senior, ...) and WHAT it gives
(pension, loan, house, ...). Customers can filter by these, or simply type / say what they need in any
language — "pension", "पेंशन", "ஓய்வூதியம்", "budhapa pension", "loan for shop", "beti padhai".
"""

import re

try:
    import Levenshtein
except ImportError:  # pragma: no cover
    Levenshtein = None

from services.schemes_data import SCHEMES_CATALOGUE

# key: (English, Hindi, Tamil, icon, search words in all languages incl. Hinglish)
AUDIENCES = {
    "farmer": ("Farmers", "किसान", "விவசாயிகள்", "🌾",
               ["farmer", "farming", "kisan", "krishi", "kheti", "khet", "crop", "agriculture", "किसान", "खेती", "कृषि", "फसल",
                "விவசாயி", "விவசாயம்", "பயிர்"]),
    "woman": ("Women", "महिलाएं", "பெண்கள்", "👩",
              ["woman", "women", "lady", "mahila", "widow", "pregnant", "mother", "didi", "महिला", "औरत", "विधवा", "गर्भवती",
               "பெண்", "பெண்கள்", "விதவை", "கர்ப்பிணி"]),
    "girl_child": ("Girl child", "बेटियां", "பெண் குழந்தைகள்", "👧",
                   ["girl", "daughter", "beti", "ladki", "बेटी", "बेटियां", "लड़की", "மகள்", "பெண் குழந்தை"]),
    "student": ("Students & children", "विद्यार्थी व बच्चे", "மாணவர்கள் & குழந்தைகள்", "🎓",
                ["student", "school", "college", "child", "children", "padhai", "chhatra", "छात्र", "विद्यार्थी", "बच्चे", "पढ़ाई",
                 "மாணவர்", "பள்ளி", "குழந்தை", "படிப்பு"]),
    "senior": ("Senior citizens", "बुज़ुर्ग", "முதியோர்", "👴",
               ["senior", "old", "elderly", "aged", "budhapa", "buzurg", "बुज़ुर्ग", "बुजुर्ग", "बुढ़ापा", "वृद्ध", "वरिष्ठ",
                "முதியோர்", "வயதானவர்", "மூத்த"]),
    "worker": ("Workers & labourers", "मज़दूर व कामगार", "தொழிலாளர்கள்", "👷",
               ["worker", "labour", "labourer", "daily wage", "mazdoor", "majdoor", "construction", "vendor", "rehri", "मज़दूर",
                "मजदूर", "श्रमिक", "कामगार", "தொழிலாளர்", "கூலி"]),
    "business": ("Small business", "छोटा व्यवसाय", "சிறு வணிகம்", "🏪",
                 ["business", "shop", "dukan", "dukaan", "self employed", "startup", "artisan", "karigar", "udyog", "दुकान",
                  "व्यवसाय", "धंधा", "कारीगर", "उद्योग", "வணிகம்", "கடை", "சுயதொழில்", "கைவினை"]),
    "poor_family": ("Poor / BPL families", "गरीब / बीपीएल परिवार", "ஏழை / BPL குடும்பங்கள்", "🏠",
                    ["poor", "bpl", "garib", "gareeb", "ration card", "antyodaya", "गरीब", "बीपीएल", "राशन कार्ड", "ஏழை", "ரேஷன்"]),
    "everyone": ("Everyone", "सभी के लिए", "அனைவருக்கும்", "👥", ["everyone", "all", "any", "सभी", "அனைவரும்"]),
}

NEEDS = {
    "cash": ("Money / cash help", "पैसों की मदद", "பண உதவி", "💰",
             ["money", "cash", "paisa", "paise", "rupees", "grant", "amount", "installment", "पैसा", "पैसे", "राशि", "सहायता",
              "பணம்", "உதவித்தொகை", "தொகை"]),
    "pension": ("Pension", "पेंशन", "ஓய்வூதியம்", "🧓",
                ["pension", "pention", "old age", "monthly income", "पेंशन", "ओल्ड एज", "ஓய்வூதியம்", "பென்ஷன்"]),
    "loan": ("Loans", "लोन / ऋण", "கடன்", "🏦",
             ["loan", "lone", "credit", "karz", "karza", "rin", "udhaar", "लोन", "ऋण", "कर्ज", "कर्ज़", "उधार", "கடன்"]),
    "insurance": ("Insurance", "बीमा", "காப்பீடு", "🛡️",
                  ["insurance", "bima", "cover", "accident", "life cover", "बीमा", "सुरक्षा", "காப்பீடு", "இன்சூரன்ஸ்"]),
    "house": ("House / home", "घर / आवास", "வீடு", "🏡",
              ["house", "home", "ghar", "makan", "awas", "aawas", "housing", "pucca", "घर", "मकान", "आवास", "வீடு", "குடியிருப்பு"]),
    "education": ("Education / scholarship", "पढ़ाई / छात्रवृत्ति", "கல்வி / உதவித்தொகை", "📚",
                  ["education", "scholarship", "study", "school", "college", "fees", "padhai", "vazhifa", "पढ़ाई", "शिक्षा",
                   "छात्रवृत्ति", "स्कॉलरशिप", "கல்வி", "படிப்பு", "கல்வி உதவித்தொகை"]),
    "health": ("Health / treatment", "स्वास्थ्य / इलाज", "சுகாதாரம் / சிகிச்சை", "🏥",
               ["health", "hospital", "treatment", "ilaj", "ilaaj", "medicine", "dawai", "doctor", "vaccine", "dialysis",
                "pregnant", "pregnancy", "maternity", "delivery", "garbhvati", "गर्भवती", "प्रसव", "கர்ப்பிணி", "பிரசவம்",
                "इलाज", "अस्पताल", "दवा", "स्वास्थ्य", "टीका", "மருத்துவம்", "சிகிச்சை", "மருந்து", "மருத்துவமனை"]),
    "food": ("Food / ration", "राशन / भोजन", "உணவு / ரேஷன்", "🍚",
             ["food", "ration", "anaj", "grain", "rice", "wheat", "meal", "khana", "राशन", "अनाज", "भोजन", "खाना",
              "உணவு", "ரேஷன்", "அரிசி"]),
    "savings": ("Savings / deposits", "बचत / जमा", "சேமிப்பு", "🐷",
                ["savings", "save", "deposit", "interest", "bachat", "बचत", "जमा", "ब्याज", "சேமிப்பு", "வட்டி"]),
    "subsidy": ("Subsidy (gas, solar, equipment)", "सब्सिडी (गैस, सोलर, उपकरण)", "மானியம் (எரிவாயு, சோலார்)", "⚡",
                ["subsidy", "gas", "lpg", "cylinder", "solar", "electricity", "bijli", "pump", "toolkit", "सब्सिडी", "गैस",
                 "सोलर", "बिजली", "மானியம்", "எரிவாயு", "சோலார்", "மின்சாரம்"]),
    "skills_jobs": ("Jobs / skill training", "रोज़गार / कौशल प्रशिक्षण", "வேலை / திறன் பயிற்சி", "🛠️",
                    ["job", "jobs", "work", "employment", "rozgar", "naukri", "training", "skill", "रोज़गार", "रोजगार",
                     "नौकरी", "प्रशिक्षण", "வேலை", "பயிற்சி", "வேலைவாய்ப்பு"]),
}

# scheme id: (who it is for, what it gives) — hand-checked against each scheme's benefit text
SCHEME_TAGS = {
    "pmkisan": (["farmer"], ["cash"]),
    "pmfby": (["farmer"], ["insurance"]),
    "kcc": (["farmer"], ["loan"]),
    "pm_kusum": (["farmer"], ["subsidy"]),
    "soil_health_card": (["farmer"], ["subsidy"]),
    "pmksy": (["farmer"], ["subsidy"]),
    "mgnrega": (["worker", "poor_family"], ["skills_jobs", "cash"]),
    "eshram": (["worker"], ["insurance"]),
    "pm_sym": (["worker"], ["pension"]),
    "bocw": (["worker"], ["cash", "insurance"]),
    "pmsvanidhi": (["worker", "business"], ["loan"]),
    "ddu_gky": (["worker", "student", "poor_family"], ["skills_jobs"]),
    "sukanya": (["girl_child"], ["savings"]),
    "post_matric_sc_st": (["student"], ["education"]),
    "nmms": (["student"], ["education", "cash"]),
    "pm_poshan": (["student"], ["food"]),
    "beti_bachao": (["girl_child", "student"], ["education"]),
    "pragati_scholarship": (["girl_child", "student"], ["education", "cash"]),
    "nsap_ignoaps": (["senior", "poor_family"], ["pension"]),
    "nsap_ignwps": (["woman", "poor_family"], ["pension"]),
    "rvv": (["senior", "poor_family"], ["health"]),
    "apy": (["worker", "everyone"], ["pension"]),
    "pmvv_scss": (["senior"], ["savings"]),
    "vaya_vandana": (["senior"], ["pension", "savings"]),
    "pmuy": (["woman", "poor_family"], ["subsidy"]),
    "pmmvy": (["woman"], ["cash", "health"]),
    "mssc": (["woman", "girl_child"], ["savings"]),
    "lakhpati_didi": (["woman", "business"], ["loan", "skills_jobs"]),
    "stand_up_women": (["woman", "business"], ["loan"]),
    "wwh_scheme": (["woman"], ["house"]),
    "mudra": (["business"], ["loan"]),
    "pm_vishwakarma": (["business", "worker"], ["loan", "skills_jobs", "subsidy"]),
    "pmegp": (["business"], ["loan", "subsidy"]),
    "cgtmse": (["business"], ["loan"]),
    "pm_egp_artisan": (["business", "worker"], ["subsidy", "skills_jobs"]),
    "pm_formalisation_fme": (["business"], ["subsidy", "loan"]),
    "pmay_g": (["poor_family"], ["house"]),
    "pm_surya_ghar": (["everyone"], ["subsidy"]),
    "pmgkay": (["poor_family"], ["food"]),
    "pmay_u": (["poor_family", "everyone"], ["house", "loan"]),
    "pahal_lpg": (["everyone"], ["subsidy"]),
    "aay_ration": (["poor_family"], ["food"]),
    "pmjay": (["poor_family"], ["health", "insurance"]),
    "pmjjby": (["everyone"], ["insurance"]),
    "pmsby": (["everyone"], ["insurance"]),
    "pmbjp": (["everyone"], ["health"]),
    "pm_dialysis": (["poor_family"], ["health"]),
    "mission_indradhanush": (["girl_child", "student", "woman"], ["health"]),
}

MINISTRIES = {
    "Ministry of Finance": ("वित्त मंत्रालय", "நிதி அமைச்சகம்"),
    "Ministry of Rural Development": ("ग्रामीण विकास मंत्रालय", "ஊரக வளர்ச்சி அமைச்சகம்"),
    "Ministry of Agriculture & Farmers Welfare": ("कृषि एवं किसान कल्याण मंत्रालय", "வேளாண்மை மற்றும் விவசாயிகள் நல அமைச்சகம்"),
    "Ministry of Women & Child Development": ("महिला एवं बाल विकास मंत्रालय", "பெண்கள் மற்றும் குழந்தைகள் மேம்பாட்டு அமைச்சகம்"),
    "Ministry of New and Renewable Energy": ("नवीन एवं नवीकरणीय ऊर्जा मंत्रालय", "புதிய மற்றும் புதுப்பிக்கத்தக்க எரிசக்தி அமைச்சகம்"),
    "Ministry of Labour & Employment": ("श्रम एवं रोज़गार मंत्रालय", "தொழிலாளர் மற்றும் வேலைவாய்ப்பு அமைச்சகம்"),
    "Ministry of Housing and Urban Affairs": ("आवास एवं शहरी कार्य मंत्रालय", "வீட்டுவசதி மற்றும் நகர்ப்புற விவகார அமைச்சகம்"),
    "Ministry of Education": ("शिक्षा मंत्रालय", "கல்வி அமைச்சகம்"),
    "Ministry of Petroleum and Natural Gas": ("पेट्रोलियम एवं प्राकृतिक गैस मंत्रालय", "பெட்ரோலியம் மற்றும் இயற்கை எரிவாயு அமைச்சகம்"),
    "Ministry of MSME / KVIC": ("सूक्ष्म, लघु एवं मध्यम उद्यम मंत्रालय / खादी ग्रामोद्योग आयोग", "குறு, சிறு, நடுத்தர தொழில் அமைச்சகம் / KVIC"),
    "Ministry of Consumer Affairs, Food and Public Distribution": ("उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय", "நுகர்வோர் விவகாரம், உணவு மற்றும் பொது விநியோக அமைச்சகம்"),
    "Ministry of Health and Family Welfare": ("स्वास्थ्य एवं परिवार कल्याण मंत्रालय", "சுகாதாரம் மற்றும் குடும்ப நல அமைச்சகம்"),
    "Ministry of Finance & Agriculture": ("वित्त एवं कृषि मंत्रालय", "நிதி மற்றும் வேளாண்மை அமைச்சகம்"),
    "State Labour Welfare Boards (Central Act)": ("राज्य श्रम कल्याण बोर्ड (केंद्रीय अधिनियम)", "மாநில தொழிலாளர் நல வாரியங்கள் (மத்திய சட்டம்)"),
    "Ministry of Social Justice & Tribal Affairs": ("सामाजिक न्याय एवं जनजातीय कार्य मंत्रालय", "சமூக நீதி மற்றும் பழங்குடியினர் விவகார அமைச்சகம்"),
    "Ministry of Education / AICTE": ("शिक्षा मंत्रालय / एआईसीटीई", "கல்வி அமைச்சகம் / AICTE"),
    "Ministry of Social Justice and Empowerment": ("सामाजिक न्याय एवं अधिकारिता मंत्रालय", "சமூக நீதி மற்றும் அதிகாரமளித்தல் அமைச்சகம்"),
    "Ministry of Finance / PFRDA": ("वित्त मंत्रालय / पीएफआरडीए", "நிதி அமைச்சகம் / PFRDA"),
    "Ministry of Finance / LIC": ("वित्त मंत्रालय / एलआईसी", "நிதி அமைச்சகம் / LIC"),
    "Ministry of Rural Development / DAY-NRLM": ("ग्रामीण विकास मंत्रालय / डीएवाई-एनआरएलएम", "ஊரக வளர்ச்சி அமைச்சகம் / DAY-NRLM"),
    "Ministry of Micro, Small and Medium Enterprises": ("सूक्ष्म, लघु एवं मध्यम उद्यम मंत्रालय", "குறு, சிறு மற்றும் நடுத்தர தொழில் அமைச்சகம்"),
    "Ministry of MSME / SIDBI": ("सूक्ष्म, लघु एवं मध्यम उद्यम मंत्रालय / सिडबी", "குறு, சிறு, நடுத்தர தொழில் அமைச்சகம் / SIDBI"),
    "Ministry of Food Processing Industries": ("खाद्य प्रसंस्करण उद्योग मंत्रालय", "உணவு பதப்படுத்தும் தொழில் அமைச்சகம்"),
    "Ministry of Health and Family Welfare / NHA": ("स्वास्थ्य एवं परिवार कल्याण मंत्रालय / एनएचए", "சுகாதாரம் மற்றும் குடும்ப நல அமைச்சகம் / NHA"),
    "Ministry of Chemicals and Fertilizers / PMBI": ("रसायन एवं उर्वरक मंत्रालय / पीएमबीआई", "ரசாயனங்கள் மற்றும் உரங்கள் அமைச்சகம் / PMBI"),
}

LANG_INDEX = {"en": 0, "hi": 1, "ta": 2}
STOP_WORDS = {"for", "the", "a", "an", "of", "to", "in", "on", "me", "my", "i", "want", "need", "scheme", "schemes", "yojana",
              "yojna", "ke", "ki", "ka", "liye", "mujhe", "chahiye", "के", "की", "का", "लिए", "मुझे", "चाहिए", "योजना",
              "योजनाएं", "திட்டம்", "திட்டங்கள்", "எனக்கு", "வேண்டும்", "help", "please", "kaise", "how", "get"}


def localize_ministry(ministry: str, language: str) -> str:
    if language not in ("hi", "ta") or ministry not in MINISTRIES:
        return ministry
    return MINISTRIES[ministry][0 if language == "hi" else 1]


def tags_for(scheme_id: str) -> tuple[list[str], list[str]]:
    return SCHEME_TAGS.get(scheme_id, ([], []))


def filter_options(language: str = "en") -> dict:
    """Who-is-it-for and what-do-you-need options with labels in the language and scheme counts."""
    idx = LANG_INDEX.get(language, 0)

    def options(table, position):
        return [{"id": key, "label": spec[idx], "icon": spec[3],
                 "count": sum(1 for tags in SCHEME_TAGS.values() if key in tags[position])}
                for key, spec in table.items()]

    return {"audiences": options(AUDIENCES, 0), "needs": options(NEEDS, 1)}


def _normalise(text: str) -> str:
    return re.sub(r"[^\wऀ-ॿ஀-௿ ]+", " ", (text or "").lower())


def _scheme_haystack(scheme: dict) -> str:
    parts = [scheme["id"].replace("_", " "), scheme.get("short_name", ""), scheme.get("ministry", "")]
    for lang in ("en", "hi", "ta"):
        tr = scheme.get("translations", {}).get(lang, {})
        parts += [tr.get("name", ""), tr.get("benefit_summary", ""), tr.get("who_can_get", "")]
    return _normalise(" ".join(parts))


_HAYSTACKS = {s["id"]: _scheme_haystack(s) for s in SCHEMES_CATALOGUE}
_TITLES = {s["id"]: _normalise(" ".join([s.get("short_name", "")] + [s.get("translations", {}).get(l, {}).get("name", "")
                                                                    for l in ("en", "hi", "ta")])) for s in SCHEMES_CATALOGUE}


def _query_terms(query: str) -> list[str]:
    return [w for w in _normalise(query).split() if w not in STOP_WORDS and len(w) >= 2]


def _tag_hits(query_norm: str, terms: list[str]):
    """Audience / need tags that the query talks about (by any of their words, in any language)."""
    hits = set()
    for table, kind in ((AUDIENCES, "audience"), (NEEDS, "need")):
        for key, spec in table.items():
            for word in spec[4]:
                w = word.lower()
                if (" " in w and w in query_norm) or w in terms or any(_close(t, w) for t in terms):
                    hits.add((kind, key))
                    break
    return hits


def _close(term: str, word: str) -> bool:
    """Typo-tolerant match for Latin words: 'pensoin' ≈ 'pension'."""
    if Levenshtein is None or len(term) < 5 or len(word) < 5 or not term.isascii() or not word.isascii():
        return False
    return Levenshtein.ratio(term, word) >= 0.85


def search(query: str) -> list[tuple[str, float]]:
    """(scheme id, score) best first, for a free-text query in English, Hindi, Tamil or Hinglish."""
    terms = _query_terms(query)
    if not terms:
        return []
    query_norm = " ".join(terms)
    tag_hits = _tag_hits(query_norm, terms)
    results = []
    for scheme in SCHEMES_CATALOGUE:
        sid = scheme["id"]
        audiences, needs = tags_for(sid)
        hay, title = _HAYSTACKS[sid], _TITLES[sid]
        score = 0.0
        for t in terms:
            if re.search(rf"(^|\s){re.escape(t)}", title):
                score += 3.0                       # scheme name / short name
            elif re.search(rf"(^|\s){re.escape(t)}", hay):
                score += 1.0                       # benefit / who-can-get text
            elif any(_close(t, w) for w in set(title.split())):
                score += 2.0
        hit_audience = hit_need = False
        for kind, key in tag_hits:
            if kind == "audience" and key in audiences:
                score += 2.5
                hit_audience = True
            elif kind == "need" and key in needs:
                score += 1.0 if key == "cash" else 2.5   # "money" is in almost every request; be specific
                hit_need = hit_need or key != "cash"
        if hit_audience and hit_need:
            score += 2.0                                  # "pregnant woman" → for women AND health
        if score > 0:
            results.append((sid, score))
    results.sort(key=lambda r: -r[1])
    if results:  # keep clearly relevant ones, not every passing mention
        cutoff = max(1.5, 0.5 * results[0][1])
        if tag_hits and all(kind == "audience" for kind, _ in tag_hits) and \
                all(any(t == w.lower() or _close(t, w.lower()) for kind, key in tag_hits for w in AUDIENCES[key][4]) for t in terms):
            cutoff = 2.0  # just "kisan" / "महिला": show every scheme for that group
        results = [r for r in results if r[1] >= cutoff]
    return results
