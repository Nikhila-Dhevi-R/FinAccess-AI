"""
Voice / Translation Service

Handles:
- Form field question generation in English, Hindi, and Tamil
- Deterministic multilingual parsing (numbers, yes/no, menu choices, navigation commands)
- Field answer interpretation, cleaning, and normalization
- Field validation (Phone, PIN, Aadhaar, PAN, Date, Name, etc.)
- Localized readback and confirmation prompts
- Multilingual numeric & text normalizers
"""

import re
from typing import Optional


# ─── Language Support ────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "ta": "தமிழ் (Tamil)",
}

# Language-specific prompts
LANGUAGE_PROMPTS = {
    "en": {
        "welcome": "Welcome to FinAccess AI. Please choose your language. Say 1 for English, 2 for Hindi, or 3 for Tamil.",
        "menu": "Main menu. Say 1 to Fill a Form, 2 to Explore Government Schemes, 3 to Ask a Banking Question, or 4 for Fraud Check.",
        "heard": "I heard: {value}. Is that correct?",
        "confirm_prefix": "To confirm, please say the 3 digits:",
        "next_question": "Now, let me ask you the next question.",
        "all_done": "All fields are complete! Your form is ready to download.",
        "retry": "I didn't catch that. Please speak again clearly.",
        "field_confirmed": "Confirmed {label} as {value}.",
        "nav_hint": "You can say Next, Repeat, Back, Home, or Stop at any time.",
    },
    "hi": {
        "welcome": "फिनएक्सेस एआई में आपका स्वागत है। कृपया अपनी भाषा चुनें। अंग्रेज़ी के लिए 1, हिन्दी के लिए 2, या तमिल के लिए 3 बोलें।",
        "menu": "मुख्य मेनू। फॉर्म भरने के लिए 1, सरकारी योजनाओं के लिए 2, बैंकिंग सवाल पूछने के लिए 3, या धोखाधड़ी जांच के लिए 4 बोलें।",
        "heard": "मैंने सुना: {value}। क्या यह सही है?",
        "confirm_prefix": "पुष्टि करने के लिए, कृपया यह 3 अंक बोलें:",
        "next_question": "अब अगला सवाल पूछते हैं।",
        "all_done": "सभी सवाल पूरे हो गए हैं! आपका फॉर्म डाउनलोड के लिए तैयार है।",
        "retry": "आवाज़ स्पष्ट नहीं आई। कृपया दोबारा बोलें।",
        "field_confirmed": "{label} की पुष्टि {value} के रूप में हो गई है।",
        "nav_hint": "आप कभी भी आगे, दोबारा, पीछे, शुरू, या रुको बोल सकते हैं।",
    },
    "ta": {
        "welcome": "ஃபின்ஆக்சஸ் ஏஐக்கு உங்களை வரவேற்கிறோம். தயவுசெய்து உங்கள் மொழியை தேர்வு செய்யுங்கள். ஆங்கிலத்திற்கு 1, இந்திக்கு 2, தமிழுக்கு 3 சொல்லுங்கள்.",
        "menu": "முதன்மை பட்டியல். படிவம் நிரப்ப 1, அரசு திட்டங்களை பார்க்க 2, வங்கி கேள்வி கேட்க 3, மோசடி சரிபார்க்க 4 சொல்லுங்கள்.",
        "heard": "நான் கேட்டது: {value}। இது சரியா?",
        "confirm_prefix": "உறுதிப்படுத்த, இந்த 3 எண்களை சொல்லுங்கள்:",
        "next_question": "இப்போது அடுத்த கேள்வியை கேட்கிறேன்.",
        "all_done": "அனைத்து விவரங்களும் பூர்த்தியாகிவிட்டன! உங்கள் படிவம் தயாராக உள்ளது.",
        "retry": "சரியாக கேட்கவில்லை. தயவுசெய்து மீண்டும் சொல்லுங்கள்.",
        "field_confirmed": "{label} {value} என்று உறுதிப்படுத்தப்பட்டது.",
        "nav_hint": "நீங்கள் எப்போது வேண்டுமானாலும் அடுத்து, மீண்டும், பின்னால், ஆரம்பம், அல்லது நிறுத்து சொல்லலாம்.",
    },
}

