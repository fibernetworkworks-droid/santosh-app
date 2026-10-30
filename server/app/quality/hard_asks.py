"""v0.272 SOCH KE JAWAB - the hard-reasoning set. HARD = asks that need thinking (step 1 pins that every one is spotted);
EASY = everyday asks and plain facts that must stay on the fast path. Step 7 adds the right answers for a live score.
HARD_SET_V moves only with a deliberate change of the set.
"""
from __future__ import annotations

HARD_SET_V = 1

HARD: list[dict] = [
    # calculation / finance
    {"id": "fin_model", "kind": "calculation", "text": "Mere business ke liye 3 saal ka financial model banao aur batao profitable kab hoga"},
    {"id": "emi", "kind": "calculation", "text": "20 lakh ke home loan ki EMI kitni banegi 9% pe 20 saal ke liye, total interest bhi batao"},
    {"id": "breakeven", "kind": "calculation", "text": "Meri bakery ka fixed cost 80,000 mahina hai, ek cake 450 ka bikta hai aur banane mein 260 lagta hai. Break-even kitne cake pe hoga?"},
    {"id": "roi", "kind": "calculation", "text": "Calculate the ROI if I invest 5 lakh in a solar plant that saves 9,000 a month"},
    {"id": "cagr", "kind": "calculation", "text": "Sales 2021 mein 40 lakh thi aur 2025 mein 95 lakh, CAGR kitna hua?"},
    {"id": "margin", "kind": "calculation", "text": "Agar main price 10% badhaun aur volume 6% gire, to profit pe kya asar padega? Margin abhi 18% hai"},
    {"id": "sip", "kind": "calculation", "text": "Har mahine 15,000 ki SIP 12% return pe 15 saal mein kitni banegi?"},
    {"id": "unit_econ", "kind": "calculation", "text": "Work out the unit economics of my tiffin service: 120 per meal, 70 food cost, 15 delivery, 300 customers"},
    # maths / logic
    {"id": "trains", "kind": "maths", "text": "Ek train 60 km/h, doosri 40 km/h, 300 km door se aamne saamne chal rahi hain, kab milengi? step by step samjhao"},
    {"id": "root2", "kind": "maths", "text": "Prove that root 2 is irrational"},
    {"id": "prob", "kind": "maths", "text": "What is the probability of getting at least one six in four throws of a dice?"},
    {"id": "puzzle", "kind": "maths", "text": "Ek paheli hal karo: teen dabbe hain, sab galat label wale, ek fal nikal ke kaise pata karein?"},
    {"id": "equation", "kind": "maths", "text": "Solve 3x + 7 = 2x - 5 and explain each step"},
    {"id": "ages", "kind": "maths", "text": "Pita ki umar bete se 3 guna hai, 10 saal baad 2 guna hogi, dono ki umar kya hai? logic samjhao"},
    # decision / comparison
    {"id": "gst_scheme", "kind": "decision", "text": "Compare GST composition vs regular scheme for my 80 lakh turnover kirana shop and recommend"},
    {"id": "rent_buy", "kind": "decision", "text": "Ghar kharidna better hai ya kiraye pe rehna? 60 lakh ka flat, rent 18,000"},
    {"id": "loan_choice", "kind": "decision", "text": "Should I prepay my home loan or invest the bonus in mutual funds?"},
    {"id": "cloud", "kind": "decision", "text": "AWS vs Azure vs GCP - meri choti SaaS company ke liye kaun sa behtar hai, faayde nuksan ke saath"},
    {"id": "hire", "kind": "decision", "text": "Do candidates hain, ek experienced aur mehenga, ek fresher aur sasta. Kise lena chahiye?"},
    {"id": "pricing", "kind": "decision", "text": "Mere app ke liye subscription better hai ya one-time price? trade-offs batao"},
    # plan / strategy
    {"id": "gtm", "kind": "plan", "text": "Plan a 6-month go-to-market strategy for an Indian SaaS startup with budget 10 lakh"},
    {"id": "expansion", "kind": "plan", "text": "Meri 2 dukaan hain, agle 2 saal mein 10 karni hain - expansion plan aur roadmap banao"},
    {"id": "marketing", "kind": "plan", "text": "Diwali ke liye ek marketing strategy banao jo 3 lakh ke budget mein ho"},
    {"id": "forecast", "kind": "plan", "text": "Pichhle 12 mahine ki sales se agle quarter ka forecast banao"},
    {"id": "hiring_plan", "kind": "plan", "text": "Create a 12 month hiring roadmap for a 20 person startup growing to 60"},
    # analysis / root cause
    {"id": "sales_drop", "kind": "analysis", "text": "Why did my sales drop 20% last quarter? Analyse the attached sheet and give root cause"},
    {"id": "churn", "kind": "analysis", "text": "Customers 3 mahine baad subscription kyun chhod dete hain? analysis karke batao"},
    {"id": "pnl", "kind": "analysis", "text": "Meri P&L dekh ke batao kharcha kahan zyada ho raha hai aur kya kaatna chahiye"},
    {"id": "competitor", "kind": "analysis", "text": "Analyse my competitor's pricing and tell me where we lose"},
    {"id": "survey", "kind": "analysis", "text": "Is survey ke results ka vishleshan karo aur insights do"},
    {"id": "website_slow", "kind": "analysis", "text": "Meri website itni slow kyun hai? diagnose karke batao kya fix karna hai"},
    # rules / tax / legal reasoning
    {"id": "tds", "kind": "rules", "text": "Freelancer ko 50,000 diye to TDS kaatna padega ya nahi, kis section mein aur kitna?"},
    {"id": "contract_risk", "kind": "rules", "text": "Is contract mein kaun se clause risky hain aur kya implication hai?"},
    {"id": "itr_regime", "kind": "rules", "text": "Old tax regime vs new regime - 18 lakh salary pe kaun sa better hai? calculate karke batao"},
    {"id": "gst_itc", "kind": "rules", "text": "Kya main car ki kharid pe GST ITC le sakti hoon? eligibility aur risk batao"},
    # deep explanation
    {"id": "explain_infl", "kind": "deep", "text": "Inflation interest rates ko kaise affect karta hai, detail mein samjhao"},
    {"id": "explain_llm", "kind": "deep", "text": "Explain how large language models work, in depth, from first principles"},
    {"id": "explain_upi", "kind": "deep", "text": "UPI payment andar se kaise kaam karta hai step by step samjhao"},
    {"id": "explain_why", "kind": "deep", "text": "Why do startups fail even with good funding? think it through"},
    # fix / optimise
    {"id": "optimise_routes", "kind": "fix", "text": "Mere 5 delivery boys hain aur 40 orders, routes kaise optimize karun taaki petrol kam lage?"},
    {"id": "debug", "kind": "fix", "text": "My Python script throws KeyError on line 40 - why, and how do I debug it?"},
    {"id": "inventory", "kind": "fix", "text": "Stock kam pad jata hai ya zyada ho jata hai - inventory ko optimize kaise karun, kitna order karun?"},
    # Hindi
    {"id": "hi_compare", "kind": "decision", "text": "मुझे FD में पैसा रखना चाहिए या म्यूचुअल फंड में? तुलना करके बताइए"},
    {"id": "hi_why", "kind": "analysis", "text": "मेरी दुकान की बिक्री क्यों घट रही है? विश्लेषण करके बताइए"},
    {"id": "hi_plan", "kind": "plan", "text": "अगले 6 महीने के लिए मेरे बिज़नेस की रणनीति बनाइए"},
    # longer real-world
    {"id": "long_case", "kind": "decision", "text": "Mera ek restaurant hai 40 seats ka. Weekday pe 30% occupancy, weekend pe 90%. Zomato commission 25% leta hai. Kya mujhe apni delivery shuru karni chahiye ya Zomato pe rehna chahiye? Kharcha aur faayda dono dekho."},
    {"id": "long_strategy", "kind": "plan", "text": "We are a 12 person agency doing 80 lakh a year, mostly from 3 clients. How do we reduce client concentration risk over the next year? Give a concrete plan."},
    {"id": "valuation", "kind": "calculation", "text": "Meri company ki valuation kaise nikalein? Revenue 2 crore, profit 30 lakh, growth 40%"},
    {"id": "best_time", "kind": "decision", "text": "Naya product launch karne ka best time kab hoga - Diwali se pehle ya baad? reasoning ke saath"},
    {"id": "kyun_logic", "kind": "analysis", "text": "Ads pe kharcha badhaya par orders nahi badhe, kyun? kya galat ho raha hai"},
]

