"""Notary Sahayak rules: document kinds + templates (English / Hindi / Marathi, filled by CODE from the party's facts; a missing
fact is a [blank], never a guess), Notaries Rules 1956 Rule 10 fee caps (2014 table, as read), Form XV register columns,
stamp value ONLY from her own state rate table, e-stamp steps, apostille / attestation steps (MEA), checks.

Nothing here is legal advice: every document carries "Draft - vakil se pakka karwaiye" until her final-print tap."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

NOT_ADVICE = "Draft / jaankari hai, kanooni salah nahi: vakil se pakka karwaiye."
NEVER = [
    "Notarise / sign / seal / stamp karna sirf aapka kaam: Hoola sirf kaagaz taiyaar karta hai.",
    "Stamp ki rakam sirf aapki state rate table se; table mein nahi to khaali [stamp ₹ ?] - kabhi andaaza nahi.",
    "Aadhaar / PAN / ID number kabhi document ke record mein nahi: sirf Pehchaan Locker ka {id:...} reference aur masked number.",
    "Paise Hoola nahi leta / bhejta: fee aap leti hain, Hoola sirf receipt aur register likhta hai.",
    "Final print sirf aapke tap se (card + hash); badla hua document = naya card.",
    "e-Stamp / GRAS / franking aur MEA apostille aap ya party khud official portal / agency par karte hain.",
]

LANGS = {"en": "English", "hi": "हिन्दी", "mr": "मराठी"}

# ---------------------------------------------------------------- Rule 10(1) Notaries Rules 1956 (2014 table, as published by DoLA)
FEE_SOURCE = ("Notaries Rules 1956 Rule 10(1) as published by the Department of Legal Affairs "
              "(legalaffairs.gov.in/sites/default/files/notaries-rules-1956.pdf, read 23 Oct 2026); naya notification aaye to Niyam mein badliye.")
ACTS: dict[str, dict[str, Any]] = {
    "affidavit": {"label": "Affidavit / oath (Rule 10(1)(g))", "cap": 35.0},
    "attest": {"label": "Verify / authenticate / attest an instrument (Rule 10(1)(e))", "cap": 35.0},
    "outside_prepare": {"label": "Instrument for use outside India - preparing (Rule 10(1)(h))", "cap": 200.0},
    "outside_attest": {"label": "Instrument for use outside India - attesting (Rule 10(1)(i))", "cap": 200.0},
    "translation": {"label": "Translating and verifying a translation (Rule 10(1)(j))", "cap": 100.0},
    "true_copy": {"label": "True copy certify (Rule 10(1)(l): 10 per page, min 20)", "cap": None, "per_page": 10.0, "min": 20.0},
    "noting": {"label": "Noting an instrument (Rule 10(1)(a))", "cap": None},
    "protest": {"label": "Protesting an instrument (Rule 10(1)(b))", "cap": None},
    "other": {"label": "Other notarial act (Rule 10(1)(m): govt jo tay kare)", "cap": None},
}
# Form XV (Notarial Register) columns, Rule 11(2)
FORM_XV = ["Serial No.", "Date", "Name of notarial act", "Name of executant / person concerned with full address",
           "Contents of document", "Prescribed stamp affixed", "Fee charged", "Receipt Book Serial No.",
           "Signature of person concerned", "Signature of Notary"]

# ---------------------------------------------------------------- document kinds
# stamp: key looked up in HER rate table; act: the notarial act it usually needs; fields: (key, label, required)
KINDS: dict[str, dict[str, Any]] = {
    "aff_name_change": {"label": "Affidavit - naam badalna", "stamp": "affidavit", "act": "affidavit", "group": "affidavit",
                        "fields": [("old_name", "Purana naam (documents mein)", True), ("new_name", "Naya naam", True),
                                   ("reason", "Kyun (shaadi / galti / apni marzi...)", True), ("documents", "Kin documents mein purana naam", False)]},
    "aff_address": {"label": "Affidavit - pata (address proof)", "stamp": "affidavit", "act": "affidavit", "group": "affidavit",
                    "fields": [("since", "Kab se rehte hain", True), ("purpose", "Kis kaam ke liye", True),
                               ("previous_address", "Pichhla pata", False)]},
    "aff_gap_year": {"label": "Affidavit - gap year", "stamp": "affidavit", "act": "affidavit", "group": "affidavit",
                     "fields": [("from_year", "Gap kab se (saal / mahina)", True), ("to_year", "Gap kab tak", True),
                                ("activity", "Us dauran kya kiya", True), ("purpose", "Kis college / sanstha ke liye", True)]},
    "aff_income": {"label": "Affidavit - aay (income)", "stamp": "affidavit", "act": "affidavit", "group": "affidavit",
                   "fields": [("annual_income", "Saalana aay (₹)", True), ("source", "Aay ka zariya", True),
                              ("year", "Kis saal ki aay (FY)", True), ("purpose", "Kis kaam ke liye", True)]},
    "aff_lost_document": {"label": "Affidavit - document kho gaya", "stamp": "affidavit", "act": "affidavit", "group": "affidavit",
                          "fields": [("document", "Kaunsa document", True), ("issuer", "Kisne diya tha", True),
                                     ("lost_on", "Kab khoya", True), ("lost_place", "Kahan khoya", True),
                                     ("police_ref", "Police / lost report no.", True), ("doc_ref", "Document ka number (ho to)", False)]},
    "aff_general": {"label": "Affidavit - general", "stamp": "affidavit", "act": "affidavit", "group": "affidavit",
                    "fields": [("statements", "Kya bayaan hai (har line ek baat)", True), ("purpose", "Kis kaam ke liye", False)]},
    "declaration": {"label": "Declaration", "stamp": "declaration", "act": "attest", "group": "declaration",
                    "fields": [("statements", "Kya ghoshna hai (har line ek baat)", True), ("purpose", "Kis kaam ke liye", True)]},
    "self_declaration": {"label": "Self-declaration (swa-ghoshna)", "stamp": "self_declaration", "act": "", "group": "declaration",
                         "fields": [("statements", "Kya ghoshna hai (har line ek baat)", True), ("purpose", "Kis kaam ke liye", True)]},
    "rent_summary": {"label": "Rent / leave & licence summary", "stamp": "rent_summary", "act": "attest", "group": "rent",
                     "fields": [("licensor", "Maalik (licensor)", True), ("licensee", "Kirayedar (licensee)", True),
                                ("premises", "Jagah ka pata", True), ("start", "Kab se", True), ("months", "Kitne mahine", True),
                                ("fee", "Mahine ka kiraya / fee (₹)", True), ("deposit", "Deposit (₹)", True),
                                ("agreement_kind", "Agreement kaisa (leave & licence / rent)", False)]},
    "poa_general": {"label": "Power of attorney - general", "stamp": "poa_general", "act": "attest", "group": "poa",
                    "fields": [("attorney_name", "Attorney ka naam", True), ("attorney_relation", "Attorney ka rishta / pita ka naam", False),
                               ("attorney_address", "Attorney ka pata", True), ("powers", "Kaun se kaam (har line ek)", True),
                               ("property", "Kis property / account ke liye (ho to)", False)]},
    "poa_special": {"label": "Power of attorney - special (ek kaam)", "stamp": "poa_special", "act": "attest", "group": "poa",
                    "fields": [("attorney_name", "Attorney ka naam", True), ("attorney_relation", "Attorney ka rishta / pita ka naam", False),
                               ("attorney_address", "Attorney ka pata", True), ("act", "Sirf kaunsa ek kaam", True),
                               ("valid_till", "Kab tak (ho to)", False)]},
    "indemnity": {"label": "Indemnity bond", "stamp": "indemnity", "act": "attest", "group": "indemnity",
                  "fields": [("indemnified", "Kisko indemnity (bank / society / company)", True),
                             ("matter", "Kis baat ke liye (duplicate certificate, payment...)", True), ("amount", "Rakam (₹, ho to)", False)]},
    "noc": {"label": "NOC (anapatti)", "stamp": "noc", "act": "attest", "group": "noc",
            "fields": [("to_whom", "Kisko NOC", True), ("subject", "Kis cheez / jagah ke baare mein", True),
                       ("purpose", "Kis kaam ke liye", True)]},
}
PARTY_FIELDS = [("name", "Naam", True), ("relation", "S/o, D/o, W/o (so / do / wo)", True), ("relative", "Pita / pati ka naam", True),
                ("age", "Umar", True), ("occupation", "Kaam / vyavsay", False), ("address", "Pura pata", True),
                ("gender", "m / f", False), ("phone", "Mobile", False)]

TITLES = {
    "aff_name_change": {"en": "AFFIDAVIT (CHANGE OF NAME)", "hi": "शपथपत्र (नाम परिवर्तन)", "mr": "प्रतिज्ञापत्र (नाव बदल)"},
    "aff_address": {"en": "AFFIDAVIT (PROOF OF RESIDENCE)", "hi": "शपथपत्र (निवास प्रमाण)", "mr": "प्रतिज्ञापत्र (रहिवास पुरावा)"},
    "aff_gap_year": {"en": "AFFIDAVIT (GAP IN EDUCATION)", "hi": "शपथपत्र (शिक्षा में अंतराल)", "mr": "प्रतिज्ञापत्र (शिक्षणातील खंड)"},
    "aff_income": {"en": "AFFIDAVIT (DECLARATION OF INCOME)", "hi": "शपथपत्र (आय घोषणा)", "mr": "प्रतिज्ञापत्र (उत्पन्न घोषणा)"},
    "aff_lost_document": {"en": "AFFIDAVIT (LOSS OF DOCUMENT)", "hi": "शपथपत्र (दस्तावेज़ गुम होना)", "mr": "प्रतिज्ञापत्र (कागदपत्र हरवणे)"},
    "aff_general": {"en": "AFFIDAVIT", "hi": "शपथपत्र", "mr": "प्रतिज्ञापत्र"},
    "declaration": {"en": "DECLARATION", "hi": "घोषणापत्र", "mr": "घोषणापत्र"},
    "self_declaration": {"en": "SELF-DECLARATION", "hi": "स्व-घोषणा पत्र", "mr": "स्वयंघोषणापत्र"},
    "rent_summary": {"en": "SUMMARY OF LEAVE AND LICENCE / RENT ARRANGEMENT", "hi": "किराया / लीव एंड लाइसेंस व्यवस्था का सारांश",
                     "mr": "भाडे / लिव्ह अँड लायसन्स व्यवस्थेचा सारांश"},
    "poa_general": {"en": "GENERAL POWER OF ATTORNEY", "hi": "सामान्य मुख्तारनामा (जनरल पावर ऑफ अटॉर्नी)", "mr": "सर्वसाधारण मुखत्यारपत्र"},
    "poa_special": {"en": "SPECIAL POWER OF ATTORNEY", "hi": "विशेष मुख्तारनामा (स्पेशल पावर ऑफ अटॉर्नी)", "mr": "विशेष मुखत्यारपत्र"},
    "indemnity": {"en": "INDEMNITY BOND", "hi": "क्षतिपूर्ति बंधपत्र (इंडेम्निटी बॉन्ड)", "mr": "नुकसानभरपाई बंधपत्र (इंडेम्निटी बॉंड)"},
    "noc": {"en": "NO OBJECTION CERTIFICATE", "hi": "अनापत्ति प्रमाणपत्र", "mr": "ना हरकत प्रमाणपत्र"},
}

REL = {"so": {"en": "son of", "hi": "पुत्र", "mr": "मुलगा"}, "do": {"en": "daughter of", "hi": "पुत्री", "mr": "मुलगी"},
       "wo": {"en": "wife of", "hi": "पत्नी", "mr": "पत्नी"}, "ho": {"en": "husband of", "hi": "पति", "mr": "पती"}}

# intro line for the person who signs (deponent / declarant / principal / executant)
INTRO = {
    "affidavit": {
        "en": "I, {name}, {rel} {relative}, aged about {age} years, occupation {occupation}, residing at {address}, do hereby solemnly affirm and state as under:",
        "hi": "मैं, {name}, {rel} {relative}, उम्र लगभग {age} वर्ष, व्यवसाय {occupation}, निवासी {address}, सत्यनिष्ठा से प्रतिज्ञान {karta} हूँ और निम्नलिखित कथन {karta} हूँ:",
        "mr": "मी, {name}, {rel} {relative}, वय सुमारे {age} वर्षे, व्यवसाय {occupation}, राहणार {address}, याद्वारे सत्यप्रतिज्ञेवर लिहून {deto} की:"},
    "declaration": {
        "en": "I, {name}, {rel} {relative}, aged about {age} years, residing at {address}, do hereby declare as under:",
        "hi": "मैं, {name}, {rel} {relative}, उम्र लगभग {age} वर्ष, निवासी {address}, निम्नलिखित घोषणा {karta} हूँ:",
        "mr": "मी, {name}, {rel} {relative}, वय सुमारे {age} वर्षे, राहणार {address}, याद्वारे घोषित {karto} की:"},
    "poa": {
        "en": "KNOW ALL MEN BY THESE PRESENTS that I, {name}, {rel} {relative}, aged about {age} years, residing at {address} (hereinafter called the \"Principal\"), do hereby appoint, nominate and constitute {attorney_name}{attorney_relation_part}, residing at {attorney_address} (hereinafter called the \"Attorney\"), as my lawful attorney to do the following acts in my name and on my behalf:",
        "hi": "सर्वसाधारण को ज्ञात हो कि मैं, {name}, {rel} {relative}, उम्र लगभग {age} वर्ष, निवासी {address} (आगे \"प्रधान\" कहा गया), {attorney_name}{attorney_relation_part}, निवासी {attorney_address} (आगे \"मुख्तार\" कहा गया) को अपना वैध मुख्तार नियुक्त {karta} हूँ, जो मेरे नाम से और मेरी ओर से निम्नलिखित कार्य करेंगे:",
        "mr": "सर्वांना कळविण्यात येते की मी, {name}, {rel} {relative}, वय सुमारे {age} वर्षे, राहणार {address} (यापुढे \"मुख्य\"), {attorney_name}{attorney_relation_part}, राहणार {attorney_address} (यापुढे \"मुखत्यार\") यांना माझे कायदेशीर मुखत्यार म्हणून नेमत {aahe} आणि ते माझ्या नावाने व माझ्या वतीने खालील कामे करतील:"},
    "indemnity": {
        "en": "I, {name}, {rel} {relative}, aged about {age} years, residing at {address} (hereinafter called the \"Indemnifier\"), execute this Indemnity Bond in favour of {indemnified} (hereinafter called the \"Indemnified\").",
        "hi": "मैं, {name}, {rel} {relative}, उम्र लगभग {age} वर्ष, निवासी {address} (आगे \"क्षतिपूर्तिकर्ता\"), यह क्षतिपूर्ति बंधपत्र {indemnified} (आगे \"क्षतिपूरित\") के पक्ष में निष्पादित {karta} हूँ।",
        "mr": "मी, {name}, {rel} {relative}, वय सुमारे {age} वर्षे, राहणार {address} (यापुढे \"नुकसानभरपाई देणार\"), हे बंधपत्र {indemnified} (यापुढे \"नुकसानभरपाई घेणार\") यांच्या नावे लिहून {deto}."},
    "noc": {
        "en": "To, {to_whom}\n\nI, {name}, {rel} {relative}, aged about {age} years, residing at {address}, hereby state as under:",
        "hi": "प्रति, {to_whom}\n\nमैं, {name}, {rel} {relative}, उम्र लगभग {age} वर्ष, निवासी {address}, निम्नलिखित कथन {karta} हूँ:",
        "mr": "प्रति, {to_whom}\n\nमी, {name}, {rel} {relative}, वय सुमारे {age} वर्षे, राहणार {address}, याद्वारे नमूद {karto} की:"},
    "rent": {
        "en": "This is a summary, prepared for reference, of the arrangement between the Licensor and the Licensee named below. It is not the agreement itself.",
        "hi": "यह नीचे लिखे मालिक (लाइसेंसर) और किरायेदार (लाइसेंसी) के बीच की व्यवस्था का संदर्भ हेतु सारांश है। यह स्वयं अनुबंध नहीं है।",
        "mr": "हा खाली नमूद मालक (लायसन्सर) व भाडेकरू (लायसन्सी) यांच्यातील व्यवस्थेचा संदर्भासाठी सारांश आहे. हा स्वतः करार नाही."},
}
GROUP_INTRO = {"affidavit": "affidavit", "declaration": "declaration", "poa": "poa", "indemnity": "indemnity", "noc": "noc", "rent": "rent"}

# numbered paragraphs per kind (lists: "{statements}" / "{powers}" expand into one paragraph per line)
BODY: dict[str, dict[str, list[str]]] = {
    "aff_name_change": {
        "en": ["That my name has been recorded as {old_name} in {documents}.",
               "That I have changed my name from {old_name} to {new_name}. Reason: {reason}.",
               "That {old_name} and {new_name} are the names of one and the same person, that is, myself.",
               "That henceforth I shall be known as {new_name} for all purposes."],
        "hi": ["यह कि मेरा नाम {documents} में {old_name} दर्ज है।",
               "यह कि मैंने अपना नाम {old_name} से बदलकर {new_name} कर लिया है। कारण: {reason}।",
               "यह कि {old_name} और {new_name} एक ही व्यक्ति, अर्थात मेरे ही नाम हैं।",
               "यह कि अब से सभी कार्यों के लिए मुझे {new_name} नाम से जाना जाए।"],
        "mr": ["माझे नाव {documents} मध्ये {old_name} असे नोंदवलेले आहे.",
               "मी माझे नाव {old_name} वरून बदलून {new_name} असे केले आहे. कारण: {reason}.",
               "{old_name} व {new_name} ही एकाच व्यक्तीची, म्हणजे माझीच नावे आहेत.",
               "यापुढे सर्व कामांसाठी मला {new_name} या नावाने ओळखले जावे."]},
    "aff_address": {
        "en": ["That I am residing at the above-mentioned address since {since}.", "That my previous address was {previous_address}.",
               "That this affidavit is made for the purpose of {purpose}."],
        "hi": ["यह कि मैं उपरोक्त पते पर {since} से निवास कर {raha} हूँ।", "यह कि मेरा पिछला पता {previous_address} था।",
               "यह कि यह शपथपत्र {purpose} हेतु दिया जा रहा है।"],
        "mr": ["मी वरील पत्त्यावर {since} पासून राहत आहे.", "माझा पूर्वीचा पत्ता {previous_address} होता.",
               "हे प्रतिज्ञापत्र {purpose} या कामासाठी देत आहे."]},
    "aff_gap_year": {
        "en": ["That there was a gap in my education from {from_year} to {to_year}.", "That during this period I was {activity}.",
               "That I was not involved in any illegal activity during this period.",
               "That this affidavit is made for submission to {purpose}."],
        "hi": ["यह कि {from_year} से {to_year} तक मेरी पढ़ाई में अंतराल रहा।", "यह कि इस अवधि में मैं {activity}।",
               "यह कि इस अवधि में मैं किसी भी गैरकानूनी गतिविधि में शामिल नहीं {tha}।",
               "यह कि यह शपथपत्र {purpose} में जमा करने हेतु दिया जा रहा है।"],
        "mr": ["{from_year} ते {to_year} या काळात माझ्या शिक्षणात खंड पडला.", "या काळात मी {activity}.",
               "या काळात मी कोणत्याही बेकायदेशीर कृत्यात सहभागी {navhato}.",
               "हे प्रतिज्ञापत्र {purpose} येथे सादर करण्यासाठी देत आहे."]},
    "aff_income": {
        "en": ["That my annual income for the year {year} from all sources is {annual_income}.",
               "That the source of my income is {source}.", "That this affidavit is made for the purpose of {purpose}."],
        "hi": ["यह कि वर्ष {year} में मेरी सभी स्रोतों से वार्षिक आय {annual_income} है।",
               "यह कि मेरी आय का स्रोत {source} है।", "यह कि यह शपथपत्र {purpose} हेतु दिया जा रहा है।"],
        "mr": ["वर्ष {year} मधील माझे सर्व मार्गांनी मिळणारे वार्षिक उत्पन्न {annual_income} आहे.",
               "माझ्या उत्पन्नाचे साधन {source} आहे.", "हे प्रतिज्ञापत्र {purpose} या कामासाठी देत आहे."]},
    "aff_lost_document": {
        "en": ["That my {document} issued by {issuer}{doc_ref_part} has been lost on {lost_on} at {lost_place}.",
               "That I have reported the loss to the police; report / reference number: {police_ref}.",
               "That the said document has not been pledged, sold or handed over to anyone, and if it is found I shall return it to {issuer}.",
               "That this affidavit is made to obtain a duplicate of the said document."],
        "hi": ["यह कि {issuer} द्वारा जारी मेरा {document}{doc_ref_part} दिनांक {lost_on} को {lost_place} में गुम हो गया है।",
               "यह कि मैंने इसकी सूचना पुलिस को दी है; रिपोर्ट / संदर्भ क्रमांक: {police_ref}।",
               "यह कि उक्त दस्तावेज़ न गिरवी रखा गया है, न बेचा गया है, न किसी को सौंपा गया है; मिलने पर मैं इसे {issuer} को लौटा {dunga}।",
               "यह कि यह शपथपत्र उक्त दस्तावेज़ की दूसरी प्रति (डुप्लिकेट) प्राप्त करने हेतु दिया जा रहा है।"],
        "mr": ["{issuer} यांनी दिलेले माझे {document}{doc_ref_part} दिनांक {lost_on} रोजी {lost_place} येथे हरवले आहे.",
               "याबाबत मी पोलिसांना कळवले आहे; अहवाल / संदर्भ क्रमांक: {police_ref}.",
               "सदर कागदपत्र गहाण ठेवलेले, विकलेले किंवा कोणालाही दिलेले नाही; सापडल्यास मी ते {issuer} यांना परत करीन.",
               "हे प्रतिज्ञापत्र सदर कागदपत्राची दुसरी प्रत (डुप्लिकेट) मिळण्यासाठी देत आहे."]},
    "aff_general": {"en": ["That {statements}.", "That this affidavit is made for the purpose of {purpose}."],
                    "hi": ["यह कि {statements}।", "यह कि यह शपथपत्र {purpose} हेतु दिया जा रहा है।"],
                    "mr": ["{statements}.", "हे प्रतिज्ञापत्र {purpose} या कामासाठी देत आहे."]},
    "declaration": {"en": ["{statements}.", "This declaration is made for the purpose of {purpose}."],
                    "hi": ["{statements}।", "यह घोषणा {purpose} हेतु की जा रही है।"],
                    "mr": ["{statements}.", "ही घोषणा {purpose} या कामासाठी करत आहे."]},
    "self_declaration": {"en": ["{statements}.", "This self-declaration is given for {purpose}. I understand that a false declaration may lead to action under law."],
                         "hi": ["{statements}।", "यह स्व-घोषणा {purpose} हेतु दी जा रही है। मैं {samajhta} हूँ कि झूठी घोषणा पर कानूनी कार्रवाई हो सकती है।"],
                         "mr": ["{statements}.", "ही स्वयंघोषणा {purpose} साठी देत आहे. खोटी घोषणा केल्यास कायदेशीर कारवाई होऊ शकते याची मला जाणीव आहे."]},
    "rent_summary": {
        "en": ["Licensor: {licensor}.", "Licensee: {licensee}.", "Premises: {premises}.",
               "Period: {months} months from {start} ({agreement_kind}).", "Monthly fee / rent: {fee}. Security deposit: {deposit}.",
               "The binding terms are those of the signed (and, where the law requires, registered) agreement; this summary does not replace it."],
        "hi": ["मालिक (लाइसेंसर): {licensor}।", "किरायेदार (लाइसेंसी): {licensee}।", "जगह: {premises}।",
               "अवधि: {start} से {months} महीने ({agreement_kind})।", "मासिक किराया / फीस: {fee}। सिक्योरिटी डिपॉज़िट: {deposit}।",
               "बाध्यकारी शर्तें हस्ताक्षरित (और जहाँ कानून कहे, पंजीकृत) अनुबंध की ही हैं; यह सारांश उसकी जगह नहीं लेता।"],
        "mr": ["मालक (लायसन्सर): {licensor}.", "भाडेकरू (लायसन्सी): {licensee}.", "जागा: {premises}.",
               "कालावधी: {start} पासून {months} महिने ({agreement_kind}).", "मासिक भाडे / फी: {fee}. अनामत रक्कम: {deposit}.",
               "बंधनकारक अटी सही केलेल्या (व कायद्याने आवश्यक तेथे नोंदणीकृत) करारातीलच आहेत; हा सारांश त्याची जागा घेत नाही."]},
    "poa_general": {
        "en": ["{powers}.", "Property / account concerned: {property}.",
               "AND I hereby agree to ratify and confirm all acts lawfully done by my said Attorney under this Power of Attorney."],
        "hi": ["{powers}।", "संबंधित संपत्ति / खाता: {property}।",
               "और मैं अपने उक्त मुख्तार द्वारा इस मुख्तारनामे के अंतर्गत विधिवत किए गए सभी कार्यों को स्वीकार और पुष्ट {karta} हूँ।"],
        "mr": ["{powers}.", "संबंधित मालमत्ता / खाते: {property}.",
               "माझ्या सदर मुखत्याराने या मुखत्यारपत्राखाली कायदेशीररीत्या केलेली सर्व कामे मी मान्य व कायम करत {aahe}."]},
    "poa_special": {
        "en": ["To do only the following act: {act}.", "This Power of Attorney is valid till {valid_till}.",
               "AND I hereby agree to ratify and confirm the said act lawfully done by my said Attorney."],
        "hi": ["केवल यह कार्य करना: {act}।", "यह मुख्तारनामा {valid_till} तक मान्य है।",
               "और मैं अपने उक्त मुख्तार द्वारा विधिवत किए गए उक्त कार्य को स्वीकार और पुष्ट {karta} हूँ।"],
        "mr": ["फक्त हे काम करणे: {act}.", "हे मुखत्यारपत्र {valid_till} पर्यंत वैध आहे.",
               "माझ्या सदर मुखत्याराने कायदेशीररीत्या केलेले सदर काम मी मान्य व कायम करत {aahe}."]},
    "indemnity": {
        "en": ["WHEREAS {matter}.", "NOW I, the Indemnifier, undertake to indemnify and keep indemnified the Indemnified against all losses, claims, costs and damages arising out of the said matter{amount_part}.",
               "This bond shall be binding on me and my legal heirs and representatives."],
        "hi": ["चूँकि {matter}।", "अतः मैं, क्षतिपूर्तिकर्ता, उक्त मामले से उत्पन्न होने वाली सभी हानि, दावों, खर्चों और नुकसान से क्षतिपूरित को सुरक्षित रखने का वचन {deta} हूँ{amount_part}।",
               "यह बंधपत्र मुझ पर और मेरे कानूनी वारिसों व प्रतिनिधियों पर बाध्यकारी होगा।"],
        "mr": ["ज्याअर्थी {matter}.", "त्याअर्थी मी, नुकसानभरपाई देणार, सदर बाबीमुळे होणाऱ्या सर्व तोटा, दावे, खर्च व नुकसानीपासून नुकसानभरपाई घेणार यांना सुरक्षित ठेवण्याची हमी {deto}{amount_part}.",
               "हे बंधपत्र माझ्यावर व माझ्या कायदेशीर वारसांवर व प्रतिनिधींवर बंधनकारक राहील."]},
    "noc": {
        "en": ["That I have no objection regarding {subject} for the purpose of {purpose}.",
               "That this certificate is issued on my free will and without any pressure."],
        "hi": ["यह कि मुझे {purpose} हेतु {subject} के संबंध में कोई आपत्ति नहीं है।", "यह कि यह प्रमाणपत्र मैं अपनी स्वेच्छा से, बिना किसी दबाव के दे {raha} हूँ।"],
        "mr": ["{purpose} या कामासाठी {subject} संदर्भात माझी कोणतीही हरकत नाही.", "हे प्रमाणपत्र मी स्वेच्छेने, कोणत्याही दबावाशिवाय देत आहे."]},
}
OPTIONAL_LINES = {  # a paragraph whose only optional field is empty is left out, never filled with a guess
    "aff_name_change": {0: "documents"}, "aff_address": {1: "previous_address"}, "aff_general": {1: "purpose"},
    "poa_general": {1: "property"}, "poa_special": {1: "valid_till"},
}
VERIFY = {
    "affidavit": {
        "en": "VERIFICATION\nI, the above-named deponent, do hereby verify that the contents of paragraphs above are true and correct to the best of my knowledge and belief, and nothing material has been concealed therefrom.\nVerified at __________ on __________.",
        "hi": "सत्यापन\nमैं, उपरोक्त शपथकर्ता, सत्यापित {karta} हूँ कि उपरोक्त अनुच्छेदों की सामग्री मेरी जानकारी एवं विश्वास के अनुसार सत्य एवं सही है और इसमें कोई महत्वपूर्ण तथ्य छिपाया नहीं गया है।\nस्थान: __________ दिनांक: __________",
        "mr": "पडताळणी\nमी, वरील प्रतिज्ञापत्रकर्ता, पडताळून {sangto} की वरील परिच्छेदांतील मजकूर माझ्या माहितीप्रमाणे व समजुतीप्रमाणे खरा व बरोबर आहे आणि त्यातील कोणतीही महत्त्वाची बाब लपवलेली नाही.\nठिकाण: __________ दिनांक: __________"},
    "default": {"en": "Place: __________    Date: __________", "hi": "स्थान: __________    दिनांक: __________",
                "mr": "ठिकाण: __________    दिनांक: __________"},
}
SIGN = {
    "affidavit": {"en": "DEPONENT", "hi": "शपथकर्ता", "mr": "प्रतिज्ञापत्रकर्ता"},
    "declaration": {"en": "DECLARANT", "hi": "घोषणाकर्ता", "mr": "घोषणाकर्ता"},
    "poa": {"en": "PRINCIPAL                                   ACCEPTED: ATTORNEY", "hi": "प्रधान                                    स्वीकृत: मुख्तार",
            "mr": "मुख्य                                     स्वीकारले: मुखत्यार"},
    "indemnity": {"en": "INDEMNIFIER", "hi": "क्षतिपूर्तिकर्ता", "mr": "नुकसानभरपाई देणार"},
    "noc": {"en": "Signature", "hi": "हस्ताक्षर", "mr": "सही"},
    "rent": {"en": "Prepared for reference", "hi": "संदर्भ हेतु तैयार", "mr": "संदर्भासाठी तयार"},
}
WITNESS = {"en": "WITNESSES:\n1. Name & signature __________\n2. Name & signature __________",
           "hi": "गवाह:\n1. नाम व हस्ताक्षर __________\n2. नाम व हस्ताक्षर __________",
           "mr": "साक्षीदार:\n1. नाव व सही __________\n2. नाव व सही __________"}
DRAFT_LINE = {"en": "DRAFT - to be checked by an advocate before execution", "hi": "मसौदा (ड्राफ्ट) - निष्पादन से पहले वकील से जाँच करवाएँ",
              "mr": "मसुदा (ड्राफ्ट) - सही करण्यापूर्वी वकिलांकडून तपासून घ्या"}


# ---------------------------------------------------------------- helpers
def lang_of(v: str) -> str:
    t = (v or "").strip().lower()
    if t in ("hi", "hindi", "हिन्दी", "हिंदी"):
        return "hi"
    if t in ("mr", "marathi", "मराठी"):
        return "mr"
    return "en" if t in ("", "en", "english", "angrezi") else ""


def num(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(lakh|lac|l|k|hazaar|hazar|thousand|crore|cr)?", s)
    if not m:
        return None
    x = float(m.group(1))
    mult = {"lakh": 1e5, "lac": 1e5, "l": 1e5, "k": 1e3, "hazaar": 1e3, "hazar": 1e3, "thousand": 1e3, "crore": 1e7, "cr": 1e7}
    return x * mult.get(m.group(2) or "", 1)


def rel_key(v: str) -> str:
    t = re.sub(r"[^a-z]", "", (v or "").lower())
    for k, words in (("so", ("so", "son", "sonof", "putra", "beta")), ("do", ("do", "daughter", "daughterof", "putri", "beti")),
                     ("wo", ("wo", "wife", "wifeof", "patni")), ("ho", ("ho", "husband", "husbandof", "pati"))):
        if t in words:
            return k
    return ""


def money_text(v, lang: str) -> tuple[str, str]:
    x = num(v)
    if x is None:
        return "", ""
    from ..india.money import inr, rupees_words
    w = rupees_words(x, lang) if lang in ("en", "hi") else ""     # Marathi number words are not built in: figures only
    return inr(x), w


def blank(label: str) -> str:
    return f"[____ {label}]"


_PH = re.compile(r"\{([a-z_]+)\}")


def _fill(tpl: str, vals: dict[str, str], labels: dict[str, str], blanks: list[str]) -> str:
    def rep(m):
        k = m.group(1)
        if k in vals:
            return vals[k]
        lab = labels.get(k, k)
        if lab not in blanks:
            blanks.append(lab)
        return blank(lab)
    return _PH.sub(rep, tpl)


def _lines(v) -> list[str]:
    if isinstance(v, list):
        items = [str(x) for x in v]
    else:
        items = re.split(r"\n|;\s*", str(v or ""))
    return [re.sub(r"[.।\s]+$", "", x.strip(" -•\t")) for x in items if x and x.strip(" -•\t")]


def build(kind: str, lang: str, party: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    """The whole document text by code. Returns {title, paragraphs, text, blanks}. Missing facts = [blanks] (block final print)."""
    k = KINDS[kind]
    lang = lang if lang in LANGS else "en"
    group = k["group"]
    f = {key: lab for key, lab, _ in k["fields"]}
    labels = {**{key: lab for key, lab, _ in PARTY_FIELDS}, **f}
    fem = str(party.get("gender") or "").strip().lower() in ("f", "female", "mahila", "stri", "woman")
    vals: dict[str, str] = {}
    for key, _lab, _ in PARTY_FIELDS:
        v = str(party.get(key) or "").strip()
        if v:
            vals[key] = v
    rk = rel_key(party.get("relation") or "")
    if rk:
        vals["rel"] = REL[rk][lang]
    labels["rel"] = "S/o, D/o, W/o"
    vals.setdefault("occupation", "")
    if not vals.get("occupation"):
        vals["occupation"] = {"en": "__________", "hi": "__________", "mr": "__________"}[lang]
    vals["karta"] = "करती" if fem else "करता"
    vals["karto"] = "करते" if fem else "करतो"
    vals["deto"] = "देते" if fem else "देतो"
    vals["aahe"] = "आहे"
    vals.update({"raha": "रही" if fem else "रहा", "tha": "थी" if fem else "था", "dunga": "दूँगी" if fem else "दूँगा",
                 "deta": "देती" if fem else "देता", "samajhta": "समझती" if fem else "समझता", "navhato": "नव्हते" if fem else "नव्हतो",
                 "sangto": "सांगते" if fem else "सांगतो"})
    for key, _lab, _req in k["fields"]:
        v = facts.get(key)
        if isinstance(v, list):
            v = "; ".join(_lines(v))
        v = str(v or "").strip()
        if v:
            vals[key] = v
    # derived parts
    for key in ("annual_income", "fee", "deposit", "amount"):
        if vals.get(key):
            t, w = money_text(vals[key], lang)
            if t:
                vals[key] = f"{t} ({w})" if w else t
    ref = vals.get("doc_ref", "")
    vals["doc_ref_part"] = (f" bearing No. {ref}" if lang == "en" else f" (क्रमांक {ref})") if ref else ""
    rel_a = vals.get("attorney_relation", "")
    vals["attorney_relation_part"] = f" ({rel_a})" if rel_a else ""
    amt = vals.get("amount", "")
    vals["amount_part"] = ({"en": f", up to {amt}", "hi": f", {amt} तक", "mr": f", {amt} पर्यंत"}[lang]) if amt else ""
    if kind == "rent_summary" and not vals.get("agreement_kind"):
        vals["agreement_kind"] = {"en": "leave and licence", "hi": "लीव एंड लाइसेंस", "mr": "लिव्ह अँड लायसन्स"}[lang]
    blanks: list[str] = []
    paras: list[str] = []
    intro_tpl = INTRO[GROUP_INTRO[group]][lang]
    if group != "rent":
        paras.append(_fill(intro_tpl, vals, labels, blanks))
    else:
        paras.append(intro_tpl)
    opt = OPTIONAL_LINES.get(kind, {})
    n = 0
    for i, tpl in enumerate(BODY[kind][lang]):
        if i in opt and not vals.get(opt[i]):
            continue
        for list_key in ("statements", "powers"):
            if "{" + list_key + "}" in tpl:
                items = _lines(facts.get(list_key))
                if not items:
                    n += 1
                    paras.append(f"{n}. " + _fill(tpl, vals, labels, blanks))
                for it in items:
                    n += 1
                    paras.append(f"{n}. " + _fill(tpl.replace("{" + list_key + "}", it), vals, labels, blanks))
                break
        else:
            n += 1
            paras.append((f"{n}. " if group not in ("rent",) else "") + _fill(tpl, vals, labels, blanks))
    verify = VERIFY["affidavit" if group == "affidavit" else "default"][lang]
    paras.append(_fill(verify, vals, labels, blanks))
    sign = SIGN.get(group, SIGN["noc"])[lang]
    if group == "poa" or group == "indemnity":
        paras.append(WITNESS[lang])
    paras.append(sign)
    title = TITLES[kind][lang]
    return {"title": title, "paragraphs": paras, "text": title + "\n\n" + "\n\n".join(paras), "blanks": blanks}


# ---------------------------------------------------------------- stamp + e-stamp
STATES = {"MH": "Maharashtra", "DL": "Delhi", "UP": "Uttar Pradesh", "KA": "Karnataka", "GJ": "Gujarat", "MP": "Madhya Pradesh",
          "RJ": "Rajasthan", "TN": "Tamil Nadu", "TG": "Telangana", "AP": "Andhra Pradesh", "GA": "Goa", "WB": "West Bengal",
          "PB": "Punjab", "HR": "Haryana", "BR": "Bihar", "KL": "Kerala", "OD": "Odisha", "CG": "Chhattisgarh", "AS": "Assam",
          "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir", "CH": "Chandigarh", "UK": "Uttarakhand", "JH": "Jharkhand"}
STAMP_KEYS = sorted({v["stamp"] for v in KINDS.values()})
STAMP_MODES = {"e_stamp": "e-Stamp (SHCIL)", "esbtr": "e-SBTR / GRAS (Maharashtra)", "franking": "Franking (bank)",
               "paper": "Physical stamp paper (licensed vendor)", "kaveri": "Kaveri Online (Karnataka)", "none": "Stamp nahi (plain paper)"}
STAMP_SOURCE = ("sansalegal.com 'How to buy e-stamp certificates online in India' (9 Aug 2026): SHCIL ~25 states / UTs incl. Delhi, UP, "
                "Punjab, Assam, HP, J&K, Chandigarh, Ladakh; Maharashtra e-SBTR, Karnataka Kaveri; verify by UIN / QR on shcilestamp.com; "
                "document usually executed within 6 months of purchase (state rules differ).")


def state_code(v: str) -> str:
    t = (v or "").strip()
    if t.upper() in STATES:
        return t.upper()
    for k, name in STATES.items():
        if name.lower() == t.lower():
            return k
    return ""


def stamp_for(rates: dict, state: str, stamp_key: str) -> dict[str, Any]:
    """Her table only: {amount, known, mode}. Missing = amount None (blank), never a guess."""
    st = state_code(state)
    tbl = (rates or {}).get(st) or {}
    x = tbl.get(stamp_key)
    if isinstance(x, dict):
        amt, mode = num(x.get("amount")), str(x.get("mode") or "")
    else:
        amt, mode = num(x), ""
    if not mode:
        mode = "esbtr" if st == "MH" else ("kaveri" if st == "KA" else "e_stamp")
    if amt == 0:
        mode = "none"
    return {"state": st, "state_label": STATES.get(st, ""), "key": stamp_key, "amount": amt, "known": amt is not None, "mode": mode,
            "mode_label": STAMP_MODES.get(mode, mode)}


def stamp_steps(stamp: dict, parties: list[str], doc_label: str) -> list[str]:
    mode = stamp.get("mode")
    amt = stamp.get("amount")
    a = f"₹{amt:,.0f}" if isinstance(amt, (int, float)) else "[stamp ₹ ?]"
    names = " / ".join(p for p in parties if p) or "[party ka naam]"
    if mode == "none":
        return ["Aapki table ke hisaab se is document par stamp nahi: plain paper par print hoga (aapki table galat ho to badliye)."]
    if mode == "e_stamp":
        return ["shcilestamp.com par login (ya authorised collection centre / bank) -> state chuniye.",
                f"Document type: {doc_label}; first party: {names}; stamp duty {a} (aapki rate table se).",
                "Party ke naam document ke naam se bilkul milne chahiye.",
                "Payment party / aap khud kariye -> certificate download / print.", "Certificate ka UIN shcilestamp.com par 'Verify e-Stamp' se jaanchiye.",
                "UIN / certificate no. Hoola ko bataiye (register ke 'stamp affixed' column ke liye)."]
    if mode == "esbtr":
        return ["Maharashtra: SHCIL nahi; state ki official e-payment (GRAS / e-SBTR) ya authorised bank / vendor se.",
                f"Rakam {a} (aapki rate table se); party ke naam document ke naam se mile.", "Payment aap / party khud; challan / e-SBTR no. Hoola ko bataiye."]
    if mode == "kaveri":
        return ["Karnataka: Kaveri Online Services ki official site se.", f"Rakam {a}; payment aap / party khud; reference no. bataiye."]
    if mode == "franking":
        return ["Authorised bank / franking centre par document frank karwaiye.", f"Rakam {a}; franking no. bataiye."]
    return ["Licensed stamp vendor se stamp paper (vendor register entry ke saath).", f"Rakam {a}; stamp paper ka serial no. bataiye."]


# ---------------------------------------------------------------- notarial fees
def fee_check(act: str, fee, pages: int = 1, caps: dict | None = None) -> dict[str, Any]:
    """Her notarial fee vs the Rule 10(1) cap (or her updated cap). Above the cap = not allowed."""
    a = ACTS.get(act) or ACTS["other"]
    x = num(fee)
    cap = a.get("cap")
    if caps and act in caps and num(caps[act]) is not None:
        cap = num(caps[act])
    if act == "true_copy" and not (caps and act in caps):
        cap = max(a["min"], a["per_page"] * max(1, int(pages or 1)))
    if x is None:
        return {"ok": False, "fee": None, "cap": cap, "why": "Fee kitni li? (aapki rate)"}
    if x < 0:
        return {"ok": False, "fee": x, "cap": cap, "why": "Fee minus nahi ho sakti."}
    if cap is not None and x > cap + 0.001:
        return {"ok": False, "fee": x, "cap": cap,
                "why": f"Rule 10(1) mein '{a['label']}' ke liye zyada se zyada ₹{cap:g} (2014 table). Zyada fee nahi likhi ja sakti; "
                       "naya notification ho to Niyam > fee caps badliye."}
    return {"ok": True, "fee": x, "cap": cap, "why": ""}


def fy_of(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


# ---------------------------------------------------------------- apostille / attestation (MEA)
APOSTILLE_SOURCE = ("mea.gov.in/apostille-menu (read 23 Oct 2026): India in the Hague Apostille Convention since 2005; personal "
                    "documents (birth / death / marriage certificates, affidavits, powers of attorney) and educational documents; "
                    "first authenticated by the State / UT designated authority (Regional Authentication Centre) or a Chamber of "
                    "Commerce; MEA fee Rs 50 per apostille sticker, attestation free; outsourced agency Rs 84 per document + Rs 3 per "
                    "page; MEA does not take documents directly from individuals and never legalises photocopies.")
DOC_TYPES = {"personal": "Personal (janm / mrityu / vivah certificate)", "educational": "Shaikshik (degree / marksheet / certificate)",
             "commercial": "Commercial (company / export kaagaz)", "affidavit": "Affidavit (notarised)", "poa": "Power of attorney (notarised)",
             "other": "Doosra"}


def apostille_steps(doc_type: str, hague: bool | None, country: str) -> list[dict[str, Any]]:
    c = country or "[desh]"
    steps: list[tuple[str, str]] = []
    if doc_type in ("affidavit", "poa"):
        steps.append(("notarise", "Document notary ke saamne execute / notarise (aapka kaam) - notary ka seal aur register entry."))
    if doc_type == "commercial":
        steps.append(("first_auth", "Chamber of Commerce se pehla attestation (MEA unhi ke designated signatory ke sign maanta hai)."))
    elif doc_type == "educational":
        steps.append(("first_auth", "State / UT ki designated authority (Regional Authentication Centre) se authentication - education "
                                    "documents ke liye state ka tay vibhag; original document saath."))
    else:
        steps.append(("first_auth", "State / UT ki designated authority (Regional Authentication Centre / Home / GAD) se authentication."))
    if hague is None:
        steps.append(("check_hague", f"{c} Hague Apostille Convention ka member hai? MEA ki list dekhiye (mea.gov.in/apostille-menu) - "
                                     "member = apostille, nahi = attestation + embassy."))
    if hague is not False:
        steps.append(("mea", "MEA apostille: MEA ke outsourced agency (BLS / Superb / IVS / Alhind - MEA site par current list) ke through; "
                             "original ya true copy + photocopy + passport photocopy; MEA fee Rs 50 / sticker + agency Rs 84 / document + Rs 3 / "
                             "page (MEA site par check karein). e-Sanad: kuch documents online (MEA e-Sanad)."))
    if hague is not True:
        steps.append(("mea_attest", "Non-Hague desh: MEA attestation (MEA charge nahi; agency ka charge) ..."))
        steps.append(("embassy", f"... phir {c} ki embassy / consulate se legalisation (unki fee / niyam unki site par)."))
    steps.append(("collect", "Agency se document wapas lekar party ko dena; receipt / tracking no. likhiye."))
    return [{"key": k, "text": t, "done": ""} for k, t in steps]


SOURCES = [
    "Notaries Act 1952 + Notaries Rules 1956 (legalaffairs.gov.in/sites/default/files/notaries-rules-1956.pdf, read 23 Oct 2026): Rule 10 "
    "fees (2014 table) + display of rates, Rule 11(2) Form XV register, 11(4) title page with page count, 11(5) inspection twice a year, "
    "11(9) fee receipt + fee register, Rule 12 seal, Rule 14 annual return in Form XIV in the first week of January (online), Rule 8(4) "
    "certificate of practice valid 5 years, Rule 8B renewal in Form XVI 'before six months' of expiry.",
    "compass.rauias.com (5 Sep 2024): Notary Portal by the Ministry of Law & Justice (applications, certificates; renewal and annual returns "
    "'in due course').",
    STAMP_SOURCE, APOSTILLE_SOURCE,
]
