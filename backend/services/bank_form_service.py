"""
Scanned Bank Form Detection (pay-in slips, withdrawal slips, cheque book requisitions,
account opening forms, cash deposit forms, ...)

Bank forms are usually scanned images, so the regular PDF text extractor finds nothing.
This service:
- Renders the page, erases printed box lines and OCRs it with Tesseract
- Fuzzy-matches printed labels against a bank-form vocabulary
- For each label, finds its blank: character boxes, a single box, a table cell,
  an underline / dotted line, ruled lines below it, or plain empty space
- Returns form fields whose position carries exact PDF placements for each value
  (rendered by cheque_service.render_filled_cheque)
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

try:
    import numpy as np
    from PIL import Image
    import Levenshtein
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from services import cheque_service as cs

TARGET_WIDTH = 2400  # OCR works best when the form is about this wide in pixels

# ─── Vocabulary ──────────────────────────────────────────────────────────────
# key: (label, field_type, phrases). Longer phrases win when they overlap shorter ones.
# Keys starting with "_" consume their words without creating a field.
SPECS = {
    "amount_words": ("Amount", "cheque_amount", [
        "rupees in words", "amount in words", "pay self rupees", "pay self", "sum of rupees", "rupees in word", "rupees in",
        "sum of",
    ]),
    # "Rs.____(in figures)____(in words)": these labels come AFTER their blank
    "amount_in_figures": ("Amount", "cheque_amount", ["in figures", "in figurers"]),
    "amount_in_words": ("Amount", "cheque_amount", ["in words"]),
    "amount_pay": ("Amount", "cheque_amount", ["pay", "rupees"]),  # only with a ruled blank or box after it
    "amount_only": ("Amount", "cheque_amount", ["only"]),
    "amount_figures": ("Amount", "cheque_amount", [
        "cash deposit in the account", "total deposit", "total amount", "amount in figures", "received rs", "rs",
    ]),
    "account_number": ("Account Number", "number", [
        "account number", "ac number", "ac no", "account no", "acc no", "acct no", "sb ac number",
        "savings account number",
    ]),
    "holder_name": ("Account Holder Name", "name", [
        "account holders name", "account holder name", "name of account holder", "name of the account holder",
        "for the credit of the bank account of", "for the credit of the bank", "credit of the bank account of",
        "credit of the bank", "credit of the account of",
        "depositors name",
        "depositor name", "customer name", "name of the customer", "name of customer", "name of ac holders",
        "name of ac holder", "ac holders name", "name",
    ]),
    "payee": ("Pay To", "payee", ["pay to", "payee name", "pay to the order of"]),
    "maturity_date": ("Maturity Date", "cheque_date", ["matured on", "date of maturity", "maturity date"]),
    "sb_account": ("SB Account Number (for credit)", "number", ["sb account no", "sb account number", "sb ac no"]),
    "account_office": ("Account Office Name", "text", ["standing at", "name of account office"]),
    "passbook_request": ("Passbook Request Type", "choice", ["passbook request for"]),
    "full_name": ("Full Name", "name", ["full name", "applicant name", "name of applicant", "name in full"]),
    "father_name": ("Father's Name", "name", [
        "fathers name", "father name", "fathers husbands name", "father spouse name", "fathers spouse name",
    ]),
    "mother_name": ("Mother's Name", "name", ["mothers name", "mother name", "mothers maiden name"]),
    "spouse_name": ("Spouse Name", "name", ["spouse name", "spouses name", "husbands name", "wifes name"]),
    "nominee_name": ("Nominee Name", "name", ["nominee name", "name of nominee", "nominee"]),
    "dob": ("Date of Birth", "cheque_date", ["date of birth", "dob", "birth date"]),
    "date": ("Date", "cheque_date", ["date"]),
    "branch": ("Branch Name", "text", [
        "account holders branch", "account holder branch", "branch name", "name of branch", "home branch", "branch",
    ]),
    "branch_code": ("Branch Code", "number", ["branch code", "code no", "code number", "sol id"]),
    "branch_address": ("Branch Address", "text", ["the branch manager", "branch manager"]),
    "address": ("Address", "address", [
        "address mentioned below", "communication address", "residential address", "permanent address",
        "correspondence address", "address",
    ]),
    "mobile": ("Mobile Number", "phone", [
        "mobile tel no", "mobile number", "mobile no", "tel no", "telephone no", "phone number", "phone no",
        "contact number", "contact no", "mobile",
    ]),
    "email": ("Email Address", "text", ["email address", "email id", "e mail", "email"]),
    "pan": ("PAN Number", "pan", ["pan number", "pan card number", "pan no", "pan"]),
    "aadhaar": ("Aadhaar Number", "number", ["aadhaar number", "aadhaar no", "aadhar number", "aadhaar", "aadhar"]),
    "customer_id": ("Customer ID", "text", ["customer id", "cif no", "cif number", "customer no"]),
    "cheque_no": ("Cheque Number", "number", ["cheque no", "cheque number", "chq no"]),
    "leaves": ("Number of Cheque Leaves", "number", ["number of leaves", "no of leaves", "no of cheque leaves"]),
    "occupation": ("Occupation", "text", ["occupation", "profession"]),
    "gender": ("Gender", "gender", ["gender", "sex"]),
    "nationality": ("Nationality", "text", ["nationality"]),
    "pin": ("PIN Code", "number", ["pin code", "pincode", "postal code"]),
    "city": ("City / Town", "text", ["city", "town"]),
    "district": ("District", "text", ["district"]),
    "state": ("State", "text", ["state"]),
    "_ignore": (None, None, [
        "signature of the account holder", "signature of the depositor", "signature of the applicant", "pay in slip",
        "transaction id", "sr no", "tracker id no", "emp id", "verified by", "approved by", "name of bm",
        "name of the bearer", "for office use only", "for bank use only", "for office use", "for bank use",
        "segment customers", "signature", "sign", "with your branch", "for non home branch", "non home branch", "type of account",
        "for office use", "cash handling charges", "state bank of india", "bank of india", "please",
    ]),
}
GROUPS = {"amount_words": "amount", "amount_only": "amount", "amount_figures": "amount", "amount_pay": "amount",
          "amount_in_figures": "amount", "amount_in_words": "amount"}
# Labels printed after their blank: "I/We ______ (Name of the customer)", "Rs.____(in figures)"
LEFT_PHRASES = {"name of the customer", "name of customer", "in figures", "in figurers", "in words", "name of account office"}
NAME_KEYS = {"holder_name", "full_name", "father_name", "mother_name", "spouse_name", "nominee_name", "address"}
CHOICE_SYNONYMS = {
    "issuance": ["first", "new", "fresh", "issue", "pehli", "naya", "नया", "नई", "पहली", "புதிய", "முதல்"],
    "reissuance": ["duplicate", "lost", "stolen", "spoil", "destroy", "damage", "again", "reissue", "re issue",
                   "dobara", "दोबारा", "डुप्लीकेट", "खो", "चोरी", "फट", "மீண்டும்", "நகல்", "தொலை", "திருட"],
    "male": ["male", "man", "boy", "purush", "पुरुष", "ஆண்"],
    "female": ["female", "woman", "girl", "mahila", "महिला", "स्त्री", "பெண்"],
}
SELF_WORDS = ["self", "myself", "me", "khud", "swayam", "सेल्फ", "खुद", "स्वयं", "मुझे", "செல்ஃப்", "நானே", "எனக்கு"]
BELOW_FIRST = {"branch_address", "address"}       # blank is ruled lines under the label
NAME_QUALIFIERS = {"branch", "bank", "father", "fathers", "mother", "mothers", "spouse", "spouses", "husband",
                   "husbands", "nominee", "nominees", "full", "applicant", "applicants", "customer", "guardian",
                   "guardians", "village", "scheme", "holder", "holders"}
COMB_BELOW_OK = {"branch_code", "account_number", "mobile", "pan", "aadhaar", "pin", "date", "dob", "cheque_no", "customer_id"}
CONTINUES = {"holder_name", "full_name", "amount_words", "address", "branch_address"}

QUESTIONS = {
    "amount": {
        "en": "How much money, in rupees, is this form for? For example, five thousand.",
        "hi": "इस फॉर्म में कितने रुपये की राशि है? जैसे, पांच हजार।",
        "ta": "இந்த படிவத்தில் எத்தனை ரூபாய் தொகை? உதாரணமாக, ஐந்து ஆயிரம்.",
    },
    "account_number": {
        "en": "What is the bank account number? Please say each digit clearly.",
        "hi": "बैंक खाता नंबर क्या है? कृपया हर अंक साफ़ बोलें।",
        "ta": "வங்கி கணக்கு எண் என்ன? ஒவ்வொரு எண்ணையும் தெளிவாக சொல்லுங்கள்.",
    },
    "holder_name": {
        "en": "What is the account holder's full name?",
        "hi": "खाताधारक का पूरा नाम क्या है?",
        "ta": "கணக்கு வைத்திருப்பவரின் முழு பெயர் என்ன?",
    },
    "full_name": {
        "en": "What is the applicant's full name for this bank form?",
        "hi": "इस बैंक फॉर्म के लिए आवेदक का पूरा नाम क्या है?",
        "ta": "இந்த வங்கி படிவத்திற்கான விண்ணப்பதாரரின் முழு பெயர் என்ன?",
    },
    "father_name": {
        "en": "What is the father's or husband's name to write on this bank form?",
        "hi": "इस बैंक फॉर्म पर पिता या पति का नाम क्या लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் தந்தை அல்லது கணவர் பெயர் என்ன?",
    },
    "mother_name": {
        "en": "What is the mother's name to write on this bank form?",
        "hi": "इस बैंक फॉर्म पर माता का नाम क्या लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் தாயின் பெயர் என்ன?",
    },
    "spouse_name": {
        "en": "What is the spouse's name to write on this bank form?",
        "hi": "इस बैंक फॉर्म पर पति या पत्नी का नाम क्या लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் வாழ்க்கைத் துணையின் பெயர் என்ன?",
    },
    "nominee_name": {
        "en": "Who is the nominee for this bank account? Please say the nominee's name.",
        "hi": "इस बैंक खाते का नॉमिनी कौन है? कृपया नॉमिनी का नाम बताएं।",
        "ta": "இந்த வங்கி கணக்கின் நாமினி யார்? நாமினியின் பெயரை சொல்லுங்கள்.",
    },
    "dob": {
        "en": "What is the date of birth to write on this bank form? Say day, month and year.",
        "hi": "इस बैंक फॉर्म पर जन्म तिथि क्या लिखनी है? दिन, महीना और साल बताएं।",
        "ta": "இந்த வங்கி படிவத்தில் பிறந்த தேதி என்ன? நாள், மாதம், ஆண்டு சொல்லுங்கள்.",
    },
    "date": {
        "en": "What date should be written on this form? You can just say today.",
        "hi": "इस फॉर्म पर कौन सी तारीख लिखनी है? आप सिर्फ 'आज' बोल सकते हैं।",
        "ta": "இந்த படிவத்தில் எந்த தேதி எழுத வேண்டும்? 'இன்று' என்று சொல்லலாம்.",
    },
    "branch": {
        "en": "Which branch of the bank is the account in? Please say the branch name.",
        "hi": "खाता बैंक की किस शाखा में है? कृपया शाखा का नाम बताएं।",
        "ta": "கணக்கு எந்த வங்கிக் கிளையில் உள்ளது? கிளையின் பெயரை சொல்லுங்கள்.",
    },
    "branch_code": {
        "en": "What is the bank branch code? Please say the digits.",
        "hi": "बैंक शाखा का कोड क्या है? कृपया अंक बताएं।",
        "ta": "வங்கிக் கிளையின் குறியீட்டு எண் என்ன? எண்களை சொல்லுங்கள்.",
    },
    "branch_address": {
        "en": "Which bank branch is this letter addressed to? Please say the branch name and city.",
        "hi": "यह पत्र किस बैंक शाखा को लिखा है? कृपया शाखा का नाम और शहर बताएं।",
        "ta": "இந்த கடிதம் எந்த வங்கிக் கிளைக்கு? கிளையின் பெயரையும் ஊரையும் சொல்லுங்கள்.",
    },
    "address": {
        "en": "What is the full address to write on this bank form?",
        "hi": "इस बैंक फॉर्म पर पूरा पता क्या लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் எழுத வேண்டிய முழு முகவரி என்ன?",
    },
    "mobile": {
        "en": "What is the 10-digit mobile number for this bank form?",
        "hi": "इस बैंक फॉर्म के लिए 10 अंकों का मोबाइल नंबर क्या है?",
        "ta": "இந்த வங்கி படிவத்திற்கான 10 இலக்க மொபைல் எண் என்ன?",
    },
    "email": {
        "en": "What is the email address for this bank form?",
        "hi": "इस बैंक फॉर्म के लिए ईमेल पता क्या है?",
        "ta": "இந்த வங்கி படிவத்திற்கான மின்னஞ்சல் முகவரி என்ன?",
    },
    "pan": {
        "en": "What is the PAN card number? Say the letters and digits one by one.",
        "hi": "पैन कार्ड नंबर क्या है? अक्षर और अंक एक-एक करके बोलें।",
        "ta": "பான் கார்டு எண் என்ன? எழுத்துகளையும் எண்களையும் ஒவ்வொன்றாக சொல்லுங்கள்.",
    },
    "aadhaar": {
        "en": "What is the 12-digit Aadhaar number for this bank form?",
        "hi": "इस बैंक फॉर्म के लिए 12 अंकों का आधार नंबर क्या है?",
        "ta": "இந்த வங்கி படிவத்திற்கான 12 இலக்க ஆதார் எண் என்ன?",
    },
    "customer_id": {
        "en": "What is the bank customer ID or CIF number?",
        "hi": "बैंक कस्टमर आईडी या सीआईएफ नंबर क्या है?",
        "ta": "வங்கி வாடிக்கையாளர் ஐடி அல்லது சிஐஎஃப் எண் என்ன?",
    },
    "cheque_no": {
        "en": "What is the cheque number on this bank form?",
        "hi": "इस बैंक फॉर्म पर चेक नंबर क्या है?",
        "ta": "இந்த வங்கி படிவத்தில் காசோலை எண் என்ன?",
    },
    "leaves": {
        "en": "How many cheque leaves do you need in the cheque book?",
        "hi": "चेक बुक में कितने पन्ने चाहिए?",
        "ta": "காசோலை புத்தகத்தில் எத்தனை தாள்கள் வேண்டும்?",
    },
    "occupation": {
        "en": "What is the occupation to write on this bank form?",
        "hi": "इस बैंक फॉर्म पर व्यवसाय क्या लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் தொழில் என்ன?",
    },
    "gender": {
        "en": "What is the gender to write on this bank form? Male, female or other?",
        "hi": "इस बैंक फॉर्म पर लिंग क्या लिखना है? पुरुष, महिला या अन्य?",
        "ta": "இந்த வங்கி படிவத்தில் பாலினம் என்ன? ஆண், பெண் அல்லது மற்றவை?",
    },
    "nationality": {
        "en": "What is the nationality to write on this bank form?",
        "hi": "इस बैंक फॉर्म पर राष्ट्रीयता क्या लिखनी है?",
        "ta": "இந்த வங்கி படிவத்தில் தேசியம் என்ன?",
    },
    "pin": {
        "en": "What is the 6-digit PIN code for this bank form?",
        "hi": "इस बैंक फॉर्म के लिए 6 अंकों का पिन कोड क्या है?",
        "ta": "இந்த வங்கி படிவத்திற்கான 6 இலக்க பின் குறியீடு என்ன?",
    },
    "city": {
        "en": "Which city or town should be written on this bank form?",
        "hi": "इस बैंक फॉर्म पर कौन सा शहर या कस्बा लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் எந்த நகரம் அல்லது ஊர்?",
    },
    "district": {
        "en": "Which district should be written on this bank form?",
        "hi": "इस बैंक फॉर्म पर कौन सा जिला लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் எந்த மாவட்டம்?",
    },
    "payee": {
        "en": "Who should this withdrawal be paid to? Say self if the money is for you.",
        "hi": "यह राशि किसे दी जानी है? अगर पैसे आपके लिए हैं तो 'सेल्फ' बोलें।",
        "ta": "இந்த தொகை யாருக்கு வழங்கப்பட வேண்டும்? உங்களுக்கே என்றால் 'செல்ஃப்' என்று சொல்லுங்கள்.",
    },
    "maturity_date": {
        "en": "On what date did the account mature? Please say the maturity date.",
        "hi": "खाता किस तारीख को परिपक्व हुआ? कृपया परिपक्वता की तारीख बताएं।",
        "ta": "கணக்கு எந்த தேதியில் முதிர்வடைந்தது? முதிர்வு தேதியை சொல்லுங்கள்.",
    },
    "sb_account": {
        "en": "Which savings bank account number should the money be credited to?",
        "hi": "पैसे किस बचत खाते में जमा किए जाएं? कृपया वह खाता नंबर बताएं।",
        "ta": "பணம் எந்த சேமிப்பு கணக்கு எண்ணில் வரவு வைக்கப்பட வேண்டும்?",
    },
    "account_office": {
        "en": "At which branch or post office is that savings account held?",
        "hi": "वह बचत खाता किस शाखा या डाकघर में है?",
        "ta": "அந்த சேமிப்பு கணக்கு எந்த கிளை அல்லது தபால் நிலையத்தில் உள்ளது?",
    },
    "passbook_request": {
        "en": "Is this passbook request for first-time issuance, or reissuance because the old one was lost or damaged?",
        "hi": "क्या यह पासबुक पहली बार जारी करने के लिए है, या पुरानी खो जाने या खराब होने पर दोबारा जारी करने के लिए?",
        "ta": "இது முதல் முறையாக பாஸ்புக் வழங்குவதற்கா, அல்லது பழையது தொலைந்ததால் அல்லது சேதமடைந்ததால் மீண்டும் வழங்குவதற்கா?",
    },
    "state": {
        "en": "Which state should be written on this bank form?",
        "hi": "इस बैंक फॉर्म पर कौन सा राज्य लिखना है?",
        "ta": "இந்த வங்கி படிவத்தில் எந்த மாநிலம்?",
    },
}
QUESTION_TRANSLATIONS = {q["en"]: q for q in QUESTIONS.values()}

TEXT_PDF_KEYWORDS = re.compile(
    r"pay[\s-]*in[\s-]*slip|deposit\s*slip|withdrawal\s*slip|withdrawal\s*form|cheque\s*book\s*requisition"
    r"|requisition\s*slip|account\s*opening\s*form|cash\s*deposit\s*(?:form|slip)|counterfoil",
    re.IGNORECASE,
)


def translate_question(english_question: str, language: str) -> Optional[str]:
    q = QUESTION_TRANSLATIONS.get(english_question)
    return q.get(language, q["en"]) if q else None


def looks_like_bank_form(file_path: str, filename: str, is_pdf: bool) -> bool:
    """Real-world forms get exact placement; the app's own demo templates keep the regular extractor."""
    if not is_pdf:
        return True
    if TEXT_PDF_KEYWORDS.search((filename or "").replace("_", " ")):
        return True
    try:
        import pypdf
        text = pypdf.PdfReader(file_path).pages[0].extract_text() or ""
        return DEMO_TEMPLATE_MARKER not in text
    except Exception:
        return False


