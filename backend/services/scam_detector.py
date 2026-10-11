"""
Scam / Fraud Message Detector (English, Hinglish, Hindi, Tamil)

How it decides
--------------
Real scams almost always combine a HOOK (a threat, prize, job offer, KYC problem, refund, ...)
with an ASK (click this link, call this number, pay a fee, reply with details, ...). Some asks are
dangerous on their own (share your OTP, enter your PIN to *receive* money, install AnyDesk, an .apk file).

  * a dangerous ask                        → fraud
  * a hook + an ask                         → fraud
  * a hook with time pressure, or a risky link on its own → suspicious
  * anything else                           → safe

Sentences that WARN about fraud ("Never share your OTP", "Do not install AnyDesk") are ignored, so
genuine OTP messages and bank safety alerts are not flagged. Links to official bank / government
sites are trusted; look-alike domains, link shorteners, raw IP addresses and odd TLDs are not.
"""

import re
from urllib.parse import urlparse

# ─── Links ───────────────────────────────────────────────────────────────────
OFFICIAL_DOMAINS = [
    "gov.in", "nic.in", "rbi.org.in", "npci.org.in", "onlinesbi.sbi", "sbi.co.in", "bank.sbi", "sbi",
    "hdfcbank.com", "icicibank.com", "axisbank.com", "kotak.com", "pnbindia.in", "bankofbaroda.in",
    "canarabank.com", "unionbankofindia.co.in", "bankofindia.co.in", "indianbank.in", "iob.in",
    "yesbank.in", "idfcfirstbank.com", "paytm.com", "phonepe.com", "amazon.in", "flipkart.com",
    "irctc.co.in", "jio.com", "airtel.in", "lic.in", "epfindia.gov.in", "licindia.in", "sbicard.com", "sbilife.co.in",
    "icicidirect.com", "hdfcbank.net", "axisbank.co.in", "amazonpay.in", "bhimupi.org.in", "google.com", "whatsapp.com",
    "netflix.com", "bsnl.co.in", "indianoil.in", "hindustanpetroleum.com", "bharatpetroleum.in", "myhpgas.in",
    "bluedart.com", "dhl.com", "fedex.com", "indiapost.gov.in", "aubank.in", "rblbank.com", "federalbank.co.in",
]
SHORTENERS = {"bit.ly", "tinyurl.com", "cutt.ly", "goo.gl", "t.ly", "is.gd", "rb.gy", "shorturl.at", "ow.ly",
              "tiny.cc", "s.id", "rebrand.ly", "bitly.com", "shorte.st"}
CHAT_LINKS = {"wa.me", "t.me", "chat.whatsapp.com", "telegram.me"}
RISKY_TLDS = {"xyz", "top", "click", "info", "link", "online", "site", "live", "buzz", "icu", "rest", "cfd", "sbs",
              "co", "cc", "tk", "ml", "ga", "cf", "gq", "work", "shop", "apk", "monster", "quest", "loan", "win"}
# Real brands: their name inside someone else's domain is impersonation
BRANDS = ["sbi", "hdfc", "icici", "axis", "kotak", "pnb", "baroda", "canara", "paytm", "phonepe", "gpay", "googlepay",
          "amazon", "amzn", "flipkart", "aadhaar", "aadhar", "uidai", "incometax", "epfo", "parivahan", "echallan",
          "indiapost", "netflix", "bluedart", "fedex", "dhl", "yono", "whatsapp", "airtel", "jio", "bsnl", "npci",
          "rbi", "irctc", "lic", "trai"]
# Generic words scammers put in domains
SCAM_WORDS = ["kyc", "bank", "refund", "reward", "verify", "update", "secure", "login", "account", "lpg",
              "electricity", "bijli", "gift", "loan", "claim", "redeem", "bonus", "prize", "support", "helpdesk"]


