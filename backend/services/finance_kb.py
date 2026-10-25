"""
Finance knowledge base for the guidance chatbot — English, Hindi and Tamil.

Each topic has:
  cat      category shown as a badge (banking, cards, payments, savings, loans, insurance, pension,
           schemes, safety, complaints, documents, tax, app)
  title    short title per language (used as a follow-up suggestion chip)
  strong   distinctive keywords (weight 3)   weak  generic keywords (weight 1)
           ASCII keywords match whole words; Hindi / Tamil keywords match as substrings (Tamil ones are stems)
  answer   2-4 plain sentences per language
  related  topics to suggest next
  links    facet → topic ('docs', 'how', 'eligibility', 'cost', 'claim', 'where')
  offer    (target, question per language) — a yes/no question asked at the end of the answer

Figures are the commonly published rules (RBI / Government of India); rates that change are described as
'currently about', and answers point people to their bank or the official portal to confirm.
"""

TOPICS = {}


def T(tid, cat, title, strong, weak, en, hi, ta, related=(), links=None, offer=None):
    TOPICS[tid] = {
        "cat": cat,
        "title": {"en": title[0], "hi": title[1], "ta": title[2]},
        "strong": strong,
        "weak": weak,
        "answer": {"en": en, "hi": hi, "ta": ta},
        "related": list(related),
        "links": links or {},
        "offer": offer,
    }


# ─── Banking basics ───────────────────────────────────────────────────────────

T("savings_account", "banking",
  ("What is a savings account?", "बचत खाता क्या है?", "சேமிப்பு கணக்கு என்றால் என்ன?"),
  ["savings account", "saving account", "bachat khata", "बचत खाता", "सेविंग", "சேமிப்பு கணக்"],
  ["account", "khata", "खाता", "கணக்"],
  "A savings account is the safest place to keep your money. It earns interest (currently about 2.5% to 4% a year) and your deposits in each bank are insured up to ₹5 lakh by DICGC, a government body. You can withdraw any time using the passbook, ATM card or UPI.",
  "बचत खाता आपके पैसे रखने की सबसे सुरक्षित जगह है। इस पर ब्याज मिलता है (अभी लगभग 2.5% से 4% सालाना) और हर बैंक में आपकी जमा राशि ₹5 लाख तक सरकारी संस्था DICGC से बीमित होती है। आप पासबुक, एटीएम कार्ड या UPI से कभी भी पैसे निकाल सकते हैं।",
  "சேமிப்பு கணக்கு உங்கள் பணத்தை வைக்க மிகவும் பாதுகாப்பான இடம். இதற்கு வட்டி கிடைக்கும் (தற்போது ஆண்டுக்கு சுமார் 2.5% முதல் 4%), ஒவ்வொரு வங்கியிலும் உங்கள் வைப்புத்தொகை ₹5 லட்சம் வரை அரசு அமைப்பான DICGC மூலம் காப்பீடு செய்யப்பட்டுள்ளது. பாஸ்புக், ஏடிஎம் அட்டை அல்லது UPI மூலம் எப்போது வேண்டுமானாலும் பணம் எடுக்கலாம்.",
  related=("open_account", "jan_dhan", "fd"),
  links={"how": "open_account", "docs": "kyc_docs", "cost": "min_balance"},
  offer=("open_account", ("Would you like to know how to open one?", "क्या आप जानना चाहेंगे कि खाता कैसे खोलें?", "கணக்கு எப்படி திறப்பது என்று தெரிந்துகொள்ள விரும்புகிறீர்களா?")))

T("open_account", "banking",
  ("How to open a bank account", "बैंक खाता कैसे खोलें", "வங்கி கணக்கு திறப்பது எப்படி"),
  ["open account", "open a bank account", "open bank account", "new account", "account kaise khole", "khata kholna", "khata khol",
   "खाता खोल", "खाता कैसे", "नया खाता", "கணக்கு திற", "கணக்கை திற", "புதிய கணக்"],
  ["account", "khata", "खाता", "கணக்", "bank", "बैंक", "வங்கி"],
  "To open a bank account, visit any bank branch or a Bank Mitra (banking correspondent) near you. Take your Aadhaar card, PAN card (or fill Form 60 if you have no PAN) and one photo. Ask for a zero-balance account (BSBDA or Jan Dhan) if you do not want to keep a minimum balance. The account is usually opened the same day.",
  "बैंक खाता खोलने के लिए नज़दीकी बैंक शाखा या बैंक मित्र के पास जाएं। अपना आधार कार्ड, पैन कार्ड (पैन न हो तो फॉर्म 60 भरें) और एक फोटो ले जाएं। अगर न्यूनतम बैलेंस नहीं रखना चाहते तो ज़ीरो बैलेंस खाता (BSBDA या जन धन) मांगें। खाता आमतौर पर उसी दिन खुल जाता है।",
  "வங்கி கணக்கு திறக்க அருகிலுள்ள வங்கிக் கிளை அல்லது வங்கி மித்ரா (வங்கி முகவர்) இடம் செல்லுங்கள். ஆதார் அட்டை, பான் அட்டை (பான் இல்லையெனில் படிவம் 60) மற்றும் ஒரு புகைப்படம் எடுத்துச் செல்லுங்கள். குறைந்தபட்ச இருப்பு வைக்க விரும்பவில்லை என்றால் ஜீரோ பேலன்ஸ் கணக்கை (BSBDA அல்லது ஜன் தன்) கேளுங்கள். பொதுவாக அதே நாளில் கணக்கு திறக்கப்படும்.",
  related=("jan_dhan", "kyc_docs", "nominee"),
  links={"docs": "kyc_docs", "cost": "min_balance", "eligibility": "kyc_docs"},
  offer=("kyc_docs", ("Shall I tell you which documents are accepted?", "क्या मैं बताऊं कि कौन-कौन से दस्तावेज़ मान्य हैं?", "எந்த ஆவணங்கள் ஏற்கப்படும் என்று சொல்லட்டுமா?")))

T("jan_dhan", "banking",
  ("Jan Dhan account (PMJDY)", "जन धन खाता (PMJDY)", "ஜன் தன் கணக்கு (PMJDY)"),
  ["jan dhan", "jandhan", "pmjdy", "zero balance", "जन धन", "जनधन", "ज़ीरो बैलेंस", "जीरो बैलेंस", "ஜன் தன்", "ஜீரோ பேலன்ஸ்"],
  [],
  "Pradhan Mantri Jan Dhan Yojana gives a free zero-balance bank account. You get a RuPay debit card with ₹2 lakh accident insurance, an overdraft of up to ₹10,000 for eligible account holders, and government benefits (DBT) come straight into this account. Open it at any bank branch or Bank Mitra with your Aadhaar.",
  "प्रधानमंत्री जन धन योजना में मुफ्त ज़ीरो बैलेंस बैंक खाता मिलता है। इसमें ₹2 लाख के दुर्घटना बीमा वाला RuPay डेबिट कार्ड, पात्र खाताधारकों को ₹10,000 तक का ओवरड्राफ्ट मिलता है, और सरकारी पैसा (DBT) सीधे इसी खाते में आता है। आधार लेकर किसी भी बैंक शाखा या बैंक मित्र के पास खुलवाएं।",
  "பிரதமர் ஜன் தன் யோஜனா மூலம் இலவச ஜீரோ பேலன்ஸ் வங்கி கணக்கு கிடைக்கும். ₹2 லட்சம் விபத்து காப்பீட்டுடன் RuPay டெபிட் அட்டை, தகுதியானவர்களுக்கு ₹10,000 வரை ஓவர்டிராஃப்ட் கிடைக்கும், அரசு உதவித்தொகை (DBT) நேரடியாக இந்தக் கணக்கில் வரும். ஆதாருடன் எந்த வங்கிக் கிளை அல்லது வங்கி மித்ராவிலும் திறக்கலாம்.",
  related=("open_account", "dbt_seeding", "pmsby"),
  links={"how": "open_account", "docs": "kyc_docs"})

T("kyc_docs", "documents",
  ("Documents needed (KYC)", "ज़रूरी दस्तावेज़ (KYC)", "தேவையான ஆவணங்கள் (KYC)"),
  ["kyc", "documents", "document", "papers", "kagaz", "kagzat", "दस्तावेज", "कागज", "केवाईसी", "ஆவண", "கேஒய்சி"],
  ["proof", "id proof", "पहचान", "அடையாள"],
  "For KYC, banks accept any one of these as identity and address proof: Aadhaar card, passport, driving licence, voter ID, NREGA job card signed by an officer, or the National Population Register letter. You also need a PAN card or Form 60, and a recent photo. If you have no documents at all, you can still open a 'small account' for 12 months.",
  "KYC के लिए बैंक पहचान और पते के प्रमाण के रूप में इनमें से कोई एक मानते हैं: आधार कार्ड, पासपोर्ट, ड्राइविंग लाइसेंस, वोटर आईडी, अधिकारी द्वारा हस्ताक्षरित नरेगा जॉब कार्ड, या राष्ट्रीय जनसंख्या रजिस्टर का पत्र। साथ में पैन कार्ड या फॉर्म 60 और एक फोटो चाहिए। अगर कोई दस्तावेज़ नहीं है, तब भी 12 महीने के लिए 'छोटा खाता' खुल सकता है।",
  "KYC-க்கு அடையாளம் மற்றும் முகவரி சான்றாக இவற்றில் ஏதேனும் ஒன்றை வங்கிகள் ஏற்கின்றன: ஆதார் அட்டை, பாஸ்போர்ட், ஓட்டுநர் உரிமம், வாக்காளர் அடையாள அட்டை, அதிகாரி கையெழுத்திட்ட நூறு நாள் வேலை அட்டை, அல்லது தேசிய மக்கள்தொகை பதிவேட்டுக் கடிதம். பான் அட்டை அல்லது படிவம் 60 மற்றும் ஒரு புகைப்படமும் தேவை. எந்த ஆவணமும் இல்லையென்றாலும் 12 மாதங்களுக்கு 'சிறு கணக்கு' திறக்கலாம்.",
  related=("small_account", "open_account", "pan"),
  offer=("small_account", ("Do you want to know about the small account for people without documents?", "क्या आप बिना दस्तावेज़ वाले 'छोटे खाते' के बारे में जानना चाहेंगे?", "ஆவணம் இல்லாதவர்களுக்கான 'சிறு கணக்கு' பற்றி தெரிந்துகொள்ள விரும்புகிறீர்களா?")))

T("small_account", "banking",
  ("Account without documents", "बिना दस्तावेज़ खाता", "ஆவணம் இல்லாத கணக்கு"),
  ["small account", "no documents", "without documents", "no document", "bina document", "bina kagaz", "छोटा खाता", "बिना दस्तावेज", "बिना कागज",
   "சிறு கணக்", "ஆவணம் இல்லா"],
  [],
  "If you have no identity documents, a bank can open a 'small account' with just your photo and signature or thumb print, signed in front of a bank officer. Limits: balance up to ₹50,000, total deposits up to ₹1 lakh in a year and withdrawals up to ₹10,000 a month. It stays valid for 12 months, and is extended if you show that you have applied for a document.",
  "अगर आपके पास कोई पहचान दस्तावेज़ नहीं है, तो बैंक अधिकारी के सामने फोटो और हस्ताक्षर या अंगूठा लगाकर 'छोटा खाता' खुल सकता है। सीमा: बैलेंस ₹50,000 तक, साल में कुल जमा ₹1 लाख तक और महीने में ₹10,000 तक निकासी। यह 12 महीने चलता है, और दस्तावेज़ के लिए आवेदन दिखाने पर आगे बढ़ जाता है।",
  "அடையாள ஆவணம் இல்லையென்றால், வங்கி அதிகாரி முன் புகைப்படம் மற்றும் கையெழுத்து அல்லது கைரேகை வைத்து 'சிறு கணக்கு' திறக்கலாம். வரம்புகள்: இருப்பு ₹50,000 வரை, ஆண்டுக்கு மொத்த வரவு ₹1 லட்சம் வரை, மாதம் ₹10,000 வரை எடுக்கலாம். இது 12 மாதங்கள் செல்லுபடியாகும்; ஆவணத்திற்கு விண்ணப்பித்ததைக் காட்டினால் நீட்டிக்கப்படும்.",
  related=("kyc_docs", "aadhaar", "jan_dhan"))

T("min_balance", "banking",
  ("Minimum balance and charges", "न्यूनतम बैलेंस और शुल्क", "குறைந்தபட்ச இருப்பு மற்றும் கட்டணம்"),
  ["minimum balance", "min balance", "minimum", "penalty", "balance charge", "न्यूनतम", "मिनिमम", "जुर्माना", "குறைந்தபட்ச இருப்ப", "அபராத"],
  ["charges", "charge", "fee", "शुल्क", "चार्ज", "கட்டண"],
  "Many regular savings accounts charge a penalty if your balance falls below the minimum the bank sets. Zero-balance accounts (BSBDA and Jan Dhan) have no minimum balance and no penalty. Banks cannot make your balance negative only because of a minimum-balance penalty. Ask your bank for its charges list before opening an account.",
  "कई सामान्य बचत खातों में बैलेंस बैंक की तय न्यूनतम राशि से कम होने पर जुर्माना लगता है। ज़ीरो बैलेंस खातों (BSBDA और जन धन) में न कोई न्यूनतम बैलेंस है, न जुर्माना। सिर्फ न्यूनतम बैलेंस के जुर्माने की वजह से बैंक आपका बैलेंस माइनस में नहीं कर सकता। खाता खोलने से पहले बैंक से शुल्क सूची मांगें।",
  "பல சாதாரண சேமிப்பு கணக்குகளில் இருப்பு வங்கி நிர்ணயித்த குறைந்தபட்சத்தை விடக் குறைந்தால் அபராதம் விதிக்கப்படும். ஜீரோ பேலன்ஸ் கணக்குகளில் (BSBDA, ஜன் தன்) குறைந்தபட்ச இருப்பும் அபராதமும் இல்லை. குறைந்தபட்ச இருப்பு அபராதத்தால் மட்டும் வங்கி உங்கள் இருப்பை மைனஸ் ஆக்க முடியாது. கணக்கு திறப்பதற்கு முன் கட்டணப் பட்டியலை கேளுங்கள்.",
  related=("jan_dhan", "atm_charges", "bank_complaint"))

T("nominee", "banking",
  ("Adding a nominee", "नॉमिनी जोड़ना", "நாமினி சேர்த்தல்"),
  ["nominee", "nomination", "after death", "death of account holder", "नॉमिनी", "नामांकन", "मृत्यु के बाद", "நாமினி", "வாரிசு", "இறப்புக்குப் பின்"],
  [],
  "A nominee is the person who receives the money in your account if something happens to you. You can add or change a nominee free of charge at your branch with a nomination form, or in net banking or the mobile app. Without a nominee, your family may have to go through long paperwork to claim the money, so please add one.",
  "नॉमिनी वह व्यक्ति है जिसे आपके साथ कुछ होने पर आपके खाते का पैसा मिलता है। आप शाखा में नामांकन फॉर्म भरकर, या नेट बैंकिंग/मोबाइल ऐप से मुफ्त में नॉमिनी जोड़ या बदल सकते हैं। नॉमिनी न होने पर परिवार को पैसा पाने के लिए लंबी कागज़ी कार्रवाई करनी पड़ सकती है, इसलिए नॉमिनी ज़रूर जोड़ें।",
  "நாமினி என்பவர் உங்களுக்கு ஏதாவது நேர்ந்தால் உங்கள் கணக்கில் உள்ள பணத்தைப் பெறுபவர். கிளையில் நியமனப் படிவம் மூலம் அல்லது நெட் பேங்கிங் / மொபைல் செயலியில் இலவசமாக நாமினியைச் சேர்க்கலாம் அல்லது மாற்றலாம். நாமினி இல்லையென்றால் குடும்பத்தினர் பணம் பெற நீண்ட ஆவண நடைமுறைகளைச் செய்ய வேண்டியிருக்கும், எனவே கண்டிப்பாக சேர்க்கவும்.",
  related=("insurance_claim", "open_account", "dormant_account"))

T("dormant_account", "banking",
  ("Inactive / dormant account", "बंद पड़ा (निष्क्रिय) खाता", "செயலற்ற கணக்கு"),
  ["dormant", "inoperative", "inactive account", "unclaimed", "account band", "khata band", "निष्क्रिय", "बंद खाता", "खाता बंद", "लावारिस",
   "செயலற்ற", "முடங்கிய கணக்", "உரிமை கோரப்படாத"],
  [],
  "If there is no deposit or withdrawal by you for 2 years, the account becomes inoperative. Your money is safe: visit any branch of your bank with your KYC documents to reactivate it, free of charge. Money unclaimed for 10 years moves to an RBI fund but can still be claimed any time; search for it on the RBI UDGAM portal (udgam.rbi.org.in).",
  "अगर 2 साल तक आपकी ओर से कोई जमा या निकासी नहीं होती, तो खाता निष्क्रिय हो जाता है। आपका पैसा सुरक्षित है: KYC दस्तावेज़ लेकर अपने बैंक की किसी भी शाखा में जाकर मुफ्त में खाता फिर से चालू कराएं। 10 साल तक बिना दावे का पैसा RBI के फंड में चला जाता है, पर कभी भी वापस मांगा जा सकता है; RBI के UDGAM पोर्टल (udgam.rbi.org.in) पर खोजें।",
  "2 ஆண்டுகள் நீங்கள் எந்த வரவு அல்லது பணம் எடுத்தலும் செய்யவில்லை என்றால் கணக்கு செயலற்றதாகிவிடும். உங்கள் பணம் பாதுகாப்பாக உள்ளது: KYC ஆவணங்களுடன் உங்கள் வங்கியின் எந்தக் கிளைக்கும் சென்று இலவசமாக மீண்டும் செயல்படுத்தலாம். 10 ஆண்டுகள் உரிமை கோரப்படாத பணம் RBI நிதிக்குச் செல்லும், ஆனாலும் எப்போது வேண்டுமானாலும் கோரலாம்; RBI UDGAM இணையதளத்தில் (udgam.rbi.org.in) தேடுங்கள்.",
  related=("kyc_docs", "nominee", "bank_complaint"))

T("check_balance", "banking",
  ("Check balance / mini statement", "बैलेंस और मिनी स्टेटमेंट", "இருப்பு மற்றும் மினி ஸ்டேட்மென்ட்"),
  ["check balance", "balance check", "balance enquiry", "mini statement", "passbook", "statement", "missed call", "balance kaise", "बैलेंस", "पासबुक", "स्टेटमेंट",
   "இருப்பு", "பாஸ்புக்", "பேலன்ஸ்"],
  [],
  "You can check your balance in many free ways: give a missed call to your bank's balance number from your registered mobile, dial *99# on any phone (works without internet), use the bank's app or UPI app, update your passbook at the branch or passbook kiosk, or use any ATM. Banks also send an SMS for every transaction — read these SMS to spot any money you did not spend.",
  "बैलेंस जानने के कई मुफ्त तरीके हैं: रजिस्टर्ड मोबाइल से बैंक के बैलेंस नंबर पर मिस्ड कॉल दें, किसी भी फोन से *99# डायल करें (बिना इंटरनेट चलता है), बैंक या UPI ऐप देखें, शाखा या पासबुक मशीन में पासबुक अपडेट कराएं, या किसी भी एटीएम का उपयोग करें। हर लेनदेन पर बैंक SMS भेजता है — इन्हें पढ़ें ताकि बिना आपकी जानकारी कटा पैसा तुरंत पकड़ में आए।",
  "இருப்பைத் தெரிந்துகொள்ள பல இலவச வழிகள் உள்ளன: பதிவு செய்த மொபைலில் இருந்து வங்கியின் இருப்பு எண்ணுக்கு மிஸ்டு கால் கொடுங்கள், எந்த போனிலும் *99# டயல் செய்யுங்கள் (இணையம் இல்லாமல் வேலை செய்யும்), வங்கி அல்லது UPI செயலியைப் பாருங்கள், கிளையில் பாஸ்புக்கை புதுப்பியுங்கள், அல்லது ஏடிஎம் பயன்படுத்துங்கள். ஒவ்வொரு பரிவர்த்தனைக்கும் வங்கி SMS அனுப்பும் — நீங்கள் செலவழிக்காத பணம் போனால் உடனே கண்டறிய அவற்றைப் படியுங்கள்.",
  related=("upi_feature_phone", "report_fraud", "atm_use"))

T("interest_basics", "savings",
  ("What is interest?", "ब्याज क्या है?", "வட்டி என்றால் என்ன?"),
  ["what is interest", "interest kya", "byaj kya", "simple interest", "compound interest", "ब्याज क्या", "चक्रवृद्धि", "வட்டி என்றால்", "கூட்டு வட்டி"],
  ["interest", "byaj", "ब्याज", "வட்டி"],
  "Interest is the extra money paid for using money. When you save in a bank, the bank pays you interest; when you take a loan, you pay interest to the lender. For example, ₹10,000 saved at 7% a year earns about ₹700 in a year. In compound interest, the interest also earns interest, so savings grow faster the longer you keep them.",
  "ब्याज वह अतिरिक्त पैसा है जो पैसे के उपयोग के बदले दिया जाता है। बैंक में बचत करने पर बैंक आपको ब्याज देता है; लोन लेने पर आप ब्याज चुकाते हैं। जैसे ₹10,000 पर 7% सालाना ब्याज से साल भर में लगभग ₹700 मिलते हैं। चक्रवृद्धि ब्याज में ब्याज पर भी ब्याज मिलता है, इसलिए जितना लंबा बचत रखें, उतनी तेज़ी से बढ़ती है।",
  "வட்டி என்பது பணத்தைப் பயன்படுத்தியதற்காகக் கொடுக்கப்படும் கூடுதல் பணம். வங்கியில் சேமித்தால் வங்கி உங்களுக்கு வட்டி தரும்; கடன் வாங்கினால் நீங்கள் வட்டி கட்ட வேண்டும். உதாரணமாக ₹10,000-க்கு ஆண்டுக்கு 7% வட்டியில் ஒரு ஆண்டில் சுமார் ₹700 கிடைக்கும். கூட்டு வட்டியில் வட்டிக்கும் வட்டி கிடைப்பதால், நீண்ட காலம் சேமித்தால் வேகமாக வளரும்.",
  related=("fd", "emi", "ppf"),
  offer=("calc_fd", ("Shall I calculate how much a fixed deposit would grow for you?", "क्या मैं हिसाब लगाऊं कि आपकी FD कितनी बढ़ेगी?", "உங்கள் நிலை வைப்பு எவ்வளவு வளரும் என்று கணக்கிடட்டுமா?")))