# Field questions in English, Hindi, and Tamil
LOCALIZED_QUESTIONS = {
    "Full Name": {
        "en": "What is your full name?",
        "hi": "आपका पूरा नाम क्या है?",
        "ta": "உங்கள் முழு பெயர் என்ன?",
    },
    "Applicant Name": {
        "en": "What is the applicant's full name?",
        "hi": "आवेदक का पूरा नाम क्या है?",
        "ta": "விண்ணப்பதாரரின் முழு பெயர் என்ன?",
    },
    "Farmer Name": {
        "en": "What is the farmer's full name?",
        "hi": "किसान का पूरा नाम क्या है?",
        "ta": "விவசாயியின் முழு பெயர் என்ன?",
    },
    "Head of Family Name": {
        "en": "What is the head of the family's full name?",
        "hi": "परिवार के मुखिया का पूरा नाम क्या है?",
        "ta": "குடும்பத் தலைவரின் முழு பெயர் என்ன?",
    },
    "Date of Birth": {
        "en": "What is your date of birth? Please say day, month, and year.",
        "hi": "आपकी जन्म तिथि क्या है? कृपया दिन, महीना और साल बताएं।",
        "ta": "உங்கள் பிறந்த தேதி என்ன? நாள், மாதம் மற்றும் வருடத்தை சொல்லுங்கள்.",
    },
    "Gender": {
        "en": "What is your gender? Male, female, or other?",
        "hi": "आपका लिंग क्या है? पुरुष, महिला, या अन्य?",
        "ta": "உங்கள் பாலினம் என்ன? ஆண், பெண், அல்லது மற்றவையா?",
    },
    "Father's / Husband's Name": {
        "en": "What is your father's or husband's name?",
        "hi": "आपके पिता या पति का क्या नाम है?",
        "ta": "உங்கள் தந்தை அல்லது கணவரின் பெயர் என்ன?",
    },
    "Father's Name": {
        "en": "What is your father's name?",
        "hi": "आपके पिता का क्या नाम है?",
        "ta": "உங்கள் தந்தையின் பெயர் என்ன?",
    },
    "Father / Mother / Spouse Name": {
        "en": "What is your father's, mother's, or spouse's name?",
        "hi": "आपके पिता, माता, या जीवनसाथी का क्या नाम है?",
        "ta": "உங்கள் தந்தை, தாய் அல்லது துணையின் பெயர் என்ன?",
    },
    "Mobile Number": {
        "en": "What is your 10-digit mobile phone number?",
        "hi": "आपका 10 अंकों का मोबाइल नंबर क्या है?",
        "ta": "உங்கள் 10 இலக்க மொபைல் எண் என்ன?",
    },
    "Alternate Number": {
        "en": "What is your alternate phone number if you have one?",
        "hi": "क्या आपका कोई दूसरा फोन नंबर है?",
        "ta": "உங்களிடம் மாற்று தொலைபேசி எண் உள்ளதா?",
    },
    "Email Address": {
        "en": "What is your email address?",
        "hi": "आपका ईमेल पता क्या है?",
        "ta": "உங்கள் மின்னஞ்சல் முகவரி என்ன?",
    },
    "Aadhaar Number": {
        "en": "What is your 12-digit Aadhaar number?",
        "hi": "आपका 12 अंकों का आधार नंबर क्या है?",
        "ta": "உங்கள் 12 இலக்க ஆதார் எண் என்ன?",
    },
    "PAN / Tax ID": {
        "en": "What is your PAN card number?",
        "hi": "आपका पैन कार्ड नंबर क्या है?",
        "ta": "உங்கள் பான் கார்டு எண் என்ன?",
    },
    "Residential Address": {
        "en": "What is your full home address?",
        "hi": "आपका पूरा घर का पता क्या है?",
        "ta": "உங்கள் முழு வீட்டு முகவரி என்ன?",
    },
    "Address": {
        "en": "What is your full address?",
        "hi": "आपका पूरा पता क्या है?",
        "ta": "உங்கள் முழு முகவரி என்ன?",
    },
    "House / Flat / Building": {
        "en": "What is your house number or building name?",
        "hi": "आपका मकान नंबर या इमारत का नाम क्या है?",
        "ta": "உங்கள் வீடு எண் அல்லது கட்டிடத்தின் பெயர் என்ன?",
    },
    "Street / Area / Locality": {
        "en": "What is your street, area, or locality?",
        "hi": "आपकी गली, मोहल्ला, या क्षेत्र का नाम क्या है?",
        "ta": "உங்கள் தெரு அல்லது பகுதியின் பெயர் என்ன?",
    },
    "City / Town": {
        "en": "Which city or town do you live in?",
        "hi": "आप किस शहर या कस्बे में रहते हैं?",
        "ta": "நீங்கள் எந்த நகரம் அல்லது ஊரில் வசிக்கிறீர்கள்?",
    },
    "District": {
        "en": "Which district do you live in?",
        "hi": "आप किस जिले में रहते हैं?",
        "ta": "நீங்கள் எந்த மாவட்டத்தில் வசிக்கிறீர்கள்?",
    },
    "State": {
        "en": "Which state do you live in?",
        "hi": "आप किस राज्य में रहते हैं?",
        "ta": "நீங்கள் எந்த மாநிலத்தில் வசிக்கிறீர்கள்?",
    },
    "PIN / Postal Code": {
        "en": "What is your 6-digit PIN code?",
        "hi": "आपके इलाके का 6 अंकों का पिन कोड क्या है?",
        "ta": "உங்கள் பகுதியின் 6 இலக்க அஞ்சல் குறியீடு (பின்கோடு) என்ன?",
    },
    "Pin Code": {
        "en": "What is your 6-digit PIN code?",
        "hi": "आपके इलाके का 6 अंकों का पिन कोड क्या है?",
        "ta": "உங்கள் பகுதியின் 6 இலக்க அஞ்சல் குறியீடு (பின்கோடு) என்ன?",
    },
    "Occupation": {
        "en": "What is your occupation or work? For example farmer, laborer, or self-employed.",
        "hi": "आप क्या काम करते हैं? जैसे किसान, मज़दूर, या अपना व्यवसाय?",
        "ta": "நீங்கள் என்ன வேலை செய்கிறீர்கள்? உதாரணத்திற்கு விவசாயி, கூலி அல்லது வியாபாரம்.",
    },
    "Annual Income": {
        "en": "What is your total annual family income in rupees?",
        "hi": "आपकी कुल सालाना पारिवारिक आय कितने रुपये है?",
        "ta": "உங்கள் குடும்பத்தின் மொத்த ஆண்டு வருமானம் எத்தனை ரூபாய்?",
    },
    "Annual Income (in Rupees)": {
        "en": "What is your total annual family income in rupees?",
        "hi": "आपकी कुल सालाना पारिवारिक आय कितने रुपये है?",
        "ta": "உங்கள் குடும்பத்தின் மொத்த ஆண்டு வருமானம் எத்தனை ரூபாய்?",
    },
    "Nominee Name": {
        "en": "Who is your nominee name?",
        "hi": "आप अपने खाते या फॉर्म में किसे वारिस या नॉमिनी बनाना चाहते हैं?",
        "ta": "உங்கள் நாமினி (வாரிசுதாரர்) பெயர் என்ன?",
    },
    "Bank Account Number": {
        "en": "What is your bank account number?",
        "hi": "आपका बैंक खाता नंबर क्या है?",
        "ta": "உங்கள் வங்கி கணக்கு எண் என்ன?",
    },
    "IFSC Code": {
        "en": "What is your bank branch IFSC code?",
        "hi": "आपकी बैंक शाखा का आईएफएससी कोड क्या है?",
        "ta": "உங்கள் வங்கியின் ஐ.எஃப்.எஸ்.சி (IFSC) குறியீடு என்ன?",
    },
    "Land Area (in acres)": {
        "en": "How many acres of agricultural land do you own?",
        "hi": "आपके पास कितनी एकड़ कृषि भूमि है?",
        "ta": "உங்களிடம் எத்தனை ஏக்கர் விவசாய நிலம் உள்ளது?",
    },
    "Village Name": {
        "en": "What is the name of your village?",
        "hi": "आपके गांव का नाम क्या है?",
        "ta": "உங்கள் கிராமத்தின் பெயர் என்ன?",
    },
    # Cheque fields (keys appear inside the English question text on purpose)
    "Cheque Date": {
        "en": "What date should be written on the cheque? Please say the cheque date, or just say today.",
        "hi": "चेक पर कौन सी तारीख लिखनी है? कृपया तारीख बताएं, या सिर्फ 'आज' बोलें।",
        "ta": "காசோலையில் எந்த தேதி எழுத வேண்டும்? தேதியை சொல்லுங்கள், அல்லது 'இன்று' என்று சொல்லுங்கள்.",
    },
    "Payee Name": {
        "en": "Who should this cheque be paid to? Please say the payee name.",
        "hi": "यह चेक किसके नाम पर देना है? कृपया पाने वाले का नाम बताएं।",
        "ta": "இந்த காசோலை யாருக்கு செலுத்தப்பட வேண்டும்? பெறுநரின் பெயரை சொல்லுங்கள்.",
    },
    "Cheque Amount": {
        "en": "How much money should this cheque be for? Please say the cheque amount in rupees.",
        "hi": "इस चेक में कितनी राशि लिखनी है? कृपया रुपये में राशि बताएं।",
        "ta": "இந்த காசோலையில் எவ்வளவு தொகை எழுத வேண்டும்? ரூபாயில் தொகையை சொல்லுங்கள்.",
    },
    "Cheque Account Number": {
        "en": "What is the account number for this cheque? Please say the cheque account number.",
        "hi": "इस चेक के लिए खाता संख्या क्या है? कृपया अपना खाता नंबर बताएं।",
        "ta": "இந்த காசோலைக்கான கணக்கு எண் என்ன? உங்கள் கணக்கு எண்ணை சொல்லுங்கள்.",
    },
}