def _impersonates_brand(host: str) -> bool:
    labels = re.split(r"[.-]", host.replace("1", "l").replace("0", "o"))
    for brand in BRANDS:
        variants = {brand, brand.replace("l", "i"), brand.replace("i", "l")}  # netfIix → netfiix
        if any(v in host or any(lbl == v or (len(v) >= 4 and v in lbl) for lbl in labels) for v in variants):
            return True
    return False
URL_RE = re.compile(
    r"(?:https?://[^\s<>\"']+|www\.[^\s<>\"']+|\b(?:[a-z0-9-]+\.)+(?:com|in|co|net|org|xyz|top|click|info|link|ly|gl|"
    r"at|me|gd|online|site|live|io|apk|cc|tk|shop|win|loan|sbi|gy)\b(?:/[^\s<>\"']*)?)",
    re.IGNORECASE,
)


def _host(url: str) -> str:
    if not re.match(r"https?://", url, re.IGNORECASE):
        url = "http://" + url
    return (urlparse(url).hostname or "").lower().rstrip(".")


OFFICIAL_SHORTENERS = {"t.jio", "amzn.in", "amzn.to", "fkrt.it", "fkrt.cc", "myntr.in", "sbi.co.in"}


def _is_official(host: str) -> bool:
    if host in OFFICIAL_SHORTENERS or host.endswith(".jio"):  # .jio is Reliance Jio's own top-level domain
        return True
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def analyse_links(text: str) -> list[dict]:
    """Every link with its risk: official / chat / risky (with reason) / unknown."""
    links = []
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(".,);:!?")
        host = _host(url)
        if not host or re.fullmatch(r"\d+(\.\d+)?", host):  # "Rs.25" / "1.5" are not links
            if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", host or ""):
                continue
        tld = host.rsplit(".", 1)[-1]
        if _is_official(host):
            risk, reason = "official", None
        elif host in CHAT_LINKS:
            risk, reason = "chat", "Moves you to a private WhatsApp / Telegram chat"
        elif host in SHORTENERS:
            risk, reason = "risky", "Uses a short link that hides the real website"
        elif re.fullmatch(r"\d+\.\d+\.\d+\.\d+", host):
            risk, reason = "risky", "Link points to a raw IP address, not a real website"
        elif url.lower().split("?")[0].endswith(".apk") or ".apk." in host:
            risk, reason = "risky", "Link downloads an app file (.apk) — can steal your bank details"
        elif _impersonates_brand(host):
            risk, reason = "risky", "Fake website made to look like a bank / official site"
        elif any(w in host for w in SCAM_WORDS):
            risk, reason = "risky", "Link uses an unusual website address often used by scammers"
        elif tld in RISKY_TLDS:
            risk, reason = "risky", "Link uses an unusual website address often used by scammers"
        elif url.lower().startswith("http://"):
            risk, reason = "risky", "Link is not secure (http)"
        else:
            risk, reason = "unknown", None
        links.append({"url": url, "host": host, "risk": risk, "reason": reason})
    return links


# ─── Sentences that warn about fraud are not fraud ───────────────────────────
WARNING_CUES = re.compile(
    r"\b(never|do not|don'?t|dont|not to)\s+(share|disclose|reveal|give|tell|click|install|respond|reply|pay)\b"
    r"|\bnever (asks?|sends?|calls?|requests?)\b|\bwill never\b|\bbeware\b|\bstay safe\b|\breport (fraud|it|such)\b|\bignore if\b|\bbe careful\b"
    r"|साझा न|किसी को न बताएं|न बताएं|कभी नहीं माँग|कभी नहीं पूछ|सावधान|பகிர வேண்டாம்|பகிர்ந்து கொள்ள வேண்டாம்|ஜாக்கிரதை",
    re.IGNORECASE,
)


def _split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?।])\s+|\n+", text) if s.strip()]


# ─── Signals ─────────────────────────────────────────────────────────────────
# kind: "danger" (fraud on its own), "hook" (lure / threat), "ask" (what the scammer wants), "pressure"
def _p(*parts):
    return re.compile("|".join(parts), re.IGNORECASE)


