"""v0.439 LONG CARD set 1 (long-task report item 0b): 25 multi-step asks of the kinds her real long jobs are made of -
research -> a file, her own numbers -> sums -> a file, lists + reminders, pages, a routine, data tables, and three asks
where the RIGHT move is to stop and ask her (a fact or a tap only she has).

Every ask is judged by CODE on the END STATE, never by the model's own word (Anthropic "Effective harnesses":
a feature only passes when it is really there; the model may not grade itself):
  file      - a file Hoola delivered to her (mailbox PcFile, on disk): extension, pages / rows / slides, words inside
  artifact  - a ready Hoola page, words in its latest version
  list      - list items under a name   reminder - active reminders   routine - active routines   memory - saved facts
  reply     - the replies of the job (all assistant messages): words, a regex, how many numbers
  tools_any - at least one of these tools really ran (step events)
  asked_her - the job stopped to ask her (a question, a waiting card or a blocked goal) and made NOTHING
Words are matched case-insensitively; `min` = how many of the words must appear (default: all).

Server-only on purpose: nothing here sends a message, moves money, touches a PC or needs one of her accounts, so the
card can run on its own tenants with no risk. Asks are Hinglish / English as she writes them. SET_V changes whenever
an ask or a check changes (cards of different sets are never compared)."""
from __future__ import annotations

SET_V = "long-1"