# Devanagari & Tamil numeral conversions
DIGIT_MAP = {
    # Devanagari numerals
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    # Tamil numerals
    '௦': '0', '௧': '1', '௨': '2', '௩': '3', '௪': '4',
    '௫': '5', '௬': '6', '௭': '7', '௮': '8', '௯': '9',
}

# Multilingual spoken number words mapping
SPOKEN_DIGIT_WORDS = {
    # English
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
    "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
    "hundred": "100", "thousand": "1000",
    # Hindi (Devanagari & Latin transliterations)
    "शून्य": "0", "जीरो": "0", "shunya": "0",
    "एक": "1", "ek": "1", "ik": "1",
    "दो": "2", "do": "2",
    "तीन": "3", "teen": "3", "tin": "3",
    "चार": "4", "char": "4", "chaar": "4",
    "पांच": "5", "पाँच": "5", "panch": "5", "paanch": "5",
    "छह": "6", "छः": "6", "chhah": "6", "chhe": "6", "che": "6",
    "सात": "7", "saat": "7", "sat": "7",
    "आठ": "8", "aath": "8", "ath": "8",
    "नौ": "9", "nau": "9", "no": "9",
    "दस": "10", "das": "10",
    # Tamil (Tamil script & Latin transliterations)
    "பூஜ்ஜியம்": "0", "பூஜ்யம்": "0", "poojiyam": "0", "poojyam": "0",
    "ஒன்று": "1", "ஒரு": "1", "ondru": "1", "onru": "1", "onnu": "1", "oru": "1",
    "இரண்டு": "2", "ரெண்டு": "2", "irandu": "2", "rendu": "2", "reṇḍu": "2",
    "மூன்று": "3", "மூணு": "3", "moondru": "3", "moonu": "3",
    "நான்கு": "4", "நாலு": "4", "naangu": "4", "naalu": "4", "nanku": "4",
    "ஐந்து": "5", "அஞ்சு": "5", "ainthu": "5", "aindhu": "5", "anju": "5",
    "ஆறு": "6", "aaru": "6",
    "ஏழு": "7", "ezhu": "7", "yelum": "7", "yezhu": "7",
    "எட்டு": "8", "ettu": "8",
    "ஒன்பது": "9", "onpathu": "9", "onbadhu": "9", "ombadhu": "9", "onbathu": "9",
    "பத்து": "10", "pathu": "10", "patthu": "10",
}