CRED = (r"(otp|o\.t\.p|one.?time.?password|pin|upi pin|atm pin|cvv|password|passcode|credentials|login details|"
        r"card (number|details)|expiry|ओटीपी|पिन|पासवर्ड|यूपीआई पिन|கடவுச்சொல்|பின்)")
SHARE = (r"(share|tell|send|forward|give|provide|reply with|enter|type|confirm|read out|read (me|us)|batao|bata do|bataye|bhejo|bhej do|"
         r"de do|dijiye|share karo|बताएं|बताइए|बताओ|बता दें|भेजें|भेजो|शेयर|दें|दीजिए|பகிர|சொல்லுங்கள்|சொல்லவும்|அனுப்ப)")

SIGNALS = [
    # ── Dangerous on their own ──
    ("credentials", "danger", 1.0, "Asks for your OTP, PIN, CVV or password — banks NEVER ask for these", _p(
        rf"{SHARE}\W+(?:\w+\W+){{0,6}}{CRED}", rf"{CRED}\W+(?:\S+\s+){{0,6}}{SHARE}",
        r"\b(\d|six|4|6)[ -]?digit code\b", r"code (you|that you) (have )?(just )?received",
        r"(read|tell|give|share).{0,20}(the )?code (we|that we|i) (have )?(sent|just sent)",
        r"card number,? expiry", r"\bcvv\b")),
    ("pin_to_receive", "danger", 1.0, "Asks you to enter your PIN or scan a QR code to RECEIVE money — PIN is only needed to SEND money", _p(
        r"(enter|type|put).{0,30}\bpin\b.{0,40}(receive|get|credit)", r"(receive|get).{0,40}(enter|type).{0,15}\bpin\b",
        r"scan.{0,30}(qr|code).{0,60}(receive|get).{0,20}(money|payment|amount)", r"approve.{0,40}(request|collect).{0,40}receive",
        r"scan (this|the|my|our)? ?qr( code)?.{0,40}(approve|accept|claim|receive|get|verify)",
        r"approve (the |this )?(payment|collect|upi) request",
        r"(पाने|प्राप्त).{0,40}(पिन|यूपीआई).{0,20}(डालें|दर्ज)", r"(பெற).{0,40}(பின்|UPI PIN).{0,20}(உள்ளிட|போட)")),
    ("remote_access", "danger", 1.0, "Asks you to install a screen-sharing / remote-control app — the scammer can then empty your account", _p(
        r"\b(any ?desk|team ?viewer|quick ?support|rust ?desk|air ?droid|ammyy|ultraviewer|screen ?shar(e|ing) app)\b",
        r"remote (access|support|control) (app|software)")),
    ("gift_cards", "danger", 0.95, "Asks you to buy gift cards and send the codes — a common impersonation scam", _p(
        r"(buy|purchase|get).{0,40}gift ?cards?", r"gift ?cards?.{0,60}(send|share).{0,20}codes?")),
    ("extortion", "danger", 1.0, "Threatens to leak private photos / videos unless you pay — this is blackmail; report it", _p(
        r"(private|intimate|nude|personal) (video|photo|pic)", r"send it to (all )?your (contacts|family|friends)")),
    ("digital_arrest", "danger", 0.95, "Fake police / CBI / customs threat ('digital arrest') — officials never do this over calls or messages", _p(
        r"(illegal|drugs|narcotics|fake passports?|money laundering).{0,80}(parcel|aadhaar|seized|customs|account)",
        r"(fir|warrant|arrest(ed)?).{0,80}(video call|press \d|join|verification)", r"\bdigital arrest\b",
        r"(cbi|narcotics|customs) (officer|department|notice)",
        r"(illegal activit|involved in).{0,100}(video call|arrest)", r"(stay|remain) on (this|the) (video )?call",
        r"cyber (cell|crime branch).{0,80}(arrest|video call|illegal)")),
    ("pay_to_receive", "danger", 0.95, "Asks you to pay a fee to receive a prize, job, loan or parcel — genuine offers never do this", _p(
        r"(pay|send|deposit|transfer|bhejein|bhejo|jama|जमा|भेजें|செலுத்த).{0,50}(registration|processing|advance|customs|release|activation|security) (fee|charges?|amount|deposit|duty)",
        r"(registration|processing|advance|activation|delivery|redelivery|customs) (fee|charges?|duty).{0,60}(to|for) (receive|claim|get|start|release|activate)",
        r"(fee|charges?|शुल्क|फीस|கட்டணம்).{0,40}(to (claim|receive|get|start)|bhejein|jama karein|जमा करें|भेजें|செலுத்த)",
        r"(इनाम|पुरस्कार|inaam|prize|பரிசு).{0,80}(शुल्क|फीस|fee|charges|கட்டணம்)",
        r"invest.{0,30}(rs\.?|₹)\s*\d[\d,]*.{0,30}(get|receive).{0,20}(rs\.?|₹)\s*\d",
        r"(after|once|when) you pay.{0,40}(charges?|fee|amount|deposit)",
        r"(insurance|gst|tax|stamp|verification|file|transfer|clearance) (charges?|fee)",
        r"(register|registration|apply|enrol).{0,30}by paying")),
    # ── Hooks ──
    ("account_threat", "hook", 0.55, "Threatens to block or close your account / card / SIM to scare you", _p(
        r"(account|a/c|wallet|card|sim|netbanking|net banking|yono|upi|khata|खाता|கணக்கு).{0,50}(block|suspend|frozen|freez|clos|deactivat|lock|restrict|disabl|banned|on hold|inactive|band|बंद|ब्लॉक|निष्क्रिय|முடக்க|மூடப்ப|தடை|செயலிழ)",
        r"(block|suspend|frozen|freez|deactivat|lock|restrict|band|बंद|ब्लॉक|முடக்க).{0,30}(account|a/c|wallet|card|sim|khata|खाता|கணக்கு)",
        r"(whatsapp|number|mobile|connection).{0,30}(will be )?(banned|disconnected|deactivated)")),
    ("kyc", "hook", 0.45, "Fake KYC / PAN / Aadhaar update — banks do this at the branch or in the official app", _p(
        r"\b(e-?kyc|re-?kyc|kyc)\b", r"\bpan\b.{0,25}(update|link|not)", r"aadhaa?r.{0,30}(link|update|not linked)",
        r"केवाईसी", r"पैन.{0,40}(अपडेट|लिंक|निष्क्रिय|बंद)", r"(पैन|आधार) कार्ड")),
    ("utility_cut", "hook", 0.6, "Threatens to cut your electricity / gas connection — a common bill scam", _p(
        r"(electricity|power|bijli|gas|connection|meter|बिजली|गैस|மின்|மின்சார).{0,60}(disconnect|cut|kaat|काट|बंद|துண்டி)")),
    ("prize", "hook", 0.6, "Claims you won a prize, lottery or lucky draw — you cannot win something you did not enter", _p(
        r"\b(you (have )?won|winner|lottery|lucky draw|jackpot|kbc|kaun banega)\b", r"\bselected for .{0,30}(gift|prize|reward)",
        r"\b(jeeti|jeeta|jeete|inaam|lottery)\b", r"लॉटरी", r"इनाम", r"(आपने|आप).{0,30}जीत(ा|ी|े)",
        r"(chosen|selected) as (the )?winner", r"\bbumper (prize|offer|draw)\b",
        r"eligible for .{0,40}(scheme|subsidy|grant|bonus|benefit)",
        r"selected to (receive|get|win)", r"(\$|rs\.?|₹|inr|usd)\s?\d[\d,]*\s+(\w+\s+){0,2}gift ?(card|voucher)",
        r"verify your eligibility", r"exclusive offer.{0,60}(claim|redeem|within)", r"லாட்டரி", r"பரிசு", r"வென்ற")),
    ("refund_reward", "hook", 0.45, "Promises a refund, cashback or reward points to make you click", _p(
        r"\b(refund|cash ?back|reward points?|redeem|tax refund)\b", r"\bclaim (now|your)\b", r"कैशबैक|रिफंड|கேஷ்பேக்",
        r"(credited|deposited|sanctioned|released).{0,50}(as|under|from) .{0,30}(relief|fund|bonus|grant|scheme|prize|subsidy)",
        r"(relief fund|government grant|free money)")),
    ("job", "hook", 0.55, "Easy money / part-time job offer — task and job scams take your money", _p(
        r"\b(part[- ]?time|work from home|home based job|ghar baithe|data entry|online work|prepaid task|telegram task)\b",
        r"(rate|review|like) (hotels|products|videos|restaurants|movies)",
        r"liking (youtube )?videos", r"घर बैठे", r"वீட்டிலிருந்து.{0,30}சம்பா", r"வீட்டிலிருந்தே")),
    ("easy_money", "hook", 0.5, "Promises big daily earnings for little work — a sign of task / job scams", _p(
        r"earn.{0,30}(daily|per day|per hour|an hour|roz|a day|every day)", r"(daily|per day|per hour) (salary|income|earning|payout)",
        r"by (following|liking|subscribing|rating|reviewing) .{0,30}(accounts|videos|channels|pages|hotels|products)",
        r"(rs\.?|₹)?\s?\d[\d,]*\s?(-|to)\s?\d[\d,]*\s?(per day|daily|a day)", r"\b(kamaye|kamaiye|kamao)\b", r"कमाएं",
        r"रोज़?.{0,15}रुपये", r"தினமும்.{0,20}சம்பா")),
    ("investment", "hook", 0.6, "Promises guaranteed or very high returns — real investments never guarantee this", _p(
        r"double your money", r"(guaranteed|assured|fixed).{0,20}(returns?|profit)", r"\d+\s?% (daily|weekly|monthly)? ?(returns?|profit)",
        r"\b\d+x (returns?|profit)", r"get rich quick", r"trading bot",
        r"\b(crypto|bitcoin|forex) (trading|plan|investment)\b", r"(stock|share) (market )?tips", r"\bvip (whatsapp )?group\b")),
    ("loan_offer", "hook", 0.5, "Instant loan with no checks — fake loan apps steal data and money", _p(
        r"pre-?approved (personal )?loan", r"instant loan", r"without (any )?(documents|cibil|credit check)",
        r"loan.{0,30}(in \d+ minutes|instant approval)", r"\bloan (is )?(approved|sanctioned)\b")),
    ("legal_threat", "hook", 0.55, "Threatens police, legal action or penalties to frighten you", _p(
        r"\b(legal action|police case|court case|arrest|warrant|penalty)\b",
        r"\bfir\b.{0,30}(registered|lodged|filed|against)", r"final notice")),
    ("delivery", "hook", 0.4, "Fake parcel / delivery problem", _p(
        r"(parcel|package|shipment|order).{0,60}(could not be delivered|on hold|stuck|undelivered|held|seized)",
        r"\bredelivery\b", r"update (your )?address")),
    ("family_emergency", "hook", 0.55, "Pretends to be a family member in trouble asking for money", _p(
        r"\bhi (mum|mom|dad|papa|maa)\b", r"\b(this is )?my new number\b", r"my phone (broke|is broken|got lost)",
        r"\bi am in trouble\b", r"don'?t call me", r"\b(stuck|stranded) (at|in)\b",
        r"^\W*(hi |hello )?(mum|mom|mummy|maa|dad|papa|daddy)\b", r"my phone (is not working|is dead|stopped working)",
        r"(my )?friend'?s (phone|number|mobile)",
        r"(lost|taken|stolen|snatched) my (wallet|phone|bag|purse)", r"will (return|pay you back|give it back)( it)? (tomorrow|soon|later)")),
    ("account_problem", "hook", 0.45, "Claims a problem with your account or payment to make you act", _p(
        r"unusual (login|activity)", r"suspicious activity", r"payment (has )?failed", r"(account|card).{0,20}(has been )?locked",
        r"verify your (identity|account)", r"technical (glitch|problem|issue)", r"(card|debit card) will expire",
        r"failed login", r"billing (problem|issue)", r"update (your )?payment (info|information|details|method)")),
    ("impersonation", "hook", 0.35, "Claims to be from your bank or an official office", _p(
        r"calling from .{0,20}(bank|sbi|head office)", r"\b(head office|kyc officer|electricity officer|bank officer|customer care executive)\b",
        r"income tax department", r"lottery department")),
    # ── Asks ──
    ("call_number", "ask", 0.45, "Asks you to call or WhatsApp an unknown number", _p(
        r"(call|contact|whatsapp|dial|ring|message|sms|reach)\b.{0,50}(\+?91[\s-]?)?[6-9]\d{9}\b",
        r"(\+?91[\s-]?)?[6-9]\d{9}.{0,30}(call|whatsapp|contact)", r"\bpress \d\b", r"\bwhatsapp (us|karein|me)\b",
        r"call karein|कॉल करें|फोन करें|संपर्क करें|व्हाट्सएप|அழைக்க|தொடர்பு கொள்ள|வாட்ஸ்அப்",
        r"contact (our|the) (officer|executive|agent|manager)",
        r"(telegram|whatsapp|instagram|insta)\s+(@|id\s*:?\s*@?)\w{3,}", r"(contact|message|dm)\s+(hr|us|me|agent)\s+on\s+(telegram|whatsapp|instagram)")),
    ("phone_number", "ask", 0.3, "Gives a private mobile number to contact", _p(r"(?<!\d)(\+?91[\s-]?)?[6-9]\d{9}(?!\d)")),
    ("reply_details", "ask", 0.5, "Asks you to send personal or bank details", _p(
        r"(send|reply with|share|provide).{0,30}(bank details|account (number|details)|name,? address|aadhaar|pan (number|card))",
        r"send (your )?details")),
    ("payment", "ask", 0.45, "Asks you to pay or send money", _p(
        r"\b(pay|paying|send money|transfer|deposit)\b.{0,40}(rs\.?|₹|inr|now|immediately|today|on this|to this)",
        r"\b(send|transfer)\s+(me\s+)?(rs\.?|₹|inr)?\s?\d[\d,]*\s*(rs|rupees|/-)?",
        r"\b(send|pay|transfer)\b.{0,40}\b(on|via|through|using) (gpay|google pay|phonepe|paytm|upi)\b",
        r"send it to this account", r"(this|my) upi id", r"(rupaye|रुपये|ரூபாய்).{0,30}(bhejein|bhejo|jama|जमा|भेजें|செலுத்த)",
        r"(bhejein|जमा करें|भेजें)")),
    ("join_group", "ask", 0.45, "Asks you to join a Telegram / WhatsApp group", _p(
        r"join (our|the|this)? ?(telegram|whatsapp|vip)", r"telegram (group|channel)", r"\bjoin (now|today|us|immediately)\b",
        r"\binvest (now|today|in our)\b", r"\b(register|sign up|enrol) now\b")),
    ("click_link", "ask", 0.3, "Asks you to click a link", _p(
        r"click (here|the link|this link|below|now)", r"click to (accept|receive|claim|get|activate|verify|update)",
        r"(लिंक|link) पर क्लिक", r"क्लिक करें", r"கிளிக் செய்ய", r"(update|verify|login|redeem|claim|link) (now )?(at|on|by|here|via)\b")),
    # ── Pressure ──
    ("urgency", "pressure", 0.25, "Creates urgency so you do not stop to think", _p(
        r"within (the )?(next )?\d+ ?(hours?|hrs?|minutes?|mins?)", r"\b(immediately|urgent(ly)?|right now|act now|last chance|before midnight)\b",
        r"\b(today|tonight)\b", r"\b(turant|jaldi|aaj raat)\b", r"तुरंत|जल्दी|आज रात|अभी", r"உடனடியாக|இன்று இரவு|உடனே")),
]

