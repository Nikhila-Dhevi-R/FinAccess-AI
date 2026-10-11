"""
Language support for voice form filling.

* Field labels read from an (English) form are shown and asked in the customer's language
  ("Name" → "नाम" / "பெயர்").
* Answers spoken in Hindi / Tamil are shown back in that script for confirmation, but written on the
  English form in English letters ("राम कुमार" → "Ram Kumar", "முருகன்" → "Murugan").
"""

import re
from typing import Optional

# ─── Field labels ────────────────────────────────────────────────────────────
LABELS = {
    # name / family
    "Full Name": ("पूरा नाम", "முழு பெயர்"),
    "Applicant Name": ("आवेदक का नाम", "விண்ணப்பதாரர் பெயர்"),
    "Farmer Name": ("किसान का नाम", "விவசாயி பெயர்"),
    "Account Holder Name": ("खाताधारक का नाम", "கணக்கு வைத்திருப்பவர் பெயர்"),
    "Payee Name": ("पाने वाले का नाम", "பெறுநர் பெயர்"),
    "Pay To": ("किसे भुगतान करना है", "யாருக்கு செலுத்த வேண்டும்"),
    "Father's Name": ("पिता का नाम", "தந்தையின் பெயர்"),
    "Mother's Name": ("माता का नाम", "தாயின் பெயர்"),
    "Spouse's Name": ("पति / पत्नी का नाम", "வாழ்க்கைத் துணையின் பெயர்"),
    "Spouse Name": ("पति / पत्नी का नाम", "வாழ்க்கைத் துணையின் பெயர்"),
    "Father / Mother / Spouse Name": ("पिता / माता / पति-पत्नी का नाम", "தந்தை / தாய் / துணையின் பெயர்"),
    "Nominee Name": ("नॉमिनी का नाम", "நாமினி பெயர்"),
    "Nominee Relationship": ("नॉमिनी से संबंध", "நாமினியுடன் உறவு"),
    # personal
    "Date of Birth": ("जन्म तिथि", "பிறந்த தேதி"),
    "Age": ("उम्र", "வயது"),
    "Gender": ("लिंग", "பாலினம்"),
    "Marital Status": ("वैवाहिक स्थिति", "திருமண நிலை"),
    "Nationality": ("राष्ट्रीयता", "தேசியம்"),
    "Occupation": ("व्यवसाय", "தொழில்"),
    "Annual Family Income": ("परिवार की सालाना आय", "குடும்ப ஆண்டு வருமானம்"),
    "Caste / Social Category": ("जाति / सामाजिक वर्ग", "சாதி / சமூகப் பிரிவு"),
    # ids
    "Aadhaar Number": ("आधार नंबर", "ஆதார் எண்"),
    "PAN Number": ("पैन नंबर", "பான் எண்"),
    "Voter ID / EPIC": ("वोटर आईडी", "வாக்காளர் அடையாள அட்டை"),
    "Ration Card Number": ("राशन कार्ड नंबर", "ரேஷன் அட்டை எண்"),
    "Disability Certificate Number": ("विकलांगता प्रमाणपत्र नंबर", "மாற்றுத்திறன் சான்றிதழ் எண்"),
    "Customer ID": ("ग्राहक आईडी", "வாடிக்கையாளர் ஐடி"),
    # contact / address
    "Mobile Number": ("मोबाइल नंबर", "மொபைல் எண்"),
    "Alternate Mobile Number": ("दूसरा मोबाइल नंबर", "மாற்று மொபைல் எண்"),
    "Email Address": ("ईमेल पता", "மின்னஞ்சல் முகவரி"),
    "Address": ("पता", "முகவரி"),
    "Residential Address": ("घर का पता", "வீட்டு முகவரி"),
    "House / Flat / Building": ("मकान / फ्लैट नंबर", "வீடு / கட்டட எண்"),
    "Street / Area / Locality": ("गली / इलाका", "தெரு / பகுதி"),
    "Village Name": ("गाँव का नाम", "கிராமத்தின் பெயர்"),
    "Block / Tehsil": ("ब्लॉक / तहसील", "வட்டம் / தாலுகா"),
    "City / Town": ("शहर / कस्बा", "நகரம் / ஊர்"),
    "District": ("जिला", "மாவட்டம்"),
    "State": ("राज्य", "மாநிலம்"),
    "PIN / Postal Code": ("पिन कोड", "அஞ்சல் குறியீடு"),
    "PIN Code": ("पिन कोड", "அஞ்சல் குறியீடு"),
    # bank
    "Account Number": ("खाता नंबर", "கணக்கு எண்"),
    "Bank Account Number": ("बैंक खाता नंबर", "வங்கி கணக்கு எண்"),
    "SB Account Number (for credit)": ("बचत खाता नंबर (जमा के लिए)", "சேமிப்பு கணக்கு எண் (வரவுக்கு)"),
    "IFSC Code": ("आईएफएससी कोड", "IFSC குறியீடு"),
    "Bank Name & Branch": ("बैंक का नाम और शाखा", "வங்கி பெயர் மற்றும் கிளை"),
    "Branch Name": ("शाखा का नाम", "கிளையின் பெயர்"),
    "Branch Code": ("शाखा कोड", "கிளை குறியீடு"),
    "Branch Address": ("शाखा का पता", "கிளை முகவரி"),
    "Account Office Name": ("खाता कार्यालय का नाम", "கணக்கு அலுவலகத்தின் பெயர்"),
    "Amount": ("राशि", "தொகை"),
    "Cheque Amount": ("चेक की राशि", "காசோலை தொகை"),
    "Cheque Date": ("चेक की तारीख", "காசோலை தேதி"),
    "Cheque Number": ("चेक नंबर", "காசோலை எண்"),
    "Number of Cheque Leaves": ("चेक के पन्नों की संख्या", "காசோலை தாள்களின் எண்ணிக்கை"),
    "Date": ("तारीख", "தேதி"),
    "Maturity Date": ("परिपक्वता की तारीख", "முதிர்வு தேதி"),
    "Passbook Request Type": ("पासबुक अनुरोध का प्रकार", "பாஸ்புக் கோரிக்கை வகை"),
    # farming
    "Land Holding (Acres)": ("ज़मीन (एकड़ में)", "நிலம் (ஏக்கரில்)"),
    "Survey / Khasra Number": ("सर्वे / खसरा नंबर", "சர்வே எண்"),
    "Crop Type": ("फसल का प्रकार", "பயிர் வகை"),
}