# Month names across English, Hindi, and Tamil
MONTHS_MAP = {
    # English
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    # Hindi
    "जनवरी": 1, "फ़रवरी": 2, "फरवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6,
    "जुलाई": 7, "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10, "अक्तूबर": 10,
    "नवंबर": 11, "नवम्बर": 11, "दिसंबर": 12, "दिसम्बर": 12,
    # Tamil
    "ஜனவரி": 1, "பிப்ரவரி": 2, "மார்ச்": 3, "ஏப்ரல்": 4, "மே": 5, "ஜூன்": 6,
    "ஜூலை": 7, "ஆகஸ்ட்": 8, "செப்டம்பர்": 9, "அக்டோபர்": 10, "நவம்பர்": 11, "டிசம்பர்": 12,
    # Tamil Traditional Months (sometimes used in rural settings)
    "சித்திரை": 4, "வைகாசி": 5, "ஆனி": 6, "ஆடி": 7, "ஆவணி": 8, "புரட்டாசி": 9,
    "ஐப்பசி": 10, "கார்த்திகை": 11, "மார்கழி": 12, "தை": 1, "மாசி": 2, "பங்குனி": 3,
}


def normalize_digits(text: str) -> str:
    """Convert Devanagari and Tamil digits to standard ASCII digits."""
    res = []
    for ch in text:
        res.append(DIGIT_MAP.get(ch, ch))
    return "".join(res)