DEMO_TEMPLATE_MARKER = "FinAccess AI Form Template"


def interpret_choice(text: str, options: list[str]) -> str:
    """Map a spoken answer onto one of the printed tick-box options."""
    t = text.lower()
    for opt in sorted(options, key=len, reverse=True):  # "Reissuance" before "Issuance"
        if opt.lower() in t:
            return opt
    for opt in sorted(options, key=len, reverse=True):
        if any(syn in t for syn in CHOICE_SYNONYMS.get(opt.lower(), [])):
            return opt
    ordinals = [["1", "one", "first", "ek", "pehla", "एक", "पहला", "ஒன்று", "முதல்"],
                ["2", "two", "second", "do", "doosra", "दो", "दूसरा", "இரண்டு", "இரண்டாவது"]]
    words = re.findall(r"[\w\u0900-\u097F\u0B80-\u0BFF]+", t)
    for idx in reversed(range(min(len(options), len(ordinals)))):  # "second one" is the second option
        if any(n in words for n in ordinals[idx]):
            return options[idx]
    return text.strip()


def interpret_payee(text: str) -> Optional[str]:
    """'self' / 'खुद' → Self; anything else is cleaned like a name by the caller."""
    t = text.lower().strip()
    if any(re.search(rf"(^|\s){re.escape(w)}($|\s)", t) for w in SELF_WORDS):
        return "Self"
    return None