GLOSSARY = {  # word-by-word fallback for labels not listed above
    "name": ("नाम", "பெயர்"), "number": ("नंबर", "எண்"), "no": ("नंबर", "எண்"), "date": ("तारीख", "தேதி"),
    "account": ("खाता", "கணக்கு"), "address": ("पता", "முகவரி"), "father": ("पिता", "தந்தை"), "mother": ("माता", "தாய்"),
    "mobile": ("मोबाइल", "மொபைல்"), "phone": ("फ़ोन", "தொலைபேசி"), "branch": ("शाखा", "கிளை"), "amount": ("राशि", "தொகை"),
    "code": ("कोड", "குறியீடு"), "birth": ("जन्म", "பிறப்பு"), "bank": ("बैंक", "வங்கி"), "card": ("कार्ड", "அட்டை"),
    "income": ("आय", "வருமானம்"), "village": ("गाँव", "கிராமம்"), "city": ("शहर", "நகரம்"), "district": ("जिला", "மாவட்டம்"),
    "state": ("राज्य", "மாநிலம்"), "email": ("ईमेल", "மின்னஞ்சல்"), "occupation": ("व्यवसाय", "தொழில்"),
    "nominee": ("नॉमिनी", "நாமினி"), "age": ("उम्र", "வயது"), "gender": ("लिंग", "பாலினம்"), "id": ("आईडी", "ஐடி"),
    "customer": ("ग्राहक", "வாடிக்கையாளர்"), "holder": ("धारक", "வைத்திருப்பவர்"), "type": ("प्रकार", "வகை"),
    "family": ("परिवार", "குடும்பம்"), "land": ("ज़मीन", "நிலம்"), "relationship": ("संबंध", "உறவு"),
    "husband": ("पति", "கணவர்"), "wife": ("पत्नी", "மனைவி"), "spouse": ("पति / पत्नी", "துணை"), "full": ("पूरा", "முழு"),
    "applicant": ("आवेदक", "விண்ணப்பதாரர்"), "signature": ("हस्ताक्षर", "கையொப்பம்"), "place": ("स्थान", "இடம்"),
    "pin": ("पिन", "பின்"), "postal": ("डाक", "அஞ்சல்"), "office": ("कार्यालय", "அலுவலகம்"), "of": ("", ""),
    "the": ("", ""), "and": ("और", "மற்றும்"), "&": ("और", "மற்றும்"),
}


