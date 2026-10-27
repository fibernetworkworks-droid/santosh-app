"""A starter Gyaan test set (`queries` = the 2-3 rewrites the agent is told to send with every gyaan_khojo call): a small fictional business's files in English, Hindi, Marathi and Hinglish, and questions in
four language slices (en, hi, hinglish, mr) incl. questions whose answer is NOT in the files (Hoola must say nahi mila).

`python -m app.gyaan.evaluate` runs it on a throw-away owner and prints recall@k per slice and the abstention score.
Her real test set (200 questions per slice, from her own files) is added the same way with `evaluate(questions=...)`."""
from __future__ import annotations

CORPUS = [
    ("Shop rent agreement 2026.pdf", "doc",
     "Rent Agreement. This agreement is made on 1 April 2026 between Ramesh Patil (Landlord) and Sai Mobile & Repair "
     "(Tenant) for shop no. 14, Station Road, Akola 444001. Monthly rent is Rs 18,500 payable by the 5th of every month. "
     "Security deposit Rs 1,10,000. Rent increases 5% every year. Notice period for vacating is 2 months. "
     "The agreement is valid for 33 months till 31 December 2028."),
    ("Electricity bill Sept 2026", "doc",
     "MSEDCL Bill. Consumer No 170012345678. Billing month September 2026. Units consumed 412. "
     "Bill amount Rs 4,286.50. Due date 18-10-2026. Pay before due date to get prompt payment discount of Rs 42."),
    ("बिजली बिल अगस्त 2026", "doc",
     "महावितरण बिल। ग्राहक क्रमांक 170012345678. बिल महीना अगस्त 2026. खपत 388 यूनिट. बिल राशि ₹3,912. "
     "भुगतान की अंतिम तिथि 18-09-2026."),
    ("GST registration certificate", "doc",
     "Form GST REG-06. Registration Certificate. GSTIN 27AAPFU0939F1ZV. Legal name: Sai Mobile & Repair. "
     "Trade name: Sai Mobiles. Address: Shop 14, Station Road, Akola, Maharashtra. Date of liability 01/07/2023. "
     "Type of registration: Regular."),
    ("Supplier price list Oct 2026.xlsx", "sheet",
     "Item | Brand | Price (Rs) | Warranty\n"
     "Display iPhone 13 | OEM | 7,800 | 3 months\n"
     "Display Redmi Note 13 | Original | 2,350 | 6 months\n"
     "Battery Samsung A54 | Original | 1,650 | 6 months\n"
     "Charging port Vivo Y21 | OEM | 280 | 1 month\n"
     "Back panel OnePlus Nord CE3 | OEM | 950 | none"),
    ("दुकान के नियम", "doc",
     "दुकान के नियम: दुकान सुबह 10 बजे से रात 9 बजे तक खुली रहती है। मंगलवार को साप्ताहिक छुट्टी। "
     "रिपेयर के लिए फोन जमा करते समय 200 रुपये अग्रिम लिए जाते हैं। 30 दिन तक फोन न ले जाने पर दुकान जिम्मेदार नहीं।"),
    ("कर्मचारी माहिती", "doc",
     "कर्मचारी माहिती: सुनील गावंडे - तंत्रज्ञ, मासिक पगार ₹16,000, रुजू दिनांक 15 जून 2025. "
     "प्रिया देशमुख - काउंटर, मासिक पगार ₹12,500, रुजू दिनांक 2 जानेवारी 2026. पगार दर महिन्याच्या 7 तारखेला दिला जातो."),
    ("Insurance policy shop", "doc",
     "Shopkeeper's insurance policy no. SHP/2026/448190 with New India Assurance. Covers fire, burglary and stock up to "
     "Rs 8 lakh. Premium Rs 6,240 per year. Policy period 10-03-2026 to 09-03-2027. Claim helpline 1800-209-1415."),
    ("Mail: Redmi display order", "mail",
     "From: Kunal Traders <orders@kunaltraders.in>\nSubject: Order INV-2026/0045 dispatched\n"
     "Your order INV-2026/0045 for 10 Redmi Note 13 displays (Rs 23,500) has been dispatched by ST Courier. "
     "Expected delivery Thursday 16 October. Payment due in 15 days."),
    ("Notes: Diwali offer", "note",
     "Diwali offer plan: 10% off on screen guards and covers from 20 Oct to 3 Nov. Free tempered glass with every display "
     "replacement above Rs 2,000. Banner to be printed by Om Printers, quote Rs 1,200."),
    ("Bank details for customers", "doc",
     "UPI ID for customers: saimobiles@okaxis. Bank: Axis Bank, Akola branch, IFSC UTIB0001234. "
     "Account holder: Sai Mobile & Repair."),
    ("Warranty rules", "doc",
     "Warranty on repairs: displays 3 to 6 months as per part, batteries 6 months, charging ports 1 month. "
     "Water damage and physical damage are not covered. Warranty card must be shown."),
]