# ─── Cards & ATM ──────────────────────────────────────────────────────────────

T("atm_use", "cards",
  ("Using an ATM safely", "एटीएम का सुरक्षित उपयोग", "ஏடிஎம்-ஐ பாதுகாப்பாக பயன்படுத்துதல்"),
  ["atm", "debit card", "withdraw cash", "cash withdraw", "paise nikal", "एटीएम", "डेबिट कार्ड", "पैसे निकाल", "ஏடிஎம்", "டெபிட் அட்டை", "பணம் எடு"],
  ["card", "कार्ड", "அட்டை", "cash", "withdraw"],
  "Insert your debit card, choose the language, enter your 4-digit PIN, select 'Withdrawal' and type the amount. Cover the keypad with your hand while typing the PIN, never take help from strangers at the ATM, and collect your card and cash before leaving. If cash does not come out but money is cut, the bank must return it within 5 working days.",
  "डेबिट कार्ड डालें, भाषा चुनें, 4 अंकों का पिन डालें, 'निकासी' चुनें और राशि लिखें। पिन डालते समय कीपैड को हाथ से ढकें, एटीएम पर किसी अजनबी से मदद न लें, और जाने से पहले कार्ड और पैसे ले लें। अगर पैसे नहीं निकले पर खाते से कट गए, तो बैंक को 5 कार्य दिवस में लौटाने होते हैं।",
  "டெபிட் அட்டையைச் செருகி, மொழியைத் தேர்ந்தெடுத்து, 4 இலக்க PIN-ஐ உள்ளிட்டு, 'பணம் எடுத்தல்' என்பதைத் தேர்ந்தெடுத்து தொகையை உள்ளிடுங்கள். PIN அழுத்தும்போது கையால் மறைக்கவும், ஏடிஎம்-இல் அந்நியர்களின் உதவியை ஏற்காதீர்கள், வெளியேறும் முன் அட்டையையும் பணத்தையும் எடுத்துக்கொள்ளுங்கள். பணம் வரவில்லை ஆனால் கணக்கில் கழிக்கப்பட்டால், வங்கி 5 வேலை நாட்களுக்குள் திருப்பித் தர வேண்டும்.",
  related=("atm_charges", "forgot_pin", "lost_card"),
  links={"cost": "atm_charges"})

T("atm_charges", "cards",
  ("ATM free limit and charges", "एटीएम की मुफ्त सीमा और शुल्क", "ஏடிஎம் இலவச வரம்பு மற்றும் கட்டணம்"),
  ["atm charges", "atm charge", "free transactions", "free limit", "atm fee", "एटीएम शुल्क", "एटीएम चार्ज", "मुफ्त लेनदेन", "ஏடிஎம் கட்டண", "இலவச பரிவர்த்தனை"],
  ["atm", "एटीएम", "ஏடிஎம்"],
  "Every month you get 5 free ATM transactions at your own bank's ATMs. At other banks' ATMs you get 3 free in big metro cities and 5 free in other places. After that, banks can charge up to about ₹23 per transaction. Checking balance on the UPI app or by missed call is free, so save ATM visits for cash.",
  "हर महीने अपने बैंक के एटीएम पर 5 लेनदेन मुफ्त होते हैं। दूसरे बैंकों के एटीएम पर बड़े महानगरों में 3 और बाकी जगह 5 लेनदेन मुफ्त हैं। उसके बाद बैंक हर लेनदेन पर लगभग ₹23 तक शुल्क ले सकते हैं। बैलेंस UPI ऐप या मिस्ड कॉल से मुफ्त में देखें, एटीएम का उपयोग सिर्फ नकद के लिए करें।",
  "ஒவ்வொரு மாதமும் உங்கள் வங்கியின் ஏடிஎம்-இல் 5 பரிவர்த்தனைகள் இலவசம். மற்ற வங்கி ஏடிஎம்-களில் பெருநகரங்களில் 3, மற்ற இடங்களில் 5 இலவசம். அதன் பிறகு ஒவ்வொரு பரிவர்த்தனைக்கும் சுமார் ₹23 வரை கட்டணம் விதிக்கலாம். இருப்பை UPI செயலி அல்லது மிஸ்டு கால் மூலம் இலவசமாகப் பாருங்கள்; ஏடிஎம்-ஐ பணம் எடுக்க மட்டும் பயன்படுத்துங்கள்.",
  related=("check_balance", "atm_use", "min_balance"))

T("forgot_pin", "cards",
  ("Forgot ATM PIN", "एटीएम पिन भूल गए", "ஏடிஎம் PIN மறந்துவிட்டது"),
  ["forgot pin", "forget pin", "pin bhool", "new pin", "reset pin", "change pin", "green pin", "पिन भूल", "नया पिन", "पिन बदल", "PIN மறந்", "புதிய PIN", "pin மறந்"],
  ["pin", "पिन", "atm", "card", "एटीएम", "ஏடிஎம்"],
  "If you forgot your ATM PIN, you can set a new one yourself: at your bank's ATM choose 'Generate PIN' or 'Green PIN' and enter the OTP sent to your registered mobile. You can also do it in your bank's app or net banking, or visit the branch. Never tell your PIN to anyone — not even bank staff.",
  "अगर एटीएम पिन भूल गए हैं, तो खुद नया बना सकते हैं: अपने बैंक के एटीएम पर 'Generate PIN' या 'Green PIN' चुनें और रजिस्टर्ड मोबाइल पर आए OTP को डालें। बैंक ऐप, नेट बैंकिंग या शाखा से भी नया पिन बनता है। अपना पिन किसी को न बताएं — बैंक कर्मचारी को भी नहीं।",
  "ஏடிஎம் PIN மறந்துவிட்டால் நீங்களே புதியதை உருவாக்கலாம்: உங்கள் வங்கியின் ஏடிஎம்-இல் 'Generate PIN' அல்லது 'Green PIN' தேர்ந்தெடுத்து, பதிவு செய்த மொபைலுக்கு வரும் OTP-ஐ உள்ளிடுங்கள். வங்கி செயலி, நெட் பேங்கிங் அல்லது கிளையிலும் செய்யலாம். உங்கள் PIN-ஐ யாரிடமும் சொல்லாதீர்கள் — வங்கி ஊழியரிடமும் கூட.",
  related=("lost_card", "otp_safety", "atm_use"))

T("lost_card", "cards",
  ("Lost card / block card", "कार्ड खो गया / ब्लॉक करें", "அட்டை தொலைந்தது / முடக்குதல்"),
  ["lost card", "card lost", "card stolen", "block card", "block my card", "card block", "lost my", "stolen", "kho gaya", "kho gya", "chori",
   "खो गया", "चोरी", "ब्लॉक", "தொலைந்த", "தொலைந்து", "திருட", "முடக்க", "பிளாக்"],
  ["atm", "card", "debit card", "एटीएम", "कार्ड", "ஏடிஎம்", "அட்டை"],
  "Block the card immediately: call your bank's 24-hour helpline (printed on the passbook and the bank website), or block it in the bank app, net banking or by SMS. If any money was taken without your permission, report it to the bank within 3 days — then you do not lose that money under RBI rules. Also call 1930 if it was a fraud.",
  "कार्ड तुरंत ब्लॉक करें: बैंक की 24 घंटे की हेल्पलाइन पर कॉल करें (पासबुक और बैंक वेबसाइट पर लिखी होती है), या बैंक ऐप, नेट बैंकिंग या SMS से ब्लॉक करें। अगर आपकी अनुमति के बिना पैसा कटा है, तो 3 दिन के अंदर बैंक को बताएं — तब RBI नियमों के अनुसार आपको वह पैसा नहीं गंवाना पड़ता। धोखाधड़ी हो तो 1930 पर भी कॉल करें।",
  "அட்டையை உடனே முடக்குங்கள்: வங்கியின் 24 மணி நேர உதவி எண்ணுக்கு அழையுங்கள் (பாஸ்புக் மற்றும் வங்கி இணையதளத்தில் இருக்கும்), அல்லது வங்கி செயலி, நெட் பேங்கிங் அல்லது SMS மூலம் முடக்குங்கள். உங்கள் அனுமதியின்றி பணம் எடுக்கப்பட்டிருந்தால் 3 நாட்களுக்குள் வங்கிக்குத் தெரிவியுங்கள் — அப்போது RBI விதிகளின்படி அந்தப் பணத்தை இழக்க மாட்டீர்கள். மோசடி என்றால் 1930-க்கும் அழையுங்கள்.",
  related=("report_fraud", "forgot_pin", "bank_complaint"))

T("atm_cash_not_dispensed", "cards",
  ("Money cut but cash not received", "पैसा कटा पर नकद नहीं मिला", "பணம் கழிந்தது ஆனால் கிடைக்கவில்லை"),
  ["cash not dispensed", "cash not received", "money deducted", "amount debited", "paise kat gaye", "paisa kat gaya", "nahi nikla", "पैसे कट", "पैसा कट",
   "नकद नहीं", "नहीं निकले", "பணம் கழிக்கப்பட்ட", "பணம் வரவில்லை", "பணம் கழிந்த"],
  ["atm", "एटीएम", "ஏடிஎம்", "cash", "नकद"],
  "If money was cut from your account but the ATM gave no cash, the bank must put it back automatically within 5 working days. If it does not, the bank has to pay you ₹100 for every day of delay. Keep the ATM slip or SMS, and complain to your bank (branch, helpline or app) with the date, time and ATM location.",
  "अगर खाते से पैसा कट गया पर एटीएम से नकद नहीं निकला, तो बैंक को 5 कार्य दिवस में अपने आप पैसा लौटाना होता है। ऐसा न होने पर देरी के हर दिन के लिए बैंक को आपको ₹100 देने होते हैं। एटीएम पर्ची या SMS संभालकर रखें, और तारीख, समय और एटीएम की जगह बताकर बैंक (शाखा, हेल्पलाइन या ऐप) में शिकायत करें।",
  "கணக்கில் பணம் கழிக்கப்பட்டு ஏடிஎம் பணம் தரவில்லை என்றால், வங்கி 5 வேலை நாட்களுக்குள் தானாகவே திருப்பித் தர வேண்டும். இல்லையென்றால் தாமதமாகும் ஒவ்வொரு நாளுக்கும் வங்கி உங்களுக்கு ₹100 வழங்க வேண்டும். ஏடிஎம் ரசீது அல்லது SMS-ஐ வைத்துக்கொண்டு, தேதி, நேரம், ஏடிஎம் இடத்துடன் வங்கியில் (கிளை, உதவி எண் அல்லது செயலி) புகார் செய்யுங்கள்.",
  related=("bank_complaint", "upi_failed", "atm_use"))

# ─── Payments ─────────────────────────────────────────────────────────────────

T("upi", "payments",
  ("How UPI works", "UPI कैसे काम करता है", "UPI எப்படி வேலை செய்கிறது"),
  ["upi", "gpay", "google pay", "phonepe", "phone pe", "paytm", "bhim", "qr code", "scan and pay", "यूपीआई", "யுபிஐ"],
  ["digital payment", "online payment", "payment", "भुगतान", "பணம் செலுத்த"],
  "UPI lets you send and receive money instantly from your phone, 24 hours a day, usually free. Install an app like BHIM, Google Pay, PhonePe or Paytm, verify the mobile number linked to your bank, choose your bank account and set a secret UPI PIN using your debit card details. To pay, scan the shop's QR code, check the name shown, type the amount and enter your PIN.",
  "UPI से आप फोन से तुरंत, 24 घंटे, आमतौर पर मुफ्त में पैसा भेज और पा सकते हैं। BHIM, Google Pay, PhonePe या Paytm जैसा ऐप डालें, बैंक से जुड़े मोबाइल नंबर की पुष्टि करें, अपना बैंक खाता चुनें और डेबिट कार्ड की जानकारी से गुप्त UPI पिन बनाएं। भुगतान के लिए दुकान का QR कोड स्कैन करें, दिखा हुआ नाम जांचें, राशि लिखें और पिन डालें।",
  "UPI மூலம் உங்கள் போனில் இருந்து உடனடியாக, 24 மணி நேரமும், பொதுவாக இலவசமாக பணம் அனுப்பவும் பெறவும் முடியும். BHIM, Google Pay, PhonePe அல்லது Paytm போன்ற செயலியை நிறுவி, வங்கியுடன் இணைந்த மொபைல் எண்ணை உறுதிப்படுத்தி, வங்கிக் கணக்கைத் தேர்ந்தெடுத்து, டெபிட் அட்டை விவரங்களுடன் ரகசிய UPI PIN அமைக்கவும். பணம் செலுத்த கடையின் QR குறியீட்டை ஸ்கேன் செய்து, காட்டப்படும் பெயரைச் சரிபார்த்து, தொகையை உள்ளிட்டு PIN அழுத்துங்கள்.",
  related=("upi_pin", "upi_wrong_transfer", "upi_feature_phone"),
  links={"how": "upi", "cost": "upi"})

T("upi_pin", "payments",
  ("UPI PIN safety", "UPI पिन की सुरक्षा", "UPI PIN பாதுகாப்பு"),
  ["upi pin", "receive money pin", "collect request", "pin to receive", "पैसे पाने के लिए पिन", "यूपीआई पिन", "UPI பின்", "upi பின்"],
  ["upi", "pin", "पिन"],
  "Your UPI PIN is needed only to SEND money — never to receive money. If someone asks you to enter your PIN or scan a QR code 'to receive' a payment, refund or prize, it is a fraud and money will leave your account. Never share your UPI PIN, and decline any 'collect request' you do not recognise.",
  "UPI पिन सिर्फ पैसा भेजने के लिए चाहिए — पैसा पाने के लिए कभी नहीं। अगर कोई पेमेंट, रिफंड या इनाम 'पाने के लिए' पिन डालने या QR कोड स्कैन करने को कहे, तो यह धोखा है और पैसा आपके खाते से चला जाएगा। अपना UPI पिन कभी किसी को न बताएं, और अनजान 'collect request' को रद्द करें।",
  "UPI PIN பணம் அனுப்ப மட்டுமே தேவை — பணம் பெறுவதற்கு ஒருபோதும் தேவையில்லை. பணம், ரீஃபண்ட் அல்லது பரிசு 'பெறுவதற்கு' PIN அழுத்தவோ QR ஸ்கேன் செய்யவோ யாராவது சொன்னால் அது மோசடி, உங்கள் கணக்கிலிருந்து பணம் போய்விடும். UPI PIN-ஐ யாரிடமும் பகிராதீர்கள்; தெரியாத 'collect request'-ஐ நிராகரியுங்கள்.",
  related=("otp_safety", "report_fraud", "upi"))

T("upi_wrong_transfer", "payments",
  ("Sent money to the wrong person", "गलत व्यक्ति को पैसे भेज दिए", "தவறான நபருக்கு பணம் அனுப்பிவிட்டேன்"),
  ["wrong person", "wrong number", "wrong account", "wrong upi", "galat", "galti se", "sent by mistake", "by mistake", "गलत", "गलती से", "தவறான", "தவறுதலாக", "தவறாக"],
  ["upi", "send money", "sent", "transfer", "पैसे भेज", "भेज दिए", "பணம் அனுப்ப", "அனுப்பிவிட்டேன்"],
  "If you sent money to the wrong UPI ID or account, act quickly: raise a complaint in your UPI app under 'Help' or 'Report a problem' for that transaction, and also inform your bank with the transaction ID. The bank will contact the receiver's bank, but the money can only be returned with the receiver's consent. If it is not resolved in 30 days, complain to the RBI Ombudsman.",
  "अगर गलत UPI आईडी या खाते में पैसे भेज दिए, तो जल्दी करें: UPI ऐप में उस लेनदेन पर 'Help' या 'Report a problem' में शिकायत करें, और ट्रांज़ैक्शन आईडी के साथ अपने बैंक को भी बताएं। बैंक पाने वाले के बैंक से संपर्क करेगा, पर पैसा पाने वाले की सहमति से ही लौटता है। 30 दिन में हल न हो तो RBI लोकपाल में शिकायत करें।",
  "தவறான UPI ID அல்லது கணக்குக்கு பணம் அனுப்பியிருந்தால் விரைவாகச் செயல்படுங்கள்: UPI செயலியில் அந்தப் பரிவர்த்தனைக்கு 'Help' அல்லது 'Report a problem' மூலம் புகார் செய்து, பரிவர்த்தனை ID-யுடன் உங்கள் வங்கிக்கும் தெரிவியுங்கள். வங்கி பெறுநரின் வங்கியைத் தொடர்புகொள்ளும், ஆனால் பெறுநரின் சம்மதத்துடன் மட்டுமே பணம் திரும்ப வரும். 30 நாட்களில் தீர்வு இல்லையெனில் RBI குறைதீர்ப்பாளரிடம் புகார் செய்யுங்கள்.",
  related=("bank_complaint", "upi_failed", "upi"))

T("upi_failed", "payments",
  ("UPI payment failed but money cut", "UPI फेल पर पैसा कटा", "UPI தோல்வி ஆனால் பணம் கழிந்தது"),
  ["payment failed", "transaction failed", "failed transaction", "upi failed", "pending transaction", "payment pending", "fail ho gaya", "फेल", "अटक",
   "தோல்வி", "நிலுவையில்", "பரிவர்த்தனை தோல்வி"],
  ["upi", "यूपीआई", "யுபிஐ", "payment", "भुगतान"],
  "If a UPI payment failed but money was cut, it is usually returned automatically by the next working day. If not, the bank must pay you ₹100 for each day of delay. Do not pay again in a hurry; check the status in the app, and raise a complaint in the app or with your bank using the transaction ID.",
  "अगर UPI भुगतान फेल हुआ पर पैसा कट गया, तो आमतौर पर अगले कार्य दिवस तक अपने आप वापस आ जाता है। न आए तो देरी के हर दिन के लिए बैंक को आपको ₹100 देने होते हैं। जल्दबाज़ी में दोबारा भुगतान न करें; ऐप में स्टेटस देखें, और ट्रांज़ैक्शन आईडी के साथ ऐप या बैंक में शिकायत करें।",
  "UPI பரிவர்த்தனை தோல்வியடைந்து பணம் கழிக்கப்பட்டால், பொதுவாக அடுத்த வேலை நாளுக்குள் தானாகத் திரும்ப வரும். இல்லையெனில் தாமதமாகும் ஒவ்வொரு நாளுக்கும் வங்கி ₹100 வழங்க வேண்டும். அவசரப்பட்டு மீண்டும் பணம் செலுத்தாதீர்கள்; செயலியில் நிலையைப் பார்த்து, பரிவர்த்தனை ID-யுடன் செயலி அல்லது வங்கியில் புகார் செய்யுங்கள்.",
  related=("bank_complaint", "atm_cash_not_dispensed", "upi_wrong_transfer"))

T("upi_feature_phone", "payments",
  ("Payments without smartphone or internet", "बिना स्मार्टफोन/इंटरनेट भुगतान", "ஸ்மார்ட்போன் / இணையம் இல்லாமல் பணம்"),
  ["99#", "*99#", "feature phone", "keypad phone", "without internet", "no internet", "no smartphone", "123pay", "upi 123", "बिना इंटरनेट", "साधारण फोन",
   "बिना स्मार्टफोन", "இணையம் இல்லாமல்", "சாதாரண போன்", "ஸ்மார்ட்போன் இல்லாமல்"],
  [],
  "You can use UPI even on a simple keypad phone without internet. Dial *99# from the mobile number linked to your bank to send money, check balance or set your UPI PIN. You can also use UPI 123PAY, where you call a number and follow voice instructions. The same safety rule applies: never share your PIN.",
  "साधारण कीपैड फोन पर बिना इंटरनेट भी UPI चलता है। बैंक से जुड़े मोबाइल नंबर से *99# डायल करें और पैसा भेजें, बैलेंस देखें या UPI पिन बनाएं। UPI 123PAY में आप एक नंबर पर कॉल करके आवाज़ के निर्देशों से भुगतान कर सकते हैं। सुरक्षा का नियम वही है: पिन किसी को न बताएं।",
  "இணையம் இல்லாத சாதாரண கீபேட் போனிலும் UPI பயன்படுத்தலாம். வங்கியுடன் இணைந்த மொபைல் எண்ணில் இருந்து *99# டயல் செய்து பணம் அனுப்பலாம், இருப்பைப் பார்க்கலாம், UPI PIN அமைக்கலாம். UPI 123PAY-இல் ஒரு எண்ணுக்கு அழைத்து குரல் வழிமுறைகள் மூலம் பணம் செலுத்தலாம். பாதுகாப்பு விதி ஒன்றே: PIN-ஐ யாரிடமும் பகிராதீர்கள்.",
  related=("upi", "check_balance", "upi_pin"))