def translate_label(label: str, language: str) -> str:
    if language not in ("hi", "ta") or not label:
        return label
    idx = 0 if language == "hi" else 1
    if label in LABELS:
        return LABELS[label][idx]
    parts = []
    for token in re.split(r"(\s+|/|\(|\))", label):
        word = token.strip().lower().rstrip("'s").rstrip("’s")
        if word in GLOSSARY:
            parts.append(GLOSSARY[word][idx])
        else:
            parts.append(token)
    return re.sub(r"\s+", " ", "".join(p if p else "" for p in parts)).strip() or label


def localized_question(label: str, english_question: str, language: str) -> str:
    """The question in the customer's language: curated translation if we have one, else a clear generic one."""
    if language not in ("hi", "ta"):
        return english_question
    from services.bank_form_service import translate_question
    from services.voice_service import LOCALIZED_QUESTIONS

    exact = translate_question(english_question, language)
    if exact:
        return exact
    for key, translations in LOCALIZED_QUESTIONS.items():
        k = key.lower()
        if k == label.lower() or k in label.lower() or k in (english_question or "").lower():
            if language in translations:
                return translations[language]
    local = translate_label(label, language)
    if language == "hi":
        return f"कृपया {local} बताएं।"
    return f"தயவுசெய்து {local} சொல்லுங்கள்."


# ─── Hindi (Devanagari) → English letters ────────────────────────────────────
DEV_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
}
DEV_NUKTA = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "य": "y"}
DEV_PRECOMPOSED = {"क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y"}
DEV_VOWELS = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri", "ए": "e", "ऐ": "ai",
              "ओ": "o", "औ": "au", "ऑ": "o"}
DEV_MATRAS = {"ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o",
              "ौ": "au", "ॉ": "o"}
DEV_FINAL_MATRAS = {"ी": "i", "ू": "u"}  # Sunita / Lakshmi / Devi, but Deepak / Pooja mid-word
LOANWORDS = {  # common English words spoken in Hindi addresses / names
    "स्टेशन": "Station", "रोड": "Road", "कॉलोनी": "Colony", "कालोनी": "Colony", "सोसाइटी": "Society",
    "अपार्टमेंट": "Apartment", "फ्लैट": "Flat", "हाउस": "House", "नंबर": "Number", "सेक्टर": "Sector",
    "ब्लॉक": "Block", "स्ट्रीट": "Street", "मार्केट": "Market", "बाज़ार": "Bazaar", "बाजार": "Bazaar",
    "चौक": "Chowk", "नगर": "Nagar", "पुर": "pur", "गंज": "ganj", "जी": "Ji", "देवी": "Devi", "कुमार": "Kumar",
    "सिंह": "Singh", "सिंघ": "Singh",
}