QUESTIONS = [
    # English
    {"q": "What is the monthly rent of the shop?", "lang": "en", "expect": "Shop rent agreement 2026.pdf"},
    {"q": "When is the electricity bill due for September?", "lang": "en", "expect": "Electricity bill Sept 2026"},
    {"q": "What is our GSTIN?", "lang": "en", "expect": "GST registration certificate"},
    {"q": "Price of Redmi Note 13 display from supplier", "lang": "en", "expect": "Supplier price list Oct 2026.xlsx"},
    {"q": "When will the Kunal Traders order arrive?", "lang": "en", "expect": "Mail: Redmi display order"},
    {"q": "Insurance claim helpline number", "lang": "en", "expect": "Insurance policy shop"},
    {"q": "Status of INV-2026/0045", "lang": "en", "expect": "Mail: Redmi display order"},
    {"q": "What is our IFSC code?", "lang": "en", "expect": "Bank details for customers"},
    {"q": "Is water damage covered in warranty?", "lang": "en", "expect": "Warranty rules"},
    {"q": "What did the CA say about income tax refund?", "lang": "en", "expect": None},
    # Hindi (Devanagari)
    {"q": "दुकान कितने बजे खुलती है?", "lang": "hi", "expect": "दुकान के नियम"},
    {"q": "अगस्त का बिजली बिल कितना था?", "lang": "hi", "expect": "बिजली बिल अगस्त 2026"},
    {"q": "रिपेयर के लिए कितना अग्रिम लेते हैं?", "lang": "hi", "expect": "दुकान के नियम"},
    {"q": "किराया कितना है?", "lang": "hi", "expect": "Shop rent agreement 2026.pdf", "queries": ["kiraya kitna hai", "monthly rent of the shop"]},
    {"q": "गाड़ी का बीमा कब खत्म होगा?", "lang": "hi", "expect": None},
    # Hinglish (Roman)
    {"q": "dukan kitne baje khulti hai", "lang": "hinglish", "expect": "दुकान के नियम"},
    {"q": "bijli bill august kitna aaya tha", "lang": "hinglish", "expect": "बिजली बिल अगस्त 2026"},
    {"q": "Diwali offer kab se kab tak hai", "lang": "hinglish", "expect": "Notes: Diwali offer"},
    {"q": "banner printing ka quote kitna tha", "lang": "hinglish", "expect": "Notes: Diwali offer"},
    {"q": "security deposit kitna diya hai", "lang": "hinglish", "expect": "Shop rent agreement 2026.pdf"},
    {"q": "customer ko UPI ID kya dena hai", "lang": "hinglish", "expect": "Bank details for customers"},
    {"q": "Samsung A54 battery ka rate", "lang": "hinglish", "expect": "Supplier price list Oct 2026.xlsx"},
    {"q": "Sunil ki salary kitni hai", "lang": "hinglish", "expect": "कर्मचारी माहिती"},
    {"q": "consumer number 170012345678 ka bill", "lang": "hinglish", "expect": "Electricity bill Sept 2026"},
    {"q": "pichle saal ka GST return file hua kya", "lang": "hinglish", "expect": None},
    # Marathi
    {"q": "प्रिया देशमुख यांचा पगार किती आहे?", "lang": "mr", "expect": "कर्मचारी माहिती"},
    {"q": "पगार कोणत्या तारखेला दिला जातो?", "lang": "mr", "expect": "कर्मचारी माहिती"},
    {"q": "सुनील कधी रुजू झाले?", "lang": "mr", "expect": "कर्मचारी माहिती"},
    {"q": "दुकानाचे भाडे किती आहे?", "lang": "mr", "expect": "Shop rent agreement 2026.pdf", "queries": ["dukanache bhade kiti", "shop monthly rent"]},
    {"q": "नवीन शाखा कधी उघडणार?", "lang": "mr", "expect": None},
]