T("bank_transfer", "payments",
  ("NEFT, RTGS and IMPS", "NEFT, RTGS और IMPS", "NEFT, RTGS மற்றும் IMPS"),
  ["neft", "rtgs", "imps", "ifsc", "bank transfer", "fund transfer", "money transfer", "transfer money", "पैसे ट्रांसफर", "ट्रांसफर", "பணப் பரிமாற்ற", "பணம் அனுப்ப"],
  ["send money", "transfer"],
  "To send money to any bank account you need the account number, the IFSC code of the branch and the receiver's name. IMPS sends money instantly at any time (up to ₹5 lakh), NEFT also works 24x7 in batches, and RTGS is for large amounts of ₹2 lakh or more. Online NEFT and RTGS from savings accounts are free; always double-check the account number before sending.",
  "किसी भी बैंक खाते में पैसा भेजने के लिए खाता संख्या, शाखा का IFSC कोड और पाने वाले का नाम चाहिए। IMPS कभी भी तुरंत पैसा भेजता है (₹5 लाख तक), NEFT भी 24 घंटे चलता है, और RTGS ₹2 लाख या उससे बड़ी राशि के लिए है। बचत खाते से ऑनलाइन NEFT और RTGS मुफ्त हैं; भेजने से पहले खाता संख्या दोबारा जांचें।",
  "எந்த வங்கிக் கணக்குக்கும் பணம் அனுப்ப கணக்கு எண், கிளையின் IFSC குறியீடு மற்றும் பெறுநர் பெயர் தேவை. IMPS எப்போதும் உடனடியாக அனுப்பும் (₹5 லட்சம் வரை), NEFT-உம் 24 மணி நேரமும் வேலை செய்யும், RTGS ₹2 லட்சம் அல்லது அதற்கு மேற்பட்ட பெரிய தொகைக்கு. சேமிப்புக் கணக்கிலிருந்து ஆன்லைன் NEFT, RTGS இலவசம்; அனுப்பும் முன் கணக்கு எண்ணை மீண்டும் சரிபாருங்கள்.",
  related=("upi", "upi_wrong_transfer", "cheque"))

T("cheque", "payments",
  ("How to write a cheque", "चेक कैसे लिखें", "காசோலை எழுதுவது எப்படி"),
  ["cheque", "check book", "cheque book", "chequebook", "crossed", "account payee", "चेक", "चेकबुक", "காசோலை", "செக்"],
  [],
  "On a cheque write the date, the receiver's name, the amount in words and in figures, and sign exactly as in the bank records. Draw two lines across the top-left corner and write 'A/C Payee' so the money can only go into the receiver's account. Never sign a blank cheque, avoid overwriting, and remember a cheque is valid for 3 months from its date. This app can also fill a cheque for you in the Form Fill section.",
  "चेक पर तारीख, पाने वाले का नाम, राशि शब्दों और अंकों में लिखें और बैंक रिकॉर्ड जैसे ही हस्ताक्षर करें। ऊपर बाएं कोने में दो लाइनें खींचकर 'A/C Payee' लिखें ताकि पैसा सिर्फ पाने वाले के खाते में जाए। खाली चेक पर कभी हस्ताक्षर न करें, काट-छांट न करें, और याद रखें कि चेक अपनी तारीख से 3 महीने तक मान्य है। फॉर्म भरें वाले हिस्से में यह ऐप आपका चेक भी भर सकता है।",
  "காசோலையில் தேதி, பெறுநர் பெயர், தொகையை எழுத்திலும் எண்ணிலும் எழுதி, வங்கிப் பதிவில் உள்ளபடியே கையெழுத்திடுங்கள். மேல் இடது மூலையில் இரண்டு கோடுகள் வரைந்து 'A/C Payee' என்று எழுதினால் பணம் பெறுநர் கணக்கில் மட்டுமே செல்லும். வெற்று காசோலையில் கையெழுத்திடாதீர்கள், அடித்தல் திருத்தல் தவிருங்கள்; காசோலை அதன் தேதியிலிருந்து 3 மாதங்கள் செல்லுபடியாகும். படிவம் நிரப்புதல் பகுதியில் இந்தச் செயலி உங்கள் காசோலையை நிரப்பவும் உதவும்.",
  related=("cheque_bounce", "form_fill_help", "bank_transfer"))

T("cheque_bounce", "payments",
  ("Cheque bounce", "चेक बाउंस", "காசோலை திரும்புதல் (பவுன்ஸ்)"),
  ["cheque bounce", "check bounce", "bounced", "bounce", "dishonour", "insufficient funds", "चेक बाउंस", "बाउंस", "பவுன்ஸ்", "திரும்பிய காசோலை"],
  ["cheque", "चेक", "காசோலை"],
  "A cheque bounces when there is not enough money in the account, or the signature or details do not match. The bank charges a fee, and if a cheque you gave for a payment bounces because of low balance, it is an offence under Section 138 of the Negotiable Instruments Act — the receiver can send a legal notice and file a case. Always keep enough balance before giving a cheque.",
  "चेक तब बाउंस होता है जब खाते में पर्याप्त पैसा न हो, या हस्ताक्षर/जानकारी मेल न खाए। बैंक शुल्क लेता है, और अगर भुगतान के लिए दिया आपका चेक कम बैलेंस से बाउंस हो, तो यह परक्राम्य लिखत अधिनियम की धारा 138 के तहत अपराध है — पाने वाला कानूनी नोटिस भेजकर केस कर सकता है। चेक देने से पहले खाते में पर्याप्त बैलेंस रखें।",
  "கணக்கில் போதுமான பணம் இல்லாதபோது அல்லது கையெழுத்து/விவரங்கள் பொருந்தாதபோது காசோலை திரும்பும். வங்கி கட்டணம் வசூலிக்கும்; பணம் செலுத்த நீங்கள் கொடுத்த காசோலை குறைந்த இருப்பால் திரும்பினால், அது செலாவணி முறிச் சட்டம் பிரிவு 138-இன் கீழ் குற்றம் — பெறுநர் சட்ட நோட்டீஸ் அனுப்பி வழக்குத் தொடரலாம். காசோலை கொடுக்கும் முன் போதுமான இருப்பு வைத்திருங்கள்.",
  related=("cheque", "bank_complaint", "check_balance"))

# ─── Savings & investment ─────────────────────────────────────────────────────

T("fd", "savings",
  ("Fixed Deposit (FD)", "फिक्स्ड डिपॉज़िट (FD)", "நிலை வைப்பு (FD)"),
  ["fixed deposit", "fd", "term deposit", "एफडी", "फिक्स्ड", "सावधि जमा", "நிலை வைப்பு", "எஃப்டி", "பிக்ஸட்"],
  ["deposit", "जमा", "வைப்பு"],
  "A Fixed Deposit (FD) keeps a lump sum in the bank for a fixed time — from 7 days to 10 years — at a fixed interest rate, currently about 6% to 7.5% a year. Senior citizens usually get about 0.5% extra. Breaking it early is allowed with a small penalty, and FDs are insured up to ₹5 lakh per bank by DICGC.",
  "फिक्स्ड डिपॉज़िट (FD) में एक बार में पैसा तय समय — 7 दिन से 10 साल — के लिए तय ब्याज पर बैंक में रखा जाता है, अभी लगभग 6% से 7.5% सालाना। वरिष्ठ नागरिकों को आमतौर पर 0.5% ज़्यादा मिलता है। समय से पहले तोड़ने पर थोड़ा जुर्माना लगता है, और FD हर बैंक में ₹5 लाख तक DICGC से बीमित होती है।",
  "நிலை வைப்பு (FD) என்பது ஒரு தொகையை குறிப்பிட்ட காலத்துக்கு — 7 நாட்கள் முதல் 10 ஆண்டுகள் வரை — நிலையான வட்டியில் வங்கியில் வைப்பது; தற்போது ஆண்டுக்கு சுமார் 6% முதல் 7.5%. மூத்த குடிமக்களுக்கு பொதுவாக 0.5% கூடுதல். முன்கூட்டியே முறிக்கலாம், சிறிய அபராதம் உண்டு; ஒவ்வொரு வங்கியிலும் ₹5 லட்சம் வரை DICGC காப்பீடு உண்டு.",
  related=("rd", "tds_15g", "scss"),
  links={"cost": "fd", "how": "fd"},
  offer=("calc_fd", ("Shall I calculate how much your FD will become?", "क्या मैं हिसाब लगाऊं कि आपकी FD कितनी हो जाएगी?", "உங்கள் FD எவ்வளவு ஆகும் என்று கணக்கிடட்டுமா?")))

T("rd", "savings",
  ("Recurring Deposit (RD)", "रेकरिंग डिपॉज़िट (RD)", "தொடர் வைப்பு (RD)"),
  ["recurring deposit", "rd", "monthly saving", "every month save", "har mahine", "आरडी", "रेकरिंग", "हर महीने", "ஆர்டி", "தொடர் வைப்பு", "மாதந்தோறும்"],
  [],
  "A Recurring Deposit (RD) lets you save a fixed small amount every month — even ₹100 — for 6 months to 10 years, and earn interest similar to an FD. It builds the saving habit. You can open it at a bank or post office, and set it to auto-debit from your savings account so you never miss an instalment.",
  "रेकरिंग डिपॉज़िट (RD) में आप हर महीने एक तय छोटी राशि — ₹100 भी — 6 महीने से 10 साल तक जमा करते हैं और FD जैसा ब्याज पाते हैं। इससे बचत की आदत बनती है। इसे बैंक या डाकघर में खोल सकते हैं, और बचत खाते से अपने आप कटने (ऑटो-डेबिट) की सुविधा लें ताकि कोई किस्त न छूटे।",
  "தொடர் வைப்பு (RD) மூலம் ஒவ்வொரு மாதமும் ஒரு சிறிய நிலையான தொகையை — ₹100 கூட — 6 மாதங்கள் முதல் 10 ஆண்டுகள் வரை சேமித்து FD போன்ற வட்டி பெறலாம். இது சேமிப்புப் பழக்கத்தை வளர்க்கும். வங்கி அல்லது அஞ்சலகத்தில் திறக்கலாம்; தவணை தவறாமல் இருக்க சேமிப்புக் கணக்கிலிருந்து தானாகக் கழிக்கும் வசதியை அமைக்கவும்.",
  related=("fd", "post_office", "budgeting"))

T("ppf", "savings",
  ("Public Provident Fund (PPF)", "पब्लिक प्रोविडेंट फंड (PPF)", "பொது வருங்கால வைப்பு நிதி (PPF)"),
  ["ppf", "public provident", "provident fund", "पीपीएफ", "भविष्य निधि", "பிபிஎஃப்", "வருங்கால வைப்பு"],
  [],
  "PPF is a government-backed 15-year savings scheme available at post offices and banks. You can deposit ₹500 to ₹1.5 lakh a year; the interest (currently 7.1% a year, set by the government every quarter) and the final amount are tax-free. Partial withdrawal is allowed from the 7th year, and loans against it from the 3rd year.",
  "PPF सरकार द्वारा समर्थित 15 साल की बचत योजना है, जो डाकघर और बैंकों में मिलती है। साल में ₹500 से ₹1.5 लाख तक जमा कर सकते हैं; ब्याज (अभी 7.1% सालाना, सरकार हर तिमाही तय करती है) और पूरी रकम टैक्स-फ्री है। 7वें साल से आंशिक निकासी और तीसरे साल से इस पर लोन मिल सकता है।",
  "PPF என்பது அஞ்சலகங்கள் மற்றும் வங்கிகளில் கிடைக்கும் அரசு ஆதரவு 15 ஆண்டு சேமிப்புத் திட்டம். ஆண்டுக்கு ₹500 முதல் ₹1.5 லட்சம் வரை செலுத்தலாம்; வட்டியும் (தற்போது ஆண்டுக்கு 7.1%, அரசு ஒவ்வொரு காலாண்டும் நிர்ணயிக்கும்) இறுதித் தொகையும் வரி இல்லாதவை. 7வது ஆண்டிலிருந்து பகுதியாகப் பணம் எடுக்கலாம், 3வது ஆண்டிலிருந்து கடன் பெறலாம்.",
  related=("sukanya", "post_office", "nps"))

T("sukanya", "savings",
  ("Sukanya Samriddhi (for daughters)", "सुकन्या समृद्धि (बेटियों के लिए)", "சுகன்யா சம்ரித்தி (மகள்களுக்கு)"),
  ["sukanya", "ssy", "daughter", "girl child", "beti", "betiyon", "सुकन्या", "बेटी", "बिटिया", "सुकन्या समृद्धि", "சுகன்யா", "மகள்", "பெண் குழந்தை"],
  [],
  "Sukanya Samriddhi Yojana is a savings account for a girl child below 10 years, opened by a parent at a post office or bank. Deposit ₹250 to ₹1.5 lakh a year for 15 years; it currently earns 8.2% a year, tax-free. Half the money can be withdrawn after she turns 18 for her education, and the account matures 21 years after opening.",
  "सुकन्या समृद्धि योजना 10 साल से छोटी बेटी के लिए बचत खाता है, जिसे माता-पिता डाकघर या बैंक में खोलते हैं। 15 साल तक साल में ₹250 से ₹1.5 लाख जमा करें; अभी 8.2% सालाना टैक्स-फ्री ब्याज मिलता है। बेटी के 18 साल की होने पर पढ़ाई के लिए आधा पैसा निकाल सकते हैं, और खाता खुलने के 21 साल बाद पूरा होता है।",
  "சுகன்யா சம்ரித்தி யோஜனா 10 வயதுக்குட்பட்ட பெண் குழந்தைக்கான சேமிப்புக் கணக்கு; பெற்றோர் அஞ்சலகம் அல்லது வங்கியில் திறக்கலாம். 15 ஆண்டுகள் ஆண்டுக்கு ₹250 முதல் ₹1.5 லட்சம் வரை செலுத்தலாம்; தற்போது ஆண்டுக்கு 8.2% வரியில்லா வட்டி. அவளுக்கு 18 வயதான பிறகு கல்விக்காக பாதி பணம் எடுக்கலாம்; திறந்து 21 ஆண்டுகளில் முதிர்ச்சி அடையும்.",
  related=("ppf", "post_office", "education_loan"),
  links={"docs": "sukanya", "how": "sukanya"})

T("post_office", "savings",
  ("Post office savings schemes", "डाकघर बचत योजनाएं", "அஞ்சலக சேமிப்புத் திட்டங்கள்"),
  ["post office", "dak ghar", "dakghar", "nsc", "kvp", "kisan vikas patra", "mis", "monthly income scheme", "डाकघर", "पोस्ट ऑफिस", "किसान विकास पत्र",
   "அஞ்சலக", "தபால் நிலைய", "போஸ்ட் ஆபீஸ்"],
  [],
  "Post office schemes are backed by the Government of India, so your money is fully safe. Popular ones: Savings Account, Recurring Deposit, Time Deposit (1–5 years), Monthly Income Scheme for regular monthly interest, National Savings Certificate (NSC), Kisan Vikas Patra (money doubles in about 9.5 years), PPF, Sukanya Samriddhi and the Senior Citizens Savings Scheme. Rates are revised every quarter.",
  "डाकघर की योजनाओं के पीछे भारत सरकार है, इसलिए पैसा पूरी तरह सुरक्षित है। लोकप्रिय योजनाएं: बचत खाता, RD, टाइम डिपॉज़िट (1–5 साल), हर महीने ब्याज के लिए मासिक आय योजना, राष्ट्रीय बचत पत्र (NSC), किसान विकास पत्र (लगभग 9.5 साल में पैसा दोगुना), PPF, सुकन्या समृद्धि और वरिष्ठ नागरिक बचत योजना। दरें हर तिमाही बदलती हैं।",
  "அஞ்சலகத் திட்டங்களுக்கு இந்திய அரசின் உத்தரவாதம் உள்ளதால் உங்கள் பணம் முழுமையாகப் பாதுகாப்பானது. பிரபலமானவை: சேமிப்புக் கணக்கு, RD, கால வைப்பு (1–5 ஆண்டுகள்), மாத வட்டிக்கு மாத வருமானத் திட்டம், தேசிய சேமிப்புப் பத்திரம் (NSC), கிசான் விகாஸ் பத்ரா (சுமார் 9.5 ஆண்டுகளில் பணம் இரட்டிப்பு), PPF, சுகன்யா சம்ரித்தி மற்றும் மூத்த குடிமக்கள் சேமிப்புத் திட்டம். வட்டி விகிதம் ஒவ்வொரு காலாண்டும் மாறும்.",
  related=("ppf", "scss", "rd"))

T("scss", "savings",
  ("Senior Citizens Savings Scheme", "वरिष्ठ नागरिक बचत योजना", "மூத்த குடிமக்கள் சேமிப்புத் திட்டம்"),
  ["scss", "senior citizen saving", "senior citizens savings", "retirement money", "वरिष्ठ नागरिक बचत", "रिटायरमेंट", "மூத்த குடிமக்கள் சேமிப்பு", "ஓய்வுக்குப் பிறகு"],
  ["senior citizen", "retired", "वरिष्ठ", "மூத்த குடிமக"],
  "The Senior Citizens Savings Scheme (SCSS) is for people aged 60 and above (55 for some retirees). You can invest up to ₹30 lakh for 5 years at a bank or post office, and interest (currently 8.2% a year) is paid every quarter into your account — good for a regular income after retirement. It can be extended by 3 years.",
  "वरिष्ठ नागरिक बचत योजना (SCSS) 60 साल या उससे ज़्यादा उम्र के लोगों के लिए है (कुछ सेवानिवृत्त लोगों के लिए 55)। बैंक या डाकघर में 5 साल के लिए ₹30 लाख तक लगा सकते हैं, और ब्याज (अभी 8.2% सालाना) हर तिमाही खाते में आता है — रिटायरमेंट के बाद नियमित आय के लिए अच्छा। इसे 3 साल और बढ़ा सकते हैं।",
  "மூத்த குடிமக்கள் சேமிப்புத் திட்டம் (SCSS) 60 வயது மற்றும் அதற்கு மேற்பட்டவர்களுக்கானது (சில ஓய்வுபெற்றவர்களுக்கு 55). வங்கி அல்லது அஞ்சலகத்தில் 5 ஆண்டுகளுக்கு ₹30 லட்சம் வரை முதலீடு செய்யலாம்; வட்டி (தற்போது ஆண்டுக்கு 8.2%) ஒவ்வொரு காலாண்டும் கணக்கில் வரும் — ஓய்வுக்குப் பின் நிலையான வருமானத்துக்கு நல்லது. மேலும் 3 ஆண்டுகள் நீட்டிக்கலாம்.",
  related=("old_age_pension", "fd", "tds_15g"))

T("budgeting", "savings",
  ("How to save and budget", "बचत और बजट कैसे करें", "சேமிப்பு மற்றும் பட்ஜெட்"),
  ["budget", "how to save", "save money", "saving tips", "bachat kaise", "paisa bachana", "kharcha", "expenses", "बचत कैसे", "पैसे बचा", "खर्च", "बजट",
   "சேமிப்பது எப்படி", "பணத்தை சேமிக்க", "செலவு", "பட்ஜெட்"],
  ["save", "saving", "बचत", "சேமி"],
  "A simple plan: when money comes in, first put a fixed part aside as savings (even 10%), then spend on needs like food, rent, school and medicine, and only then on wants. Write down where the money goes for one month. Build an emergency fund equal to 3–6 months of expenses in a bank account, and avoid borrowing for festivals or celebrations.",
  "आसान तरीका: पैसा आते ही पहले एक तय हिस्सा (कम से कम 10%) बचत में अलग रखें, फिर खाना, किराया, स्कूल, दवा जैसी ज़रूरतों पर खर्च करें, और उसके बाद ही शौक पर। एक महीने तक लिखें कि पैसा कहाँ जाता है। 3–6 महीने के खर्च जितना आपातकालीन फंड बैंक खाते में रखें, और त्योहार या समारोह के लिए उधार लेने से बचें।",
  "எளிய திட்டம்: பணம் வந்தவுடன் முதலில் ஒரு நிலையான பகுதியை (குறைந்தது 10%) சேமிப்புக்காக ஒதுக்குங்கள், பிறகு உணவு, வாடகை, பள்ளி, மருந்து போன்ற தேவைகளுக்கு, அதன் பிறகே விருப்பங்களுக்குச் செலவிடுங்கள். ஒரு மாதம் பணம் எங்கே போகிறது என்று எழுதுங்கள். 3–6 மாத செலவுக்குச் சமமான அவசர நிதியை வங்கிக் கணக்கில் வையுங்கள்; விழாக்களுக்குக் கடன் வாங்குவதைத் தவிருங்கள்.",
  related=("rd", "savings_account", "high_return_scam"))

T("mutual_funds", "savings",
  ("Mutual funds and SIP", "म्यूचुअल फंड और SIP", "மியூச்சுவல் ஃபண்ட் மற்றும் SIP"),
  ["mutual fund", "mutual funds", "sip", "share market", "stock market", "shares", "equity", "म्यूचुअल फंड", "शेयर बाजार", "शेयर", "எஸ்ஐபி", "மியூச்சுவல்", "பங்குச் சந்தை"],
  ["invest", "investment", "निवेश", "முதலீடு"],
  "A mutual fund pools money from many people and invests it in shares or bonds; a SIP lets you invest a fixed amount every month, even ₹500. Returns are NOT guaranteed — the value can go down as well as up, so money you need soon or your emergency fund should stay in a bank or post office. Invest only through SEBI-registered platforms, and never through someone who promises fixed high returns.",
  "म्यूचुअल फंड कई लोगों का पैसा मिलाकर शेयर या बॉन्ड में लगाता है; SIP से आप हर महीने तय राशि, ₹500 भी, लगा सकते हैं। मुनाफा पक्का नहीं होता — कीमत घट भी सकती है, इसलिए जल्दी ज़रूरत वाला पैसा और आपातकालीन फंड बैंक या डाकघर में ही रखें। सिर्फ SEBI-पंजीकृत प्लेटफॉर्म से निवेश करें, और पक्के ऊंचे मुनाफे का वादा करने वाले से कभी नहीं।",
  "மியூச்சுவல் ஃபண்ட் பலரின் பணத்தைச் சேர்த்து பங்குகள் அல்லது பத்திரங்களில் முதலீடு செய்கிறது; SIP மூலம் ஒவ்வொரு மாதமும் ₹500 போன்ற நிலையான தொகையை முதலீடு செய்யலாம். லாபம் உத்தரவாதம் இல்லை — மதிப்பு குறையவும் செய்யலாம்; எனவே விரைவில் தேவைப்படும் பணமும் அவசர நிதியும் வங்கி அல்லது அஞ்சலகத்திலேயே இருக்கட்டும். SEBI-பதிவு செய்த தளங்கள் மூலம் மட்டும் முதலீடு செய்யுங்கள்; நிலையான அதிக லாபம் வாக்களிப்பவரிடம் ஒருபோதும் வேண்டாம்.",
  related=("high_return_scam", "ppf", "nps"))