EASY: list[str] = [
    "Hello Hoola, kaise ho?", "Aaj ka mausam kaisa hai?", "Sharma ji ko mail bhej do ki kal meeting hai",
    "Subah 6 baje ka alarm laga do", "Kal 4 baje meeting calendar mein daal do", "YouTube pe gaane chala do",
    "Mera last order kahan pahuncha?", "Aaj Bitcoin ka rate kya hai", "Paas mein koi dentist batao",
    "Grocery list mein doodh daal do", "Thank you!", "Haan bhej do", "Ek company profile PDF bana do",
    "Is photo ka background hata do", "Diwali kab hai is saal", "India ki capital kya hai?",
    "Mujhe shaam 7 baje dawai yaad dilana", "Swiggy se biryani mangwa do", "Mere unread mails dikhao",
    "Drive mein invoice file dhoondo", "Yeh video reel bana do", "Agle hafte ki meetings batao",
    "Kal Delhi se Jaipur ki train kaun si hai", "Mera Aadhaar locker mein save karo", "TV pe news laga do",
]


# HOLDOUT: written fresh AFTER the rules were tuned on HARD / EASY and never tuned on - the honest number.
HOLDOUT_HARD: list[str] = [
    'Mera cafe weekend pe full hai par weekdays khali, weekday sales badhane ke 5 tareeke soch ke batao',
    'I have 3 job offers: 18 LPA Bangalore, 15 LPA remote, 22 LPA Gurgaon with long hours. Help me decide',
    'Kitne customers chahiye 1 lakh mahina kamane ke liye agar har order pe 120 bachta hai?',
    'Hamari delivery late kyon ho rahi hai pichhle mahine se? kya karein',
    'Should we raise a seed round now or bootstrap for another year? consider runway of 8 months',
    'Ek 2BHK ko Airbnb pe dena better rahega ya normal rent pe? numbers ke saath',
    'Explain why the sky is blue using physics, properly',
    'Mere 4 bachche ki fees aur ghar kharch - monthly budget kaise banaun 1.2 lakh salary mein?',
    'What would happen to my margins if raw material cost goes up 15%?',
    'Agar main 2 naye salesmen rakhun 25,000 each, to kitni extra sale chahiye kharcha nikalne ke liye?',
    'Is my pricing of 499/month too low compared to competitors at 799 and 999? what should I do',
    'Ek gaon mein 100 log hain, har din 2% badhte hain, 1 saal baad kitne honge?',
    'Hamare employees jaldi naukri kyun chhod rahe hain? HR data dekh ke pattern batao',
    'Compare running Google Ads vs Instagram ads for a local salon with 20k monthly budget',
    'Startup idea: tiffin for hostels in Kota. Is it viable? market size, costs, risks',
    'Main kaise decide karun ki kaun sa product band karna chahiye? 40 SKU hain',
    'मेरे बेटे के लिए इंजीनियरिंग बेहतर है या मेडिकल? सोचकर सलाह दीजिए',
    'Why is my electricity bill double in summer - think through the AC usage math',
    'Ek project 3 log 12 din mein karte hain, 4 log kitne din mein karenge? explain',
    "What's the best way to structure equity between 3 cofounders with unequal contribution?",
    'Agar GST 18% se 12% ho jaye to customer price aur mera profit dono pe kya asar hoga?',
    'Mere shop ke liye loan lena sahi rahega ya savings use karun? interest 11% hai',
    'Analyse karo mere last 6 mahine ke kharche aur batao kahan bachat ho sakti hai',
    'Design an onboarding process for new delivery partners that cuts dropout',
    'If inflation is 6% and my FD gives 7%, am I actually earning? explain with numbers',
]
HOLDOUT_EASY: list[str] = [
    'GST kya hai?',
    "Explain this word: 'serendipity'",
    'Mera kal ka schedule kya hai?',
    'Hello!',
    'Kitne baje hain abhi?',
    'Mausam kaisa rahega kal Mumbai mein?',
    'Is mail ka reply bhej do ki main aa rahi hoon',
    'Ek photo bana do sunset ki',
    'Who is the PM of India?',
    'Sharma ji ka birthday kab hai?',
    'Yeh file Drive pe upload karo',
    'Mujhe ek joke sunao',
    'Kal subah 8 baje uthana',
    'Paneer butter masala ki recipe batao',
    'Mere orders ka status kya hai',
    "Translate 'thank you' in Tamil",
    'Is link ko phone pe kholo',
    'Aaj ki news batao',
    'Spotify pe Arijit chalao',
    'Mera last invoice dhoondo',
    'Kitna kharcha hua AI ka is mahine?',
    'Ek reminder: bijli bill 10 tarikh',
    'Rahul ko meeting invite bhejo',
    'Yeh video download karo',
    'Thanks, bas itna hi',
]