# ─── Image analysis helpers ──────────────────────────────────────────────────
def _runs(mask, min_len: int):
    """(row, start, end) of horizontal runs of True with length >= min_len."""
    out = []
    for y in np.where(mask.sum(axis=1) >= min_len)[0]:
        edges = np.diff(np.concatenate([[0], mask[y].astype(np.int8), [0]]))
        for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
            if e - s >= min_len:
                out.append((int(y), int(s), int(e)))
    return out


def _merge_segments(runs, gap_along: int, gap_across: int = 3) -> list[dict]:
    """Merge (pos, start, end) runs from neighbouring rows into segments {p0, p1, s0, s1}."""
    segs = []
    for p, s, e in runs:
        for m in segs:
            if p - m["p1"] <= gap_across and s < m["s1"] + gap_along and e > m["s0"] - gap_along:
                m["p1"] = p
                m["s0"], m["s1"] = min(m["s0"], s), max(m["s1"], e)
                break
        else:
            segs.append({"p0": p, "p1": p, "s0": s, "s1": e})
    return segs


def _bridge(mask, gap: int):
    """Close small horizontal gaps so dotted / dashed leaders become solid rules."""
    out = mask.copy()
    for y in np.where(mask.any(axis=1))[0]:
        xs = np.where(mask[y])[0]
        jumps = np.where((np.diff(xs) > 1) & (np.diff(xs) <= gap))[0]
        for j in jumps:
            out[y, xs[j]:xs[j + 1]] = True
    return out


def _text_height(words, width) -> float:
    # Low percentile: words fused with box edges report inflated heights
    heights = [w["h"] for w in words if len(re.sub(r"[^A-Za-z0-9]", "", w["text"])) >= 3]
    return float(np.percentile(heights, 30)) if heights else width * 0.012


def _analyse_lines(gray, text_h):
    height, width = gray.shape
    dark = gray < cs._ink_threshold(gray)

    # Solid rules / box edges (used to erase them before OCR); must be clearly longer than letter strokes
    h_runs = _runs(dark, int(max(width * 0.03, text_h * 2.5)))
    v_runs = _runs(dark.T, int(max(width * 0.008, text_h * 1.4)))
    line_mask = np.zeros_like(dark)
    for y, s, e in h_runs:
        line_mask[max(0, y - 1):y + 2, s:e] = True
    for x, s, e in v_runs:
        line_mask[s:e, max(0, x - 1):x + 2] = True

    # Rules including dotted / dashed leaders
    bridged = _bridge(dark, max(6, int(text_h * 0.9)))
    probe = max(8, int(width * 0.01))
    # Keep only thin runs (blank just above and below), so bridged text lines are not mistaken for rules
    k = max(4, int(text_h * 0.6))
    thin = []
    for y, s, e in _runs(bridged, int(width * 0.05)):
        above = dark[max(0, y - k), s:e].mean()
        below_row = dark[min(height - 1, y + k), s:e].mean()
        if above < 0.25 and below_row < 0.25:
            thin.append((y, s, e))
    hrules = []
    for m in _merge_segments(thin, gap_along=int(width * 0.01)):
        if m["p1"] - m["p0"] > max(6, height * 0.006, text_h * 0.4):  # thicker = text, not a rule
            continue
        # Devanagari headlines (shirorekha) look like rules but have letters hanging below them
        below = dark[m["p1"] + 3:m["p1"] + 3 + probe, m["s0"]:m["s1"]]
        if below.size and below.any(axis=0).mean() > 0.45 and below.mean() > 0.08:
            continue
        hrules.append({"y0": m["p0"], "y1": m["p1"], "x0": m["s0"], "x1": m["s1"]})
    vsegs = [
        {"x0": m["p0"], "x1": m["p1"], "y0": m["s0"], "y1": m["s1"]}
        for m in _merge_segments(v_runs, gap_along=4)
        if m["p1"] - m["p0"] <= max(6, width * 0.004)
    ]
    return line_mask, hrules, vsegs


def _ocr(gray, line_mask, first_pass) -> list[dict]:
    """Merge OCR of the line-erased page (grey and binarised) with the plain first pass."""
    cleaned = np.where(line_mask, 255, gray).clip(0, 255).astype("uint8")
    binary = np.where((gray < cs._ink_threshold(gray)) & ~line_mask, 0, 255).astype("uint8")
    # Sparse (psm 11) and block (psm 6) modes recover different labels on noisy scans; run them in parallel
    jobs = [(cleaned, "11"), (binary, "11"), (binary, "6"), (cleaned, "6")]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(lambda job: cs._ocr_words(Image.fromarray(job[0]), psm=job[1]), jobs))
    words = []
    passes = [(r, 0) for r in results] + [(first_pass, 10)]
    for found, penalty in passes:
        for w in found:
            w = {**w, "conf": w["conf"] - penalty}
            overlaps = [o for o in words if w["x0"] < o["x1"] and o["x0"] < w["x1"] and w["y0"] < o["y1"] and o["y0"] < w["y1"]]
            if not overlaps:
                words.append(w)
            elif w["conf"] > max(o["conf"] for o in overlaps) + 5:
                words = [o for o in words if o not in overlaps] + [w]
    return words


def _drop_text_rules(hrules, words) -> list[dict]:
    """A 'rule' running through the middle of recognised words is really a line of text."""
    real = [w for w in words if len(re.sub(r"[^A-Za-z0-9]", "", w["text"])) >= 2 and w["conf"] >= 60]
    kept = []
    for r in hrules:
        y = (r["y0"] + r["y1"]) / 2
        covered = sum(
            max(0, min(r["x1"], w["x1"]) - max(r["x0"], w["x0"]))
            for w in real if w["y0"] + w["h"] * 0.15 < y < w["y1"] - w["h"] * 0.15
        )
        if covered < (r["x1"] - r["x0"]) * 0.3:
            kept.append(r)
    return kept


def _is_junk(word, hrules) -> bool:
    alnum = re.sub(r"[^A-Za-z0-9]", "", word["text"])
    if len(alnum) < 2 and word["text"].lower() not in ("rs", "no"):
        return True
    if re.fullmatch(r"[eEsSoO._\-—–=~|]+", word["text"]):
        return True
    if word["x1"] - word["x0"] > len(word["text"]) * word["h"] * 2.5:
        return True  # an empty box outline read as a "word"
    yc = (word["y0"] + word["y1"]) / 2
    # OCR noise produced by dotted / dashed lines sits right on the rule
    return any(r["y0"] - word["h"] * 0.35 <= yc <= r["y1"] + word["h"] * 0.35 and r["x0"] <= word["x0"] and word["x1"] <= r["x1"]
               for r in hrules) and len(alnum) <= 4


def _tokens(words) -> list[dict]:
    """Split OCR words into normalised tokens (on / - : |), each with an approximate x-range."""
    tokens = []
    for w in words:
        text = re.sub(r"a\s*/\s*c\b", "ac", w["text"].lower())
        parts = [(m.start(), m.end()) for m in re.finditer(r"[^/\-:|,;()\[\]]+", text)]
        n = max(1, len(text))
        for s, e in parts:
            norm = re.sub(r"[^a-z0-9]", "", text[s:e])
            if not norm:
                continue
            x0 = w["x0"] + (w["x1"] - w["x0"]) * s / n
            x1 = w["x0"] + (w["x1"] - w["x0"]) * e / n
            tokens.append({"norm": norm, "x0": x0, "x1": x1, "word": w})
    return tokens


def _rows(words) -> list[list[dict]]:
    """Group words into reading-order phrases (same text line, small horizontal gaps)."""
    lines = []
    for w in sorted(words, key=lambda w: (w["y0"] + w["y1"]) / 2):
        yc = (w["y0"] + w["y1"]) / 2
        for line in lines:
            if abs(line["yc"] - yc) < min(line["h"], w["h"]) * 0.55:
                line["words"].append(w)
                break
        else:
            lines.append({"yc": yc, "h": w["h"], "words": [w]})

    phrases = []
    for line in lines:
        current = []
        for w in sorted(line["words"], key=lambda w: w["x0"]):
            if current and w["x0"] - current[-1]["x1"] > max(current[-1]["h"], w["h"]) * 2.2:
                phrases.append(current)
                current = []
            current.append(w)
        phrases.append(current)
    return phrases


