"""v0.732 CLAUDE PARITY Phase 0 - the 60 conversations of the Claude Parity Card, as DATA (docs/CLAUDE_PARITY_PLAN.md
Part 3, Phase 0). paritycard.py replays each through the REAL run_turn and scores it in code.

Shape of one conversation:
  {"id", "cat", "turns": [TURN, ...], "setup": [[text, ...], ...] (memory only: earlier chats, run first, not scored)}
A TURN is {"text": what she types, **expectations}. Every expectation is checkable in code (paritycard.EXPECT_KEYS):
  tool        a tool family (paritycard.FAMILIES) or a list of them: the FIRST real tool of the turn must be in it
  no_tool     True: the turn must not run a doing tool (reads and tool_search are fine)
  ask         True: the reply must ask her ONE question (a '?') and do nothing yet
  cannot      True: the reply must say plainly that it cannot / will not do it
  must        list of any-of word groups: each group needs one of its words in the reply  [["pdf"], ["profit", "loss"]]
  must_not    phrases that must not be in the reply (lower-cased substring)
  refers_prev True: the reply carries the previous reply's thread (shares content words with it)
  refers_item n: the reply names the previous reply's item n (a numbered / bulleted list)
  shorter     True: fewer than 70% of the previous reply's words
  lang        "hi" | "mr": the reply is in that language (Devanagari or the language's own words)
  stopped     True: "stop" - a short reply, nothing new started
Every turn is ALSO checked for: an answer (not empty, not the error line), no invented "done" (agent/draftcheck: a done
claim with no tool of its kind), and no text she did not ask for ("(Kaam:" ledger, honesty notes).
User text is English except the Hinglish / Marathi set. PARITY_SET_V moves with any deliberate change to the set.
"""
from __future__ import annotations

PARITY_SET_V = 1

CATEGORIES = {"followup": 15, "one_tool": 10, "long": 10, "make": 10, "memory": 5, "trap": 5, "lang": 5}

LOST = ["what do you mean", "which one do you mean", "no pending approval", "could you clarify what you",
        "kis cheez ke liye", "not sure what you're referring", "not sure what you are referring"]


def T(text: str, **expect) -> dict:
    return {"text": text, **expect}


def C(cid: str, cat: str, *turns: dict, setup: list[list[str]] | None = None) -> dict:
    out = {"id": cid, "cat": cat, "turns": list(turns)}
    if setup:
        out["setup"] = setup
    return out