# ─── Loans & credit ───────────────────────────────────────────────────────────

T("loan_basics", "loans",
  ("How to get a bank loan", "बैंक से लोन कैसे लें", "வங்கியில் கடன் பெறுவது எப்படி"),
  ["loan", "loans", "karz", "karza", "rin", "udhar", "borrow", "लोन", "कर्ज", "ऋण", "उधार", "கடன்", "லோன்"],
  [],
  "Banks give loans for farming, business, education, housing, gold and personal needs. Compare the interest rate, processing fee and total repayment at two or three banks, and read the loan agreement before signing. You usually need KYC documents, income proof and bank statements. Bank and government-scheme loans are much cheaper and safer than moneylenders or unknown loan apps.",
  "बैंक खेती, व्यापार, पढ़ाई, घर, सोने और निजी ज़रूरतों के लिए लोन देते हैं। दो-तीन बैंकों में ब्याज दर, प्रोसेसिंग फीस और कुल चुकाई जाने वाली राशि की तुलना करें, और हस्ताक्षर से पहले लोन एग्रीमेंट पढ़ें। आमतौर पर KYC दस्तावेज़, आय का प्रमाण और बैंक स्टेटमेंट चाहिए। साहूकार या अनजान लोन ऐप से बैंक और सरकारी योजना के लोन बहुत सस्ते और सुरक्षित हैं।",
  "விவசாயம், தொழில், கல்வி, வீடு, தங்கம் மற்றும் தனிப்பட்ட தேவைகளுக்கு வங்கிகள் கடன் தருகின்றன. இரண்டு மூன்று வங்கிகளில் வட்டி விகிதம், செயலாக்கக் கட்டணம், மொத்தத் திருப்பிச் செலுத்தும் தொகையை ஒப்பிட்டு, கையெழுத்திடும் முன் கடன் ஒப்பந்தத்தைப் படியுங்கள். பொதுவாக KYC ஆவணங்கள், வருமானச் சான்று, வங்கி அறிக்கை தேவை. கந்துவட்டிக்காரர்கள் அல்லது தெரியாத கடன் செயலிகளை விட வங்கி மற்றும் அரசுத் திட்டக் கடன்கள் மிகவும் மலிவானவை, பாதுகாப்பானவை.",
  related=("emi", "credit_score", "mudra"),
  links={"how": "loan_basics"},
  offer=("calc_emi", ("Would you like me to calculate the monthly EMI for a loan?", "क्या मैं किसी लोन की मासिक EMI का हिसाब लगाऊं?", "ஒரு கடனுக்கான மாதத் தவணையை (EMI) கணக்கிடட்டுமா?")))

T("emi", "loans",
  ("What is EMI?", "EMI क्या है?", "EMI என்றால் என்ன?"),
  ["emi", "kist", "kisht", "installment", "instalment", "equated monthly", "किस्त", "ईएमआई", "தவணை", "இஎம்ஐ"],
  [],
  "EMI (Equated Monthly Instalment) is the fixed amount you pay every month to repay a loan; it includes part of the loan and the interest. A longer loan period means a smaller EMI but more total interest. Keep all EMIs below about 40% of your monthly income, and pay on time — late payments add penalties and hurt your credit score.",
  "EMI (मासिक किस्त) वह तय राशि है जो लोन चुकाने के लिए हर महीने देनी होती है; इसमें लोन का हिस्सा और ब्याज दोनों होते हैं। लंबी अवधि में EMI छोटी होती है पर कुल ब्याज ज़्यादा लगता है। सारी EMI मिलाकर मासिक आय के लगभग 40% से कम रखें, और समय पर भरें — देर से भरने पर जुर्माना लगता है और क्रेडिट स्कोर खराब होता है।",
  "EMI (சம மாதத் தவணை) என்பது கடனைத் திருப்பிச் செலுத்த ஒவ்வொரு மாதமும் கட்டும் நிலையான தொகை; இதில் கடனின் ஒரு பகுதியும் வட்டியும் அடங்கும். நீண்ட காலம் என்றால் EMI குறையும், ஆனால் மொத்த வட்டி அதிகமாகும். எல்லா EMI-களும் சேர்த்து மாத வருமானத்தின் சுமார் 40%-க்குள் இருக்கட்டும்; தாமதமானால் அபராதம் வரும், கிரெடிட் ஸ்கோர் பாதிக்கும்.",
  related=("loan_basics", "credit_score", "loan_trouble"),
  offer=("calc_emi", ("Shall I calculate your EMI? Just tell me the loan amount.", "क्या मैं आपकी EMI का हिसाब लगाऊं? बस लोन की राशि बताइए।", "உங்கள் EMI-ஐ கணக்கிடட்டுமா? கடன் தொகையைச் சொல்லுங்கள்.")))

T("gold_loan", "loans",
  ("Gold loan", "गोल्ड लोन", "தங்கக் கடன் (நகைக் கடன்)"),
  ["gold loan", "gold", "jewellery loan", "sona", "gehne", "सोना", "गोल्ड", "गहने", "தங்க", "நகைக் கடன்", "நகை"],
  ["loan", "लोन", "कर्ज", "கடன்"],
  "A gold loan is a quick loan given against your gold jewellery, usually within a day. Banks lend about 75% to 85% of the gold's value (a higher share for small loans), at rates usually lower than personal loans. Take it only from a bank or an RBI-registered company, get a receipt describing your gold and its weight, and repay on time — otherwise the lender can auction the gold after giving notice.",
  "गोल्ड लोन आपके सोने के गहनों के बदले मिलने वाला जल्दी का लोन है, आमतौर पर एक दिन में। बैंक सोने की कीमत का लगभग 75% से 85% तक देते हैं (छोटे लोन पर ज़्यादा हिस्सा), और ब्याज आमतौर पर पर्सनल लोन से कम होता है। सिर्फ बैंक या RBI-पंजीकृत कंपनी से लें, गहनों और वज़न के विवरण वाली रसीद लें, और समय पर चुकाएं — वरना नोटिस देकर सोना नीलाम हो सकता है।",
  "தங்கக் கடன் என்பது உங்கள் தங்க நகைகளை அடமானமாக வைத்துப் பெறும் விரைவுக் கடன், பொதுவாக ஒரே நாளில். வங்கிகள் தங்க மதிப்பில் சுமார் 75% முதல் 85% வரை தருகின்றன (சிறிய கடன்களுக்கு அதிக பங்கு); வட்டி பொதுவாக தனிநபர் கடனை விடக் குறைவு. வங்கி அல்லது RBI-பதிவு நிறுவனத்திடம் மட்டும் வாங்குங்கள், நகை விவரமும் எடையும் உள்ள ரசீது பெறுங்கள், சரியான நேரத்தில் திருப்பிச் செலுத்துங்கள் — இல்லையெனில் நோட்டீஸ் கொடுத்து நகை ஏலம் விடப்படலாம்.",
  related=("loan_basics", "emi", "kcc"))

T("mudra", "loans",
  ("MUDRA business loan", "मुद्रा बिज़नेस लोन", "முத்ரா தொழில் கடன்"),
  ["mudra", "business loan", "shop loan", "dukan", "vyapar loan", "self employed loan", "मुद्रा", "व्यापार लोन", "दुकान", "முத்ரா", "தொழில் கடன்", "கடை"],
  ["business", "व्यापार", "தொழில்"],
  "Under PM MUDRA Yojana, banks give loans without any security for small businesses like shops, tailoring, repair work or food stalls: Shishu up to ₹50,000, Kishore up to ₹5 lakh, Tarun up to ₹10 lakh, and Tarun Plus up to ₹20 lakh for those who repaid a Tarun loan. Apply at any bank with your business plan, KYC and quotations, or online on the JanSamarth portal.",
  "पीएम मुद्रा योजना में बैंक दुकान, सिलाई, मरम्मत या खाने के ठेले जैसे छोटे कारोबार के लिए बिना गारंटी लोन देते हैं: शिशु ₹50,000 तक, किशोर ₹5 लाख तक, तरुण ₹10 लाख तक, और तरुण लोन चुका चुके लोगों के लिए तरुण प्लस ₹20 लाख तक। व्यापार योजना, KYC और कोटेशन लेकर किसी भी बैंक में या JanSamarth पोर्टल पर ऑनलाइन आवेदन करें।",
  "பிஎம் முத்ரா யோஜனாவில் கடை, தையல், பழுதுபார்ப்பு, உணவுக் கடை போன்ற சிறு தொழில்களுக்கு வங்கிகள் பிணையின்றி கடன் தருகின்றன: ஷிஷு ₹50,000 வரை, கிஷோர் ₹5 லட்சம் வரை, தருண் ₹10 லட்சம் வரை, தருண் கடனைத் திருப்பிச் செலுத்தியவர்களுக்கு தருண் பிளஸ் ₹20 லட்சம் வரை. தொழில் திட்டம், KYC, விலைப்புள்ளிகளுடன் எந்த வங்கியிலும் அல்லது JanSamarth இணையதளத்தில் விண்ணப்பிக்கலாம்.",
  related=("loan_basics", "shg_loan", "schemes_general"))

T("kcc", "loans",
  ("Kisan Credit Card (KCC)", "किसान क्रेडिट कार्ड (KCC)", "கிசான் கிரெடிட் கார்டு (KCC)"),
  ["kisan credit", "kcc", "crop loan", "farm loan", "kheti loan", "किसान क्रेडिट", "फसल लोन", "खेती लोन", "கிசான் கிரெடிட்", "பயிர்க் கடன்", "விவசாயக் கடன்"],
  [],
  "The Kisan Credit Card gives farmers short-term loans for seeds, fertiliser and farm costs at about 7% interest; if you repay on time you get 3% back, so the effective rate is about 4% on up to ₹3 lakh (the limit is being raised to ₹5 lakh). Loans up to ₹2 lakh need no land mortgage or guarantor. Apply at your bank with land records, Aadhaar and a photo.",
  "किसान क्रेडिट कार्ड से किसानों को बीज, खाद और खेती के खर्च के लिए लगभग 7% ब्याज पर छोटी अवधि का लोन मिलता है; समय पर चुकाने पर 3% वापस मिलता है, यानी ₹3 लाख तक असल ब्याज लगभग 4% (यह सीमा ₹5 लाख की जा रही है)। ₹2 लाख तक के लोन के लिए ज़मीन गिरवी या गारंटर नहीं चाहिए। ज़मीन के कागज़, आधार और फोटो लेकर बैंक में आवेदन करें।",
  "கிசான் கிரெடிட் கார்டு மூலம் விவசாயிகளுக்கு விதை, உரம், விவசாயச் செலவுகளுக்கு சுமார் 7% வட்டியில் குறுகியகாலக் கடன் கிடைக்கும்; சரியான நேரத்தில் திருப்பிச் செலுத்தினால் 3% திரும்பக் கிடைக்கும், எனவே ₹3 லட்சம் வரை உண்மையான வட்டி சுமார் 4% (இந்த வரம்பு ₹5 லட்சமாக உயர்த்தப்படுகிறது). ₹2 லட்சம் வரையிலான கடனுக்கு நில அடமானமோ ஜாமீன்தாரரோ தேவையில்லை. நிலப் பதிவு, ஆதார், புகைப்படத்துடன் வங்கியில் விண்ணப்பிக்கவும்.",
  related=("crop_insurance", "pm_kisan", "gold_loan"))

T("education_loan", "loans",
  ("Education loan", "एजुकेशन लोन", "கல்விக் கடன்"),
  ["education loan", "study loan", "student loan", "padhai loan", "college fees", "vidyalaxmi", "vidya lakshmi", "शिक्षा ऋण", "पढ़ाई के लिए लोन", "एजुकेशन लोन",
   "கல்விக் கடன்", "படிப்புக் கடன்"],
  ["loan", "लोन", "कर्ज", "கடன்"],
  "Banks give education loans for college and professional courses in India and abroad. Loans up to ₹7.5 lakh are usually given without any property as security, repayment starts after the course plus a grace period, and students from families earning up to ₹4.5 lakh a year can get an interest subsidy during the study period. Apply to many banks at once on the PM-Vidyalaxmi portal.",
  "बैंक भारत और विदेश में कॉलेज व प्रोफेशनल कोर्स के लिए एजुकेशन लोन देते हैं। ₹7.5 लाख तक के लोन आमतौर पर बिना संपत्ति गिरवी रखे मिलते हैं, चुकाना कोर्स खत्म होने और कुछ समय बाद शुरू होता है, और ₹4.5 लाख तक सालाना आय वाले परिवारों के छात्रों को पढ़ाई के दौरान ब्याज सब्सिडी मिल सकती है। PM-Vidyalaxmi पोर्टल पर एक साथ कई बैंकों में आवेदन करें।",
  "இந்தியா மற்றும் வெளிநாட்டில் கல்லூரி, தொழில்முறைப் படிப்புகளுக்கு வங்கிகள் கல்விக் கடன் தருகின்றன. ₹7.5 லட்சம் வரையிலான கடன்கள் பொதுவாக சொத்து அடமானம் இல்லாமல் கிடைக்கும்; படிப்பு முடிந்து சிறிது காலத்துக்குப் பிறகே திருப்பிச் செலுத்தத் தொடங்க வேண்டும்; ஆண்டு வருமானம் ₹4.5 லட்சம் வரை உள்ள குடும்ப மாணவர்களுக்குப் படிப்புக் காலத்தில் வட்டி மானியம் கிடைக்கலாம். PM-Vidyalaxmi இணையதளத்தில் ஒரே நேரத்தில் பல வங்கிகளுக்கு விண்ணப்பிக்கலாம்.",
  related=("sukanya", "loan_basics", "schemes_general"))

T("home_loan", "loans",
  ("Home loan and housing schemes", "होम लोन और आवास योजना", "வீட்டுக் கடன் மற்றும் வீட்டுவசதித் திட்டம்"),
  ["home loan", "housing loan", "house loan", "ghar", "makaan", "awas", "pmay", "होम लोन", "घर", "मकान", "आवास", "வீட்டுக் கடன்", "வீடு"],
  ["loan", "लोन", "कर्ज", "கடன்"],
  "Banks and housing finance companies give home loans for buying, building or repairing a house, usually for up to 20–30 years. Under Pradhan Mantri Awas Yojana, poor families in villages can get money to build a pucca house, and eligible urban families get help or an interest subsidy. Check eligibility on the Schemes page of this app, and compare interest rates before choosing a lender.",
  "बैंक और हाउसिंग फाइनेंस कंपनियां घर खरीदने, बनाने या मरम्मत के लिए आमतौर पर 20–30 साल तक का होम लोन देती हैं। प्रधानमंत्री आवास योजना में गांव के गरीब परिवारों को पक्का घर बनाने के लिए पैसा, और पात्र शहरी परिवारों को मदद या ब्याज सब्सिडी मिलती है। इस ऐप के योजनाएं पेज पर पात्रता देखें, और लोन लेने से पहले ब्याज दरों की तुलना करें।",
  "வீடு வாங்க, கட்ட அல்லது பழுதுபார்க்க வங்கிகளும் வீட்டு நிதி நிறுவனங்களும் பொதுவாக 20–30 ஆண்டுகள் வரை வீட்டுக் கடன் தருகின்றன. பிரதமர் ஆவாஸ் யோஜனாவில் கிராமப்புற ஏழைக் குடும்பங்களுக்கு கான்கிரீட் வீடு கட்ட நிதியும், தகுதியான நகரக் குடும்பங்களுக்கு உதவி அல்லது வட்டி மானியமும் கிடைக்கும். இந்தச் செயலியின் திட்டங்கள் பக்கத்தில் தகுதியைப் பாருங்கள்; கடன் வாங்கும் முன் வட்டி விகிதங்களை ஒப்பிடுங்கள்.",
  related=("emi", "schemes_general", "credit_score"))

T("shg_loan", "loans",
  ("Self-Help Group (SHG) loans", "स्वयं सहायता समूह (SHG) लोन", "சுய உதவிக் குழு (SHG) கடன்"),
  ["shg", "self help group", "self-help group", "mahila samuh", "samuh", "microfinance", "lakhpati didi", "स्वयं सहायता", "समूह", "माइक्रोफाइनेंस",
   "சுய உதவிக் குழு", "மகளிர் குழு", "மைக்ரோ ஃபைனான்ஸ்"],
  [],
  "Women can form a Self-Help Group of 10–20 members, save a small amount regularly, and then get collateral-free bank loans through the government's DAY-NRLM programme, often with interest subvention. Groups that repay well get bigger loans for livelihoods like dairy, tailoring or shops. Contact your village Gram Panchayat, block office or the nearest bank branch to join or form a group.",
  "महिलाएं 10–20 सदस्यों का स्वयं सहायता समूह बनाकर नियमित थोड़ी बचत करती हैं, और फिर सरकार के DAY-NRLM कार्यक्रम से बिना गारंटी बैंक लोन पाती हैं, अक्सर ब्याज छूट के साथ। अच्छी तरह चुकाने वाले समूहों को डेयरी, सिलाई या दुकान जैसे काम के लिए बड़े लोन मिलते हैं। समूह से जुड़ने या बनाने के लिए ग्राम पंचायत, ब्लॉक कार्यालय या नज़दीकी बैंक शाखा से संपर्क करें।",
  "பெண்கள் 10–20 உறுப்பினர்கள் கொண்ட சுய உதவிக் குழுவை அமைத்து தொடர்ந்து சிறிது சேமித்து, பின்னர் அரசின் DAY-NRLM திட்டம் மூலம் பிணையில்லா வங்கிக் கடன் பெறலாம், பெரும்பாலும் வட்டிச் சலுகையுடன். நன்றாகத் திருப்பிச் செலுத்தும் குழுக்களுக்கு பால்பண்ணை, தையல், கடை போன்ற வாழ்வாதாரத்துக்குப் பெரிய கடன்கள் கிடைக்கும். குழுவில் சேர அல்லது அமைக்க கிராம ஊராட்சி, வட்டார அலுவலகம் அல்லது அருகிலுள்ள வங்கிக் கிளையைத் தொடர்புகொள்ளுங்கள்.",
  related=("mudra", "loan_basics", "schemes_general"))

T("credit_score", "loans",
  ("Credit score (CIBIL)", "क्रेडिट स्कोर (CIBIL)", "கிரெடிட் ஸ்கோர் (CIBIL)"),
  ["credit score", "cibil", "credit report", "credit history", "score", "क्रेडिट स्कोर", "सिबिल", "கிரெடிட் ஸ்கோர்", "சிபில்"],
  [],
  "A credit score (like CIBIL) is a number from 300 to 900 that shows how well you repay loans and credit cards; 750 or more is considered good and helps you get loans faster and cheaper. Pay every EMI and card bill on time, do not use your full credit limit, and avoid applying for many loans at once. You can get one free credit report every year from each credit bureau.",
  "क्रेडिट स्कोर (जैसे CIBIL) 300 से 900 के बीच का अंक है जो बताता है कि आप लोन और क्रेडिट कार्ड कितनी अच्छी तरह चुकाते हैं; 750 या उससे ज़्यादा अच्छा माना जाता है और इससे लोन जल्दी और सस्ता मिलता है। हर EMI और कार्ड बिल समय पर भरें, पूरी क्रेडिट सीमा इस्तेमाल न करें, और एक साथ कई लोन के लिए आवेदन न करें। हर क्रेडिट ब्यूरो से साल में एक बार मुफ्त क्रेडिट रिपोर्ट मिलती है।",
  "கிரெடிட் ஸ்கோர் (CIBIL போன்றது) 300 முதல் 900 வரையிலான எண்; நீங்கள் கடன்களையும் கிரெடிட் கார்டையும் எவ்வளவு சரியாகத் திருப்பிச் செலுத்துகிறீர்கள் என்பதைக் காட்டும். 750 அல்லது அதற்கு மேல் நல்லது; இதனால் கடன் விரைவாகவும் குறைந்த வட்டியிலும் கிடைக்கும். ஒவ்வொரு EMI-யையும் கார்டு பில்லையும் சரியான நேரத்தில் கட்டுங்கள், முழு வரம்பையும் பயன்படுத்தாதீர்கள், ஒரே நேரத்தில் பல கடன்களுக்கு விண்ணப்பிக்காதீர்கள். ஒவ்வொரு கிரெடிட் பீரோவிடமிருந்தும் ஆண்டுக்கு ஒருமுறை இலவச அறிக்கை பெறலாம்.",
  related=("emi", "loan_basics", "loan_trouble"))

T("loan_trouble", "loans",
  ("Cannot repay a loan", "लोन नहीं चुका पा रहे", "கடனைத் திருப்பிச் செலுத்த முடியவில்லை"),
  ["cannot repay", "can't repay", "unable to pay", "not able to pay emi", "default", "overdue", "emi bounce", "nahi chuka", "loan nahi", "चुका नहीं",
   "किस्त नहीं", "डिफ़ॉल्ट", "திருப்பிச் செலுத்த முடியவில்லை", "தவணை கட்ட முடியவில்லை"],
  ["loan", "emi", "लोन", "கடன்"],
  "If you cannot pay your EMI, talk to your bank before the due date — do not hide. Banks can offer more time, a lower EMI over a longer period (restructuring), or a one-time settlement, especially after illness, crop loss or job loss. Get any new arrangement in writing. Do not take a new high-interest loan from a moneylender or app to repay the old one.",
  "अगर EMI नहीं भर पा रहे, तो तारीख से पहले बैंक से बात करें — छिपें नहीं। बैंक खासकर बीमारी, फसल खराब होने या नौकरी जाने पर ज़्यादा समय, लंबी अवधि में कम EMI (रीस्ट्रक्चरिंग) या एकमुश्त समझौता दे सकते हैं। कोई भी नई व्यवस्था लिखित में लें। पुराना लोन चुकाने के लिए साहूकार या ऐप से नया महंगा लोन न लें।",
  "EMI கட்ட முடியவில்லை என்றால் கடைசி தேதிக்கு முன்பே வங்கியிடம் பேசுங்கள் — மறைக்காதீர்கள். குறிப்பாக நோய், பயிர் இழப்பு அல்லது வேலை இழப்புக்குப் பிறகு வங்கிகள் கூடுதல் அவகாசம், நீண்ட காலத்தில் குறைந்த EMI (மறுசீரமைப்பு) அல்லது ஒருமுறைத் தீர்வு வழங்கலாம். எந்தப் புதிய ஏற்பாட்டையும் எழுத்துப்பூர்வமாகப் பெறுங்கள். பழைய கடனை அடைக்க கந்துவட்டிக்காரர் அல்லது செயலியிடம் புதிய அதிக வட்டிக் கடன் வாங்காதீர்கள்.",
  related=("recovery_harassment", "credit_score", "bank_complaint"))