OCR_CONFUSIONS = {frozenset(p) for p in [("i", "l"), ("l", "1"), ("i", "1"), ("o", "0"), ("s", "5"), ("e", "c"), ("t", "f")]}


def _short_match(joined: str, target: str) -> bool:
    """Exact match for short labels, allowing one common OCR confusion (Oniy → Only)."""
    if joined == target:
        return True
    if len(joined) != len(target) or len(target) < 4:
        return False
    diffs = [(a, b) for a, b in zip(joined, target) if a != b]
    return len(diffs) == 1 and frozenset(diffs[0]) in OCR_CONFUSIONS


def _match_labels(rows) -> list[dict]:
    candidates = []
    for row in rows:
        toks = _tokens(row)
        for key, (_, _, phrases) in SPECS.items():
            for phrase in phrases:
                target = phrase.replace(" ", "")
                n = len(phrase.split())
                for i in range(len(toks)):
                    for span in range(max(1, n - 1), n + 2):
                        window = toks[i:i + span]
                        if len(window) < span:
                            break
                        joined = "".join(t["norm"] for t in window)
                        if all(t["word"].get("exact") for t in window):
                            # text read from the PDF itself is exact: no OCR tolerance
                            if joined == target:
                                candidates.append({"key": key, "phrase": phrase, "score": 1.0, "n": n,
                                                   "tokens": window, "row": row})
                            continue
                        first_word = phrase.split()[0]
                        head = window[0]["norm"]
                        if (len(first_word) >= 4 and head != first_word and head.endswith(first_word)
                                and len(head) - len(first_word) <= 6):
                            # Hindi text glued onto the English label by OCR: "SIVCASH" → "CASH"
                            joined = first_word + "".join(t["norm"] for t in window[1:])
                        if len(first_word) <= 3 and not joined.startswith(first_word):
                            score = 0.0  # "Account Number" is not "SB Account Number"
                        elif len(target) <= 5:
                            score = 1.0 if _short_match(joined, target) else 0.0
                        elif min(len(joined), len(target)) / max(len(joined), len(target)) < 0.85:
                            score = 0.0  # a fragment of the phrase is not the phrase
                        else:
                            score = Levenshtein.ratio(joined, target)
                        threshold = 0.91 if len(target) <= 10 else 0.86 if len(target) <= 14 else 0.8
                        if score >= threshold:
                            candidates.append({
                                "key": key, "phrase": phrase, "score": score, "n": n, "tokens": window, "row": row,
                            })
    # Longest phrases first, then best score; each word can belong to one label only
    candidates.sort(key=lambda c: (-len(c["phrase"].replace(" ", "")), -c["score"]))
    all_words = [w for row in rows for w in row]
    used, labels = set(), []
    for c in candidates:
        ids = {id(t["word"]) for t in c["tokens"]}
        if ids & used:
            continue
        if c["phrase"] == "name":
            # nearest word to the left on the same line, even if OCR put it in another phrase
            word = c["tokens"][0]["word"]
            yc = (word["y0"] + word["y1"]) / 2
            lefts = [w for w in all_words if w["x1"] <= word["x0"] + 2 and word["x0"] - w["x1"] < word["h"] * 2.5
                     and abs((w["y0"] + w["y1"]) / 2 - yc) < word["h"] * 0.7]
            if lefts:
                prev = max(lefts, key=lambda w: w["x1"])
                if _tokens([prev]) and _tokens([prev])[-1]["norm"] in NAME_QUALIFIERS:
                    continue
        used |= ids
        if c["key"].startswith("_"):
            continue
        words = [t["word"] for t in c["tokens"]]
        labels.append({
            "key": c["key"],
            "phrase": c["phrase"],
            "x0": min(t["x0"] for t in c["tokens"]), "x1": max(t["x1"] for t in c["tokens"]),
            "wx0": min(w["x0"] for w in words), "wx1": max(w["x1"] for w in words),
            "y0": min(w["y0"] for w in words), "y1": max(w["y1"] for w in words),
            "h": float(np.median([w["h"] for w in words])),
            "words": words,
            "row_words": c["row"],
            "row_x0": min(w["x0"] for w in c["row"]),
        })
    labels.sort(key=lambda l: (l["y0"], l["x0"]))
    return labels


# ─── Blank finding ───────────────────────────────────────────────────────────
class _Page:
    def __init__(self, gray, words, hrules, vsegs, tf):
        self.gray, self.words, self.hrules, self.vsegs, self.tf = gray, words, hrules, vsegs, tf
        self.height, self.width = gray.shape
        xs = [w["x1"] for w in words] + [r["x1"] for r in hrules]
        self.content_right = max(xs) if xs else self.width * 0.95
        self.text_h = float(np.median([w["h"] for w in words])) if words else 20.0
        self.dark = gray < cs._ink_threshold(gray)

    def ink_ratio(self, x0, x1, y0, y1) -> float:
        region = self.dark[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))]
        return float(region.mean()) if region.size else 0.0

    def has_border(self, x0, x1, top, bottom) -> bool:
        """Printed horizontal edges join x0..x1 at both the top and bottom (i.e. it is a real box)."""
        if x1 - x0 < 4:
            return False
        for y in (top, bottom):
            band = self.dark[max(0, int(y) - 4):int(y) + 5, int(x0) + 2:int(x1) - 1]
            if not band.size or band.any(axis=0).mean() <= 0.6:
                return False
        return True

    def ink_end(self, x_start, y0, y1, x_limit, gap):
        """First x after x_start where a blank stretch of `gap` px begins (skips untranscribed label text)."""
        y1 = y1 - (y1 - y0) * 0.25  # dotted leaders / underlines run along the baseline
        band = self.dark[max(0, int(y0)):int(y1), int(x_start):max(int(x_start), int(x_limit))]
        cols = band.sum(axis=0) >= max(3, (y1 - y0) * 0.2)  # letters, not the dots of a leader
        run = 0
        for i, has_ink in enumerate(cols):
            run = 0 if has_ink else run + 1
            if run >= gap:
                return x_start + i - run + 1
        return x_start

    def to_original(self, x, y):
        """Map a point in the deskewed image back to the original (un-rotated) image."""
        angle = self.tf.get("skew", 0.0)
        if not angle:
            return x, y
        t = np.radians(angle)
        cx, cy = self.width / 2, self.height / 2
        dx, dy = x - cx, y - cy
        return cx + np.cos(t) * dx - np.sin(t) * dy, cy + np.sin(t) * dx + np.cos(t) * dy

    def area(self, x0, x1, baseline, size_px):
        s = self.tf["scale"]
        ox0, oy = self.to_original(x0, baseline)
        ox1, _ = self.to_original(x1, baseline)
        return {
            "x0": round(self.tf["left"] + float(ox0) * s, 2),
            "x1": round(self.tf["left"] + float(ox1) * s, 2),
            "baseline": round(self.tf["top"] - float(oy) * s, 2),
            "size": round(max(5.0, min(14.0, size_px * s)), 2),
        }

    def words_in(self, x0, x1, y0, y1, exclude=()):
        return [w for w in self.words if w not in exclude
                and w["x0"] < x1 and w["x1"] > x0 and w["y0"] < y1 and w["y1"] > y0]

    def row_obstacle(self, label, side="right"):
        """Nearest printed word on the label's row, to the right (or left) of the label."""
        yc, h = (label["y0"] + label["y1"]) / 2, label["h"]
        # The label's own phrase is not an obstacle, except printed numbers ("Code No. 3003407")
        own = [w for w in label.get("row_words", label["words"]) if w in label["words"] or not re.search(r"\d", w["text"])]
        row = [w for w in self.words if w not in own and abs((w["y0"] + w["y1"]) / 2 - yc) < h * 0.6]
        if side == "right":
            xs = sorted((w for w in row if w["x0"] > label["wx1"] - 2), key=lambda w: w["x0"])
            # skip the label's own tail ("account of", "(in words)") chained right after it
            end = label["wx1"]
            while xs and xs[0]["x0"] - end <= h * 1.2 and not re.search(r"\d", xs[0]["text"]):
                end = xs.pop(0)["x1"]
            return xs[0] if xs else None
        xs = [w for w in row if w["x1"] < label["wx0"] + 2]
        return max(xs, key=lambda w: w["x1"]) if xs else None

    def vsegs_crossing(self, yc, x_min=-1, x_max=None, slack=0.0):
        x_max = self.width if x_max is None else x_max
        return sorted((v for v in self.vsegs if v["y0"] <= yc + slack and v["y1"] >= yc - slack and x_min <= v["x0"] <= x_max),
                      key=lambda v: v["x0"])


def _comb_cells(page, label, segs, limit_x):
    """Evenly spaced vertical edges right after a label → one character per box."""
    h = label["h"]
    segs = [v for v in segs if v["x0"] < limit_x]
    if len(segs) < 4 or segs[0]["x0"] - label["wx1"] > h * 8:
        return None
    cells = []
    for a, b in zip(segs, segs[1:]):
        gap = b["x0"] - a["x1"]
        if gap > h * 5 and cells:
            break
        if not cells and a["x0"] - label["wx1"] > h * 8:
            return None  # boxes further along the row belong to another label
        if not (h * 0.5 <= gap <= h * 3.2):
            continue
        top, bottom = int(max(a["y0"], b["y0"])), int(min(a["y1"], b["y1"]))
        span = page.dark[:, int(a["x1"]) + 2:int(b["x0"]) - 1]
        top_border = span[max(0, top - 3):top + 5].any(axis=0).mean() if span.size else 0
        bottom_border = span[max(0, bottom - 4):bottom + 4].any(axis=0).mean() if span.size else 0
        # closed boxes, or tick marks standing on a baseline (open at the top)
        if (top_border > 0.6 and bottom - top >= h * 0.8) or (bottom_border > 0.6 and bottom - top >= h * 0.35):
            cells.append((a["x1"] + 1, b["x0"] - 1, top, bottom))
    return cells if len(cells) >= 3 else None