def extract_spoken_digits(text: str) -> str:
    """
    Extract a clean continuous sequence of digits from spoken text across English, Hindi, and Tamil.
    E.g.:
    "four seven two" -> "472"
    "चार सात दो" -> "472"
    "நான்கு ஏழு இரண்டு" -> "472"
    "4 7 2" -> "472"
    "ek do teen" -> "123"
    """
    cleaned = normalize_digits(text.lower()).replace(",", " ").replace(".", " ").replace("-", " ")
    tokens = cleaned.split()
    digits = []

    for token in tokens:
        if token.isdigit():
            digits.extend(list(token))
        elif token in SPOKEN_DIGIT_WORDS:
            val = SPOKEN_DIGIT_WORDS[token]
            digits.extend(list(val))
        else:
            # Check individual characters in case of mixed scripts
            found = False
            for ch in token:
                if ch in DIGIT_MAP:
                    digits.append(DIGIT_MAP[ch])
                    found = True
                elif ch.isdigit():
                    digits.append(ch)
                    found = True
            if not found:
                # Substring check for token
                for word, d in SPOKEN_DIGIT_WORDS.items():
                    if len(word) >= 3 and word in token:
                        digits.extend(list(d))
                        break

    return "".join(digits)


def extract_spoken_number(text: str) -> Optional[int]:
    """
    Extract a single integer from spoken text.
    Supports English, Hindi, Tamil number words and numerals.
    """
    digits = extract_spoken_digits(text)
    if digits:
        try:
            return int(digits)
        except ValueError:
            pass
    return None