SCAM_TYPES = [  # first matching signal names the scam
    ("upi_binding", "UPI SIM-binding hijack"), ("duplicate_ref", "Fake credit alert ('sent by mistake') scam"),
    ("alert_from_mobile", "Fake credit alert ('sent by mistake') scam"), ("mistake_return", "Fake credit alert ('sent by mistake') scam"),
    ("credentials", "OTP / PIN theft"), ("pin_to_receive", "UPI 'receive money' scam"), ("remote_access", "Remote-access app scam"),
    ("extortion", "Blackmail / sextortion"), ("digital_arrest", "Fake police / 'digital arrest' scam"),
    ("gift_cards", "Gift card scam"), ("kyc", "Fake KYC update scam"), ("prize", "Fake lottery / prize scam"),
    ("job", "Fake job / task scam"), ("investment", "Investment scam"), ("loan_offer", "Fake loan scam"),
    ("utility_cut", "Fake electricity / bill scam"), ("family_emergency", "Fake family emergency"),
    ("delivery", "Fake delivery / courier scam"), ("refund_reward", "Fake refund / reward scam"),
    ("account_threat", "Account-block scare scam"), ("account_problem", "Phishing (fake account problem)"),
    ("legal_threat", "Threat / intimidation scam"), ("pay_to_receive", "Advance-fee scam"),
]