def _comb_below(page, label):
    """Character boxes printed on the line just under the label."""
    h = label["h"]
    for step in (0.6, 1.0, 1.5, 2.0, 2.5):
        y = label["y1"] + h * step
        segs = page.vsegs_crossing(y, x_min=label["row_x0"] - h * 12, x_max=label["wx1"] + h * 12)
        if not segs:
            continue
        probe = {**label, "wx1": segs[0]["x0"] - 1}
        combs = _comb_cells(page, probe, segs, page.width)
        if combs:
            cells = [_cell_area(page, *cell) for cell in combs]
            fallback = {**cells[0], "x1": max(c["x1"] for c in cells)}
            return {"type": "comb", "cells": cells, "fallback": fallback}, (combs[0][2], combs[0][3], combs[0][0], combs[-1][1])
    return None, None


def _right_blank(page, label, key):
    h = label["h"]
    yc = (label["y0"] + label["y1"]) / 2
    obstacle = page.row_obstacle(label)
    limit_x = obstacle["x0"] - h * 0.4 if obstacle else page.content_right
    size_px = max(h, page.text_h) * 1.1

    # 1) Character boxes / table cells / single box
    segs = page.vsegs_crossing(yc, x_min=label["wx1"] - h * 0.3, slack=h * 0.3)
    combs = _comb_cells(page, label, segs, page.width)  # box rows end at a large gap, not at OCR noise
    if combs:
        if key in NAME_KEYS:
            combs = combs + (_comb_continuation(page, label, combs) or [])
        cells = [_cell_area(page, *cell) for cell in combs]
        fallback = {**cells[0], "x1": max(c["x1"] for c in cells)}  # value longer than the boxes
        return {"type": "comb", "cells": cells, "fallback": fallback}, (combs[0][2], combs[0][3], combs[0][0], combs[-1][1])

    lefts = [v for v in page.vsegs_crossing(yc, x_max=label["wx0"]) if v["x1"] <= label["wx0"] + 2]
    inside = bool(lefts) and label["wx0"] - lefts[-1]["x1"] < h * 3
    if segs and segs[0]["x0"] < limit_x + h:
        first = segs[0]
        second = segs[1] if len(segs) > 1 else None
        if key == "amount_figures" and second and first["x0"] - label["wx1"] > h * 2:
            # Table row: amount goes in the column after the label's cell (paise in a narrow next cell)
            third = segs[2] if len(segs) > 2 else None
            top, bottom = max(first["y0"], second["y0"]), min(first["y1"], second["y1"])
            cell_h = min(bottom - top, h * 2.2)
            base = yc + h * 0.35
            p = {"type": "amount_figures",
                 "area": page.area(first["x1"] + h * 0.4, second["x0"] - h * 0.3, base, min(size_px * 1.15, cell_h * 0.8))}
            if third and (third["x0"] - second["x1"]) < (second["x0"] - first["x1"]) * 0.5:
                p["paise"] = page.area(second["x1"] + 2, third["x0"] - 2, base, min(size_px * 1.15, cell_h * 0.8))
            return p, (top, bottom, first["x1"], second["x0"])
        gap_words = page.words_in(label["wx1"] + 2, first["x0"] - 2, label["y0"], label["y1"], exclude=label["row_words"])
        if second and not inside and not gap_words:
            x0, x1 = first["x1"], second["x0"]                  # box to the right of the label
        else:
            # label printed inside the box / cell: write after the label's own ink
            x0 = page.ink_end(label["wx1"], label["y0"], label["y1"], first["x0"], h * 0.8)
            x1 = first["x0"]
        top, bottom = first["y0"], first["y1"]
        if second and x0 == first["x1"]:
            top, bottom = max(first["y0"], second["y0"]), min(first["y1"], second["y1"])
        # (ignore OCR noise read off the box borders themselves)
        # A field box is about one text line tall: shorter is a tick on a line, taller is a column / page border
        is_box = h * 0.8 <= bottom - top <= h * 3 and page.has_border(x0, x1, top, bottom)
        if is_box and x1 - x0 >= h * 2.5 and not page.words_in(x0 + h * 0.6, x1 - h * 0.6, top + 2, bottom - 2, exclude=label["words"]):
            box_h = bottom - top
            base = (top + bottom) / 2 + min(size_px, box_h * 0.6) * 0.36
            return ({"type": "text", "lines": [page.area(x0 + h * 0.4, x1 - h * 0.3, base, min(size_px, box_h * 0.62))]},
                    (top, bottom, x0, x1))

    # 2) Underline / dotted leader on this row
    # words chained right after the label ("(in words)", ":") belong to it
    tail_end = label["wx1"]
    for w in sorted(page.words_in(label["wx1"] + 2, page.width, label["y0"], label["y1"], exclude=label["words"]), key=lambda w: w["x0"]):
        if w["x0"] - tail_end > h * 3 or re.search(r"\d", w["text"]):
            break
        tail_end = w["x1"]

    def near(r):
        if r["x0"] < label["wx1"] + h * 6:
            return True
        # leader starts after the label's tail text such as "(in words)"
        return r["x0"] < tail_end + h * 8 and not page.words_in(tail_end + 2, r["x0"], label["y0"], label["y1"], exclude=label["words"])

    rules = [r for r in page.hrules
             if (label["y0"] + label["y1"]) / 2 <= r["y0"] <= label["y1"] + h * 1.2
             and r["x1"] > label["wx1"] + h * 3 and near(r)]
    if key in ("date", "dob", "maturity_date"):
        parts = _slash_date_parts(page, label, size_px)
        if parts:
            return parts
    if rules:
        r = min(rules, key=lambda r: r["y0"])
        x0 = max(label["wx1"] + h * 0.4, r["x0"])
        x0 = max(x0, page.ink_end(label["wx1"], label["y0"], label["y1"], r["x1"], h * 0.8))
        x1 = min(r["x1"], limit_x)
        base = r["y0"] - h * 0.2
        if obstacle and key == "date" and re.fullmatch(r"20\W*", obstacle["text"]) and r["x1"] > obstacle["x1"] + h:
            # "Date ........ 20 ....": write DD/MM/ before the printed 20 and YY after it
            return ({"type": "date_prefix", "lines": [page.area(x0, x1, base, size_px)],
                     "year": page.area(obstacle["x1"] + h * 0.15, min(r["x1"], obstacle["x1"] + h * 3), base, size_px)},
                    (r["y0"] - h, r["y0"], x0, r["x1"]))
        if x1 - x0 >= h * 2.5 and page.ink_ratio(x0, x1, r["y0"] - h * 0.9, r["y0"] - 3) < 0.05:
            return {"type": "text", "lines": [page.area(x0, x1, base, size_px)]}, (r["y0"] - h, r["y0"], x0, x1)

    # 3) Plain empty space after the label ("NAME: ...", "Date: ...")
    x0 = max(label["wx1"] + h * 0.6, page.ink_end(label["wx1"], label["y0"], label["y1"], limit_x, h * 0.8) + h * 0.3)
    x1 = min(limit_x, x0 + h * 30, page.content_right)
    if x1 - x0 >= h * 4 and page.ink_ratio(x0, x1, label["y0"], label["y1"]) < 0.03:
        return {"type": "text", "lines": [page.area(x0, x1, label["y1"], size_px)]}, (label["y0"], label["y1"], x0, x1)
    return None, None


def _slash_date_parts(page, label, size_px):
    """'Date: ____/_____/ 20 _ _' → day, month and (2-digit) year slots."""
    h = label["h"]
    yc = (label["y0"] + label["y1"]) / 2
    row = sorted((r for r in page.hrules if yc <= r["y0"] <= label["y1"] + h * 1.2
                  and r["x0"] >= label["wx1"] - h and r["x0"] < label["wx1"] + h * 25 and r["x1"] - r["x0"] >= h * 1.2),
                 key=lambda r: r["x0"])
    merged = []
    for r in row:  # drop duplicates of the same rule found twice (image + vector)
        if merged and r["x0"] < merged[-1]["x1"] - h * 0.3:
            merged[-1] = {**merged[-1], "x1": max(merged[-1]["x1"], r["x1"])}
        else:
            merged.append(r)
    twenty = [w for w in page.words if abs((w["y0"] + w["y1"]) / 2 - yc) < h * 0.8 and w["x0"] > label["wx1"]
              and re.fullmatch(r"/?\s*20[\W_]*", w["text"].strip())]
    if len(merged) == 1 and twenty and twenty[0]["x0"] >= merged[0]["x1"] - h:
        # "____/_____" drawn as one line with a printed slash on it: split at the slash
        r = merged[0]
        y0 = int(r["y0"] - h * 1.1)
        band = page.dark[max(0, y0):int(r["y0"]) - 2, int(r["x0"]) + 2:int(r["x1"]) - 2]
        cols = np.where(band.any(axis=0))[0] if band.size else []
        clusters = []
        for x in cols:
            if clusters and x - clusters[-1][1] <= 3:
                clusters[-1][1] = x
            else:
                clusters.append([x, x])
        slashes = [c for c in clusters if c[1] - c[0] < h * 0.8]
        if len(slashes) == 1:
            sx0, sx1 = r["x0"] + 2 + slashes[0][0], r["x0"] + 2 + slashes[0][1]
            merged = [{**r, "x1": sx0 - 2}, {**r, "x0": sx1 + 2}]
    if len(merged) < 2:
        return None
    r0, r1 = merged[0], merged[1]
    if r1["x0"] - r0["x1"] > h * 3:
        return None  # not a single date row
    base = r0["y0"] - h * 0.2
    if twenty and twenty[0]["x0"] > r1["x0"]:
        tw = twenty[0]
        year = page.area(tw["x1"] + h * 0.15, tw["x1"] + h * 2.6, base, size_px)
        digits = 2
    elif len(merged) >= 3 and merged[2]["x0"] - r1["x1"] < h * 3:
        year, digits = page.area(merged[2]["x0"], merged[2]["x1"], base, size_px), 4
    else:
        return None
    parts = [page.area(r0["x0"], r0["x1"], base, size_px), page.area(r1["x0"], r1["x1"], base, size_px), year]
    return {"type": "date_parts", "parts": parts, "year_digits": digits}, (r0["y0"] - h, r0["y0"], r0["x0"], r1["x1"])