def check() -> list[str]:
    bad = []
    ids = [a["id"] for a in HARD]
    if len(ids) != len(set(ids)):
        bad.append("duplicate ids")
    return bad


def card() -> dict:
    """Free (no model): how the rules alone sort the set - spotted, sent to the judge, missed; easy kept fast."""
    from ..agent import hard
    rows = []
    for a in HARD:
        v = hard.assess(a["text"])
        rows.append({"id": a["id"], "kind": a["kind"], "hard": v["hard"], "maybe": v.get("maybe", False), "why": v["why"]})
    easy = [hard.assess(t) for t in EASY]
    return {"set": HARD_SET_V, "hard_asks": len(HARD), "spotted": sum(r["hard"] for r in rows),
            "to_judge": sum(r["maybe"] for r in rows), "missed": sum(not r["hard"] and not r["maybe"] for r in rows),
            "easy_asks": len(EASY), "easy_marked_hard": sum(e["hard"] for e in easy),
            "easy_to_judge": sum(bool(e.get("maybe")) for e in easy), "rows": rows}


def lines(c: dict) -> list[str]:
    out = [f"Hard asks (set v{c['set']}): spotted by rules {c['spotted']}/{c['hard_asks']}, to the judge {c['to_judge']}, "
           f"missed {c['missed']} | everyday asks marked hard {c['easy_marked_hard']}/{c['easy_asks']}, "
           f"to the judge {c['easy_to_judge']}"]
    out += [f"  - missed: {r['id']}" for r in c["rows"] if not r["hard"] and not r["maybe"]]
    return out