def _devanagari_word(word: str) -> str:
    if word in LOANWORDS:
        return LOANWORDS[word]
    for k, v in DEV_PRECOMPOSED.items():
        word = word.replace(k, "\u0000" + v + "\u0001")  # protect precomposed nukta letters
    # Build syllables: (consonant_latin or None, vowel_latin or None, kind)
    units = []
    i, n = 0, len(word)
    while i < n:
        ch = word[i]
        if ch == "\u0000":
            j = word.index("\u0001", i)
            cons = word[i + 1:j]
            i = j + 1
            units.append({"c": cons, "v": None})
            continue
        if ch in DEV_CONSONANTS:
            cons = DEV_CONSONANTS[ch]
            if i + 1 < n and word[i + 1] == "़":  # nukta
                cons = DEV_NUKTA.get(ch, cons)
                i += 1
            units.append({"c": cons, "v": None})
        elif ch in DEV_VOWELS:
            units.append({"c": "", "v": DEV_VOWELS[ch]})
        elif ch in DEV_MATRAS and units:
            final = i + 1 >= n or word[i + 1] in "ंँः"
            # long ई / ऊ read "ee" / "oo" only in the first syllable: Deepak, Pooja — but Sunita, Jagdish
            first_syllable = not any(u["v"] is None or u["v"] for u in units[:-1]) \
                or (len(units) >= 2 and units[-2]["v"] == "")
            long_vowel = ch in DEV_FINAL_MATRAS and not final and first_syllable
            units[-1]["v"] = DEV_MATRAS[ch] if long_vowel or ch not in DEV_FINAL_MATRAS else DEV_FINAL_MATRAS[ch]
        elif ch == "्" and units:          # virama: no vowel
            units[-1]["v"] = ""
            units[-1]["virama"] = True
        elif ch in "ंँ" and units:              # nasal
            units[-1]["nasal"] = True
        elif ch == "ः" and units:
            units[-1]["visarga"] = True
        else:
            units.append({"c": ch, "v": "", "other": True})
        i += 1

    # Inherent vowel 'a' for consonants without a sign, then Hindi schwa deletion
    for u in units:
        if u["v"] is None:
            u["v"] = "a"
            u["inherent"] = True
    m = len(units)
    if m > 1 and units[-1].get("inherent"):
        conjunct = m >= 2 and units[-2]["v"] == ""            # कृष्ण → Krishna, गुप्त → Gupta
        if not conjunct:
            units[-1]["v"] = ""
    # Medial schwa deletion, right to left: a vowel before and a voweled consonant after → drop the 'a'
    # जगदीश → Jagdish, मनमोहन → Manmohan, राजकुमार → Rajkumar, अमरनाथ → Amarnath
    for k in range(m - 2, 0, -1):
        u, prev, nxt = units[k], units[k - 1], units[k + 1]
        starts_cluster = nxt.get("virama") and k + 2 < m and units[k + 2]["v"]   # हरप्रीत → Harpreet
        if u.get("inherent") and u["v"] == "a" and prev["v"] and nxt["c"] and (nxt["v"] or starts_cluster) \
                and not nxt.get("other"):
            u["v"] = ""
    out = []
    for idx, u in enumerate(units):
        out.append(u["c"] + u["v"])
        if u.get("nasal"):
            nxt = units[idx + 1]["c"] if idx + 1 < m else ""
            out.append("m" if nxt[:1] in ("p", "b", "m") else "n")
        if u.get("visarga"):
            out.append("h")
    return "".join(out)


# ─── Tamil → English letters ─────────────────────────────────────────────────
TA_CONSONANTS = {
    "க": "k", "ங": "n", "ச": "s", "ஞ": "nj", "ட": "t", "ண": "n", "த": "th", "ந": "n", "ப": "p", "ம": "m",
    "ய": "y", "ர": "r", "ல": "l", "வ": "v", "ழ": "zh", "ள": "l", "ற": "r", "ன": "n",
    "ஜ": "j", "ஷ": "sh", "ஸ": "s", "ஹ": "h", "ஶ": "sh",
}
TA_VOWELS = {"அ": "a", "ஆ": "a", "இ": "i", "ஈ": "ee", "உ": "u", "ஊ": "oo", "எ": "e", "ஏ": "e", "ஐ": "ai",
             "ஒ": "o", "ஓ": "o", "ஔ": "au"}