ALERT_RE = re.compile(
    r"(rs\.?|inr|₹)\s?([\d,]+(?:\.\d+)?)\s*(?:has been\s+|is\s+)?(credited|debited|received|deposited)", re.IGNORECASE)
REF_RE = re.compile(r"(?:upi\s*)?ref(?:erence)?\.?\s*(?:no\.?|number)?\s*:?\s*(\d{9,})", re.IGNORECASE)
def _personal_sender(text: str) -> bool:
    """A line near the top that is only a mobile number: the SMS came from a person, not a bank sender ID."""
    for line in text.splitlines()[:8]:
        line = re.sub(r"(?i)^\W*texting with\s*", "", line.strip())
        digits = re.sub(r"[\s()+\-.>]", "", line)
        if re.fullmatch(r"(91)?[6-9]\d{9}", digits):
            return True
    return False


UPI_BINDING_RE = re.compile(r"\b(sbiupi|upi\s*confidential)\b|confidential\s*:?\s*don'?t share if asked", re.IGNORECASE)
ENCODED_TOKEN_RE = re.compile(r"(%2[0-9a-f]|%21)|[A-Za-z0-9+/]{24,}", re.IGNORECASE)


def _message_level_signals(text: str) -> list[dict]:
    """Scam tricks recognised from the whole message (and its sender line), not from one sentence."""
    hits = []
    alerts = ALERT_RE.findall(text)
    if alerts:
        refs = REF_RE.findall(text)
        amounts = {a[1].replace(",", "") for a in alerts}
        if len(refs) >= 2 and len(set(refs)) < len(refs) and len(amounts) > 1:
            hits.append({"name": "duplicate_ref", "kind": "danger", "weight": 1.0,
                         "indicator": "Fake credit alerts: the same UPI reference number is used for different amounts"})
        if _personal_sender(text):
            hits.append({"name": "alert_from_mobile", "kind": "danger", "weight": 0.95,
                         "indicator": "Bank credit / debit alerts come from bank sender IDs (like AX-SBIINB), never from a personal mobile number"})
    if re.search(r"(sent|credited|transferred|paid)\s+(to you\s+)?(by|in)\s+mistake|galti se", text, re.IGNORECASE) \
            and re.search(r"(return|send (it )?back|refund|wapas|वापस)", text, re.IGNORECASE):
        hits.append({"name": "mistake_return", "kind": "danger", "weight": 1.0,
                     "indicator": "'Money sent by mistake, please return it' — check your bank app first; the credit is usually fake"})
    if UPI_BINDING_RE.search(text) and ENCODED_TOKEN_RE.search(text):
        hits.append({"name": "upi_binding", "kind": "danger", "weight": 1.0,
                     "indicator": "Secret UPI registration code — whoever gets it can link YOUR bank account to THEIR phone. Never forward it"})
    return hits