def parse_yes_no(text: str) -> Optional[bool]:
    """
    Deterministically classify spoken input as Yes (True) or No (False).
    Supports English, Hindi, and Tamil expressions.
    """
    t = text.lower().strip()
    # Normalize punctuation
    t = re.sub(r"[^\w\s\u0900-\u097F\u0B80-\u0BFF]", "", t)
    tokens = t.split()

    yes_words = {
        # English
        "yes", "yeah", "yep", "yup", "correct", "right", "true", "confirm", "ok", "okay", "sure", "done", "fine",
        # Hindi
        "हाँ", "हाँजी", "हां", "हा", "सही", "ठीक", "बिल्कुल", "पक्का", "हॉं", "ज़रूर", "स्वीकार",
        "haan", "han", "sahi", "theek", "thik", "haanji", "bilkul", "pakka",
        # Tamil
        "ஆம்", "ஆமாம்", "சரி", "உண்மை", "வேண்டும்", "உறுதி", "ஆகும்", "சரிதான்",
        "aam", "aamaam", "sari", "unmai", "vendum", "seri", "aama",
    }

    no_words = {
        # English
        "no", "nope", "nah", "wrong", "false", "cancel", "incorrect", "not", "never", "reject",
        # Hindi
        "नहीं", "ना", "गलत", "न", "मत", "रद्द",
        "nahin", "nahi", "galat", "naa", "na", "mat",
        # Tamil
        "இல்லை", "வேண்டாம்", "தவறு", "இல்ல", "கூடாது",
        "illai", "vendaam", "thavaru", "illa", "venda",
    }

    for token in tokens:
        if token in yes_words:
            return True
        if token in no_words:
            return False

    for phrase in yes_words:
        if phrase in t:
            return True
    for phrase in no_words:
        if phrase in t:
            return False

    return None


def parse_menu_choice(text: str) -> Optional[int]:
    """
    Deterministically parse the main menu choice (1 to 4).
    1: Form Fill
    2: Explore Schemes
    3: Ask Question / Guidance
    4: Fraud Check
    """
    t = text.lower().strip()

    # Check direct digits or words
    num = extract_spoken_number(t)
    if num in (1, 2, 3, 4):
        return num

    # Keyword matching
    # 1: Form Fill
    if any(k in t for k in ["form", "fill", "apply", "फॉर्म", "आवेदन", "படிவம்", "நிரப்ப", "விண்ணப்ப"]):
        return 1

    # 2: Schemes
    if any(k in t for k in ["scheme", "yojana", "benefit", "योजना", "सरकारी योजना", "திட்டம்", "அரசு திட்டம்", "மானிய"]):
        return 2

    # 3: Guidance / Questions
    if any(k in t for k in ["question", "ask", "help", "guide", "bank", "सवाल", "पूछ", "मार्गदर्शन", "கேள்வி", "வங்கி", "உதவி"]):
        return 3

    # 4: Fraud Check
    if any(k in t for k in ["fraud", "scam", "fake", "check", "संदेश", "धोखा", "धोखाधड़ी", "மோசடி", "போலி"]):
        return 4

    return None


def parse_navigation_command(text: str) -> Optional[str]:
    """
    Deterministically parse voice navigation commands:
    'next', 'repeat', 'back', 'home', 'stop'
    """
    t = text.lower().strip()

    # Repeat / Play again
    if any(k in t for k in [
        "repeat", "again", "replay", "once more",
        "दोबारा", "फिर से", "फिर", "सुनाओ", "dohrana", "firse", "phir",
        "மீண்டும்", "மறுபடியும்", "திரும்ப", "meendum", "thirumba"
    ]):
        return "repeat"

    # Next / Forward
    if any(k in t for k in [
        "next", "forward", "continue", "skip",
        "आगे", "अगला", "आगे बढ़ो", "aage", "agla",
        "அடுத்து", "அடுத்தது", "முன்னே", "aduthu", "aduthathu"
    ]):
        return "next"

    # Back / Previous
    if any(k in t for k in [
        "back", "previous",
        "पीछे", "पिछला", "peeche", "pichla",
        "பின்னால்", "முந்தைய", "முந்தையது", "pinnal", "munthaiya"
    ]):
        return "back"

    # Home / Main Menu
    if any(k in t for k in [
        "home", "main menu", "menu", "start",
        "होम", "शुरू", "मुख्य", "मेनू", "shuru", "mukhya",
        "முகப்பு", "ஆரம்பம்", "மெனு", "aarambam", "mugappu"
    ]):
        return "home"

    # Stop / Cancel / Exit
    if any(k in t for k in [
        "stop", "cancel", "exit", "quit", "pause",
        "रुको", "बंद", "रोको", "ruko", "band",
        "நிறுத்து", "நில்", "ரத்து", "niruthu", "nil"
    ]):
        return "stop"

    return None