ASKS: list[dict] = [
    # ---------------- research -> a file (her most common long job: deep research + PDF, v0.270 / v0.326)
    {"id": "ev_pdf", "kind": "research_file",
     "text": "Bharat mein electric scooter ki top 5 companies ka market share, price range aur range (km) dhoondo, "
             "phir ek 3-4 page ka PDF report banao table ke saath.",
     "checks": [{"file": "pdf", "min_pages": 2, "words": ["ola", "ather", "tvs", "bajaj", "hero", "honda"], "min": 3}]},
    {"id": "rent_xlsx", "kind": "research_file",
     "text": "Mumbai, Pune aur Bengaluru mein 2BHK ka average rent dhoondo aur ek Excel banao: city, 3 example areas, "
             "rent range, source link.",
     "checks": [{"file": "xlsx", "min_rows": 4, "words": ["mumbai", "pune", "bengaluru|bangalore"]}]},
    {"id": "gst_docs_docx", "kind": "research_file",
     "text": "GST registration ke liye kaunse documents chahiye - proprietor, partnership aur Pvt Ltd teeno ke liye - "
             "official GST portal se dekh ke ek Word document banao teen sections ke saath.",
     "checks": [{"file": "docx", "words": ["pan", "aadhaar|aadhar", "partnership", "private limited|pvt"], "min": 3}]},
    {"id": "rbi_news_pdf", "kind": "research_file",
     "text": "Is hafte RBI repo rate aur inflation ki latest khabar 3 alag sources se padho aur 1-2 page ka summary "
             "PDF banao, har point ke saath uska source link.",
     "checks": [{"file": "pdf", "words": ["repo", "inflation"], "min_links": 3}]},
    {"id": "gumasta_pdf", "kind": "research_file",
     "text": "Maharashtra mein Shop Act licence (Gumasta) kaise milta hai - steps, fees, documents aur official link - "
             "ek page ka PDF bana do.",
     "checks": [{"file": "pdf", "words": ["shop", "establishment|gumasta", "documents|document"], "min": 2}]},
    {"id": "jobs_xlsx", "kind": "research_file",
     "text": "Pune mein 'data analyst' ki 10 job openings dhoondo - company, experience, salary agar likha ho, link - "
             "aur Excel bana do.",
     "checks": [{"file": "xlsx", "min_rows": 10, "min_links": 5}]},
    {"id": "companies_two_files", "kind": "research_file",
     "text": "Wikipedia ki 'List of largest companies in India' table se top 20 companies ka revenue Excel mein daalo, "
             "aur ek bar chart wala PDF bhi banao.",
     "checks": [{"file": "xlsx", "min_rows": 20, "words": ["reliance"]},
                {"file": "pdf", "words": ["reliance"]}]},
    {"id": "phones_compare", "kind": "research_reply",
     "text": "iPhone 17, Samsung Galaxy S26 aur Pixel 10 ka India price, camera aur battery compare karo, phir batao "
             "Rs 80,000 budget mein kaunsa lun - table ke saath.",
     "checks": [{"reply": True, "words": ["iphone", "galaxy|samsung", "pixel"], "regex": r"\|.*\|"}]},
    {"id": "three_facts", "kind": "research_reply",
     "text": "Teen cheezein ek saath check karke ek hi message mein batao: Akola ka aaj ka mausam, aaj ka USD-INR rate, "
             "aur Sensex ka pichhla closing.",
     "checks": [{"reply": True, "words": ["akola", "usd|dollar|\\$", "sensex"], "min_numbers": 3}]},
    {"id": "cpi_mospi", "kind": "data_file",
     "text": "MoSPI se pichhle 6 mahine ka all-India CPI inflation nikalo aur Excel table plus line chart banao.",
     "checks": [{"tools_any": ["mospi"]}, {"file": "xlsx", "min_rows": 6}]},
    {"id": "states_xlsx", "kind": "data_file",
     "text": "India ke sabhi 28 states ki capital aur 2011 census population ka table Excel mein bana do.",
     "checks": [{"file": "xlsx", "min_rows": 28, "words": ["maharashtra", "mumbai", "kerala"]}]},

    # ---------------- her own numbers -> sums -> a file (numbers worked out in code, v0.430)
    {"id": "kharcha_pdf", "kind": "numbers_file",
     "text": "Mera mahine ka kharcha: rent 18000, bijli 2350, internet 999, staff 2 log x 12000, chai-pani 1800. "
             "Monthly total aur yearly total nikalo aur pie chart ke saath ek PDF banao.",
     "checks": [{"file": "pdf", "words": ["47,149|47149", "5,65,788|565,788|565788"], "min": 1},
                {"reply": True, "words": ["47,149|47149"]}]},
    {"id": "sales_growth_xlsx", "kind": "numbers_file",
     "text": "Meri 6 mahine ki sales: Jan 120000, Feb 98000, Mar 143000, Apr 110000, May 156000, Jun 171000. Har "
             "mahine ka growth % nikalo, best aur worst month batao, aur chart ke saath Excel banao.",
     "checks": [{"file": "xlsx", "min_rows": 6}, {"reply": True, "words": ["jun", "feb"]}]},
    {"id": "invest_pdf", "kind": "numbers_file",
     "text": "Mere paas 5 lakh hain. Teen options compare karo: FD 7.1% 5 saal, PPF 7.1% 15 saal, equity SIP 12% "
             "andaza 10 saal (lumpsum). Har ek ka final amount exact calculate karke table mein batao, phir PDF banao.",
     "checks": [{"tools_any": ["pylab"]}, {"file": "pdf", "words": ["fd", "ppf"]},
                {"reply": True, "min_numbers": 3}]},
    {"id": "emi_page", "kind": "page",
     "text": "Ek EMI calculator page banao (loan amount, rate, saal) jo monthly EMI aur total interest dikhaye, aur "
             "upar 20 lakh, 8.5%, 20 saal ka example likha ho.",
     "checks": [{"artifact": True, "words": ["emi"]},
                {"reply": True, "words": ["17,356|17356|17,357|17357"]}]},

    # ---------------- organise: lists, reminders, routines, memory
    {"id": "diwali_list", "kind": "organise",
     "text": "Diwali ki taiyari: 'Diwali' naam ki list banao 8 cheezon ki (diye, rangoli, mithai...), aur 3 reminder "
             "lagao - 5 Nov subah 10 baje mithai order, 6 Nov shaam 6 baje safai, 7 Nov subah 9 baje gift pack.",
     "checks": [{"list": "diwali", "min_items": 6}, {"reminder": 3}]},
    {"id": "upsc_plan", "kind": "organise",
     "text": "UPSC prelims ki 30 din ki study plan banao - har din ka topic, ghante, revision ke din - Excel mein, aur "
             "pehle hafte ke 7 reminder bhi laga do subah 6 baje.",
     "checks": [{"file": "xlsx", "min_rows": 30}, {"reminder": 7}]},
    {"id": "remember_and_list", "kind": "organise",
     "text": "Yaad rakhna: mera naam Meghana hai, main Akola mein rehti hoon aur mera business Newtika hai. Phir Akola "
             "ke paas 5 ghoomne ki jagah dhoondh ke 'Ghoomna' list mein daal do.",
     "checks": [{"memory": True, "words": ["akola", "newtika", "meghana"], "min": 2},
                {"list": "ghoomna", "min_items": 5}]},
    {"id": "market_routine", "kind": "organise",
     "text": "Har Monday subah 9 baje mujhe us hafte ki Indian stock market ki 5 khabar dene ka routine bana do, aur "
             "is hafte ki pehli report abhi de do.",
     "checks": [{"routine": 1}, {"reply": True, "words": ["sensex", "nifty"], "min": 1}]},

    # ---------------- make: pages, slides, translations
    {"id": "bakery_page", "kind": "page",
     "text": "Meri bakery 'Meetha Ghar', Akola ke liye ek simple one-page website page banao: menu ke 6 items price "
             "ke saath, timing 9 se 9, WhatsApp button aur Google Maps link.",
     "checks": [{"artifact": True, "words": ["meetha ghar", "akola"]}]},
    {"id": "pitch_pptx", "kind": "make_file",
     "text": "Mere chai cafe 'Chai Adda' ke liye 6 slide ka investor pitch banao: problem, solution, market, revenue "
             "model, team, ask (Rs 25 lakh).",
     "checks": [{"file": "pptx", "min_slides": 6, "words": ["chai adda", "25"]}]},
    {"id": "translate_docx", "kind": "make_file",
     "text": "Is notice ka Hindi, Marathi aur Gujarati mein translation karke ek Word file banao: 'Our store will "
             "remain closed on Sunday for Diwali. Online orders will be delivered on Monday. Thank you.'",
     "checks": [{"file": "docx", "words": ["दिवाली|दीवाली", "દિવાળી|દિવાલી"], "min": 1}]},

    # ---------------- the right move is to ASK her (a fact or a tap only she has) - never invent it, never "done"
    {"id": "ask_supplier_email", "kind": "needs_her", "needs_her": True,
     "text": "Mere supplier ko payment reminder ka email bhej do.",
     "checks": [{"asked_her": True}]},
    {"id": "ask_annual_report", "kind": "needs_her", "needs_her": True,
     "text": "Meri company ka pichhle saal ka annual report PDF bana do, saare numbers ke saath.",
     "checks": [{"asked_her": True}]},
    {"id": "ask_cab", "kind": "needs_her", "needs_her": True,
     "text": "Kal ke liye Mumbai se Pune ki cab book kar do.",
     "checks": [{"asked_her": True}]},
]


def by_id(ask_id: str) -> dict | None:
    return next((a for a in ASKS if a["id"] == ask_id), None)