def _cell_area(page, x0, x1, top, bottom):
    """One character per box; tick-style boxes are short, so size from the width too."""
    ch, cw = bottom - top, x1 - x0
    size = min(cw * 0.95, max(ch * 0.7, cw * 0.8))
    return page.area(x0, x1, bottom - max(ch * 0.2, size * 0.15), size)


def _comb_continuation(page, label, combs):
    """Second row of character boxes directly under the first (long names)."""
    x0, x1, top, bottom = combs[0]
    cell_h, cell_w = bottom - top, x1 - x0
    for step in (0.7, 1.1, 1.5):
        y = bottom + cell_h * step
        segs = page.vsegs_crossing(y, x_min=x0 - cell_w * 1.6)
        if len(segs) < 4 or segs[0]["x0"] > x0 + cell_w * 1.5:
            continue
        probe = {**label, "wx1": segs[0]["x0"] - 1}
        more = _comb_cells(page, probe, segs, page.width)
        if more and more[0][2] > bottom:
            return more
    return None


def _choice_boxes(page, label):
    """'Passbook request for [ ] Issuance [ ] Reissuance' → tick-box options."""
    h = label["h"]
    yc = (label["y0"] + label["y1"]) / 2
    segs = page.vsegs_crossing(yc, x_min=label["wx1"] - h * 0.3, slack=h * 0.3)
    options = []
    for a, b in zip(segs, segs[1:]):
        top, bottom = max(a["y0"], b["y0"]), min(a["y1"], b["y1"])
        bh, bw = bottom - top, b["x0"] - a["x1"]
        if bh < h * 0.6 or bh > h * 2.4 or not (0.6 <= bw / max(bh, 1) <= 1.7):
            continue
        if not page.has_border(a["x1"], b["x0"], top, bottom):
            continue
        right = [w for w in page.words if w["x0"] >= b["x1"] - 2 and w["x0"] - b["x1"] < h * 3
                 and abs((w["y0"] + w["y1"]) / 2 - (top + bottom) / 2) < h]
        if not right:
            continue
        text = re.sub(r"[^A-Za-z0-9\- ]", "", min(right, key=lambda w: w["x0"])["text"]).strip()
        if text and text.lower() not in (o["label"].lower() for o in options):
            options.append({"label": text, "box": page.area(a["x1"] + 1, b["x0"] - 1, bottom - bh * 0.2, bh * 0.85)})
    return {"type": "choice", "options": options} if len(options) >= 2 else None


def _figures_box_near(page, label, region):
    """An empty box beside the amount-in-words line ('Sum of ____  ₹ [      ]')."""
    top, bottom, x0, x1 = region
    h = label["h"]
    yc = (top + bottom) / 2
    best = None
    for a in page.vsegs:
        bh = a["y1"] - a["y0"]
        if a["x0"] < x1 - h * 2 or not (h * 0.8 <= bh <= h * 3.5) or abs((a["y0"] + a["y1"]) / 2 - yc) > h * 2.5:
            continue
        right = [b for b in page.vsegs if b["x0"] > a["x1"] + 2 and abs(b["y0"] - a["y0"]) < h * 0.5
                 and abs(b["y1"] - a["y1"]) < h * 0.5]
        if not right:
            continue
        b = min(right, key=lambda v: v["x0"])
        if not (h * 3 <= b["x0"] - a["x1"] <= h * 30):
            continue
        if not page.has_border(a["x1"], b["x0"], a["y0"], a["y1"]):
            continue
        if page.words_in(a["x1"] + h * 0.6, b["x0"] - h * 0.6, a["y0"] + 2, a["y1"] - 2):
            continue
        if best is None or a["x0"] < best[0]["x0"]:
            best = (a, b)
    if not best:
        return None
    a, b = best
    size = min(max(h, page.text_h) * 1.3, (a["y1"] - a["y0"]) * 0.6)
    return {"type": "amount_figures", "area": page.area(a["x1"] + h * 0.5, b["x0"] - h * 0.3,
                                                      (a["y0"] + a["y1"]) / 2 + size * 0.36, size)}


def _left_blank(page, label, allow_box=True):
    """Blank printed before the label: '[ ............ Only]', '........ Branch'."""
    h = label["h"]
    yc = (label["y0"] + label["y1"]) / 2
    obstacle = page.row_obstacle(label, side="left")
    limit_x = obstacle["x1"] + h * 0.4 if obstacle else 0
    segs = [v for v in page.vsegs_crossing(yc, x_max=label["wx0"]) if v["x1"] < label["wx0"]]
    if segs and allow_box and segs[-1]["y1"] - segs[-1]["y0"] < h * 2.4:
        left = segs[-1]
        x0, x1 = max(left["x1"] + h * 0.4, limit_x), label["wx0"] - h * 0.5
        if x1 - x0 >= h * 4 and page.ink_ratio(x0, x1, label["y0"], label["y1"]) < 0.03:
            base = (left["y0"] + left["y1"]) / 2 + h * 0.36
            return {"type": "text", "lines": [page.area(x0, x1, base, min(h * 1.05, (left["y1"] - left["y0"]) * 0.62))]}
    rules = [r for r in page.hrules
             if (label["y0"] + label["y1"]) / 2 <= r["y0"] <= label["y1"] + h * 1.2
             and label["wx0"] - h * 2 <= r["x1"] <= label["wx0"] + h and r["x1"] - r["x0"] > h * 4]
    if rules:
        r = max(rules, key=lambda r: r["x0"])  # the line itself, not a detection bridged into the page border
        x0 = max(r["x0"] + h * 0.3, limit_x)
        x1 = min(r["x1"], label["wx0"] - h * 0.4)
        if x1 - x0 >= h * 4 and page.ink_ratio(x0, x1, r["y0"] - h * 0.9, r["y0"] - 3) < 0.05:
            return {"type": "text", "lines": [page.area(x0, x1, r["y0"] - h * 0.2, h * 1.05)]}
    return None


def _lines_below(page, label, start_y, x_ref, max_lines=4, max_first_gap=10.0):
    """Ruled (or dotted) empty lines stacked under a label / previous blank."""
    h = label["h"]
    found, last_y = [], start_y
    for r in sorted(page.hrules, key=lambda r: r["y0"]):
        if r["y0"] <= last_y + h * 0.8:
            continue
        gap_limit = h * (max_first_gap if not found else 4.5)
        if r["y0"] - last_y > gap_limit:
            break
        if not (x_ref - h * 4 <= r["x0"] <= x_ref + h * 8) or r["x1"] - r["x0"] < h * 6:
            continue
        between = [w for w in page.words_in(r["x0"], r["x1"], last_y, r["y0"], exclude=label["words"])
                   if w["y0"] > last_y - 2 and (w["y0"] + w["y1"]) / 2 < r["y0"] - h * 0.3]
        if between:
            break  # printed text in between: the lines belong to something else
        if page.ink_ratio(r["x0"], r["x1"], r["y0"] - h * 0.7, r["y0"] - 3) > 0.08:
            continue
        x1 = r["x1"]
        for other in sorted(page.hrules, key=lambda o: o["x0"]):
            if abs(other["y0"] - r["y0"]) <= 6 and 0 <= other["x0"] - x1 <= h * 3:
                x1 = other["x1"]  # same line, broken by a faint gap
        found.append(page.area(r["x0"] + h * 0.3, x1, r["y0"] - h * 0.2, max(h, page.text_h) * 1.1))
        last_y = r["y1"]
        if len(found) >= max_lines:
            break
    return found


def _box_below(page, label, region):
    """An empty box directly below a filled box (e.g. second line for a long name)."""
    top, bottom, x0, x1 = region
    h = label["h"]
    for v in page.vsegs:
        if not (bottom - h * 0.6 <= v["y0"] <= bottom + h * 1.5):
            continue
        partners = [u for u in page.vsegs if u is not v and abs(u["y0"] - v["y0"]) < h * 0.5
                    and abs(u["y1"] - v["y1"]) < h * 0.5 and u["x0"] > v["x0"] + h * 6]
        if not partners:
            continue
        right = max(partners, key=lambda u: u["x0"])
        if min(right["x0"], x1) - max(v["x1"], x0) < (x1 - x0) * 0.5:
            continue
        if page.words_in(v["x1"] + 2, right["x0"] - 2, v["y0"] + 2, v["y1"] - 2):
            continue
        box_h = v["y1"] - v["y0"]
        size = min(h * 1.05, box_h * 0.62)
        return page.area(v["x1"] + h * 0.4, right["x0"] - h * 0.3, (v["y0"] + v["y1"]) / 2 + size * 0.36, size)
    return None


def _line_word_count(page, label) -> int:
    yc, h = (label["y0"] + label["y1"]) / 2, label["h"]
    return sum(1 for w in page.words if abs((w["y0"] + w["y1"]) / 2 - yc) < h * 0.5)