T("recovery_harassment", "loans",
  ("Harassment by recovery agents", "रिकवरी एजेंट द्वारा परेशान करना", "வசூல் முகவர்களின் துன்புறுத்தல்"),
  ["recovery agent", "recovery agents", "harass", "harassment", "threat", "threatening", "abusive calls", "dhamki", "वसूली", "रिकवरी", "धमकी", "परेशान",
   "வசூல் முகவர்", "மிரட்ட", "துன்புறுத்த"],
  ["loan", "लोन", "कर्ज", "கடன்"],
  "Recovery agents must follow RBI rules: they can call only between 8 am and 7 pm, must carry an ID and the bank's authorisation letter, and cannot threaten, abuse, shame you in public or contact your friends and relatives. Complain to the bank in writing; if it does not act within 30 days, complain to the RBI Ombudsman at cms.rbi.org.in or 14448, and to the police for threats.",
  "रिकवरी एजेंट को RBI के नियम मानने होते हैं: वे सिर्फ सुबह 8 से शाम 7 बजे तक कॉल कर सकते हैं, उनके पास पहचान पत्र और बैंक का अधिकार पत्र होना चाहिए, और वे धमकी, गाली, सबके सामने बेइज़्ज़ती या आपके दोस्तों-रिश्तेदारों से संपर्क नहीं कर सकते। बैंक को लिखित शिकायत दें; 30 दिन में कार्रवाई न हो तो cms.rbi.org.in या 14448 पर RBI लोकपाल से, और धमकी पर पुलिस से शिकायत करें।",
  "வசூல் முகவர்கள் RBI விதிகளைப் பின்பற்ற வேண்டும்: காலை 8 முதல் மாலை 7 மணி வரை மட்டுமே அழைக்கலாம், அடையாள அட்டையும் வங்கியின் அங்கீகாரக் கடிதமும் வைத்திருக்க வேண்டும்; மிரட்டவோ, திட்டவோ, பொது இடத்தில் அவமானப்படுத்தவோ, உங்கள் நண்பர்கள் உறவினர்களைத் தொடர்புகொள்ளவோ கூடாது. வங்கிக்கு எழுத்துப்பூர்வமாகப் புகார் செய்யுங்கள்; 30 நாட்களில் நடவடிக்கை இல்லையெனில் cms.rbi.org.in அல்லது 14448-இல் RBI குறைதீர்ப்பாளரிடமும், மிரட்டலுக்குக் காவல்துறையிடமும் புகார் செய்யுங்கள்.",
  related=("bank_complaint", "loan_trouble", "loan_apps"))

T("loan_apps", "safety",
  ("Instant loan apps", "इंस्टेंट लोन ऐप", "உடனடி கடன் செயலிகள்"),
  ["loan app", "loan apps", "instant loan", "online loan", "quick loan", "lending app", "लोन ऐप", "इंस्टेंट लोन", "ऑनलाइन लोन", "கடன் செயலி", "உடனடி கடன்", "ஆன்லைன் கடன்"],
  ["loan", "लोन", "कर्ज", "கடன்"],
  "Many instant loan apps are illegal: they charge huge hidden fees, take access to your contacts and photos, and then harass and blackmail people. Borrow only from a bank or an RBI-registered NBFC — the app must name its lender, and you can check it on the RBI website. Never give an app access to contacts or gallery. If you are being harassed, call 1930 and report at cybercrime.gov.in.",
  "कई इंस्टेंट लोन ऐप गैरकानूनी हैं: वे भारी छिपी फीस लेते हैं, आपके कॉन्टैक्ट और फोटो का एक्सेस ले लेते हैं, फिर परेशान और ब्लैकमेल करते हैं। सिर्फ बैंक या RBI-पंजीकृत NBFC से उधार लें — ऐप को अपने लोन देने वाले का नाम बताना होता है, जिसे RBI वेबसाइट पर जांच सकते हैं। किसी ऐप को कॉन्टैक्ट या गैलरी का एक्सेस न दें। परेशान किया जा रहा हो तो 1930 पर कॉल करें और cybercrime.gov.in पर शिकायत करें।",
  "பல உடனடி கடன் செயலிகள் சட்டவிரோதமானவை: பெரும் மறைமுகக் கட்டணம் வசூலித்து, உங்கள் தொடர்புகள், புகைப்படங்களை அணுகி, பின்னர் துன்புறுத்தி மிரட்டுகின்றன. வங்கி அல்லது RBI-பதிவு NBFC-யிடம் மட்டும் கடன் வாங்குங்கள் — செயலி தனது கடன் வழங்குநரின் பெயரைக் காட்ட வேண்டும், அதை RBI இணையதளத்தில் சரிபார்க்கலாம். எந்தச் செயலிக்கும் தொடர்புகள் அல்லது கேலரி அணுகல் தராதீர்கள். துன்புறுத்தப்பட்டால் 1930-க்கு அழைத்து cybercrime.gov.in-இல் புகார் செய்யுங்கள்.",
  related=("report_fraud", "recovery_harassment", "loan_basics"))

# ─── Insurance ────────────────────────────────────────────────────────────────

T("insurance_basics", "insurance",
  ("Which insurance do I need?", "मुझे कौन सा बीमा चाहिए?", "எனக்கு எந்தக் காப்பீடு தேவை?"),
  ["insurance", "bima", "beema", "policy", "बीमा", "पॉलिसी", "காப்பீடு", "இன்சூரன்ஸ்", "பாலிசி"],
  [],
  "Insurance protects your family from big money shocks. Every earning adult should have: life cover (PMJJBY gives ₹2 lakh for ₹436 a year), accident cover (PMSBY gives ₹2 lakh for just ₹20 a year), and health cover (Ayushman Bharat gives ₹5 lakh a year free to eligible families). Farmers should also insure crops under PMFBY. Buy from your bank, post office or a registered insurer — not from callers.",
  "बीमा आपके परिवार को बड़े आर्थिक झटकों से बचाता है। हर कमाने वाले के पास होना चाहिए: जीवन बीमा (PMJJBY में ₹436 सालाना में ₹2 लाख), दुर्घटना बीमा (PMSBY में सिर्फ ₹20 सालाना में ₹2 लाख), और स्वास्थ्य बीमा (आयुष्मान भारत में पात्र परिवारों को ₹5 लाख सालाना मुफ्त)। किसान फसल का बीमा PMFBY में कराएं। बीमा बैंक, डाकघर या पंजीकृत कंपनी से लें — फोन करने वालों से नहीं।",
  "காப்பீடு பெரிய பணச் சிக்கல்களிலிருந்து உங்கள் குடும்பத்தைக் காக்கும். சம்பாதிக்கும் ஒவ்வொருவருக்கும் தேவை: ஆயுள் காப்பீடு (PMJJBY-யில் ஆண்டுக்கு ₹436-க்கு ₹2 லட்சம்), விபத்துக் காப்பீடு (PMSBY-யில் ஆண்டுக்கு வெறும் ₹20-க்கு ₹2 லட்சம்), மருத்துவக் காப்பீடு (ஆயுஷ்மான் பாரத் தகுதியான குடும்பங்களுக்கு ஆண்டுக்கு ₹5 லட்சம் இலவசம்). விவசாயிகள் PMFBY-யில் பயிர்க் காப்பீடும் செய்யுங்கள். வங்கி, அஞ்சலகம் அல்லது பதிவு பெற்ற நிறுவனத்திடம் வாங்குங்கள் — போனில் அழைப்பவர்களிடம் அல்ல.",
  related=("pmjjby", "pmsby", "health_insurance"),
  links={"claim": "insurance_claim"})

T("pmjjby", "insurance",
  ("PMJJBY life insurance (₹436/year)", "PMJJBY जीवन बीमा (₹436/साल)", "PMJJBY ஆயுள் காப்பீடு (₹436/ஆண்டு)"),
  ["pmjjby", "jeevan jyoti", "life insurance", "life cover", "जीवन ज्योति", "जीवन बीमा", "ஜீவன் ஜோதி", "ஆயுள் காப்பீடு"],
  ["insurance", "bima", "बीमा", "காப்பீடு"],
  "Pradhan Mantri Jeevan Jyoti Bima Yojana gives ₹2 lakh to your nominee if you die for any reason. The premium is just ₹436 a year, auto-debited from your bank account. Anyone aged 18 to 50 with a bank account can join (cover continues up to 55). Enrol at your bank branch, net banking or app, or through a Bank Mitra.",
  "प्रधानमंत्री जीवन ज्योति बीमा योजना में किसी भी कारण से मृत्यु होने पर नॉमिनी को ₹2 लाख मिलते हैं। प्रीमियम सिर्फ ₹436 सालाना है, जो बैंक खाते से अपने आप कटता है। 18 से 50 साल का कोई भी बैंक खाताधारक जुड़ सकता है (कवर 55 साल तक चलता है)। बैंक शाखा, नेट बैंकिंग, ऐप या बैंक मित्र से जुड़ें।",
  "பிரதமர் ஜீவன் ஜோதி பீமா யோஜனாவில் எந்தக் காரணத்தால் இறந்தாலும் உங்கள் நாமினிக்கு ₹2 லட்சம் கிடைக்கும். பிரீமியம் ஆண்டுக்கு வெறும் ₹436, வங்கிக் கணக்கிலிருந்து தானாகக் கழிக்கப்படும். வங்கிக் கணக்குள்ள 18 முதல் 50 வயது வரையிலான எவரும் சேரலாம் (காப்பீடு 55 வயது வரை தொடரும்). வங்கிக் கிளை, நெட் பேங்கிங், செயலி அல்லது வங்கி மித்ரா மூலம் சேருங்கள்.",
  related=("pmsby", "insurance_claim", "nominee"),
  links={"claim": "insurance_claim"})

T("pmsby", "insurance",
  ("PMSBY accident insurance (₹20/year)", "PMSBY दुर्घटना बीमा (₹20/साल)", "PMSBY விபத்துக் காப்பீடு (₹20/ஆண்டு)"),
  ["pmsby", "suraksha bima", "accident insurance", "accident cover", "accident", "सुरक्षा बीमा", "दुर्घटना", "விபத்து", "சுரக்ஷா பீமா"],
  ["insurance", "bima", "बीमा", "காப்பீடு"],
  "Pradhan Mantri Suraksha Bima Yojana gives ₹2 lakh for accidental death or total permanent disability, and ₹1 lakh for partial permanent disability. The premium is only ₹20 a year, auto-debited from your bank account. Anyone aged 18 to 70 with a bank account can join at their bank, through net banking or a Bank Mitra.",
  "प्रधानमंत्री सुरक्षा बीमा योजना में दुर्घटना से मृत्यु या पूरी स्थायी विकलांगता पर ₹2 लाख, और आंशिक स्थायी विकलांगता पर ₹1 लाख मिलते हैं। प्रीमियम सिर्फ ₹20 सालाना है, जो बैंक खाते से अपने आप कटता है। 18 से 70 साल का कोई भी बैंक खाताधारक बैंक, नेट बैंकिंग या बैंक मित्र से जुड़ सकता है।",
  "பிரதமர் சுரக்ஷா பீமா யோஜனாவில் விபத்தில் இறப்பு அல்லது முழு நிரந்தர ஊனத்துக்கு ₹2 லட்சமும், பகுதி நிரந்தர ஊனத்துக்கு ₹1 லட்சமும் கிடைக்கும். பிரீமியம் ஆண்டுக்கு வெறும் ₹20, வங்கிக் கணக்கிலிருந்து தானாகக் கழிக்கப்படும். வங்கிக் கணக்குள்ள 18 முதல் 70 வயது வரையிலான எவரும் வங்கி, நெட் பேங்கிங் அல்லது வங்கி மித்ரா மூலம் சேரலாம்.",
  related=("pmjjby", "insurance_claim", "health_insurance"),
  links={"claim": "insurance_claim"})

T("health_insurance", "insurance",
  ("Health insurance / Ayushman card", "स्वास्थ्य बीमा / आयुष्मान कार्ड", "மருத்துவக் காப்பீடு / ஆயுஷ்மான் அட்டை"),
  ["health insurance", "ayushman", "pmjay", "pm-jay", "hospital", "medical", "treatment", "mediclaim", "आयुष्मान", "अस्पताल", "इलाज", "स्वास्थ्य बीमा",
   "ஆயுஷ்மான்", "மருத்துவமனை", "சிகிச்சை", "மருத்துவக் காப்பீடு"],
  ["insurance", "bima", "बीमा", "காப்பீடு"],
  "Ayushman Bharat PM-JAY gives eligible poor families free hospital treatment of up to ₹5 lakh per family every year at government and listed private hospitals, with no premium. Every person aged 70 or above can get the Ayushman Vay Vandana card, whatever their income. Check your eligibility and get the card at a Common Service Centre, a listed hospital, the Ayushman app, or by calling 14555.",
  "आयुष्मान भारत PM-JAY में पात्र गरीब परिवारों को सरकारी और सूचीबद्ध निजी अस्पतालों में हर साल प्रति परिवार ₹5 लाख तक मुफ्त इलाज मिलता है, बिना प्रीमियम। 70 साल या उससे ज़्यादा उम्र का हर व्यक्ति, आय कुछ भी हो, आयुष्मान वय वंदना कार्ड पा सकता है। पात्रता जांचने और कार्ड बनवाने के लिए जन सेवा केंद्र, सूचीबद्ध अस्पताल, आयुष्मान ऐप या 14555 पर कॉल करें।",
  "ஆயுஷ்மான் பாரத் PM-JAY மூலம் தகுதியான ஏழைக் குடும்பங்களுக்கு அரசு மற்றும் பட்டியலிடப்பட்ட தனியார் மருத்துவமனைகளில் ஆண்டுக்கு குடும்பத்துக்கு ₹5 லட்சம் வரை இலவச சிகிச்சை கிடைக்கும், பிரீமியம் இல்லை. 70 வயது அல்லது அதற்கு மேற்பட்ட ஒவ்வொருவரும் வருமானம் எதுவாக இருந்தாலும் ஆயுஷ்மான் வய வந்தனா அட்டை பெறலாம். தகுதியைச் சரிபார்த்து அட்டை பெற பொது சேவை மையம், பட்டியலிடப்பட்ட மருத்துவமனை, ஆயுஷ்மான் செயலி அல்லது 14555-ஐ அழையுங்கள்.",
  related=("insurance_basics", "pmsby", "schemes_general"))

T("crop_insurance", "insurance",
  ("Crop insurance (PMFBY)", "फसल बीमा (PMFBY)", "பயிர்க் காப்பீடு (PMFBY)"),
  ["crop insurance", "pmfby", "fasal bima", "crop loss", "crop damage", "फसल बीमा", "फसल खराब", "फसल नुकसान", "பயிர்க் காப்பீடு", "பயிர் சேதம்", "பயிர் இழப்பு"],
  ["insurance", "bima", "बीमा", "காப்பீடு"],
  "Under Pradhan Mantri Fasal Bima Yojana, farmers pay only 2% of the sum insured for Kharif crops, 1.5% for Rabi crops and 5% for commercial or horticulture crops; the government pays the rest. If your crop is damaged by hail, flood, landslide or similar local events, inform the insurance company, your bank or the agriculture office within 72 hours, or call the Krishi Rakshak helpline 14447.",
  "प्रधानमंत्री फसल बीमा योजना में किसान खरीफ फसल के लिए बीमा राशि का सिर्फ 2%, रबी के लिए 1.5% और व्यावसायिक या बागवानी फसल के लिए 5% प्रीमियम देते हैं; बाकी सरकार देती है। ओले, बाढ़, भूस्खलन जैसी स्थानीय आपदा से फसल खराब होने पर 72 घंटे के अंदर बीमा कंपनी, बैंक या कृषि कार्यालय को बताएं, या कृषि रक्षक हेल्पलाइन 14447 पर कॉल करें।",
  "பிரதமர் பசல் பீமா யோஜனாவில் விவசாயிகள் காரீப் பயிர்களுக்குக் காப்பீட்டுத் தொகையில் 2%, ரபி பயிர்களுக்கு 1.5%, வணிக/தோட்டப் பயிர்களுக்கு 5% மட்டுமே பிரீமியம் செலுத்துகின்றனர்; மீதியை அரசு செலுத்தும். ஆலங்கட்டி, வெள்ளம், நிலச்சரிவு போன்ற உள்ளூர் பேரிடரால் பயிர் சேதமானால் 72 மணி நேரத்துக்குள் காப்பீட்டு நிறுவனம், வங்கி அல்லது வேளாண் அலுவலகத்துக்குத் தெரிவியுங்கள், அல்லது கிருஷி ரக்ஷக் உதவி எண் 14447-ஐ அழையுங்கள்.",
  related=("kcc", "pm_kisan", "insurance_claim"))

T("insurance_claim", "insurance",
  ("How to claim insurance", "बीमा का दावा कैसे करें", "காப்பீட்டுத் தொகையைக் கோருவது எப்படி"),
  ["claim", "insurance claim", "claim form", "dava", "daava", "दावा", "क्लेम", "கோரிக்கை", "க்ளெய்ம்"],
  ["insurance", "bima", "बीमा", "காப்பீடு"],
  "For PMJJBY or PMSBY, the nominee should go to the bank branch where the insured person had the account, collect the claim form, and submit it with the death certificate (and for accidents, the FIR or police report and hospital records), the nominee's ID and a cancelled cheque or passbook copy. Submit within 30 days if possible; the bank forwards it to the insurer, which must settle eligible claims within about 30 days.",
  "PMJJBY या PMSBY के लिए नॉमिनी उस बैंक शाखा में जाएं जहाँ बीमित व्यक्ति का खाता था, दावा फॉर्म लें, और मृत्यु प्रमाण पत्र (दुर्घटना में FIR या पुलिस रिपोर्ट और अस्पताल के कागज़), नॉमिनी का पहचान पत्र और रद्द चेक या पासबुक की कॉपी के साथ जमा करें। हो सके तो 30 दिन के अंदर जमा करें; बैंक इसे बीमा कंपनी को भेजता है, जिसे सही दावे लगभग 30 दिन में निपटाने होते हैं।",
  "PMJJBY அல்லது PMSBY-க்கு, காப்பீடு செய்தவருக்குக் கணக்கு இருந்த வங்கிக் கிளைக்கு நாமினி சென்று கோரிக்கைப் படிவம் பெற்று, இறப்புச் சான்றிதழ் (விபத்து என்றால் FIR அல்லது காவல் அறிக்கை, மருத்துவமனை ஆவணங்கள்), நாமினியின் அடையாளச் சான்று, ரத்து செய்த காசோலை அல்லது பாஸ்புக் நகலுடன் சமர்ப்பிக்க வேண்டும். முடிந்தால் 30 நாட்களுக்குள் சமர்ப்பியுங்கள்; வங்கி அதைக் காப்பீட்டு நிறுவனத்துக்கு அனுப்பும், தகுதியான கோரிக்கைகளை சுமார் 30 நாட்களில் தீர்க்க வேண்டும்.",
  related=("nominee", "pmjjby", "bank_complaint"))

# ─── Pension ──────────────────────────────────────────────────────────────────

T("apy", "pension",
  ("Atal Pension Yojana", "अटल पेंशन योजना", "அடல் ஓய்வூதியத் திட்டம்"),
  ["atal pension", "apy", "अटल पेंशन", "அடல் ஓய்வூதிய", "அடல் பென்ஷன்"],
  [],
  "Atal Pension Yojana gives a guaranteed pension of ₹1,000 to ₹5,000 a month from age 60. Anyone aged 18 to 40 with a savings account who does not pay income tax can join; the earlier you join, the smaller the monthly contribution (for example, about ₹42 a month at age 18 for a ₹1,000 pension). After the subscriber, the spouse gets the pension, and then the nominee gets the saved amount.",
  "अटल पेंशन योजना में 60 साल की उम्र से हर महीने ₹1,000 से ₹5,000 तक पक्की पेंशन मिलती है। 18 से 40 साल का बचत खाताधारक, जो आयकर नहीं भरता, जुड़ सकता है; जितनी जल्दी जुड़ें, मासिक अंशदान उतना कम (जैसे 18 साल पर ₹1,000 पेंशन के लिए लगभग ₹42 महीना)। सदस्य के बाद पति/पत्नी को पेंशन, और फिर नॉमिनी को जमा राशि मिलती है।",
  "அடல் ஓய்வூதியத் திட்டத்தில் 60 வயதிலிருந்து மாதம் ₹1,000 முதல் ₹5,000 வரை உத்தரவாத ஓய்வூதியம் கிடைக்கும். வருமான வரி செலுத்தாத, சேமிப்புக் கணக்குள்ள 18 முதல் 40 வயது வரையிலான எவரும் சேரலாம்; எவ்வளவு சீக்கிரம் சேருகிறீர்களோ, மாதப் பங்களிப்பு அவ்வளவு குறைவு (உதாரணமாக 18 வயதில் ₹1,000 ஓய்வூதியத்துக்கு மாதம் சுமார் ₹42). உறுப்பினருக்குப் பிறகு வாழ்க்கைத் துணைக்கு ஓய்வூதியமும், பின்னர் நாமினிக்குச் சேமிப்புத் தொகையும் கிடைக்கும்.",
  related=("nps", "old_age_pension", "pmjjby"))