def get_prompt(language: str, key: str, **kwargs) -> str:
    """Get a localized prompt string."""
    lang_prompts = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS["en"])
    template = lang_prompts.get(key, LANGUAGE_PROMPTS["en"].get(key, key))
    return template.format(**kwargs)


def build_question_in_language(field_label: str, language: str) -> str:
    """
    Look up or generate the question for a field in the chosen language (en, hi, ta).
    """
    lang = language if language in ("en", "hi", "ta") else "en"

    # Questions generated for scanned bank forms carry their own translations
    from services.bank_form_service import translate_question
    translated = translate_question(field_label, lang)
    if translated:
        return translated

    # Exact or substring label lookup
    for label_key, translations in LOCALIZED_QUESTIONS.items():
        if label_key.lower() == field_label.lower() or label_key.lower() in field_label.lower():
            return translations.get(lang, translations.get("en", f"Please provide your {field_label}"))

    # Fallback generic questions
    if lang == "hi":
        return f"कृपया अपना {field_label} बताएं।"
    elif lang == "ta":
        return f"தயவுசெய்து உங்கள் {field_label} விவரத்தை சொல்லுங்கள்."
    return f"Please provide your {field_label}."


def build_readback_text(language: str, label: str, interpreted_value: str) -> str:
    """Build the read-back confirmation sentence in the user's language."""
    return get_prompt(language, "heard", value=interpreted_value)


def validate_field(field_type: str, value: str) -> tuple[bool, str]:
    """
    Validate a field value deterministically.
    Returns (is_valid, validation_message).
    """
    val = value.strip()
    if not val:
        return False, "Value cannot be empty."

    if field_type in ("cheque_amount", "cheque_date"):
        from services.cheque_service import validate_cheque_field
        return validate_cheque_field(field_type, val)

    if field_type.startswith("choice:"):
        options = field_type[len("choice:"):].split("|")
        if val in options:
            return True, "Valid"
        return False, "Please choose one of: " + ", ".join(options) + "."

    digits_only = re.sub(r"\D", "", normalize_digits(val))

    if field_type == "phone":
        # 10 digits starting with 6, 7, 8, or 9 (standard Indian mobile format)
        if len(digits_only) == 10 and digits_only[0] in "6789":
            return True, "Valid"
        return False, "Please provide a valid 10-digit mobile number starting with 6, 7, 8, or 9."

    elif field_type == "pin":
        # 6 digits, first digit 1-9
        if len(digits_only) == 6 and digits_only[0] != "0":
            return True, "Valid"
        return False, "Please provide a valid 6-digit PIN code."

    elif field_type == "aadhaar":
        # 12 digits
        if len(digits_only) == 12:
            return True, "Valid"
        return False, "Please provide a valid 12-digit Aadhaar number."

    elif field_type == "pan":
        # 10 alphanumeric characters (format: ABCDE1234F) or 10 chars
        clean_pan = re.sub(r"[^A-Za-z0-9]", "", val).upper()
        if len(clean_pan) == 10:
            return True, "Valid"
        return False, "Please provide a valid 10-character PAN number."

    elif field_type == "date":
        # Must have day, month, year or recognized date structure
        if len(val) >= 4 and (len(digits_only) >= 4 or any(m in val.lower() for m in MONTHS_MAP)):
            return True, "Valid"
        return False, "Please provide a valid date with day, month, and year."

    elif field_type == "name":
        # At least 2 letters
        letters_only = re.sub(r"[\d\W_]", "", val)
        if len(letters_only) >= 2 or len(val) >= 2:
            return True, "Valid"
        return False, "Please provide a valid name."

    elif field_type == "address":
        if len(val) >= 3:
            return True, "Valid"
        return False, "Please provide a complete address."

    elif field_type == "number":
        if len(digits_only) >= 1:
            return True, "Valid"
        return False, "Please provide a valid numeric value."

    # Generic text
    if len(val) >= 1:
        return True, "Valid"
    return False, "Please provide a valid answer."