def _placements_for(page, label):
    key = label["key"]
    h = label["h"]
    if key in ("passbook_request", "gender"):
        choice = _choice_boxes(page, label)
        if choice or key == "passbook_request":
            return choice
    if label.get("phrase") in LEFT_PHRASES:
        p = _left_blank(page, label, allow_box=False)
        if p and key == "amount_in_figures":
            return {"type": "amount_figures", "area": p["lines"][0]}
        if p and key == "amount_in_words":
            return {"type": "amount_words", "lines": p["lines"], "prefix": True, "suffix": True}
        if p:
            return p
        if key in ("amount_in_figures", "amount_in_words"):
            return None
    if key == "amount_only":
        p = _left_blank(page, label)
        if p:
            p.update({"type": "amount_words", "prefix": False, "suffix": False})
        return p

    if key in BELOW_FIRST:
        lines = _lines_below(page, label, label["y1"], label["row_x0"])
        if lines:
            return {"type": "text", "lines": lines}
        if key == "branch_address":
            return None  # "The Branch Manager," with no lines under it is just the letter's salutation

    if key == "branch":
        left = _left_blank(page, label, allow_box=False)
        if left and left["lines"][0]["x1"] >= page.area(label["wx0"] - h * 1.5, label["wx0"], 0, 1)["x0"]:
            return left
    p, region = _right_blank(page, label, key)
    if p and region and region[0] == label["y0"] and region[1] == label["y1"] and _line_word_count(page, label) >= 7:
        p, region = None, None  # "...contact me on mobile number updated in..." is a sentence, not a field
    if key in COMB_BELOW_OK and (not p or p["type"] != "comb"):
        below, below_region = _comb_below(page, label)
        if below:
            p, region = below, below_region
    if not p:
        if key == "branch":
            return _left_blank(page, label, allow_box=False)  # "............ Branch"
        return None

    if key == "amount_pay":
        # A bare "Pay" only means "Pay (self) Rupees ..." when a box follows it
        if p["type"] != "text" or region[3] - region[2] < h * 8 or region[0] == label["y0"]:
            return None
        key = "amount_words"
    if key == "amount_figures" and p["type"] == "text":
        if region[0] == label["y0"]:
            return None  # figures need a printed box / cell / line, not just empty space
        return {"type": "amount_figures", "area": p["lines"][0]}
    if key == "amount_words":
        phrase = " ".join(w["text"].lower() for w in label["row_words"])
        # "Pay Self-Rupees" / "Rupees (in words)" already print "Rupees" before the blank
        p = {"type": "amount_words", "lines": p.get("lines") or [p.get("fallback")],
             "prefix": "rupee" not in phrase and label["key"] != "amount_pay", "suffix": True}
    if key in CONTINUES and p.get("lines") and region:
        top, bottom, x0, x1 = region
        extra = _lines_below(page, label, bottom - h * 0.2, label["row_x0"], max_lines=2, max_first_gap=3.0)
        if not extra:
            box = _box_below(page, label, region)
            extra = [box] if box else []
        p["lines"] = p["lines"] + extra
    if key in ("date", "dob", "maturity_date") and p["type"] == "text":
        p["type"] = "date_text"
    if key == "amount_words" and region:
        figures = _figures_box_near(page, label, region)
        if figures:
            return [p, figures]
    return p


def _estimate_skew(img, max_angle: float = 3.0) -> float:
    """Angle (degrees, counter-clockwise) that makes text rows / rules most horizontal."""
    small = img.convert("L")
    small = small.resize((800, max(1, int(small.height * 800 / small.width))))
    arr = np.asarray(small).astype(np.int16)
    mask = Image.fromarray(np.where(arr < cs._ink_threshold(arr), 255, 0).astype("uint8"))

    def sharpness(angle):
        rows = np.asarray(mask.rotate(angle, resample=Image.NEAREST)).sum(axis=1).astype(np.float64)
        return float(np.sum(np.diff(rows) ** 2))

    coarse = max(np.arange(-max_angle, max_angle + 0.01, 0.25), key=sharpness)
    fine = max(np.arange(coarse - 0.25, coarse + 0.26, 0.05), key=sharpness)
    return round(float(fine), 2)


# ─── Public entry point ──────────────────────────────────────────────────────
def detect_form_fields(file_path: str, is_pdf: bool) -> list[dict]:
    """Detect fillable fields on a scanned bank form. Returns [] when nothing usable is found."""
    if not AVAILABLE or not cs.IMAGING_AVAILABLE:
        return []
    try:
        img, tf = cs._load_page_image(file_path, is_pdf, dpi=300)
        if img is None:
            return []
        layer = _pdf_layer(file_path) if is_pdf else None
        fields = _analyse_image(img, tf, layer)
        if layer and len(layer["words"]) >= 10:
            return _finalize_fields(fields, tf)  # exact text positions: no OCR, no skew
        skew = _estimate_skew(img)
        if abs(skew) >= 0.15:
            # Scans / photos are often slightly rotated: also read a straightened copy (rules become
            # horizontal) and keep, per field, whichever reading found more of it
            straight = _analyse_image(img.rotate(skew, resample=Image.BICUBIC, fillcolor=(255, 255, 255)),
                                      {**tf, "skew": skew})
            for key, f in straight.items():
                if key not in fields or len(f["placements"]) >= len(fields[key]["placements"]):
                    fields[key] = f
        return _finalize_fields(fields, tf)
    except Exception as e:
        print(f"[BANK_FORM] Detection notice: {e}")
        return []


def _analyse_image(img, tf, layer=None) -> dict:
    factor = TARGET_WIDTH / img.width
    if factor > 1.15 or factor < 0.6:
        img = img.resize((int(img.width * factor), int(img.height * factor)), Image.LANCZOS)
        tf = {**tf, "scale": tf["scale"] / factor}
    gray = np.asarray(img.convert("L")).astype(np.int16).copy()
    k = img.width / layer["width"] if layer else 1.0
    text_words = [_layer_word(w, layer, k) for w in layer["words"]] if layer else []

    if len(text_words) >= 10:
        first_pass, raw_words = text_words, text_words  # exact text from the PDF itself
    else:
        first_pass = cs._ocr_words(Image.fromarray(gray.clip(0, 255).astype("uint8")))
        raw_words = None
    text_h = _text_height(first_pass, gray.shape[1])

    vec_h, vec_v = _layer_lines(layer, k, text_h, gray.shape) if layer else ([], [])
    for r in vec_h:  # light-grey printed boxes count as ink for box / border checks
        gray[int(r["y0"]):int(r["y0"]) + 2, int(r["x0"]):int(r["x1"]) + 1] = 0
    for v in vec_v:
        gray[int(v["y0"]):int(v["y1"]) + 1, int(v["x0"]):int(v["x0"]) + 2] = 0

    line_mask, hrules, vsegs = _analyse_lines(gray, text_h)
    if raw_words is None:
        raw_words = _ocr(gray, line_mask, first_pass)
    hrules = _drop_text_rules(hrules, raw_words) + vec_h
    vsegs = vsegs + vec_v
    words = [w for w in raw_words if not _is_junk(w, hrules)]
    page = _Page(gray, words, hrules, vsegs, tf)
    rows = _rows(words)
    labels = _match_labels(rows) + _wrapped_labels(rows)
    regions = _bank_use_regions(page, rows)
    labels = [l for l in labels if not any(
        x0 <= (l["wx0"] + l["wx1"]) / 2 <= x1 and y0 <= (l["y0"] + l["y1"]) / 2 <= y1 for x0, x1, y0, y1 in regions)]
    labels.sort(key=lambda l: (l["y0"], l["x0"]))
    for label in labels:
        label["h"] = min(label["h"], page.text_h * 1.5)  # one tall OCR fragment must not skew distances
    return _collect_fields(page, labels)


def _pdf_layer(file_path):
    """Words (with leader runs '____' / '.....' split off) and vector lines from a PDF's first page."""
    if not cs.PYMUPDF_AVAILABLE:
        return None
    import pymupdf
    doc = pymupdf.open(file_path)
    try:
        page = doc[0]
        page.set_rotation(0)
        rect = page.rect
        words, leaders = [], []
        for block in page.get_text("rawdict")["blocks"]:
            for line in block.get("lines", []):
                if abs(line.get("dir", (1, 0))[0] - 1) > 0.01:
                    continue  # rotated text ("This form is not a cheque")
                for span in line["spans"]:
                    words_, leaders_ = _split_span(span)
                    words += words_
                    leaders += leaders_
        lines = []
        for d in page.get_drawings():
            stroked, filled = d.get("color") is not None, d.get("fill") is not None
            for item in d["items"]:
                if item[0] == "l" and stroked:
                    lines.append((item[1].x, item[1].y, item[2].x, item[2].y))
                elif item[0] in ("re", "qu"):
                    r = item[1] if item[0] == "re" else item[1].rect
                    if stroked:
                        lines += [(r.x0, r.y0, r.x1, r.y0), (r.x0, r.y1, r.x1, r.y1), (r.x0, r.y0, r.x0, r.y1), (r.x1, r.y0, r.x1, r.y1)]
                    elif filled and min(r.width, r.height) <= 2.5:  # a line drawn as a thin filled bar
                        if r.width >= r.height:
                            lines.append((r.x0, (r.y0 + r.y1) / 2, r.x1, (r.y0 + r.y1) / 2))
                        else:
                            lines.append(((r.x0 + r.x1) / 2, r.y0, (r.x0 + r.x1) / 2, r.y1))
        return {"words": words, "leaders": leaders, "lines": lines, "x0": rect.x0, "y0": rect.y0, "width": rect.width}
    except Exception as e:
        print(f"[BANK_FORM] PDF layer notice: {e}")
        return None
    finally:
        doc.close()