T("pension_options", "pension",
  ("Pension options", "पेंशन के विकल्प", "ஓய்வூதிய வாய்ப்புகள்"),
  ["pension", "pensions", "retirement", "budhape ka sahara", "पेंशन", "रिटायरमेंट", "ஓய்வூதிய", "பென்ஷன்", "ஓய்வுக்கால"],
  [],
  "There are pensions for different people: Atal Pension Yojana (join at 18–40, get ₹1,000–5,000 a month from 60), PM Shram Yogi Maan-dhan for unorganised workers (₹3,000 a month from 60), the National Pension System for anyone aged 18–70, and a free monthly old-age, widow or disability pension for poor families. Senior citizens can also get regular interest from the Senior Citizens Savings Scheme.",
  "अलग-अलग लोगों के लिए पेंशन हैं: अटल पेंशन योजना (18–40 साल में जुड़ें, 60 से ₹1,000–5,000 महीना), असंगठित मज़दूरों के लिए पीएम श्रम योगी मानधन (60 से ₹3,000 महीना), 18–70 साल के किसी के लिए राष्ट्रीय पेंशन प्रणाली, और गरीब परिवारों के लिए मुफ्त मासिक वृद्धावस्था, विधवा या विकलांग पेंशन। वरिष्ठ नागरिक वरिष्ठ नागरिक बचत योजना से नियमित ब्याज भी पा सकते हैं।",
  "வெவ்வேறு மக்களுக்கு ஓய்வூதியங்கள் உள்ளன: அடல் ஓய்வூதியத் திட்டம் (18–40 வயதில் சேர்ந்து, 60 முதல் மாதம் ₹1,000–5,000), அமைப்புசாராத் தொழிலாளர்களுக்கு பிஎம் ஷ்ரம் யோகி மான்-தன் (60 முதல் மாதம் ₹3,000), 18–70 வயதுடைய எவருக்கும் தேசிய ஓய்வூதிய அமைப்பு, ஏழைக் குடும்பங்களுக்கு இலவச மாத முதியோர், விதவை அல்லது மாற்றுத்திறனாளி ஓய்வூதியம். மூத்த குடிமக்கள் மூத்த குடிமக்கள் சேமிப்புத் திட்டம் மூலம் தொடர் வட்டியும் பெறலாம்.",
  related=("apy", "old_age_pension", "nps"),
  links={"eligibility": "old_age_pension"})

T("nps", "pension",
  ("National Pension System (NPS)", "राष्ट्रीय पेंशन प्रणाली (NPS)", "தேசிய ஓய்வூதிய அமைப்பு (NPS)"),
  ["nps", "national pension", "राष्ट्रीय पेंशन", "एनपीएस", "தேசிய ஓய்வூதிய"],
  [],
  "The National Pension System (NPS) is a government-regulated retirement savings scheme for citizens aged 18 to 70. You save regularly (minimum ₹1,000 a year) and the money is invested; at retirement, part can be taken as a lump sum and the rest buys a monthly pension. Returns depend on the market and are not fixed. Open it at a bank, post office or online on the NPS website.",
  "राष्ट्रीय पेंशन प्रणाली (NPS) 18 से 70 साल के नागरिकों के लिए सरकार द्वारा नियंत्रित रिटायरमेंट बचत योजना है। आप नियमित बचत करते हैं (कम से कम ₹1,000 सालाना) और पैसा निवेश होता है; रिटायरमेंट पर कुछ हिस्सा एकमुश्त मिलता है और बाकी से मासिक पेंशन मिलती है। मुनाफा बाज़ार पर निर्भर है, तय नहीं। बैंक, डाकघर या NPS वेबसाइट पर खोलें।",
  "தேசிய ஓய்வூதிய அமைப்பு (NPS) 18 முதல் 70 வயது குடிமக்களுக்கான அரசு ஒழுங்குபடுத்திய ஓய்வுக்கால சேமிப்புத் திட்டம். நீங்கள் தொடர்ந்து சேமிக்கிறீர்கள் (ஆண்டுக்குக் குறைந்தது ₹1,000), பணம் முதலீடு செய்யப்படுகிறது; ஓய்வின்போது ஒரு பகுதி மொத்தமாகவும், மீதி மாத ஓய்வூதியமாகவும் கிடைக்கும். லாபம் சந்தையைப் பொறுத்தது, நிலையானது அல்ல. வங்கி, அஞ்சலகம் அல்லது NPS இணையதளத்தில் திறக்கலாம்.",
  related=("apy", "ppf", "scss"))

T("old_age_pension", "pension",
  ("Old age / widow pension", "वृद्धावस्था / विधवा पेंशन", "முதியோர் / விதவை ஓய்வூதியம்"),
  ["old age pension", "widow pension", "vridha pension", "budhapa pension", "disability pension", "nsap", "वृद्धावस्था पेंशन", "बुढ़ापा पेंशन", "विधवा पेंशन",
   "विकलांग पेंशन", "முதியோர் ஓய்வூதிய", "விதவை ஓய்வூதிய", "மாற்றுத்திறனாளி ஓய்வூதிய"],
  [],
  "Under the National Social Assistance Programme, poor (BPL) elderly people aged 60+, widows aged 40+ and people with severe disabilities get a monthly pension into their bank account; many states add their own top-up, so the total differs by state. Apply at your Gram Panchayat, block office, municipal office or a Common Service Centre with Aadhaar, an age proof, a BPL card and bank details.",
  "राष्ट्रीय सामाजिक सहायता कार्यक्रम में गरीब (BPL) 60+ बुजुर्गों, 40+ विधवाओं और गंभीर विकलांगता वाले लोगों को हर महीने बैंक खाते में पेंशन मिलती है; कई राज्य अपनी ओर से राशि बढ़ाते हैं, इसलिए कुल राशि राज्य के अनुसार अलग है। आधार, उम्र का प्रमाण, BPL कार्ड और बैंक विवरण लेकर ग्राम पंचायत, ब्लॉक कार्यालय, नगर कार्यालय या जन सेवा केंद्र पर आवेदन करें।",
  "தேசிய சமூக உதவித் திட்டத்தின் கீழ் வறுமைக்கோட்டுக்குக் கீழுள்ள (BPL) 60+ வயது முதியோர், 40+ வயது விதவைகள், கடுமையான மாற்றுத்திறனாளிகளுக்கு மாத ஓய்வூதியம் வங்கிக் கணக்கில் வரும்; பல மாநிலங்கள் கூடுதல் தொகை சேர்ப்பதால் மொத்தத் தொகை மாநிலத்துக்கு மாநிலம் வேறுபடும். ஆதார், வயதுச் சான்று, BPL அட்டை, வங்கி விவரங்களுடன் கிராம ஊராட்சி, வட்டார அலுவலகம், நகராட்சி அலுவலகம் அல்லது பொது சேவை மையத்தில் விண்ணப்பிக்கவும்.",
  related=("life_certificate", "scss", "health_insurance"))

T("life_certificate", "pension",
  ("Life certificate for pensioners", "पेंशनभोगियों का जीवन प्रमाण पत्र", "ஓய்வூதியதாரர்களுக்கான உயிர்வாழ் சான்றிதழ்"),
  ["life certificate", "jeevan pramaan", "jeevan praman", "jivan praman", "जीवन प्रमाण", "लाइफ सर्टिफिकेट", "உயிர்வாழ் சான்று", "ஜீவன் பிரமாண்", "வாழ்நாள் சான்று"],
  [],
  "Pensioners must submit a life certificate every November so their pension continues; those aged 80 and above can submit from 1 October. You can do it at your bank branch, through the doorstep banking service, at a Common Service Centre, or yourself at home with the Jeevan Pramaan face authentication app using your Aadhaar.",
  "पेंशन जारी रखने के लिए पेंशनभोगियों को हर नवंबर में जीवन प्रमाण पत्र देना होता है; 80 साल या उससे ज़्यादा उम्र वाले 1 अक्टूबर से दे सकते हैं। यह बैंक शाखा में, डोरस्टेप बैंकिंग सेवा से, जन सेवा केंद्र पर, या घर बैठे आधार से जीवन प्रमाण फेस ऑथेंटिकेशन ऐप द्वारा खुद कर सकते हैं।",
  "ஓய்வூதியம் தொடர ஓய்வூதியதாரர்கள் ஒவ்வொரு நவம்பரிலும் உயிர்வாழ் சான்றிதழ் சமர்ப்பிக்க வேண்டும்; 80 வயது மற்றும் அதற்கு மேற்பட்டவர்கள் அக்டோபர் 1 முதல் சமர்ப்பிக்கலாம். வங்கிக் கிளை, வீட்டு வாசல் வங்கிச் சேவை, பொது சேவை மையம், அல்லது வீட்டிலிருந்தே ஆதாருடன் ஜீவன் பிரமாண் முக அங்கீகாரச் செயலி மூலம் நீங்களே செய்யலாம்.",
  related=("old_age_pension", "aadhaar", "scss"))

# ─── Government benefits ──────────────────────────────────────────────────────

T("schemes_general", "schemes",
  ("Government schemes for me", "मेरे लिए सरकारी योजनाएं", "எனக்கான அரசுத் திட்டங்கள்"),
  ["scheme", "schemes", "yojana", "yojna", "sarkari", "government benefit", "subsidy", "welfare", "योजना", "योजनाएं", "सरकारी", "सब्सिडी", "திட்டம்", "திட்டங்கள்", "அரசு உதவி", "மானியம்"],
  ["benefit", "government", "लाभ", "சலுகை"],
  "The government has schemes for farmers, women, girls, students, senior citizens, workers, small businesses and poor families — covering cash support, pensions, loans, insurance, housing, health and food. Tell me who you are (for example 'I am a farmer' or 'I am 65 years old') and I will suggest schemes, or open the Schemes page to search and filter them in your language.",
  "सरकार की योजनाएं किसानों, महिलाओं, बेटियों, छात्रों, बुजुर्गों, मज़दूरों, छोटे व्यापारियों और गरीब परिवारों के लिए हैं — नकद मदद, पेंशन, लोन, बीमा, घर, इलाज और राशन के लिए। मुझे अपने बारे में बताइए (जैसे 'मैं किसान हूँ' या 'मेरी उम्र 65 साल है') और मैं योजनाएं सुझाऊंगा, या योजनाएं पेज पर अपनी भाषा में खोजें।",
  "விவசாயிகள், பெண்கள், பெண் குழந்தைகள், மாணவர்கள், மூத்த குடிமக்கள், தொழிலாளர்கள், சிறு தொழில் செய்வோர், ஏழைக் குடும்பங்களுக்கு அரசுத் திட்டங்கள் உள்ளன — பண உதவி, ஓய்வூதியம், கடன், காப்பீடு, வீடு, மருத்துவம், உணவு. உங்களைப் பற்றிச் சொல்லுங்கள் (உதாரணமாக 'நான் விவசாயி' அல்லது 'எனக்கு 65 வயது') நான் திட்டங்களைப் பரிந்துரைக்கிறேன், அல்லது திட்டங்கள் பக்கத்தில் உங்கள் மொழியில் தேடுங்கள்.",
  related=("pm_kisan", "dbt_seeding", "health_insurance"))

T("dbt_seeding", "schemes",
  ("Getting government money in your account (DBT)", "सरकारी पैसा खाते में (DBT)", "அரசுப் பணம் கணக்கில் (DBT)"),
  ["dbt", "direct benefit", "aadhaar seeding", "aadhaar link", "link aadhaar", "npci mapper", "money not received", "paisa nahi aaya", "पैसा नहीं आया", "आधार लिंक",
   "आधार सीडिंग", "பணம் வரவில்லை", "ஆதார் இணை", "நேரடி பயன்"],
  [],
  "Government benefits (DBT) are sent to the bank account that is linked ('seeded') with your Aadhaar in the NPCI mapper. If money has not come, check your Aadhaar–bank seeding status on the myAadhaar website or ask your bank; if needed, fill the Aadhaar seeding consent form at your branch. Also make sure your eKYC is done for schemes like PM-Kisan.",
  "सरकारी लाभ (DBT) उस बैंक खाते में भेजा जाता है जो NPCI मैपर में आपके आधार से जुड़ा (सीड) है। अगर पैसा नहीं आया, तो myAadhaar वेबसाइट पर आधार-बैंक सीडिंग की स्थिति देखें या बैंक से पूछें; ज़रूरत हो तो शाखा में आधार सीडिंग सहमति फॉर्म भरें। PM-किसान जैसी योजनाओं के लिए eKYC भी पूरा करें।",
  "அரசு உதவி (DBT) NPCI மேப்பரில் உங்கள் ஆதாருடன் இணைக்கப்பட்ட வங்கிக் கணக்குக்கே அனுப்பப்படும். பணம் வரவில்லை என்றால் myAadhaar இணையதளத்தில் ஆதார்–வங்கி இணைப்பு நிலையைப் பாருங்கள் அல்லது வங்கியிடம் கேளுங்கள்; தேவையெனில் கிளையில் ஆதார் இணைப்பு ஒப்புதல் படிவத்தை நிரப்புங்கள். PM-கிசான் போன்ற திட்டங்களுக்கு eKYC-யும் முடியுங்கள்.",
  related=("aadhaar", "pm_kisan", "jan_dhan"))

T("pm_kisan", "schemes",
  ("PM-Kisan ₹6,000 a year", "पीएम-किसान ₹6,000 सालाना", "பிஎம்-கிசான் ஆண்டுக்கு ₹6,000"),
  ["pm kisan", "pm-kisan", "pmkisan", "kisan samman", "kisan nidhi", "6000", "किसान सम्मान", "पीएम किसान", "किसान निधि", "கிசான் சம்மான்", "பிஎம் கிசான்"],
  [],
  "PM-Kisan gives land-holding farmer families ₹6,000 a year in three instalments of ₹2,000, directly into the Aadhaar-linked bank account. eKYC is compulsory — do it with OTP on pmkisan.gov.in, at a Common Service Centre, or by face authentication on the PM-Kisan app. Check your status and instalments on pmkisan.gov.in, or call 155261.",
  "पीएम-किसान में ज़मीन वाले किसान परिवारों को साल में ₹6,000 तीन किस्तों (₹2,000 हर एक) में सीधे आधार से जुड़े बैंक खाते में मिलते हैं। eKYC ज़रूरी है — pmkisan.gov.in पर OTP से, जन सेवा केंद्र पर, या पीएम-किसान ऐप में चेहरे से करें। अपनी स्थिति और किस्तें pmkisan.gov.in पर देखें या 155261 पर कॉल करें।",
  "பிஎம்-கிசான் திட்டத்தில் நிலம் வைத்திருக்கும் விவசாயக் குடும்பங்களுக்கு ஆண்டுக்கு ₹6,000 மூன்று தவணைகளாக (ஒவ்வொன்றும் ₹2,000) ஆதார் இணைந்த வங்கிக் கணக்கில் நேரடியாக வழங்கப்படுகிறது. eKYC கட்டாயம் — pmkisan.gov.in-இல் OTP மூலம், பொது சேவை மையத்தில், அல்லது பிஎம்-கிசான் செயலியில் முக அங்கீகாரம் மூலம் செய்யுங்கள். உங்கள் நிலையையும் தவணைகளையும் pmkisan.gov.in-இல் பாருங்கள் அல்லது 155261-ஐ அழையுங்கள்.",
  related=("kcc", "crop_insurance", "dbt_seeding"))

# ─── Safety ───────────────────────────────────────────────────────────────────

T("otp_safety", "safety",
  ("Never share OTP or PIN", "OTP या पिन कभी न बताएं", "OTP அல்லது PIN-ஐ ஒருபோதும் பகிராதீர்கள்"),
  ["otp", "one time password", "share otp", "pin share", "cvv", "password", "ओटीपी", "पासवर्ड", "ஓடிபி", "கடவுச்சொல்"],
  [],
  "Never share your OTP, PIN, CVV or passwords with anyone. No bank, RBI, police, government officer or customer care ever asks for them. If someone asks for your OTP, it is a fraud — hang up, do not click links they send, and call your bank's official helpline. If money is already gone, call 1930 immediately.",
  "अपना OTP, पिन, CVV या पासवर्ड कभी किसी को न बताएं। कोई बैंक, RBI, पुलिस, सरकारी अधिकारी या कस्टमर केयर इन्हें कभी नहीं मांगता। अगर कोई OTP मांगे, तो यह धोखा है — फोन काटें, उनके भेजे लिंक न खोलें, और बैंक की आधिकारिक हेल्पलाइन पर कॉल करें। पैसा कट चुका हो तो तुरंत 1930 पर कॉल करें।",
  "உங்கள் OTP, PIN, CVV அல்லது கடவுச்சொற்களை யாரிடமும் பகிராதீர்கள். எந்த வங்கியோ, RBI-யோ, காவல்துறையோ, அரசு அதிகாரியோ, வாடிக்கையாளர் சேவையோ இவற்றைக் கேட்பதில்லை. யாராவது OTP கேட்டால் அது மோசடி — அழைப்பைத் துண்டியுங்கள், அவர்கள் அனுப்பும் இணைப்புகளைத் திறக்காதீர்கள், வங்கியின் அதிகாரப்பூர்வ உதவி எண்ணை அழையுங்கள். பணம் ஏற்கனவே போயிருந்தால் உடனே 1930-ஐ அழையுங்கள்.",
  related=("report_fraud", "kyc_scam", "fraud_check_help"))

T("report_fraud", "safety",
  ("Report a fraud / lost money", "धोखाधड़ी की शिकायत करें", "மோசடியைப் புகார் செய்தல்"),
  ["report fraud", "fraud", "cheated", "scammed", "money stolen", "cyber crime", "cybercrime", "1930", "dhokha", "thagi", "धोखा", "धोखाधड़ी", "ठगी",
   "साइबर", "மோசடி", "ஏமாற்ற", "சைபர்"],
  ["scam", "complaint", "शिकायत"],
  "If you lost money to a fraud, act within minutes: call 1930 (National Cyber Crime Helpline) or report at cybercrime.gov.in, and call your bank to block your card, UPI and net banking. Reporting fast gives the best chance to freeze the money, and reporting to the bank within 3 days protects you under RBI rules. Keep screenshots, the caller's number and transaction IDs.",
  "धोखाधड़ी में पैसा गया हो तो कुछ ही मिनटों में कार्रवाई करें: 1930 (राष्ट्रीय साइबर अपराध हेल्पलाइन) पर कॉल करें या cybercrime.gov.in पर शिकायत करें, और बैंक को फोन करके कार्ड, UPI और नेट बैंकिंग बंद कराएं। जितनी जल्दी शिकायत, पैसा रुकने की उतनी अच्छी संभावना; 3 दिन के अंदर बैंक को बताने पर RBI नियम आपकी रक्षा करते हैं। स्क्रीनशॉट, कॉल करने वाले का नंबर और ट्रांज़ैक्शन आईडी संभालकर रखें।",
  "மோசடியில் பணம் இழந்தால் சில நிமிடங்களுக்குள் செயல்படுங்கள்: 1930 (தேசிய சைபர் குற்ற உதவி எண்) அழையுங்கள் அல்லது cybercrime.gov.in-இல் புகார் செய்யுங்கள், வங்கியை அழைத்து அட்டை, UPI, நெட் பேங்கிங்கை முடக்குங்கள். விரைவாகப் புகார் செய்தால் பணத்தை முடக்க நல்ல வாய்ப்பு; 3 நாட்களுக்குள் வங்கிக்குத் தெரிவித்தால் RBI விதிகள் உங்களைப் பாதுகாக்கும். திரைப்பிடிப்புகள், அழைத்தவரின் எண், பரிவர்த்தனை ID-களை வைத்திருங்கள்.",
  related=("otp_safety", "fraud_check_help", "bank_complaint"))

T("kyc_scam", "safety",
  ("Fake KYC / account-block messages", "नकली KYC / खाता बंद संदेश", "போலி KYC / கணக்கு முடக்கச் செய்திகள்"),
  ["kyc update", "kyc expired", "account blocked", "account will be blocked", "pan update", "fake call", "fake sms", "fake message", "link click", "apk",
   "खाता बंद हो जाएगा", "केवाईसी अपडेट", "फर्जी", "नकली", "கணக்கு முடக்க", "போலி", "கேஒய்சி புதுப்பி"],
  [],
  "Messages saying 'your account will be blocked, update KYC/PAN now' with a link or an app (.apk) to install are a common fraud. Banks never ask you to update KYC through a link, or to install an app sent on SMS or WhatsApp. Do not click, do not call numbers in the message — contact your bank only through its official number. You can check any message on the Fraud Check page of this app.",
  "'आपका खाता बंद हो जाएगा, अभी KYC/पैन अपडेट करें' जैसे संदेश, जिनमें लिंक या इंस्टॉल करने के लिए ऐप (.apk) हो, आम धोखा हैं। बैंक कभी लिंक से KYC अपडेट करने या SMS/WhatsApp पर भेजा ऐप डालने को नहीं कहते। क्लिक न करें, संदेश में दिए नंबर पर कॉल न करें — बैंक से सिर्फ आधिकारिक नंबर पर संपर्क करें। इस ऐप के सुरक्षा जांच पेज पर कोई भी संदेश जांच सकते हैं।",
  "'உங்கள் கணக்கு முடக்கப்படும், உடனே KYC/PAN புதுப்பியுங்கள்' என்று இணைப்பு அல்லது நிறுவ வேண்டிய செயலியுடன் (.apk) வரும் செய்திகள் பொதுவான மோசடி. இணைப்பு மூலம் KYC புதுப்பிக்கவோ, SMS/WhatsApp-இல் அனுப்பிய செயலியை நிறுவவோ வங்கிகள் ஒருபோதும் சொல்வதில்லை. கிளிக் செய்யாதீர்கள், செய்தியிலுள்ள எண்களை அழைக்காதீர்கள் — அதிகாரப்பூர்வ எண்ணில் மட்டும் வங்கியைத் தொடர்புகொள்ளுங்கள். இந்தச் செயலியின் மோசடி சரிபார்ப்புப் பக்கத்தில் எந்தச் செய்தியையும் சரிபார்க்கலாம்.",
  related=("fraud_check_help", "otp_safety", "report_fraud"))