def detect(text: str) -> dict:
    """Return the matched signals, link analysis and the classification."""
    sentences = [s for s in _split_sentences(text) if not WARNING_CUES.search(s)]
    active = " ".join(sentences)

    hits = _message_level_signals(text or "")
    for name, kind, weight, indicator, pattern in SIGNALS:
        if active and pattern.search(active):
            hits.append({"name": name, "kind": kind, "weight": weight, "indicator": indicator})

    links = analyse_links(active)
    risky_links = [l for l in links if l["risk"] == "risky"]
    for reason in dict.fromkeys(l["reason"] for l in risky_links):
        hits.append({"name": "risky_link", "kind": "ask", "weight": 0.6, "indicator": reason})
    if any(l["reason"] == "Fake website made to look like a bank / official site" for l in risky_links):
        hits.append({"name": "fake_site", "kind": "danger", "weight": 0.9,
                     "indicator": "Fake website made to look like a bank / official site"})
    if any(".apk" in (l["reason"] or "") for l in risky_links):
        hits.append({"name": "apk", "kind": "danger", "weight": 1.0,
                     "indicator": "Link downloads an app file (.apk) — can steal your bank details"})
    if any(l["risk"] == "chat" for l in links):
        hits.append({"name": "chat_link", "kind": "ask", "weight": 0.4, "indicator": "Moves you to a private WhatsApp / Telegram chat"})
    if any(l["risk"] == "unknown" for l in links) and not any(h["name"] == "risky_link" for h in hits):
        hits.append({"name": "link", "kind": "ask", "weight": 0.25, "indicator": "Contains a link to an unknown website — do not open it"})
    if links and all(l["risk"] == "official" for l in links):
        hits = [h for h in hits if h["name"] != "click_link"]  # "update at https://www.incometax.gov.in" is fine

    kinds = {h["kind"] for h in hits}
    danger = [h for h in hits if h["kind"] == "danger"]
    hooks = [h for h in hits if h["kind"] == "hook"]
    asks = [h for h in hits if h["kind"] == "ask"]
    # Weak lures (a KYC / Aadhaar / refund / delivery mention) are normal in genuine messages too:
    # they only count together with an ask, time pressure or a second lure.
    strong_hooks = [h for h in hooks if h["name"] != "impersonation"]
    standalone_hooks = [h for h in strong_hooks if h["weight"] >= 0.5]
    total = sum(h["weight"] for h in hits)

    if danger:
        classification = "fraud"
        likelihood = min(0.99, 0.88 + 0.03 * (len(hits) - 1))
    elif (strong_hooks and asks) or len({h["name"] for h in standalone_hooks}) >= 2:
        classification = "fraud"
        likelihood = min(0.97, 0.7 + 0.05 * (len(hits) - 2))
    elif risky_links or (strong_hooks and ("pressure" in kinds or len(strong_hooks) >= 2)):
        classification = "suspicious"
        likelihood = min(0.6, 0.4 + 0.05 * len(hits))
    elif standalone_hooks or (asks and "pressure" in kinds):
        classification = "suspicious"
        likelihood = 0.35
    else:
        classification = "safe"
        likelihood = min(0.15, 0.03 + 0.04 * total)

    order = {"danger": 0, "hook": 1, "ask": 2, "pressure": 3}
    hits.sort(key=lambda h: (order[h["kind"]], -h["weight"]))
    names = {h["name"] for h in hits}
    scam_type = next((label for key, label in SCAM_TYPES if key in names), None)
    if classification == "safe":
        scam_type = None
    elif scam_type is None:
        scam_type = "Phishing link" if risky_links else "Suspicious message"

    return {
        "classification": classification,
        "likelihood": round(likelihood, 3),
        "signals": hits,
        "links": links,
        "scam_type": scam_type,
    }