def _split_span(span):
    chars = span.get("chars") or []
    size = span["size"]
    texts = [c["c"] for c in chars]
    lead = [t in "_\u2026" for t in texts]
    i = 0
    while i < len(texts):  # three or more dots in a row are a dotted leader
        if texts[i] in ".\u00b7":
            j = i
            while j < len(texts) and texts[j] in ".\u00b7":
                j += 1
            if j - i >= 3:
                for m in range(i, j):
                    lead[m] = True
            i = j
        else:
            i += 1
    groups, cur = [], []
    for idx, t in enumerate(texts):
        if t.isspace():
            if cur:
                groups.append(cur)
            cur = []
            continue
        if cur and lead[idx] != lead[cur[0]]:
            groups.append(cur)
            cur = []
        cur.append(idx)
    if cur:
        groups.append(cur)
    words, leaders = [], []
    for g in groups:
        x0, x1 = chars[g[0]]["bbox"][0], chars[g[-1]]["bbox"][2]
        base = chars[g[0]]["origin"][1]
        if lead[g[0]]:
            leaders.append({"x0": x0, "x1": x1, "y": base + size * 0.1})
        else:
            words.append({"text": "".join(texts[m] for m in g), "x0": x0, "x1": x1,
                          "y0": base - size * 0.72, "y1": base + size * 0.2})
    return words, leaders


def _layer_word(w, layer, k):
    x0, x1 = (w["x0"] - layer["x0"]) * k, (w["x1"] - layer["x0"]) * k
    y0, y1 = (w["y0"] - layer["y0"]) * k, (w["y1"] - layer["y0"]) * k
    return {"text": w["text"], "norm": re.sub(r"[^a-z/]", "", w["text"].lower()),
            "x0": x0, "y0": y0, "x1": x1, "y1": y1, "h": y1 - y0, "conf": 99.0, "exact": True}


def _layer_lines(layer, k, text_h, shape):
    """Vector lines / box edges and text leaders as rules (h) and vertical segments (v), in pixels."""
    height, width = shape
    hr, vs = [], []
    for x0, y0, x1, y1 in layer["lines"]:
        X0, Y0 = (min(x0, x1) - layer["x0"]) * k, (min(y0, y1) - layer["y0"]) * k
        X1, Y1 = (max(x0, x1) - layer["x0"]) * k, (max(y0, y1) - layer["y0"]) * k
        if Y1 - Y0 <= 3 and X1 - X0 >= text_h * 1.0:
            hr.append({"y0": Y0, "y1": Y0 + 1, "x0": X0, "x1": X1})
        elif X1 - X0 <= 3 and Y1 - Y0 >= text_h * 0.9:
            vs.append({"x0": X0, "x1": X0 + 1, "y0": Y0, "y1": Y1})
    for l in layer["leaders"]:
        X0, X1 = (l["x0"] - layer["x0"]) * k, (l["x1"] - layer["x0"]) * k
        if X1 - X0 >= text_h * 1.2:
            Y = (l["y"] - layer["y0"]) * k
            hr.append({"y0": Y, "y1": Y + 1, "x0": X0, "x1": X1})
    clip = lambda v, hi: int(round(max(0, min(hi - 1, v))))
    for r in hr:
        r.update(x0=clip(r["x0"], width), x1=clip(r["x1"], width), y0=clip(r["y0"], height), y1=clip(r["y1"], height))
    for v in vs:
        v.update(x0=clip(v["x0"], width), x1=clip(v["x1"], width), y0=clip(v["y0"], height), y1=clip(v["y1"], height))
    return hr, vs


def _row_text(row) -> str:
    return re.sub(r"[^a-z ]", " ", " ".join(w["text"].lower() for w in row))


def _bank_use_regions(page, rows):
    """Areas marked 'For office / bank use only' (plus what follows them) are not for the customer."""
    starts = [r for r in rows if re.search(r"(office|bank)\s+use", _row_text(r))]
    ends = [min(w["y0"] for w in r) for r in rows
            if re.search(r"acquittance|acknowledg|to be filled by|customer copy|counterfoil", _row_text(r))]
    regions = []
    for row in starts:
        x0, x1 = min(w["x0"] for w in row), max(w["x1"] for w in row)
        y0, y1 = min(w["y0"] for w in row), max(w["y1"] for w in row)
        h = float(np.median([w["h"] for w in row]))
        yc, xc = (y0 + y1) / 2, (x0 + x1) / 2
        # Marker inside a closed box (e.g. a "(FOR BANK USE ONLY)" panel): just that box
        box = None
        for r in sorted(page.hrules, key=lambda r: r["y0"]):
            if not (y1 <= r["y0"] <= y1 + h * 8 and r["x0"] <= xc <= r["x1"]):
                continue
            sides = [v for v in page.vsegs if v["y0"] <= y0 + 2 and v["y1"] >= r["y0"] - 4]
            if any(abs(v["x0"] - r["x0"]) < h for v in sides) and any(abs(v["x0"] - r["x1"]) < h for v in sides):
                box = (r["x0"], r["x1"], y0 - 2, r["y0"])
                break
        if box and box[3] - box[2] > h * 2.5:
            regions.append(box)
            continue
        # Otherwise: from the marker down to the next customer section, within the marker's table cell
        lefts = [v for v in page.vsegs_crossing(yc) if v["x1"] <= x0 + 2]
        rights = [v for v in page.vsegs_crossing(yc) if v["x0"] >= x1 - 2]
        cx0 = lefts[-1]["x0"] if lefts and x0 - lefts[-1]["x0"] < h * 15 else 0
        cx1 = rights[0]["x1"] if rights and rights[0]["x0"] - x1 < h * 15 else page.width
        stop = min([e for e in ends if e > y1] or [page.height])
        regions.append((cx0, cx1, y0 - 2, stop - 2))
    return regions


def _wrapped_labels(rows) -> list[dict]:
    """'...account matured' / 'on________' — a label split across two lines."""
    labels = []
    lines = sorted(rows, key=lambda r: min(w["y0"] for w in r))
    for prev, row in zip(lines, lines[1:]):
        first = min(row, key=lambda w: w["x0"])
        last = max(prev, key=lambda w: w["x1"])
        if re.sub(r"[^a-z]", "", first["text"].lower()) == "on" and re.sub(r"[^a-z]", "", last["text"].lower()) == "matured":
            labels.append({
                "key": "maturity_date", "phrase": "matured on",
                "x0": first["x0"], "x1": first["x1"], "wx0": first["x0"], "wx1": first["x1"],
                "y0": first["y0"], "y1": first["y1"], "h": first["h"], "words": [first],
                "row_words": [first], "row_x0": first["x0"],
            })
    return labels


def _ref_area(placement) -> dict:
    options = [o["box"] for o in placement.get("options", [])]
    return (placement.get("lines") or placement.get("cells") or placement.get("parts") or options
            or [placement.get("area") or {}])[0]


def _collect_fields(page, labels) -> dict:
    fields = {}
    for label in labels:
        key = GROUPS.get(label["key"], label["key"])
        if key in fields and key not in GROUPS.values():
            continue  # first occurrence in reading order wins
        found = _placements_for(page, label)
        if not found:
            continue
        for p in (found if isinstance(found, list) else [found]):
            _add_placement(fields, key, label, p)
    return fields


def _add_placement(fields, key, label, p):
        if key not in fields:
            spec_label, field_type, _ = SPECS[label["key"]]
            if p["type"] == "choice":
                field_type = "choice:" + "|".join(o["label"] for o in p["options"])
            fields[key] = {
                "label": spec_label,
                "field_type": field_type,
                "question_text": QUESTIONS[key]["en"],
                "page": 1,
                "order": (-round(_ref_area(p).get("baseline", 0) / 8), _ref_area(p).get("x0", 0)),
                "placements": [],
            }
        ref = _ref_area(p)
        duplicate = any(
            q["type"] == p["type"] and abs(_ref_area(q).get("baseline", 0) - ref.get("baseline", 0)) < 3
            and min(_ref_area(q).get("x1", 0), ref.get("x1", 0)) > max(_ref_area(q).get("x0", 0), ref.get("x0", 0))
            for q in fields[key]["placements"]
        )
        if not duplicate:
            fields[key]["placements"].append(p)


def _finalize_fields(fields: dict, tf) -> list[dict]:
    page_info = {"kind": tf["kind"], "page_width": tf["page_width"], "page_height": tf["page_height"]}

    amount = fields.get("amount")
    if amount:
        # "Pay Self-Rupees [.....]" + "[..... Only]" are one sentence: wrap the words across both
        words = [p for p in amount["placements"] if p["type"] == "amount_words"]
        if len(words) > 1:
            words.sort(key=lambda p: (-p["lines"][0]["baseline"], p["lines"][0]["x0"]))
            merged = {"type": "amount_words", "lines": [l for p in words for l in p["lines"]],
                      "prefix": words[0].get("prefix", True), "suffix": words[-1].get("suffix", True)}
            amount["placements"] = [p for p in amount["placements"] if p["type"] != "amount_words"] + [merged]

    out = []
    for key, f in sorted(fields.items(), key=lambda kv: kv[1]["order"]):
        first = f["placements"][0]
        ref = (first.get("lines") or first.get("cells") or [first.get("area") or first.get("parts", [{}])[0]])[0]
        out.append({
            "label": f["label"],
            "field_type": f["field_type"],
            "question_text": f["question_text"],
            "page": 1,
            "x": ref.get("x0", 180),
            "y": ref.get("baseline", 700),
            "width": round(ref.get("x1", 440) - ref.get("x0", 180), 2),
            "height": ref.get("size", 12),
            "cheque": {"role": key, "page": page_info, "placements": f["placements"]},
        })
    return out