T("digital_arrest", "safety",
  ("'Digital arrest' and police-threat calls", "'डिजिटल अरेस्ट' और पुलिस धमकी कॉल", "'டிஜிட்டல் கைது' மற்றும் காவல் மிரட்டல் அழைப்புகள்"),
  ["digital arrest", "cbi", "customs", "parcel", "police call", "arrest warrant", "money laundering", "drugs parcel", "video call", "डिजिटल अरेस्ट", "गिरफ्तार",
   "पार्सल", "डिजिटल गिरफ्तारी", "டிஜிட்டல் கைது", "பார்சல்", "கைது"],
  [],
  "There is no such thing as a 'digital arrest'. Police, CBI, customs, ED or courts never arrest anyone over a video call and never ask you to transfer money to 'verify' or 'clear your name'. If someone threatens you about a parcel, drugs or a case and asks for money, disconnect, do not pay, and report it on 1930 or cybercrime.gov.in. Tell a family member — these frauds work by keeping you scared and alone.",
  "'डिजिटल अरेस्ट' जैसी कोई चीज़ नहीं होती। पुलिस, CBI, कस्टम, ED या कोर्ट कभी वीडियो कॉल पर गिरफ्तार नहीं करते और 'जांच' या 'नाम साफ करने' के लिए कभी पैसे ट्रांसफर नहीं करवाते। अगर कोई पार्सल, ड्रग्स या केस के नाम पर डराकर पैसे मांगे, तो फोन काटें, पैसा न दें, और 1930 या cybercrime.gov.in पर शिकायत करें। परिवार को बताएं — यह धोखा आपको डराकर अकेला रखकर ही चलता है।",
  "'டிஜிட்டல் கைது' என்று எதுவும் இல்லை. காவல்துறை, CBI, சுங்கம், ED அல்லது நீதிமன்றம் வீடியோ அழைப்பில் யாரையும் கைது செய்வதில்லை; 'சரிபார்க்க' அல்லது 'பெயரைச் சுத்தப்படுத்த' பணம் அனுப்பச் சொல்வதுமில்லை. பார்சல், போதைப்பொருள் அல்லது வழக்கு என்று மிரட்டிப் பணம் கேட்டால், அழைப்பைத் துண்டியுங்கள், பணம் செலுத்தாதீர்கள், 1930 அல்லது cybercrime.gov.in-இல் புகார் செய்யுங்கள். குடும்பத்தினரிடம் சொல்லுங்கள் — இந்த மோசடி உங்களைப் பயமுறுத்தித் தனிமைப்படுத்தியே நடக்கிறது.",
  related=("report_fraud", "otp_safety", "fraud_check_help"))

T("prize_job_scam", "safety",
  ("Lottery, prize and job offer frauds", "लॉटरी, इनाम और नौकरी धोखा", "லாட்டரி, பரிசு, வேலை மோசடிகள்"),
  ["lottery", "prize", "won", "winner", "lucky draw", "kbc", "job offer", "work from home", "part time job", "task", "like videos", "processing fee", "registration fee",
   "लॉटरी", "इनाम", "जीत", "नौकरी", "पार्ट टाइम", "லாட்டரி", "பரிசு", "வேலை வாய்ப்பு", "பகுதி நேர வேலை"],
  [],
  "If you are told you won a lottery, prize or KBC draw you never entered, or offered an easy job like liking videos or rating hotels for high pay, it is a fraud. They ask for a 'processing', 'tax' or 'registration' fee, or ask you to invest in 'tasks' — and you lose that money. Real prizes and jobs never ask you to pay first. Do not pay or share details; report it on 1930.",
  "अगर आपको बताया जाए कि आपने ऐसी लॉटरी, इनाम या KBC ड्रॉ जीता है जिसमें आपने हिस्सा ही नहीं लिया, या वीडियो लाइक करने, होटल रेटिंग जैसी आसान नौकरी में ज़्यादा कमाई का ऑफर मिले, तो यह धोखा है। वे 'प्रोसेसिंग', 'टैक्स' या 'रजिस्ट्रेशन' फीस मांगते हैं, या 'टास्क' में पैसा लगवाते हैं — और वह पैसा डूब जाता है। असली इनाम और नौकरी में पहले पैसा नहीं मांगा जाता। पैसा या जानकारी न दें; 1930 पर शिकायत करें।",
  "நீங்கள் பங்கேற்காத லாட்டரி, பரிசு அல்லது KBC குலுக்கலில் வென்றதாகச் சொன்னால், அல்லது வீடியோ லைக் செய்தல், ஹோட்டல் மதிப்பீடு போன்ற எளிய வேலைக்கு அதிக சம்பளம் என்றால், அது மோசடி. அவர்கள் 'செயலாக்க', 'வரி' அல்லது 'பதிவு' கட்டணம் கேட்பார்கள், அல்லது 'டாஸ்க்'களில் முதலீடு செய்யச் சொல்வார்கள் — அந்தப் பணம் போய்விடும். உண்மையான பரிசுகளும் வேலைகளும் முதலில் பணம் கேட்பதில்லை. பணமோ விவரங்களோ தராதீர்கள்; 1930-இல் புகார் செய்யுங்கள்.",
  related=("report_fraud", "high_return_scam", "fraud_check_help"))

T("high_return_scam", "safety",
  ("Schemes promising double money", "पैसा दोगुना करने वाली योजनाएं", "பணத்தை இரட்டிப்பாக்கும் திட்டங்கள்"),
  ["double money", "money double", "high return", "guaranteed return", "chit fund", "ponzi", "pyramid", "crypto", "paisa double", "पैसा डबल", "दोगुना", "चिट फंड",
   "இரட்டிப்பு", "சீட்டு", "அதிக லாபம்"],
  [],
  "Be very careful of anyone promising to double your money quickly or guaranteed high returns every month — this is usually a Ponzi or illegal deposit scheme that collapses, and people lose their savings. Check that the company is registered with RBI or SEBI before investing. You can report suspicious deposit schemes on the RBI Sachet portal (sachet.rbi.org.in).",
  "जल्दी पैसा दोगुना करने या हर महीने पक्के ऊंचे मुनाफे का वादा करने वालों से बहुत सावधान रहें — यह आमतौर पर पोंज़ी या गैरकानूनी जमा योजना होती है जो डूब जाती है और लोगों की बचत चली जाती है। निवेश से पहले जांचें कि कंपनी RBI या SEBI में पंजीकृत है। संदिग्ध जमा योजनाओं की शिकायत RBI के सचेत पोर्टल (sachet.rbi.org.in) पर करें।",
  "விரைவில் பணத்தை இரட்டிப்பாக்குவதாக அல்லது ஒவ்வொரு மாதமும் உத்தரவாத அதிக லாபம் தருவதாகச் சொல்பவர்களிடம் மிகவும் கவனமாக இருங்கள் — இது பொதுவாக சரிந்துவிடும் போன்சி அல்லது சட்டவிரோத வைப்புத் திட்டம், மக்கள் சேமிப்பை இழக்கின்றனர். முதலீடு செய்யும் முன் நிறுவனம் RBI அல்லது SEBI-யில் பதிவு பெற்றதா எனச் சரிபாருங்கள். சந்தேகமான வைப்புத் திட்டங்களை RBI சசேத் இணையதளத்தில் (sachet.rbi.org.in) புகார் செய்யலாம்.",
  related=("mutual_funds", "post_office", "report_fraud"))

# ─── Complaints ───────────────────────────────────────────────────────────────

T("bank_complaint", "complaints",
  ("Complaint against a bank", "बैंक के खिलाफ शिकायत", "வங்கிக்கு எதிரான புகார்"),
  ["complaint", "complain", "ombudsman", "grievance", "not resolved", "bank not helping", "shikayat", "शिकायत", "लोकपाल", "புகார்", "குறைதீர்ப்பாளர்"],
  [],
  "First complain to your bank — at the branch, by email, on its website or helpline — and keep the complaint number. If the bank does not reply within 30 days, or you are not satisfied, complain free of charge to the RBI Ombudsman at cms.rbi.org.in, by calling 14448, or by post to the RBI's central receipt centre in Chandigarh.",
  "पहले अपने बैंक में शिकायत करें — शाखा, ईमेल, वेबसाइट या हेल्पलाइन पर — और शिकायत नंबर संभालकर रखें। अगर बैंक 30 दिन में जवाब न दे या आप संतुष्ट न हों, तो cms.rbi.org.in पर, 14448 पर कॉल करके, या चंडीगढ़ में RBI के केंद्रीय प्राप्ति केंद्र को डाक से मुफ्त में RBI लोकपाल को शिकायत करें।",
  "முதலில் உங்கள் வங்கியிடம் புகார் செய்யுங்கள் — கிளை, மின்னஞ்சல், இணையதளம் அல்லது உதவி எண் மூலம் — புகார் எண்ணை வைத்துக்கொள்ளுங்கள். 30 நாட்களில் வங்கி பதில் அளிக்கவில்லை அல்லது திருப்தி இல்லையென்றால், cms.rbi.org.in-இல், 14448-ஐ அழைத்து, அல்லது சண்டிகரிலுள்ள RBI மைய வரவேற்பு மையத்துக்கு அஞ்சல் மூலம் RBI குறைதீர்ப்பாளரிடம் இலவசமாகப் புகார் செய்யலாம்.",
  related=("report_fraud", "recovery_harassment", "atm_cash_not_dispensed"))

# ─── Documents ────────────────────────────────────────────────────────────────

T("aadhaar", "documents",
  ("Aadhaar card", "आधार कार्ड", "ஆதார் அட்டை"),
  ["aadhaar", "aadhar", "adhar", "uidai", "biometric", "आधार", "ஆதார்"],
  [],
  "Aadhaar is your 12-digit identity number from UIDAI, linked to your fingerprints, eyes and photo. It is needed for bank KYC and most government schemes. Enrolment is free at any Aadhaar centre; you can update your address or download e-Aadhaar on the myAadhaar website, or update photo and biometrics at an Aadhaar centre. Never share the OTP sent for Aadhaar with anyone.",
  "आधार UIDAI द्वारा दिया गया आपका 12 अंकों का पहचान नंबर है, जो आपकी उंगलियों के निशान, आंखों और फोटो से जुड़ा है। बैंक KYC और ज़्यादातर सरकारी योजनाओं के लिए ज़रूरी है। किसी भी आधार केंद्र पर नामांकन मुफ्त है; पता अपडेट या ई-आधार डाउनलोड myAadhaar वेबसाइट पर, और फोटो/बायोमेट्रिक अपडेट आधार केंद्र पर कराएं। आधार के लिए आया OTP किसी को न बताएं।",
  "ஆதார் என்பது UIDAI வழங்கும் உங்கள் 12 இலக்க அடையாள எண்; உங்கள் கைரேகை, கண், புகைப்படத்துடன் இணைக்கப்பட்டது. வங்கி KYC மற்றும் பெரும்பாலான அரசுத் திட்டங்களுக்குத் தேவை. எந்த ஆதார் மையத்திலும் பதிவு இலவசம்; முகவரி மாற்றம் அல்லது இ-ஆதார் பதிவிறக்கம் myAadhaar இணையதளத்தில், புகைப்படம்/பயோமெட்ரிக் மாற்றம் ஆதார் மையத்தில் செய்யலாம். ஆதாருக்கு வரும் OTP-ஐ யாரிடமும் பகிராதீர்கள்.",
  related=("dbt_seeding", "pan", "kyc_docs"))

T("pan", "documents",
  ("PAN card", "पैन कार्ड", "பான் அட்டை"),
  ["pan", "pan card", "e-pan", "epan", "form 60", "पैन", "பான்"],
  [],
  "PAN is a 10-character tax ID from the Income Tax Department. You need it for things like depositing more than ₹50,000 in cash in a day, opening an FD above ₹50,000, or buying property. You can get an e-PAN free and almost instantly on the Income Tax e-filing website using your Aadhaar. If you have no PAN, fill Form 60 at the bank. Keep your PAN linked with Aadhaar.",
  "पैन आयकर विभाग का 10 अक्षरों का टैक्स नंबर है। एक दिन में ₹50,000 से ज़्यादा नकद जमा करने, ₹50,000 से ज़्यादा की FD या संपत्ति खरीदने जैसे कामों में चाहिए। आयकर ई-फाइलिंग वेबसाइट पर आधार से मुफ्त और लगभग तुरंत ई-पैन मिल जाता है। पैन न हो तो बैंक में फॉर्म 60 भरें। पैन को आधार से जोड़कर रखें।",
  "பான் என்பது வருமான வரித் துறையின் 10 எழுத்து வரி அடையாள எண். ஒரே நாளில் ₹50,000-க்கு மேல் ரொக்கம் செலுத்த, ₹50,000-க்கு மேல் FD திறக்க, சொத்து வாங்க போன்றவற்றுக்குத் தேவை. வருமான வரி இ-ஃபைலிங் இணையதளத்தில் ஆதார் மூலம் இலவசமாக, கிட்டத்தட்ட உடனடியாக இ-பான் பெறலாம். பான் இல்லையென்றால் வங்கியில் படிவம் 60 நிரப்புங்கள். பானை ஆதாருடன் இணைத்து வையுங்கள்.",
  related=("aadhaar", "income_tax", "kyc_docs"))

# ─── Tax ──────────────────────────────────────────────────────────────────────

T("income_tax", "tax",
  ("Do I need to pay income tax?", "क्या मुझे आयकर देना होगा?", "நான் வருமான வரி செலுத்த வேண்டுமா?"),
  ["income tax", "tax", "itr", "tax return", "आयकर", "इनकम टैक्स", "टैक्स", "வருமான வரி", "வரி"],
  [],
  "From the financial year 2025-26, under the new tax regime, people with total income up to ₹12 lakh a year usually pay no income tax (up to about ₹12.75 lakh for salaried people). Filing a return is still useful to claim back any tax deducted (TDS) and as income proof for loans. Farm income is exempt. For your own case, ask a tax practitioner or use the free Income Tax e-filing website.",
  "वित्त वर्ष 2025-26 से नई टैक्स व्यवस्था में ₹12 लाख तक की कुल सालाना आय वालों को आमतौर पर कोई आयकर नहीं देना होता (नौकरीपेशा के लिए लगभग ₹12.75 लाख तक)। फिर भी रिटर्न भरना काटे गए टैक्स (TDS) को वापस पाने और लोन के लिए आय प्रमाण के रूप में उपयोगी है। खेती की आय पर टैक्स नहीं है। अपने मामले के लिए टैक्स सलाहकार से पूछें या मुफ्त आयकर ई-फाइलिंग वेबसाइट देखें।",
  "2025-26 நிதியாண்டு முதல் புதிய வரி முறையில் ஆண்டு மொத்த வருமானம் ₹12 லட்சம் வரை உள்ளவர்கள் பொதுவாக வருமான வரி செலுத்தத் தேவையில்லை (சம்பளதாரர்களுக்கு சுமார் ₹12.75 லட்சம் வரை). இருப்பினும் பிடித்தம் செய்த வரியை (TDS) திரும்பப் பெறவும், கடனுக்கான வருமானச் சான்றாகவும் வரிக் கணக்குத் தாக்கல் பயனுள்ளது. விவசாய வருமானத்துக்கு வரி இல்லை. உங்கள் நிலைக்கு வரி ஆலோசகரிடம் கேளுங்கள் அல்லது இலவச வருமான வரி இ-ஃபைலிங் இணையதளத்தைப் பயன்படுத்துங்கள்.",
  related=("tds_15g", "pan", "ppf"))

T("tds_15g", "tax",
  ("TDS on FD interest / Form 15G-15H", "FD ब्याज पर TDS / फॉर्म 15G-15H", "FD வட்டியில் TDS / படிவம் 15G-15H"),
  ["tds", "15g", "15h", "form 15g", "form 15h", "tax deducted", "टीडीएस", "कटौती", "டிடிஎஸ்"],
  [],
  "Banks deduct tax (TDS) from FD interest if it is more than ₹50,000 in a year at that bank (₹1 lakh for senior citizens). If your total income is below the taxable limit, submit Form 15G (below 60 years) or Form 15H (60 and above) to the bank at the start of each financial year so no TDS is cut. Tax already deducted can be claimed back by filing an income tax return.",
  "अगर किसी बैंक में साल का FD ब्याज ₹50,000 से ज़्यादा हो (वरिष्ठ नागरिकों के लिए ₹1 लाख), तो बैंक उस पर टैक्स (TDS) काटता है। अगर आपकी कुल आय टैक्स सीमा से कम है, तो हर वित्त वर्ष की शुरुआत में बैंक को फॉर्म 15G (60 से कम उम्र) या फॉर्म 15H (60 या ज़्यादा) दें ताकि TDS न कटे। कटा हुआ टैक्स आयकर रिटर्न भरकर वापस मिल सकता है।",
  "ஒரு வங்கியில் ஆண்டு FD வட்டி ₹50,000-க்கு மேல் இருந்தால் (மூத்த குடிமக்களுக்கு ₹1 லட்சம்) வங்கி வரி (TDS) பிடித்தம் செய்யும். உங்கள் மொத்த வருமானம் வரி வரம்புக்குக் கீழ் இருந்தால், ஒவ்வொரு நிதியாண்டின் தொடக்கத்திலும் படிவம் 15G (60 வயதுக்குக் கீழ்) அல்லது 15H (60 மற்றும் மேல்) வங்கியில் கொடுத்தால் TDS பிடிக்கப்படாது. ஏற்கனவே பிடித்த வரியை வருமான வரிக் கணக்குத் தாக்கல் செய்து திரும்பப் பெறலாம்.",
  related=("fd", "income_tax", "scss"))

# ─── This app ─────────────────────────────────────────────────────────────────

T("form_fill_help", "app",
  ("Fill a form by voice", "बोलकर फॉर्म भरें", "குரல் மூலம் படிவம் நிரப்புதல்"),
  ["fill form", "form fill", "fill a form", "fill the form", "upload form", "help me fill", "form bharna", "form bharo", "फॉर्म भर", "फॉर्म", "படிவம் நிரப்ப", "படிவம்"],
  ["form", "fill"],
  "I can fill bank and government forms for you — account opening, cash deposit or withdrawal slips, cheques, cheque-book requests and more. Open '1. Form Fill', upload a photo or PDF of the form, and I will ask each question by voice in your language. You confirm every answer, can go back to change any of them or skip one, and then download the filled form.",
  "मैं आपके बैंक और सरकारी फॉर्म भर सकता हूँ — खाता खोलना, नकद जमा या निकासी पर्ची, चेक, चेकबुक अनुरोध और भी। '1. फॉर्म भरें' खोलें, फॉर्म की फोटो या PDF अपलोड करें, और मैं हर सवाल आपकी भाषा में बोलकर पूछूंगा। आप हर उत्तर की पुष्टि करते हैं, पीछे जाकर कोई भी उत्तर बदल या छोड़ सकते हैं, और फिर भरा हुआ फॉर्म डाउनलोड करें।",
  "வங்கி மற்றும் அரசுப் படிவங்களை நான் உங்களுக்கு நிரப்ப முடியும் — கணக்கு திறப்பு, பணம் செலுத்தும்/எடுக்கும் சீட்டு, காசோலை, காசோலைப் புத்தகக் கோரிக்கை மற்றும் பல. '1. படிவம்' திறந்து, படிவத்தின் புகைப்படம் அல்லது PDF-ஐப் பதிவேற்றுங்கள்; ஒவ்வொரு கேள்வியையும் உங்கள் மொழியில் குரலில் கேட்பேன். ஒவ்வொரு பதிலையும் நீங்கள் உறுதிப்படுத்தலாம், பின்னால் சென்று மாற்றலாம் அல்லது தவிர்க்கலாம், பின்னர் நிரப்பிய படிவத்தைப் பதிவிறக்கலாம்.",
  related=("cheque", "kyc_docs", "fraud_check_help"))

T("fraud_check_help", "app",
  ("Check a suspicious message", "संदिग्ध संदेश जांचें", "சந்தேகமான செய்தியைச் சரிபார்க்கவும்"),
  ["check message", "check sms", "is this message", "suspicious message", "suspicious sms", "is it fake", "real or fake", "sms check", "संदेश जांच", "मैसेज जांच",
   "असली या नकली", "செய்தியைச் சரிபார்", "உண்மையா போலியா"],
  [],
  "Open '4. Fraud Check' and paste or type the message, or take a photo of it. I will check it for signs of fraud — like requests for OTP, PIN or KYC, fake links, threats or prizes — and explain what to do in your language. You choose what to share; I never read your SMS on my own.",
  "'4. सुरक्षा जांच' खोलें और संदेश पेस्ट करें या लिखें, या उसकी फोटो लें। मैं उसमें धोखे के संकेत — जैसे OTP, पिन या KYC की मांग, नकली लिंक, धमकी या इनाम — जांचूंगा और आपकी भाषा में बताऊंगा कि क्या करें। क्या दिखाना है यह आप चुनते हैं; मैं खुद आपके SMS कभी नहीं पढ़ता।",
  "'4. மோசடி' திறந்து செய்தியை ஒட்டவும் அல்லது தட்டச்சு செய்யவும், அல்லது அதன் புகைப்படம் எடுக்கவும். OTP, PIN அல்லது KYC கோரிக்கை, போலி இணைப்புகள், மிரட்டல் அல்லது பரிசு போன்ற மோசடி அறிகுறிகளைச் சரிபார்த்து, என்ன செய்ய வேண்டும் என்று உங்கள் மொழியில் விளக்குவேன். எதைப் பகிர்வது என்பதை நீங்களே தேர்வு செய்கிறீர்கள்; உங்கள் SMS-ஐ நானாக ஒருபோதும் படிப்பதில்லை.",
  related=("kyc_scam", "report_fraud", "otp_safety"))


# ─── Conversation phrases ─────────────────────────────────────────────────────