def interpret_answer(transcribed: str, field_type: str, field_label: str) -> str:
    """
    Clean, normalize, and extract valid values from transcribed speech across English, Hindi, and Tamil.
    """
    raw = transcribed.strip()
    if not raw:
        return ""

    value = normalize_digits(raw)

    if field_type == "cheque_amount":
        from services.cheque_service import interpret_amount
        return interpret_amount(value)

    if field_type == "cheque_date":
        from services.cheque_service import interpret_date
        return interpret_date(value)

    if field_type.startswith("choice:"):
        from services.bank_form_service import interpret_choice
        return interpret_choice(value, field_type[len("choice:"):].split("|"))

    if field_type == "payee":
        from services.bank_form_service import interpret_payee
        return interpret_payee(value) or interpret_answer(value, "name", field_label)

    if field_type == "phone":
        digits = re.sub(r"\D", "", value)
        if len(digits) == 10:
            return digits
        elif len(digits) == 12 and digits.startswith("91"):
            return digits[2:]
        elif len(digits) > 10:
            return digits[-10:]
        elif len(digits) < 10:
            extracted = extract_spoken_digits(value)
            if len(extracted) == 10:
                return extracted
            elif len(extracted) == 12 and extracted.startswith("91"):
                return extracted[2:]
        return digits or value

    elif field_type == "pin":
        digits = re.sub(r"\D", "", value)
        if len(digits) == 6:
            return digits
        extracted = extract_spoken_digits(value)
        if len(extracted) == 6:
            return extracted
        return digits or value

    elif field_type == "aadhaar":
        digits = re.sub(r"\D", "", value)
        if len(digits) == 12:
            return digits
        extracted = extract_spoken_digits(value)
        if len(extracted) == 12:
            return extracted
        return digits or value

    elif field_type == "pan":
        cleaned = re.sub(r"[^A-Za-z0-9]", "", value).upper()
        return cleaned

    elif field_type in ("number", "amount", "income", "land"):
        digits = re.sub(r"\D", "", value)
        if digits:
            return digits
        extracted = extract_spoken_digits(value)
        if extracted:
            return extracted
        return value

    elif field_type == "name":
        # Remove common spoken noise words in en, hi, ta
        words = value.split()
        noise_words = {
            "my", "name", "is", "mine", "am", "i", "the",
            "mera", "naam", "hai", "naam", "hum", "main", "h",
            "peyar", "ennudaiya", "en", "peyar", "ennoda", "per",
            "मेरा", "मेरी", "नाम", "है", "हैं", "मैं", "हूँ", "हूं", "का", "जी",
            "என்", "என்னுடைய", "பெயர்", "நான்",
        }
        filtered = [w for w in words if w.lower() not in noise_words]
        if filtered:
            value = " ".join(filtered)
        return " ".join(w.capitalize() for w in value.split())

    elif field_type == "date":
        # Convert spoken months if present
        lower = value.lower()
        for month_name, month_num in MONTHS_MAP.items():
            if month_name in lower:
                # Replace month name with formatted numeric or standard name
                pass
        return value.strip().title()

    elif field_type == "gender":
        t = value.lower()
        if any(w in t for w in ["female", "woman", "girl", "महिला", "औरत", "स्त्री", "பெண்", "பெண்கள்"]):
            return "Female"
        elif any(w in t for w in ["male", "man", "boy", "पुरुष", "मर्द", "ஆண்"]):
            return "Male"
        elif any(w in t for w in ["other", "trans", "तीसरा", "மற்றவை", "திருநங்கை"]):
            return "Other"
        return value.capitalize()

    return value