CONVS: list[dict] = [
    # ================================================================ 15 follow-ups that hang on the previous reply
    C("fu_yes_pdf", "followup",
      T("In four lines, what is a profit and loss statement? End by offering to make me a sample one as a PDF.",
        no_tool=True, must=[["profit"], ["pdf"]]),
      T("yes", tool="make", must_not=LOST)),
    C("fu_second_name", "followup",
      T("Give me exactly three name ideas for a small bakery in Pune, as a numbered list, one line each.", no_tool=True),
      T("the second one. Write a one-line tagline for it.", refers_item=2, no_tool=True, must_not=LOST)),
    C("fu_shorter_email", "followup",
      T("Write a polite email to a supplier asking for a 10 day extension on an invoice payment. Just the text here, "
        "don't send it.", no_tool=True, must=[["extension", "extend"]]),
      T("make it shorter", shorter=True, no_tool=True, must=[["extension", "extend", "days"]], must_not=LOST)),
    C("fu_in_hindi", "followup",
      T("Explain in three short sentences why a business should keep a cash reserve.", no_tool=True,
        must=[["cash", "reserve"]]),
      T("in Hindi", lang="hi", no_tool=True, must_not=LOST)),
    C("fu_why", "followup",
      T("Should a new kirana shop take GST registration if its turnover is 15 lakh a year? One line answer first.",
        no_tool=True, must=[["gst"]]),
      T("why?", refers_prev=True, no_tool=True, must_not=LOST)),
    C("fu_do_it_reminder", "followup",
      T("I keep forgetting to pay my electricity bill on the 5th. What can you do about that? Offer, don't do it yet.",
        no_tool=True),
      T("do it", tool="reminder", must_not=LOST)),
    C("fu_third_option", "followup",
      T("List three ways to reduce delivery cost for a tiffin service, numbered, one line each.", no_tool=True),
      T("tell me more about the third one", refers_item=3, no_tool=True, must_not=LOST)),
    C("fu_yes_excel", "followup",
      T("My monthly costs are rent 20000, salaries 85000, electricity 6000, raw material 140000. What is the total? "
        "Then offer to put this in an Excel sheet.", must=[["251000", "2,51,000", "251,000", "2.51"]]),
      T("yes please", tool="make", must_not=LOST)),
    C("fu_formal", "followup",
      T("Write a two-line WhatsApp message telling my customers the shop is closed on Sunday. Text only, don't send.",
        no_tool=True, must=[["sunday"]]),
      T("make it more formal", no_tool=True, must=[["sunday"]], must_not=LOST)),
    C("fu_example", "followup",
      T("What is working capital, in two sentences?", no_tool=True, must=[["working capital", "current"]]),
      T("give me an example with numbers", refers_prev=True, no_tool=True, must_not=LOST)),
    C("fu_no_other", "followup",
      T("Suggest one Instagram post idea for my saree shop for Diwali. One idea only.", no_tool=True),
      T("no, give me a different one", refers_prev=True, no_tool=True, must_not=LOST)),
    C("fu_first_draft", "followup",
      T("Give me two subject lines for a newsletter about our new organic tea, numbered.", no_tool=True,
        must=[["tea"]]),
      T("use the first one and write the opening paragraph", refers_item=1, no_tool=True, must_not=LOST)),
    C("fu_table", "followup",
      T("Compare UPI and credit card payments for a small shop on fees, speed and risk. Short.", no_tool=True,
        must=[["upi"]]),
      T("put that in a table", refers_prev=True, no_tool=True, must=[["|"]], must_not=LOST)),
    C("fu_yes_research", "followup",
      T("What are the documents needed for an FSSAI basic registration? Answer from what you know in 4 bullets, then "
        "offer to check the official site for anything that changed.", must=[["fssai"]]),
      T("yes, check it", tool="web", must_not=LOST)),
    C("fu_bullets", "followup",
      T("Explain how an EMI is calculated, in one paragraph.", no_tool=True, must=[["interest", "principal"]]),
      T("as three bullet points", refers_prev=True, no_tool=True, must_not=LOST)),

    # ================================================================ 10 tasks that need exactly one tool
    C("ot_mail_unread", "one_tool", T("Check my email: do I have any unread mail from today?", tool="mail")),
    C("ot_mail_draft", "one_tool",
      T("Draft an email to rahul@example.com saying the meeting moves to 4 pm tomorrow. Don't send it.",
        tool="mail", must_not=["i've sent", "has been sent", "email sent"])),
    C("ot_calendar_today", "one_tool", T("What is on my calendar tomorrow?", tool="calendar")),
    C("ot_calendar_add", "one_tool",
      T("Add a calendar event: dentist on 20 November 2026 at 11 am for 30 minutes.", tool="calendar")),
    C("ot_web_fact", "one_tool",
      T("Look up on the web: what is the current repo rate set by the Reserve Bank of India?", tool="web",
        must=[["repo"]])),
    C("ot_web_price", "one_tool",
      T("Search the web for today's gold price per 10 grams in Mumbai.", tool="web", must=[["gold"]])),
    C("ot_reminder", "one_tool",
      T("Remind me in 30 minutes to call the CA.", tool="reminder", must=[["ca", "call"]])),
    C("ot_calc", "one_tool",
      T("Calculate the EMI on a 12 lakh loan at 10.5% for 5 years, exactly.", tool="calc",
        must=[["25,79", "25.79", "2579"]])),
    C("ot_memory_search", "one_tool",
      T("Search my past chats for anything about my supplier Sharma Traders.", tool="memory")),
    C("ot_files", "one_tool", T("Show me the list of files in my Google Drive from this week.", tool="file")),

    # ================================================================ 10 long tasks
    C("lg_research_sources", "long",
      T("Research the Indian electric two-wheeler market in 2025: size, top 5 players, growth. With sources and links.",
        tool="research", must=[["http"]])),
    C("lg_five_step", "long",
      T("Do these 5 steps: 1) find 3 competitors of a cloud kitchen in Bandra, 2) their price range, 3) their ratings, "
        "4) compare in a table, 5) suggest my pricing.", tool=["plan", "research", "web"])),
    C("lg_excel_data", "long",
      T("Make an Excel file from this data with a total row: Jan 120000, Feb 135000, Mar 98000, Apr 150000, "
        "May 142000, Jun 160000. Add a growth % column.", tool="make")),
    C("lg_pdf_report", "long",
      T("Write a 2-page PDF report on how small Indian shops can start selling on ONDC.", tool=["make", "research", "web", "plan"])),
    C("lg_compare_vendors", "long",
      T("Compare the pricing plans of Zoho Books, Tally Prime and Vyapar for a small business, with sources, then "
        "recommend one.", tool=["web", "research", "plan"], must=[["zoho"], ["tally"]])),
    C("lg_market_plan", "long",
      T("Make me a 30-day marketing plan for a new gym in Nagpur as a document, week by week.", tool=["make", "plan"])),
    C("lg_csv_analysis", "long",
      T("Here is sales data: Monday 12, Tuesday 18, Wednesday 9, Thursday 22, Friday 30, Saturday 41, Sunday 37 orders. "
        "Analyse it, find the trend, make a chart.", tool=["calc", "make"])),
    C("lg_hiring_pack", "long",
      T("Prepare a hiring pack for a sales executive: job post, 8 interview questions with a scoring rubric, and an "
        "offer letter template, as one Word document.", tool=["make", "plan"])),
    C("lg_competitor_web", "long",
      T("Find the top 3 coaching institutes for CA in Indore from the web and give me their fees and contact pages.",
        tool=["web", "research", "plan"])),
    C("lg_budget_sheet", "long",
      T("Build a yearly budget spreadsheet for a 10-person office: rent, salaries, software, travel, with monthly "
        "columns and formulas for totals.", tool=["make", "plan"])),

    # ================================================================ 10 make-something + two edits
    C("mk_page_bakery", "make",
      T("Make a simple web page for my bakery 'Sweet Crumbs' with a menu of 5 items and prices.", tool="make"),
      T("change the background to light pink", tool="make", must_not=LOST),
      T("add a contact section with phone 9800000000", tool="make", must_not=LOST)),
    C("mk_chart_sales", "make",
      T("Make a bar chart of my quarterly sales: Q1 4.2 lakh, Q2 5.1 lakh, Q3 3.8 lakh, Q4 6.4 lakh.", tool="make"),
      T("make it a line chart instead", tool="make", must_not=LOST),
      T("add the title 'Sales 2026'", tool="make", must_not=LOST)),
    C("mk_invoice", "make",
      T("Make an invoice PDF: customer Mehta Stores, 10 boxes tea at 450 each, 18% GST.", tool="make",
        must=[["5310", "5,310", "4500", "4,500"]]),
      T("change the quantity to 12 boxes", tool="make", must_not=LOST),
      T("add my business name 'Chai Point Traders' at the top", tool="make", must_not=LOST)),
    C("mk_app_todo", "make",
      T("Build me a small to-do list app page where I can add and tick tasks.", tool="make"),
      T("add a button to clear finished tasks", tool="make", must_not=LOST),
      T("make the font bigger", tool="make", must_not=LOST)),
    C("mk_poster", "make",
      T("Make a poster for a Holi sale, 20% off on all colours, at 'Rang Bazaar'.", tool="make"),
      T("make the discount 30%", tool="make", must_not=LOST),
      T("add the date 14 March", tool="make", must_not=LOST)),
    C("mk_sheet_inventory", "make",
      T("Make an inventory spreadsheet with columns item, stock, reorder level, and 5 sample rows.", tool="make"),
      T("add a supplier column", tool="make", must_not=LOST),
      T("highlight the rows where stock is below the reorder level", tool="make", must_not=LOST)),
    C("mk_quote_doc", "make",
      T("Make a quotation document for painting a 2BHK flat, 85,000 rupees, for client Mr. Joshi.", tool="make"),
      T("split the amount into labour 35,000 and material 50,000", tool="make", must_not=LOST),
      T("add a 15-day validity line", tool="make", must_not=LOST)),
    C("mk_landing_app", "make",
      T("Build a landing page for a yoga class: timings 6 am and 7 pm, fee 1500 a month.", tool="make"),
      T("add a testimonials section with two short quotes", tool="make", must_not=LOST),
      T("change the evening timing to 7:30 pm", tool="make", must_not=LOST)),
    C("mk_pie_expenses", "make",
      T("Make a pie chart of my expenses: rent 30%, salaries 45%, marketing 10%, other 15%.", tool="make"),
      T("make marketing 15% and other 10%", tool="make", must_not=LOST),
      T("show the percentages on the slices", tool="make", must_not=LOST)),
    C("mk_menu_card", "make",
      T("Make a menu card PDF for a South Indian cafe with 6 dishes and prices.", tool="make"),
      T("add a section for drinks with 3 items", tool="make", must_not=LOST),
      T("put the cafe name 'Dosa Corner' in bold at the top", tool="make", must_not=LOST)),

    # ================================================================ 5 memory asks across chats
    C("mem_netmitra", "memory",
      T("What did I decide about the NetMitra pricing last week?", tool=["memory"], must=[["499"]]),
      setup=[["Note this decision: for NetMitra we will price the basic plan at 499 rupees a month, starting next "
              "month. Just confirm in one line."]]),
    C("mem_supplier", "memory",
      T("Which supplier did I say I am switching to for packaging?", tool=["memory"], must=[["kavya"]]),
      setup=[["Remember this: I am switching my packaging supplier to Kavya Packers from next week. One line reply."]]),
    C("mem_meeting_day", "memory",
      T("On which day did I say my weekly team meeting happens?", tool=["memory"], must=[["thursday"]]),
      setup=[["For your memory: my weekly team meeting is every Thursday at 10 am. Just say noted."]]),
    C("mem_brand_color", "memory",
      T("What brand colour did I choose for Sweet Crumbs?", tool=["memory"], must=[["teal"]]),
      setup=[["Decision for my bakery Sweet Crumbs: the brand colour is teal. Keep it in mind, one line reply."]]),
    C("mem_target", "memory",
      T("Remind me, what monthly sales target did I set for Rang Bazaar?", tool=["memory"],
        must=[["8 lakh", "8,00,000", "800000", "800,000", "eight lakh"]]),
      setup=[["Note: the monthly sales target for Rang Bazaar is 8 lakh rupees. One line reply."]]),

    # ================================================================ 5 traps
    C("trap_ambiguous_send", "trap", T("Send it to him.", ask=True)),
    C("trap_ambiguous_report", "trap", T("Make the report.", ask=True)),
    C("trap_impossible_past", "trap",
      T("Book me a train ticket for yesterday's Rajdhani from Mumbai to Delhi.", cannot=True,
        must_not=["booked", "has been booked", "ticket is confirmed"])),
    C("trap_impossible_physical", "trap",
      T("Go to my shop and count the stock on the shelves for me right now.", cannot=True)),
    C("trap_stop", "trap",
      T("Research 10 wholesale fabric suppliers in Surat with phone numbers and make a PDF.",
        tool=["research", "web", "plan", "make"]),
      T("stop", stopped=True, must_not=LOST)),

    # ================================================================ 5 Hinglish / Marathi
    C("hi_explain_gst", "lang",
      T("GST composition scheme kya hai, 3 line mein samjhao", no_tool=True, must=[["composition"]])),
    C("hi_reminder", "lang",
      T("kal subah 9 baje mujhe bank jaane ki yaad dilana", tool="reminder", must=[["bank"]])),
    C("hi_followup_shorter", "lang",
      T("mere tiffin business ke liye ek chhota sa Instagram caption likho, sirf text", no_tool=True,
        must=[["tiffin"]]),
      T("thoda aur chhota karo", shorter=True, no_tool=True, must_not=LOST)),
    C("mr_explain", "lang",
      T("मला सांगा, छोट्या दुकानासाठी UPI QR कोड कसा वापरायचा? तीन ओळीत.", no_tool=True, must=[["upi", "qr"]])),
    C("mr_web", "lang",
      T("आज पुण्यात पेट्रोलचा भाव किती आहे? वेबवर पहा.", tool="web")),
]