CATEGORY_LABELS = {
    "banking": ("Bank account", "बैंक खाता", "வங்கிக் கணக்கு"),
    "cards": ("ATM & cards", "एटीएम और कार्ड", "ஏடிஎம் & அட்டைகள்"),
    "payments": ("Payments & UPI", "भुगतान और UPI", "பணப் பரிமாற்றம் & UPI"),
    "savings": ("Savings", "बचत", "சேமிப்பு"),
    "loans": ("Loans", "लोन", "கடன்"),
    "insurance": ("Insurance", "बीमा", "காப்பீடு"),
    "pension": ("Pension", "पेंशन", "ஓய்வூதியம்"),
    "schemes": ("Govt schemes", "सरकारी योजना", "அரசுத் திட்டம்"),
    "safety": ("Safety", "सुरक्षा", "பாதுகாப்பு"),
    "complaints": ("Complaints", "शिकायत", "புகார்"),
    "documents": ("Documents", "दस्तावेज़", "ஆவணங்கள்"),
    "tax": ("Tax", "टैक्स", "வரி"),
    "app": ("Using this app", "इस ऐप का उपयोग", "இந்தச் செயலி"),
    "calculator": ("Calculator", "हिसाब", "கணக்கீடு"),
    "general": ("Help", "मदद", "உதவி"),
}

# Topics offered when the user asks for the menu or we did not understand twice
MENU_TOPICS = ["open_account", "upi", "loan_basics", "fd", "insurance_basics", "pension_options", "schemes_general", "report_fraud", "bank_complaint"]

YES_WORDS = ["yes", "yeah", "yep", "sure", "ok", "okay", "please", "haan", "han", "ha", "haa", "ji", "haanji", "theek", "thik", "bilkul", "aama", "aamaa", "sari",
             "हाँ", "हां", "हा", "जी", "ठीक", "बिल्कुल", "ज़रूर", "जरूर", "ஆம்", "ஆமா", "சரி", "ஓகே", "கண்டிப்பாக"]
NO_WORDS = ["no", "nope", "nahi", "nahin", "na", "mat", "not now", "later", "illai", "vendam", "venda",
            "नहीं", "ना", "मत", "बाद में", "இல்லை", "வேண்டாம்", "பிறகு"]
MORE_WORDS = ["more", "tell me more", "explain", "detail", "details", "aur batao", "aur bataiye", "aage", "next", "then", "phir",
              "और बताओ", "और बताइए", "विस्तार", "आगे", "फिर", "மேலும்", "இன்னும்", "விரிவாக", "அடுத்து"]
CANCEL_WORDS = ["cancel", "stop", "leave it", "forget it", "rehne do", "chhodo", "bas", "रहने दो", "छोड़ो", "बस", "रद्द", "நிறுத்து", "விடுங்கள்", "வேண்டாம்", "ரத்து"]
THANKS_WORDS = ["thank", "thanks", "dhanyavad", "dhanyawad", "shukriya", "धन्यवाद", "शुक्रिया", "நன்றி"]
BYE_WORDS = ["bye", "goodbye", "alvida", "अलविदा", "போய் வருகிறேன்", "சென்று வருகிறேன்"]
GREET_WORDS = ["hi", "hello", "hey", "namaste", "namaskar", "good morning", "good evening", "vanakkam", "नमस्ते", "नमस्कार", "हेलो", "வணக்கம்", "ஹலோ"]
HELP_WORDS = ["help", "menu", "what can you do", "who are you", "options", "madad", "मदद", "क्या कर सकते", "कौन हो", "உதவி", "என்ன செய்ய முடியும்", "நீங்கள் யார்"]
HUMAN_WORDS = ["talk to human", "human", "agent", "customer care", "helpline", "call centre", "call center", "insaan", "कस्टमर केयर", "हेल्पलाइन", "इंसान",
               "வாடிக்கையாளர் சேவை", "உதவி எண்", "மனிதர்"]

# facet words → facet name
FACETS = {
    "docs": ["document", "documents", "papers", "kagaz", "kagzat", "proof", "दस्तावेज", "कागज", "ஆவண", "சான்று"],
    "how": ["how", "apply", "kaise", "kahan se", "process", "procedure", "steps", "कैसे", "आवेदन", "प्रक्रिया", "எப்படி", "விண்ணப்ப"],
    "eligibility": ["eligible", "eligibility", "who can", "kaun", "patra", "पात्र", "कौन", "தகுதி", "யார்"],
    "cost": ["interest", "rate", "charges", "charge", "fee", "fees", "cost", "kitna", "kitni", "byaj", "ब्याज", "कितना", "कितनी", "शुल्क", "வட்டி", "கட்டண", "எவ்வளவு"],
    "claim": ["claim", "दावा", "क्लेम", "க்ளெய்ம்", "கோரிக்கை"],
}

# words that tell us who the user is → scheme_finder audience ids
PROFILE_WORDS = {
    "farmer": ["i am a farmer", "i am farmer", "i'm a farmer", "farmer", "kisan hu", "kisaan", "kheti karta", "kheti karti", "किसान हूँ", "किसान हूं", "खेती करता",
               "खेती करती", "விவசாயி", "விவசாயம் செய்"],
    "woman": ["i am a woman", "housewife", "homemaker", "lady", "mahila", "grihini", "महिला हूँ", "महिला हूं", "गृहिणी", "பெண் நான்", "இல்லத்தரசி"],
    "senior": ["senior citizen", "retired", "old age", "budhapa", "बुजुर्ग", "रिटायर", "வயதானவர்", "ஓய்வு பெற்ற", "மூத்த குடிமகன்"],
    "student": ["i am a student", "student", "studying", "college", "padhai karta", "padhai karti", "छात्र", "छात्रा", "पढ़ाई कर", "மாணவன்", "மாணவி", "படிக்கிறேன்"],
    "worker": ["labourer", "laborer", "daily wage", "mazdoor", "majdoor", "construction worker", "मज़दूर", "मजदूर", "दिहाड़ी", "கூலித் தொழிலாளி", "தினக்கூலி"],
    "business": ["shopkeeper", "my shop", "small business", "dukandar", "vendor", "street vendor", "दुकानदार", "मेरी दुकान", "रेहड़ी", "கடை வைத்திருக்கிறேன்",
                       "சிறு தொழில்", "வியாபாரி"],
    "girl_child": ["my daughter", "beti", "मेरी बेटी", "बेटी", "என் மகள்"],
}

PROFILE_LABELS = {
    "farmer": ("a farmer", "किसान", "விவசாயி"),
    "woman": ("a woman", "महिला", "பெண்"),
    "senior": ("a senior citizen", "वरिष्ठ नागरिक", "மூத்த குடிமகன்"),
    "student": ("a student", "छात्र", "மாணவர்"),
    "worker": ("a worker", "मज़दूर", "தொழிலாளி"),
    "business": ("running a small business", "छोटे व्यापारी", "சிறு தொழில் செய்பவர்"),
    "girl_child": ("a parent of a daughter", "बेटी के माता-पिता", "மகளின் பெற்றோர்"),
}

# topics that fit a profile best (used for suggestions)
PROFILE_TOPICS = {
    "farmer": ["pm_kisan", "kcc", "crop_insurance"],
    "woman": ["shg_loan", "pmsby", "sukanya"],
    "senior": ["scss", "old_age_pension", "life_certificate"],
    "student": ["education_loan", "jan_dhan", "upi"],
    "worker": ["apy", "pmsby", "jan_dhan"],
    "business": ["mudra", "upi", "credit_score"],
    "girl_child": ["sukanya", "education_loan", "ppf"],
}

PHRASES = {
    "as_mentioned": ("As I mentioned earlier: ", "जैसा मैंने पहले बताया: ", "நான் முன்பே சொன்னது போல: "),
    "yes_what": ("Sure! What would you like to know? You can pick one of these.",
                 "ज़रूर! आप क्या जानना चाहेंगे? इनमें से कुछ चुन सकते हैं।",
                 "நிச்சயமாக! என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்? இவற்றில் ஒன்றைத் தேர்ந்தெடுக்கலாம்."),
    "again_short": ("I just explained this. In short: ", "यह मैंने अभी बताया। संक्षेप में: ", "இதை இப்போதுதான் சொன்னேன். சுருக்கமாக: "),
    "next_offer": ("Would you like to know about {t}?", "क्या आप {t} के बारे में जानना चाहेंगे?", "{t} பற்றி தெரிந்துகொள்ள விரும்புகிறீர்களா?"),
    "about_that": ("About {t}: ", "{t} के बारे में: ", "{t} பற்றி: "),
    "related_to": ("Related to that — {t}: ", "इसी से जुड़ा — {t}: ", "இதனுடன் தொடர்புடையது — {t}: "),
    "ok_no": ("Okay. What else can I help you with? You can ask about any of these.",
              "ठीक है। मैं और किस बारे में मदद करूं? आप इनमें से कुछ भी पूछ सकते हैं।",
              "சரி. வேறு எதில் உதவட்டும்? இவற்றில் எதைப் பற்றியும் கேட்கலாம்."),
    "greet": ("Namaste! I am your FinAccess money guide. Ask me about bank accounts, UPI, loans, savings, insurance, pensions, government schemes or safety from fraud.",
              "नमस्ते! मैं आपका FinAccess वित्तीय सहायक हूँ। बैंक खाता, UPI, लोन, बचत, बीमा, पेंशन, सरकारी योजनाएं या धोखाधड़ी से सुरक्षा के बारे में पूछें।",
              "வணக்கம்! நான் உங்கள் FinAccess நிதி வழிகாட்டி. வங்கிக் கணக்கு, UPI, கடன், சேமிப்பு, காப்பீடு, ஓய்வூதியம், அரசுத் திட்டங்கள் அல்லது மோசடிப் பாதுகாப்பு பற்றி கேளுங்கள்."),
    "greet_again": ("Hello again! We were talking about {t}. Do you want to continue with that, or ask something new?",
                    "फिर से नमस्ते! हम {t} के बारे में बात कर रहे थे। क्या उसी पर आगे बढ़ें, या कुछ नया पूछना है?",
                    "மீண்டும் வணக்கம்! நாம் {t} பற்றிப் பேசிக்கொண்டிருந்தோம். அதைத் தொடரலாமா, அல்லது புதிதாக ஏதாவது கேட்க விரும்புகிறீர்களா?"),
    "thanks": ("You're welcome! Is there anything else about money or banking I can help with?",
               "आपका स्वागत है! पैसे या बैंकिंग के बारे में और कुछ मदद चाहिए?",
               "மகிழ்ச்சி! பணம் அல்லது வங்கி தொடர்பாக வேறு ஏதாவது உதவி வேண்டுமா?"),
    "bye": ("Goodbye! Remember: never share your OTP or PIN. Come back any time.",
            "अलविदा! याद रखें: OTP या पिन किसी को न बताएं। जब चाहें फिर आइए।",
            "சென்று வாருங்கள்! நினைவில் கொள்ளுங்கள்: OTP அல்லது PIN-ஐ யாரிடமும் பகிராதீர்கள். எப்போது வேண்டுமானாலும் வாருங்கள்."),
    "help": ("I can explain bank accounts, ATM and UPI, savings and FDs, loans and EMIs, insurance, pensions, government schemes, taxes, and how to stay safe from fraud. I can also calculate a loan EMI or FD maturity. Pick a topic below or just ask in your own words.",
             "मैं बैंक खाता, एटीएम और UPI, बचत और FD, लोन और EMI, बीमा, पेंशन, सरकारी योजनाएं, टैक्स, और धोखाधड़ी से बचाव समझा सकता हूँ। लोन की EMI या FD की परिपक्वता राशि का हिसाब भी लगा सकता हूँ। नीचे कोई विषय चुनें या अपने शब्दों में पूछें।",
             "வங்கிக் கணக்கு, ஏடிஎம் மற்றும் UPI, சேமிப்பு மற்றும் FD, கடன் மற்றும் EMI, காப்பீடு, ஓய்வூதியம், அரசுத் திட்டங்கள், வரி, மோசடியிலிருந்து பாதுகாப்பு ஆகியவற்றை விளக்க முடியும். கடன் EMI அல்லது FD முதிர்வுத் தொகையையும் கணக்கிட முடியும். கீழே ஒரு தலைப்பைத் தேர்ந்தெடுங்கள் அல்லது உங்கள் சொந்த வார்த்தைகளில் கேளுங்கள்."),
    "human": ("For personal help: call your bank's helpline (on your passbook or card), visit your branch or Bank Mitra, call 1930 for cyber fraud, 14448 for RBI complaints, or visit a Common Service Centre for government schemes.",
              "व्यक्तिगत मदद के लिए: अपने बैंक की हेल्पलाइन (पासबुक या कार्ड पर लिखी) पर कॉल करें, शाखा या बैंक मित्र के पास जाएं, साइबर धोखाधड़ी के लिए 1930, RBI शिकायत के लिए 14448 पर कॉल करें, या सरकारी योजनाओं के लिए जन सेवा केंद्र जाएं।",
              "நேரடி உதவிக்கு: உங்கள் வங்கியின் உதவி எண்ணை (பாஸ்புக் அல்லது அட்டையில் இருக்கும்) அழையுங்கள், கிளை அல்லது வங்கி மித்ராவிடம் செல்லுங்கள், சைபர் மோசடிக்கு 1930, RBI புகாருக்கு 14448 அழையுங்கள், அரசுத் திட்டங்களுக்குப் பொது சேவை மையத்துக்குச் செல்லுங்கள்."),
    "miss1": ("Sorry, I did not fully understand. Could you say it another way? For example, you can ask: ",
              "माफ़ कीजिए, मैं पूरी तरह समझ नहीं पाया। क्या आप दूसरे तरीके से कह सकते हैं? जैसे आप पूछ सकते हैं: ",
              "மன்னிக்கவும், எனக்கு முழுமையாகப் புரியவில்லை. வேறு விதமாகச் சொல்ல முடியுமா? உதாரணமாக இப்படிக் கேட்கலாம்: "),
    "miss2": ("I still could not match that to a topic. Please pick one of these topics, or say a simple word like 'loan', 'pension' or 'UPI'.",
              "मैं अब भी इसे किसी विषय से नहीं जोड़ पाया। कृपया इनमें से कोई विषय चुनें, या 'लोन', 'पेंशन' या 'UPI' जैसा आसान शब्द बोलें।",
              "இன்னும் இதை ஒரு தலைப்புடன் பொருத்த முடியவில்லை. இந்தத் தலைப்புகளில் ஒன்றைத் தேர்ந்தெடுங்கள், அல்லது 'கடன்', 'ஓய்வூதியம்', 'UPI' போன்ற எளிய சொல்லைச் சொல்லுங்கள்."),
    "miss3": ("This seems to need personal help. ", "इसके लिए शायद व्यक्तिगत मदद चाहिए। ", "இதற்கு நேரடி உதவி தேவைப்படலாம். "),
    "profile_ack": ("Thank you — I will remember that you are {p}. ", "धन्यवाद — मैं याद रखूंगा कि आप {p} हैं। ", "நன்றி — நீங்கள் {p} என்பதை நினைவில் கொள்கிறேன். "),
    "profile_suggest": ("These are most useful for you: {list}. Which one should I explain?",
                        "आपके लिए ये सबसे उपयोगी हैं: {list}। मैं किसके बारे में बताऊं?",
                        "உங்களுக்கு இவை மிகவும் பயனுள்ளவை: {list}. எதைப் பற்றி விளக்கட்டும்?"),
    "schemes_for_you": ("Since you told me you are {p}, these schemes fit you: {list}. Open the Schemes page to see details and how to apply.",
                        "आपने बताया कि आप {p} हैं, इसलिए ये योजनाएं आपके लिए हैं: {list}। विवरण और आवेदन का तरीका योजनाएं पेज पर देखें।",
                        "நீங்கள் {p} என்று சொன்னதால், இந்தத் திட்டங்கள் உங்களுக்குப் பொருந்தும்: {list}. விவரங்களும் விண்ணப்ப முறையும் அறிய திட்டங்கள் பக்கத்தைத் திறக்கவும்."),
    "scheme_who": ("Who can get it: ", "कौन ले सकता है: ", "யார் பெறலாம்: "),
    "scheme_how": ("How to apply: ", "आवेदन कैसे करें: ", "விண்ணப்பிக்கும் முறை: "),
    "scheme_help": ("Helpline: ", "हेल्पलाइन: ", "உதவி எண்: "),
    "calc_cancel": ("Okay, I have stopped the calculation. ", "ठीक है, मैंने हिसाब रोक दिया है। ", "சரி, கணக்கீட்டை நிறுத்திவிட்டேன். "),
    "calc_leave": ("Leaving the calculation for now. ", "हिसाब अभी छोड़ रहे हैं। ", "கணக்கீட்டை இப்போதைக்கு விடுகிறோம். "),
    "calc_retry": ("Sorry, I need a number. ", "माफ़ कीजिए, मुझे एक संख्या चाहिए। ", "மன்னிக்கவும், எனக்கு ஒரு எண் தேவை. "),
}

CALC_TEXT = {
    "emi": {
        "start": ("Let's calculate your EMI. ", "चलिए आपकी EMI का हिसाब लगाते हैं। ", "உங்கள் EMI-ஐ கணக்கிடுவோம். "),
        "amount": ("How much loan do you want? For example, 2 lakh or 50,000.",
                   "आप कितना लोन लेना चाहते हैं? जैसे 2 लाख या 50,000।",
                   "எவ்வளவு கடன் வேண்டும்? உதாரணமாக 2 லட்சம் அல்லது 50,000."),
        "rate": ("What is the yearly interest rate? For example, 10 percent.",
                 "सालाना ब्याज दर कितनी है? जैसे 10 प्रतिशत।",
                 "ஆண்டு வட்டி விகிதம் என்ன? உதாரணமாக 10 சதவீதம்."),
        "years": ("For how many years or months? For example, 3 years.",
                  "कितने साल या महीनों के लिए? जैसे 3 साल।",
                  "எத்தனை ஆண்டுகள் அல்லது மாதங்களுக்கு? உதாரணமாக 3 ஆண்டுகள்."),
        "result": ("For a loan of {p} at {r}% a year for {n}, your EMI is about {emi} a month. In total you will pay {total}, of which {interest} is interest. Want to try a different amount or period? Just tell me the new numbers.",
                   "{p} के लोन पर {r}% सालाना ब्याज से {n} के लिए आपकी EMI लगभग {emi} महीना होगी। कुल आप {total} चुकाएंगे, जिसमें {interest} ब्याज है। दूसरी राशि या अवधि आज़माना चाहें तो नई संख्या बताइए।",
                   "{p} கடனுக்கு ஆண்டுக்கு {r}% வட்டியில் {n} காலத்துக்கு உங்கள் EMI மாதம் சுமார் {emi}. மொத்தமாக {total} செலுத்துவீர்கள், அதில் {interest} வட்டி. வேறு தொகை அல்லது காலத்தை முயற்சிக்க புதிய எண்களைச் சொல்லுங்கள்."),
    },
    "fd": {
        "start": ("Let's calculate your FD. ", "चलिए आपकी FD का हिसाब लगाते हैं। ", "உங்கள் FD-ஐ கணக்கிடுவோம். "),
        "amount": ("How much money do you want to deposit? For example, 1 lakh.",
                   "आप कितना पैसा जमा करना चाहते हैं? जैसे 1 लाख।",
                   "எவ்வளவு பணம் வைப்பு செய்ய விரும்புகிறீர்கள்? உதாரணமாக 1 லட்சம்."),
        "rate": ("What interest rate does the bank offer? For example, 7 percent.",
                 "बैंक कितना ब्याज दे रहा है? जैसे 7 प्रतिशत।",
                 "வங்கி எவ்வளவு வட்டி தருகிறது? உதாரணமாக 7 சதவீதம்."),
        "years": ("For how many years? For example, 5 years.",
                  "कितने साल के लिए? जैसे 5 साल।",
                  "எத்தனை ஆண்டுகளுக்கு? உதாரணமாக 5 ஆண்டுகள்."),
        "result": ("If you deposit {p} at {r}% a year for {n} (interest added every quarter), you will get about {total} at maturity — that is {interest} as interest. Actual amounts can differ slightly by bank, and TDS may apply.",
                   "अगर आप {p} को {r}% सालाना ब्याज पर {n} के लिए जमा करें (हर तिमाही ब्याज जुड़ता है), तो परिपक्वता पर लगभग {total} मिलेंगे — यानी {interest} ब्याज। असली राशि बैंक के हिसाब से थोड़ी अलग हो सकती है, और TDS कट सकता है।",
                   "{p}-ஐ ஆண்டுக்கு {r}% வட்டியில் {n} காலத்துக்கு வைப்பு செய்தால் (ஒவ்வொரு காலாண்டும் வட்டி சேரும்), முதிர்வில் சுமார் {total} கிடைக்கும் — அதாவது {interest} வட்டி. உண்மையான தொகை வங்கிக்கு வங்கி சற்று மாறலாம், TDS பிடிக்கப்படலாம்."),
    },
    "title": {
        "calc_emi": ("Calculate my loan EMI", "मेरी लोन EMI का हिसाब", "என் கடன் EMI கணக்கிடு"),
        "calc_fd": ("Calculate FD maturity", "FD की परिपक्वता राशि का हिसाब", "FD முதிர்வுத் தொகை கணக்கிடு"),
    },
    "triggers": {
        "calc_emi": ["calculate emi", "emi calculate", "emi calculator", "my emi", "emi kitni", "kitni emi", "emi for", "emi on", "emi hisab", "ईएमआई कितनी", "किस्त कितनी",
                     "EMI कितनी", "emi कितनी", "EMI का हिसाब", "emi का हिसाब", "EMI கணக்கிடு", "emi கணக்கிடு", "தவணை எவ்வளவு", "EMI எவ்வளவு", "emi எவ்வளவு"],
        "calc_fd": ["fd calculate", "calculate fd", "fd calculator", "fd maturity", "maturity amount", "fd kitna milega", "how much will i get", "kitna milega",
                    "कितना मिलेगा", "FD का हिसाब", "fd का हिसाब", "எவ்வளவு கிடைக்கும்", "முதிர்வுத் தொகை", "FD கணக்கிடு", "fd கணக்கிடு"],
    },
    "unit_years": ("{n} years", "{n} साल", "{n} ஆண்டுகள்"),
    "unit_year": ("1 year", "1 साल", "1 ஆண்டு"),
    "unit_months": ("{n} months", "{n} महीने", "{n} மாதங்கள்"),
}

LANG_INDEX = {"en": 0, "hi": 1, "ta": 2}