TA_MATRAS = {"ா": "a", "ி": "i", "ீ": "ee", "ு": "u", "ூ": "oo", "ெ": "e", "ே": "e", "ை": "ai", "ொ": "o",
             "ோ": "o", "ௌ": "au"}
TA_SOFT = {"k": "g", "t": "d", "th": "dh"}  # voiced between vowels / after a nasal: முருகன் → Murugan


def _tamil_word(word: str) -> str:
    word = word.replace("ட்ச", "\u0000")  # ட்ச spells the Sanskrit "ksh": லட்சுமி → Lakshmi
    units = []
    for ch in word:
        if ch == "\u0000":
            units.append({"c": "ksh", "v": "a", "c0": "ksh"})
        elif ch in TA_CONSONANTS:
            units.append({"c": TA_CONSONANTS[ch], "v": "a", "c0": TA_CONSONANTS[ch]})
        elif ch in TA_VOWELS:
            units.append({"c": "", "v": TA_VOWELS[ch], "c0": ""})
        elif ch in TA_MATRAS and units:
            units[-1]["v"] = TA_MATRAS[ch]
        elif ch == "்" and units:
            units[-1]["v"] = ""
        else:
            units.append({"c": ch, "v": "", "c0": ch})
    out = []
    for i, u in enumerate(units):
        c = u["c0"]
        prev = units[i - 1] if i else None
        doubled = prev is not None and prev["c0"] == c and prev["v"] == ""
        if prev is not None and u["v"] and not doubled:
            after_nasal = prev["v"] == "" and prev["c0"] in ("n", "nj", "m")
            if c in TA_SOFT and (prev["v"] or after_nasal):      # முருகன் → Murugan, மாதவன் → Madhavan
                c = TA_SOFT[c]
            elif c == "p" and after_nasal:                       # அன்பு → Anbu
                c = "b"
            elif c == "s" and prev["c0"] == "nj" and prev["v"] == "":
                c = "j"
        if doubled and c in ("th", "s"):                          # கார்த்திக் → Karthik, பிச்சை → Pichai
            out[-1] = ""
            c = "th" if c == "th" else "ch"
        nxt = units[i + 1] if i + 1 < len(units) else None
        vowel = u["v"]
        if c == "ksh" and vowel == "u" and nxt is not None and nxt["c0"]:
            vowel = ""                                            # லட்சுமி → Lakshmi
        if c == "k" and vowel == "" and nxt is not None and nxt["c0"] in ("n", "m"):
            c = "g"                                               # விக்னேஷ் → Vignesh
        out.append(c + vowel)
    return "".join(out)



DEVANAGARI = re.compile(r"[ऀ-ॿ]")
TAMIL = re.compile(r"[஀-௿]")
DIGITS = str.maketrans("०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯", "01234567890123456789")


def has_indic(text: str) -> bool:
    return bool(text) and bool(DEVANAGARI.search(text) or TAMIL.search(text))


def to_english_letters(text: str, capitalize: bool = True) -> str:
    """Hindi / Tamil words → English spelling; English words, digits and punctuation are kept."""
    if not text:
        return text
    text = text.translate(DIGITS)

    def convert(match):
        word = match.group(0)
        if DEVANAGARI.search(word):
            latin = _devanagari_word(word)
        elif TAMIL.search(word):
            latin = _tamil_word(word)
        else:
            return word
        return latin[:1].upper() + latin[1:] if capitalize and latin else latin

    return re.sub(r"[ऀ-ॿ஀-௿]+", convert, text).replace("।", ".")


TEXT_TYPES = {"name", "text", "address", "payee"}


def form_value(value: Optional[str], field_type: str) -> Optional[str]:
    """What gets written on the (English) form: Hindi / Tamil text in English letters."""
    if not value or not has_indic(value):
        return value
    if field_type in TEXT_TYPES or field_type is None:
        return to_english_letters(value)
    return value.translate(DIGITS)
