"""v0.317 HIRE AN EMPLOYEE: the owner picks an AI employee in the Employee Hub (web console or app); only then does its
desk appear on her surfaces and its 24/7 jobs run. SEO Specialist is the first one; the rest of the catalogue shows as
"coming" so she sees where Hoola is going.

States: hired -> paused -> hired (resume) ; hired / paused -> left. Letting go stops every job at once and keeps the
history read-only (nothing is deleted). One row per (tenant, employee key)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session


class HireError(Exception):
    pass


class HiredEmployee(Base):
    __tablename__ = "hired_employees"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("he"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(10), default="hired")          # hired | paused | left
    trust: Mapped[str] = mapped_column(String(10), default="seekh")           # seekh | saathi | bharosa
    settings: Mapped[str] = mapped_column(Text, default="{}")
    hired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_table() -> None:
    """Self-heal (the table is also created by db.init_db): once per database engine."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        HiredEmployee.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


TRUST = ("seekh", "saathi", "bharosa")

RETAIL_GROUP = "Retail & E-commerce"   # v0.604
HEALTHINS_GROUP = "Health Insurance"   # v0.609
FIN_GROUP = "Finance & Banking"   # v0.585 the consumer money-safety employee
VOICE_GROUP = "Voice, Meetings & Transcription"   # v0.589 the KAAN PACK employee (WhisperAI Wave W0)
FILM_GROUP = "Film, Media & Entertainment"   # v0.565 the Film Desk employee
GAME_GROUP = "Game Development, Simulation & VR"   # v0.379 the Game Desk employees' heading in the Hub
SW_GROUP = "Software Architecture, Engineering & Core Systems"   # v0.410 the Architecture Desk employees' heading
EDU_GROUP = "Education, Research & Lab"   # v0.453 the Shiksha suite + Prayogshala in the Hub (one Education Desk)
ENT_GROUP = "Enterprise Systems & ERP"   # v0.453 the ten enterprise jobs (v0.358) in the Hub; their desk is Systems
# v0.453 these employees' tools were open to every user before they joined the Hub, so hiring one only adds its desk;
# a tool must never start checking is_hired() for them (tested), or users would silently lose what they had.
EDU_OPEN = True
CONST_GROUP = "Construction & Real Estate"   # v0.512 the construction Wave-1 employees (plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md);
# the register lives at docs/research/building_industry/07_ai_employees_register.md (123 employees, tier + human gate).
# The already-live Makaan suite (sitesup / theka / propagent...) predates the Hub and keeps its own surfaces; these rows
# are the Wave-1 desks hired from the Hub. PREPARE, never CERTIFY: tier C never ships (construction/gates.py).

# The catalogue. `live` employees can be hired today; the others show as "coming".
CATALOG: dict[str, dict[str, Any]] = {
    "seo": {
        "name": "SEO Specialist", "live": True, "icon": "search",
        "pitch": "Gets your business found on Google and in AI answers. Works 24/7 on your website and Google profile.",
        "does": ["Full audit of your website every week (up to 500 pages) with a fix list",
                 "Watches your site every hour: down, blocked from Google, pages dropped",
                 "Reads your Search Console and Google Analytics: clicks, searches, leads from Google",
                 "Core Web Vitals (speed) on mobile",
                 "A 90-day plan you approve, worked as a weekly board",
                 "Weekly note and a monthly PDF report with charts"],
        "needs": ["Your website address", "Google sign-in for Search Console (and Analytics, if you use it)"],
        "never": ["Buy links or fake reviews", "Publish anything on your site or Google profile without your OK",
                  "Make mass AI pages or doorway pages", "Promise a ranking"],
    },
    "social": {"name": "Social Media Manager", "live": True, "icon": "share",
               "pitch": "Runs your Instagram and Facebook Page like a good agency: plans the month, writes the posts, learns what works.",
               "does": ["Reads your last 50 posts and their numbers: what works, when your people are online",
                        "A strategy: content themes, posting rhythm, hashtags, the one number the month is judged on",
                        "A 30-day calendar of ready posts (hook, caption in your language, hashtags, picture brief) for your OK",
                        "Indian festivals and local moments planned in",
                        "Checks your connections every hour and fresh numbers every day"],
               "needs": ["Instagram Business or Creator account and / or your Facebook Page",
                         "One login on Instagram / Facebook's own page (Hoola never sees your password)"],
               "never": ["Buy followers or likes, or use engagement pods", "Post anything without your OK",
                         "Invent prices, offers or claims", "Read or touch any account you did not connect"]},
    # v0.806 BAHI A0 (owner: 'FULL GST AND ACCOUNT EMPLOYEE --- I HAVE WHITEBOOK APIS' -> 'GO A0'; docs/ACCOUNTS_EMPLOYEE_PLAN.md):
    # live with the foundation - one register, rules as data, locks, the WhiteBooks pipe on sandbox. Hiring adds the desk and gates
    # NO existing tool (gst / paisa / office / thok / payroll stay open to every user - the EDU_OPEN law). What it does today vs
    # later is said on the desk itself (the phases list), never claimed here.
    "accounts": {"name": "GST & Accounts", "live": True, "icon": "receipt",
                 "pitch": "Your accountant that never takes a day off: every bill in one register, GST prepared and checked before the "
                          "deadlines, filed from Hoola when you give the OTP.",
                 "does": ["One register of every sale and purchase bill - from GST Sahayak, wholesale, office bills and your app - each counted once",
                          "This month's GST dates with days left, and what happens if one is missed",
                          "Flags the same bill entered in two places, and any change to a month you have locked",
                          "Rules kept as data with their source and the date they were checked - nothing remembered silently",
                          "Coming next: connect your GSTIN through WhiteBooks, then IMS, GSTR-1 and GSTR-3B filed on your OTP"],
                 "needs": ["Your GSTIN and your GST portal username (the password is never asked)",
                          "For filing: the OTP the GST portal sends you - Hoola never files without it"],
                 "never": ["Move money - a challan is a number you pay at your bank",
                           "File a return without your OTP, or keep your GST portal password",
                           "Change a month you or your CA locked - a change there becomes an amendment for you to approve",
                           "Give tax or legal advice as a professional, or certify anything"]},
    "telecaller": {"name": "Telecaller", "live": False, "icon": "phone",
                   "pitch": "Calls your leads and customers with a script, notes every answer."},
    "support": {"name": "Customer Support", "live": False, "icon": "chat",
                "pitch": "Answers customer questions on WhatsApp and email from your own FAQ."},
    # v0.686.0 LEADS EMPLOYEE (owner: "PUT THE LEAD GENERATION AI EMPLOYEE IN THE AI EMPLOYEES BUSINESS SECTION
    # OF THE WEB CONSOLE"): the P0-P5 leads engine (docs/LEADS_PLAN.md) joins the Hub's Business department.
    # The six leads tools were open to every user before this row existed, so hiring only adds the desk - no
    # leads tool starts checking is_hired() (the EDU_OPEN law, tested). NOT VERIFIED stands: her first live run
    # on each lane is the true confirmation; the desk reads the real /api/leads/* surface, nothing is faked.
    "leads": {
        "name": "Lead Generation", "live": True, "icon": "search",
        "pitch": "Finds real businesses that may need you, keeps one clean row per business with its source named, and hands a list to the WhatsApp / email desks only after your two taps. It gathers; it never contacts anyone on its own.",
        "does": ["Searches IndiaMART through IndiaMART's own official MCP, and Google Maps through the official Places routes on your account",
                 "Imports your own CSV lists and keeps ONE row per business - the same business met twice is merged, and every row carries its source (lane, URL, fetched-at) as columns",
                 "One polite pass over a kept row's own website fills empty phone / email slots only (1 request a second, robots honoured, no SMTP probes)",
                 "Shows the caps before every run: 5,000 rows per run, 20,000 per day by default - a 5,001-row ask is refused at plan time with the cap named, never silently truncated",
                 "Hands a list to the campaign desk with a CONFIRM CARD first: you see the rows, the ones without a phone and the opt-outs, and nothing is built until your second tap",
                 "Writes every real WhatsApp / email send to a ledger you can read (GET /api/leads/outreach), and honours opt-outs again at send time",
                 "Forgets a business completely on your word - the DPO duty"],
        "needs": ["IndiaMART's MCP connection for the IndiaMART lane (free)",
                  "The Google Maps key already on your account for the Places lane; place details are bought per run under a cap you set",
                  "Your explicit per-tenant opt-in before the public-listing scrape lane ever runs - it is OFF until you switch it on",
                  "A vendor's config if you want the paid vendor lane; it is priced before it runs and never retried"],
        "never": ["Contact anyone: it gathers - your two taps send",
                  "Message a person who opted out - they are refused at send time",
                  "Scrape anything until the scrape opt-in is ON",
                  "Take consumer (vyakti) lists or logins, or cross a login wall - businesses' public data only",
                  "Invent vendor rows, retry a billed vendor call, or print the vendor key",
                  "Hide a send: every real send lands in the ledger",
                  "Keep what you asked it to forget"]},
    # v0.357 ENGINEERING DESK (docs/ENGINEERING_DESK_PLAN.md): one shared locked runner, a pack per role
    "cad": {"name": "CAD Engineer", "live": True, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "Turns your words and sizes into a real 3D part: STEP and STL files plus a dimensioned drawing.",
            "does": ["Designs the part from your words (and your sizes in mm) as clean, parametric CadQuery code",
                     "Builds it in a locked box on Hoola's server and checks it: valid solid, one body, the size you asked",
                     "Gives you STEP (for any CAD / CNC shop), STL (for 3D printing), 4 views and a drawing PDF",
                     "Changes it on your words: 'holes 10 mm karo', 'wall 3 mm moti'",
                     "Keeps every version on the CAD Desk"],
            "needs": ["What the part is and its main sizes in mm (a photo of a sketch with numbers helps)"],
            "never": ["Call a design certified, approved or safe to use without a qualified engineer",
                      "Sign or stamp drawings", "Use cracked or unlicensed CAD software",
                      "Design weapons or export-controlled parts"]},
    "fea": {"name": "Structural Analysis (FEA)", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "Will the part break? Stress, deflection and safety factor with plots (CalculiX)."},
    "cfd": {"name": "CFD Engineer", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "Air and heat flow around or through your design, with plots (OpenFOAM)."},
    "acoustic": {"name": "Acoustic Simulation", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
                 "pitch": "How a room or hall sounds: echo time, sound level map, what to treat."},
    "optics": {"name": "Optical Systems Simulation", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
               "pitch": "Lens and laser paths: ray trace, spot size, focal length, tolerances."},
    "ecu": {"name": "Automotive ECU (AUTOSAR) Programmer", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
            "pitch": "C code, MISRA checks, unit tests and requirement tracing for vehicle ECUs (draft, not certified)."},
    "flight_sw": {"name": "Spacecraft Flight Software", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
                  "pitch": "Flight code review, fault handling and tests to NASA / ESA style rules (draft, not certified)."},
    "med_sw": {"name": "Medical Device Software", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
               "pitch": "Embedded code and IEC 62304 / ISO 14971 files and tests (draft for your engineers)."},
    "litho": {"name": "Chip Layout (Lithography) Software", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
              "pitch": "Layout scripts and design-rule checks on GDS files (KLayout)."},
    "iiot": {"name": "Industrial IoT Architect", "live": False, "icon": "cube", "group": "Research, CAD, Hardware & Industrial Tech",
             "pitch": "SCADA and factory network design: device list, protocols, security zones, BOM (paper only)."},
    # v0.585 PAISA SAHAYAK (register docs/research/banking_finance_industry, Wave 1 consumer slice: #1-3, 5-8)
    "paisa_sahayak": {"name": "Paisa Sahayak (money safety)", "live": True, "icon": "receipt", "group": FIN_GROUP,
                      "pitch": "On your side with money: reads a loan's real cost, finds hidden bank charges, warns about scams, and drafts the complaint. It calculates and explains; you decide and you tap.",
                      "does": ["Loan reader: EMI, every fee, the money you actually receive and the true yearly rate (APR); a 'flat rate' turned into its real rate; offers side by side",
                               "Part-payment check: interest saved against the prepayment charge you typed in",
                               "Debt planner: snowball vs avalanche vs minimums, and what happens if income drops",
                               "Statement reader: every fee-like line by kind, GST check, double debits, subscriptions, month by month spending",
                               "Scam shield: paste a message or what a caller said; it names the scam, shows the words that gave it away, checks the link without opening it",
                               "UPI safety coach and a complaint letter with an evidence list and the escalation steps (you send it)"],
                      "needs": ["Your loan offer numbers, or a CSV / Excel statement, or the message you doubt"],
                      "never": ["Ask for or keep your PIN, OTP, CVV, card number or password",
                                "Move money, place an order, or recommend a lender or a product",
                                "Give personalised investment, tax or legal advice, or promise a loan or a score",
                                "Store your statement: it reads it, answers, and forgets"]},
    # v0.602 VITT SAHAYAK (register docs/research/banking_finance_industry, Wave 2: institution assists with a named decider)
    "vitt_sahayak": {"name": "Vitt Sahayak (finance desk)", "live": True, "icon": "receipt", "group": FIN_GROUP,
                     "pitch": "A finance-desk assistant for owners, CAs and credit teams: goal and tax-date maths, TDS and ageing checks, AML and name-screening triage, credit memo drafts. It prepares and checks; the CA, analyst or committee decides.",
                     "does": ["Goal planner: monthly SIP per low / mid / high scenario, inflation-adjusted; advance-tax instalment dates",
                              "TDS in your books against 26AS / AIS rows: what matches, what to ask the party",
                              "Receivables / payables ageing by party, and purchase-order / receipt / invoice three-way matching",
                              "AML alert triage with a draft narrative for the analyst, and name screening against YOUR watch list with the reason for every score",
                              "Credit memo draft: ratios from the financials, checks against YOUR policy floors, blanks for the officer"],
                     "needs": ["Rows you paste (books, invoices, transactions, financials) and, where relevant, your own thresholds, watch list or policy floors"],
                     "never": ["File an STR, a return or an ITR, or approve / decline a loan",
                               "Decide a true sanctions match, block or freeze an account, or sign anything",
                               "Move money or run a payment: that is the approver's tap",
                               "Store your rows: it reads them, answers, and forgets"]},
    # v0.603 RISK DESK (register docs/research/banking_finance_industry, Wave 3: markets and credit; prepare and check, a named person decides)
    "risk_desk": {"name": "Risk Desk (markets and credit)", "live": True, "icon": "receipt", "group": FIN_GROUP,
                  "pitch": "Prepares the papers a markets or credit desk works from: an order ticket for your confirm, portfolio-limit checks, underwriting rule hits with reason codes, key fact statements, past-due ageing, loss provisioning and valuation worksheets. It never places an order or decides a loan.",
                  "does": ["Order ticket: size, price sanity, concentration and charges (from rates you give) before you confirm; the order itself only goes on your tap through your broker's official connector",
                           "Portfolio check against YOUR mandate: weights, drift, limit breaches, margin use, rebalance proposals for the manager",
                           "Underwriting rule hits with reason codes from YOUR policy; rules on religion, caste, gender or locality are refused",
                           "Key fact statement draft, past-due (SMA / NPA) ageing, expected-credit-loss working paper",
                           "DCF worksheet with a sensitivity grid; fraud velocity rule hits and round-trip trade flags for the analyst"],
                  "needs": ["Rows you paste and your own limits, rules, rates and assumptions: nothing is built in"],
                  "never": ["Place, modify or cancel an order, or move money: only your explicit tap through the broker's official connector can",
                            "Say what to buy or sell, promise returns, or act as a registered adviser or analyst",
                            "Approve or decline a loan, classify an account as NPA, or start recovery",
                            "Block an account or accuse anyone: alerts are evidence for the analyst or compliance officer",
                            "Store your rows: it reads them, answers, and forgets"]},
    # v0.604 DUKAAN DESK (register docs/research/retail_ecommerce_industry, Wave 1: kirana and small online seller copilots; prepare and check, the owner decides)
    "dukaan_desk": {"name": "Dukaan Desk (shop and online seller)", "live": True, "icon": "receipt", "group": RETAIL_GROUP,
                    "pitch": "A copilot for a shop or a small online seller: the day's sales, what to reorder, what is stuck or expiring, margin and MRP checks, oversell and return-risk warnings, settlement matching and GST split. It prepares and checks; you set prices, place orders and publish.",
                    "does": ["Daily summary: total, cash / UPI / credit split, best hour, top items; weekly sales forecast with your own festival multipliers",
                             "Reorder quantities with the formula shown, fast and slow movers, expiring stock and the cash stuck in dead stock",
                             "Margin and MRP check (selling above MRP, selling below cost) and a licence / GST date calendar",
                             "Oversell check across your website and marketplaces; return-risk score per order with reasons",
                             "Settlement vs sales matching, product-claim check for listings, GST split, and for shoppers: true landed cost and scam signals"],
                    "needs": ["Rows you paste or say: sales, stock, orders, settlements, offers. Your own dates, licences and festival multipliers"],
                    "never": ["Change a price, discount, refund, listing or order, or place a supplier order: those are your tap",
                              "Block or blacklist a customer: a risk score is a heads-up, not a verdict",
                              "Publish a product claim or call anything genuine, organic or certified without your proof",
                              "File GST or issue an invoice: your CA / you do",
                              "Store your rows: it reads them, answers, and forgets"]},
    # v0.607 RETAIL GROWTH (register docs/research/retail_ecommerce_industry, Wave 2: growth and operations assists with a named owner / manager)
    "retail_growth": {"name": "Retail Growth (owner / manager copilot)", "live": True, "icon": "receipt", "group": RETAIL_GROUP,
                      "pitch": "Turns your rows into proposals: markdown steps for near-expiry stock, price checks inside your floor and MRP, scheme accruals, retailer credit exposure, unit economics, visit order and cash cycle. It proposes; you decide and you tap.",
                      "does": ["Markdown steps for near-expiry stock that never cross your floor or MRP, with the waste still at risk",
                               "Price rule check against competitor prices you give: proposed price, why, and anything that moves more than your cap",
                               "Scheme accrual vs retailer claims, retailer credit exposure against your own limit multiple, working-capital days",
                               "Unit economics (contribution, LTV / CAC), ABC range review, loyalty lists for customers who opted in only",
                               "Beat visit order and delivery batches by area"],
                      "needs": ["Rows you paste, and your own floors, caps, schedules and multipliers: nothing is built in"],
                      "never": ["Change a price, scheme, credit limit, route or listing: those are your tap",
                                "Message a customer or sell a list: loyalty lists carry only people who said yes, and nothing is sent",
                                "Scrape marketplaces or competitor sites: competitor prices are only those you give",
                                "Use caste, religion, area or other personal attributes for credit or pricing",
                                "Store your rows: it reads them, answers, and forgets"]},
    # v0.607 RETAIL TRUST (register docs/research/retail_ecommerce_industry, Wave 3: platform trust, fraud, compliance; investigators decide)
    "retail_trust": {"name": "Retail Trust (fraud and compliance desk)", "live": True, "icon": "receipt", "group": RETAIL_GROUP,
                     "pitch": "Evidence for the people who decide on a marketplace or store: fraud and return-abuse rule hits, fake-review signals, seller KYC format checks, label and dark-pattern checklists, grievance deadlines, delivery-promise honesty, model override rates and pricing fairness. It flags; a named person decides.",
                     "does": ["Fraud rule hits (order bursts, shared addresses and devices, high-value COD) with the rule shown, and return-abuse lists above your threshold",
                              "Review authenticity signals, seller KYC checks (GSTIN check digit, PAN inside GSTIN, IFSC, bank name) and missing documents",
                              "Dark-pattern text and checklist audit, Legal Metrology label checklist, grievance acknowledge / resolve clock",
                              "Delivery-promise audit with an honest promise hint, AI-model override rates, price spread between customer segments"],
                     "needs": ["Rows you paste and your own thresholds; deadlines and label lists are from memory and marked verify"],
                     "never": ["Ban, block, refund, fine or remove anyone or anything: a rule hit is evidence, not a verdict",
                               "Accuse a customer, seller or worker, or profile a customer",
                               "Decide a takedown, a seller approval or a grievance outcome",
                               "Check that a GSTIN or bank account really exists: only its format and check digit",
                               "Store your rows: it reads them, answers, and forgets"]},
    # v0.609 BIMA DESK (health-insurance register Wave 1: customer side + admin)
    "bima_desk": {"name": "Bima Desk (health-insurance claims and servicing)", "live": True, "icon": "receipt", "group": HEALTHINS_GROUP,
                  "pitch": "A coworker for the policyholder, the broker desk and the claims-admin team: what documents a claim needs, a transparent payable worksheet, why a settlement came out lower, appeal outlines, renewals and grievance clocks. It prepares; the insurer, the TPA or a named officer decides.",
                  "does": ["Claim document checklist (cashless or reimbursement) with missing items and filing deadlines",
                           "Itemised payable worksheet (non-payables, tariff caps, room-rent proportion, co-pay, deductible) and the gap to the settled amount",
                           "Settlement vs payment match (UTR, TDS, short / excess / duplicates), claim ageing against a timeline you set",
                           "Renewal reminders, grievance triage with due dates, rejection-appeal outline, status-update drafts, KYC format checks"],
                  "needs": ["Rows you paste and the policy terms you read; periods and rules are from memory and marked verify"],
                  "never": ["Approve, reject, reduce or settle a claim, or give a medical opinion on necessity",
                            "Give legal advice or tell anyone to switch insurers",
                            "Send a message, file an appeal or store your documents: it drafts and checks, you send",
                            "Verify an ID with any authority: format checks only, Aadhaar shown masked"]},
    # v0.610 BIMA ASSIST (health-insurance register Wave 2: assists with a named human decider)
    "bima_assist": {"name": "Bima Assist (adviser, claims and compliance desk)", "live": True, "icon": "receipt", "group": HEALTHINS_GROUP,
                    "pitch": "Drafts and flags for the people who decide: plan side-by-sides, disclosure prompts, coverage and waiting-period checks with the clause shown, pre-auth checks, query replies, medical timelines, rejection and grievance letters, ombudsman packets, wording and mis-selling reviews, FHIR claim skeletons and code maps.",
                    "does": ["Plan comparison from the numbers you give, material-fact prompts, proposal completeness check",
                             "Coverage and exclusion checks (waiting periods, moratorium, sub-limits, room-rent proportion) with each line tied to the clause you supplied",
                             "Pre-auth checks, query-reply drafts from the chart, medical timeline with gaps, rejection and grievance letter drafts (no clause, no letter)",
                             "Ombudsman packet index and dates, policy-wording and mis-selling reviews, FHIR Claim skeleton, code mapping from your table"],
                    "needs": ["Policy terms, clause text, package rates and code tables from you; periods are from memory and marked verify"],
                    "never": ["Approve, deny, reduce or settle a claim, accuse anyone of fraud or mis-selling, or give a medical opinion",
                              "Sign or send a letter, file with an ombudsman or submit to NHCX",
                              "Recommend a plan or tell anyone to switch insurers: suitability is the adviser's and the customer's call",
                              "Store your documents: it reads, drafts and forgets"]},
    # v0.611 BIMA RISK (health-insurance register Wave 3: pricing, underwriting and fraud signals)
    "bima_risk": {"name": "Bima Risk (actuary, underwriting and SIU desk)", "live": True, "icon": "receipt", "group": HEALTHINS_GROUP,
                  "pitch": "Worksheets for the people who decide: loss ratio and frequency by group, a run-off triangle working paper, premium-vs-cost fairness checks, underwriting rule routing with the rule shown, provider and duplicate-claim outliers, cashless-upgrade flags, a neutral case file and a fairness audit of the fraud model. Hits are questions, not verdicts.",
                  "does": ["Experience tables (loss ratio, frequency, severity, thin groups marked), observed price trends, chain-ladder triangle as a working paper",
                           "Pricing-fairness gaps and jumps on the relativities you give; protected attributes refused as factors",
                           "Underwriting triage from YOUR manual: which rule fired, the manual page, the loading you set; a decline rule becomes a human referral",
                           "Provider outliers, overlapping stays, geo plausibility, cashless upgrades, a neutral case file with the allegation left blank, fraud-model flag-rate and false-positive audit, scheme anomalies"],
                  "needs": ["Your rows, thresholds, rules, loadings and peer sets; nothing is built in except keyword-free arithmetic"],
                  "never": ["Decline, price, load, reserve, sign off a rate, blacklist or accuse anyone of fraud: those are the actuary's, underwriter's and SIU head's",
                            "Use religion, caste, gender, locality or name as a rule or rating factor",
                            "Share data with any industry database or store your rows: it reads, answers and forgets"]},
    # v0.589 KAAN PACK (WhisperAI Wave W0: the transcription core; engine = openai-whisper MIT, local-first)
    "kaan": {"name": "Kaan (transcription)", "live": True, "icon": "ear", "group": VOICE_GROUP,
             "pitch": "Audio sun-kar likhawat: a meeting, voice note or video file becomes a clean transcript with per-word timing, on your own server.",
             "does": ["Transcribe an audio / video file from chat into text (mp3, wav, m4a, ogg, flac... up to 5 GB)",
                      "Detect the language (hi, mr, en... 90+), or you name it; translate-to-English on the capable models",
                      "Per-word timestamps for subtitles and precise edits",
                      "Your transcripts are stored, listed, re-opened and searched by what was said",
                      "Engine status made honest: gate, model ladder (tiny to large-v3), what is missing, all in one status"],
             "needs": ["The audio / video file sent in chat (or its file id)"],
             "never": ["Send your audio anywhere: engine and files stay on your server (KAAN_AUDIO=1 turns it on)",
                       "Record or transcribe while the AUDIO gate is off",
                       "Guess a transcript it did not hear: silence is reported as silence, never filled in"]},
    # v0.565 FILM DESK producer layers (script coverage, previs, schedule, budget, festivals, windows, deliverables, royalties)
    "film": {"name": "AI Film Producer", "live": True, "icon": "game", "group": FILM_GROUP,
             "pitch": "A film producer's coworker: script facts, shot-list checks, shooting schedule, rate-card budget, festivals, release windows, deliverables and royalty sums.",
             "does": ["Reads your script and counts it: scenes, characters, who speaks how much, places, night scenes, and flags worth a second look",
                      "Checks the shot list: timing, missing cameras, scenes with no shot, speech that cannot fit its shot",
                      "Plans the shoot: days grouped by place, day-out-of-days, call sheet with blanks for what only you know",
                      "Budget from YOUR rate card only; festival deadlines, release windows and holdbacks from YOUR facts",
                      "Deliverables and subtitle / dub tracker; an AI voice is held unless that person's recorded consent covers it",
                      "Royalty sums from the terms you type in from your contract, exact to the paisa"],
             "needs": ["A film (title and logline) and your script, or let Hoola write a first one from your words"],
             "never": ["Invent a rate, fee, deadline, holdback or guild table: every number is yours, with its source",
                       "Give a reader's verdict (pass / consider / recommend) or a rating",
                       "Send, submit, sign or pay anything: messages and release are cards for your tap",
                       "Use a real person's face or voice without their recorded consent"]},
    # v0.379 GAME DESK (docs/GAME_DESK_PLAN.md): one shared desk, a pack per role; Phase 1 = the Game Developer
    "game_dev": {"name": "Game Developer", "live": True, "icon": "game", "group": GAME_GROUP,
                 "pitch": "Makes original games from your words with Godot 4, tests them itself and gives you a link to play on any phone.",
                 "does": ["Writes a short design doc first: you OK it or change it",
                          "Builds the game in Godot 4 (free, open source) for the phone browser",
                          "Plays it itself before you see it: frame rate, taps and keys, screenshots, script errors",
                          "Fixes its own mistakes from the real errors (up to four rounds)",
                          "A private play link and QR, plus the whole Godot project as a zip",
                          "Changes in your words make a new version; the last good one keeps working"],
                 "needs": ["Your idea in two or three lines (what you do, how you win, who it is for)"],
                 "never": ["Copy a specific existing game, its characters, levels or art",
                           "Real-money, betting or gambling games", "Cheats, bots for other people's games, weapon targeting",
                           "Share your game anywhere: the link is private until you share it"]},
    # v0.422 Phase 7 batch 3 (docs/GAME_DESK_PLAN.md phase 4)
    "xr_dev": {"name": "AR / VR Interaction Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
               "pitch": "A WebXR room that opens in a phone or headset browser, with hand gestures and comfort rules checked.",
               "does": ["Sets up VR or AR with teleport, snap turning and a seated mode",
                        "Checks comfort in code: panel distance, text size, no forced camera motion",
                        "Hand gestures (pinch, grab, point) scored on a test set and checked in Godot itself",
                        "A walk-in demo room you open in your headset or phone browser",
                        "Your OK puts it into your game (HoolaXR)"],
               "needs": ["VR or AR, and the device (a headset or a phone)"],
               "never": ["Claim frame rates on your headset it has not measured", "Use smooth turning (a sickness cause)"]},
    "netcode_dev": {"name": "Multiplayer Network Programmer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Netcode for your game - server, prediction, lag compensation - proved by bots on bad networks; "
                             "the server runs on your own cloud.",
                    "does": ["Designs tick rate, send rate and interest range from your numbers",
                             "Bots play over good, 150 ms / 2 % loss and bad mobile networks",
                             "Measures rubber-banding, desync (must be 0), bandwidth and lag-compensation hits",
                             "Runs the Godot netcode itself with a server and three clients",
                             "A kit: a game server for your cloud (Docker) and the client code"],
                    "needs": ["How many players, how fast they move, and your own cloud for the server"],
                    "never": ["Host your game server on Hoola", "Claim the network part works before it runs on your server"]},
    # v0.420 Phase 7 batch 1 (docs/GAME_DESK_PLAN.md phase 2): each role is a PACK on the shared Game Desk
    "physics_dev": {"name": "Physics Engine Developer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Sets up your game's physics and proves it in the real engine: falling, jumping, bouncing and "
                             "fast bullets checked against textbook answers.",
                    "does": ["Takes your numbers (fastest thing, thinnest wall, gravity) from your words or your Game Bible",
                             "Works out tick rate and continuous collision in code so nothing passes through walls",
                             "Runs a physics lab in Godot itself: free fall, jumps, bounces, a box stack, 3D, run twice",
                             "Every case compared with the formula; failures are named, never hidden",
                             "Your OK puts the proven settings and jump helpers into your game"],
                    "needs": ["A game on the Game Desk (or just your numbers)"],
                    "never": ["Claim a number the lab did not measure", "Change your game before your OK",
                              "Fluid simulation (not built yet - said plainly)"]},
    # v0.423 Phase 7 batch 4 (docs/GAME_DESK_PLAN.md phase 5)
    "sim_dev": {"name": "Simulation Software Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
                "pitch": "Flight, space and driving training models, each validated against a textbook case, with cited data "
                         "and repeatable scenarios.",
                "does": ["Orbits (two-body + J2), a light-aircraft glide model or a car's handling model",
                         "Checks each against its textbook answer: orbit period, node drift, glide angle, phugoid, yaw rate",
                         "States the data source, the time step and the integrator; every scenario runs twice the same",
                         "A log (CSV) and a plot; an orbit model can go into your game (HoolaSim)"],
                "needs": ["What should be simulated, and the numbers you have"],
                "never": ["Weapon targeting, missile or combat simulators", "Call itself a certified flight training device"]},
    "procgen_dev": {"name": "Procedural World Generation Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "Islands, dungeons, cities and platform levels from rules and a seed - checked playable, "
                             "previewed, and walkable in your browser.",
                    "does": ["Makes terrain (biomes, rivers, villages), dungeons, cities or side-view levels from your words",
                             "Same seed = same world, proved by making it twice",
                             "Checks every village, room, exit and goal can be reached; a level is walked with your jump",
                             "A preview picture, a walk-it link, world.json, heightmap and a 3D .glb mesh",
                             "Your OK puts the world into your game (HoolaWorld) without new code"],
                    "needs": ["Two lines: what kind of world, how big, anything special"],
                    "never": ["Copy a real game's map or levels", "Put a world in your game before your OK"]},
    "vfx_td": {"name": "VFX Pipeline Technical Director", "live": True, "icon": "game", "group": GAME_GROUP,
               "pitch": "A CG pipeline for your shots: naming and versions, ACES colour end to end, EXR frames, a render queue "
                        "with cost per shot.",
               "does": ["Shot and file naming with versions that only go up",
                        "Colour from camera / texture to ACEScg to your screen, converted and measured",
                        "Writes a real ACEScg EXR test frame and reads it back",
                        "Plans the render queue: failed frames re-queued, cost per shot, every frame traced to its scene",
                        "A kit with the manifest and a Blender render script for your machines"],
               "needs": ["Your shots (frame ranges), your sources and your farm's size and rate"],
               "never": ["Claim Blender / OpenColorIO ran here (they are not installed on the server)"]},
    # v0.421 Phase 7 batch 2 (docs/GAME_DESK_PLAN.md phase 3)
    "audio_dev": {"name": "Spatial Audio Systems Programmer", "live": True, "icon": "game", "group": GAME_GROUP,
                  "pitch": "3D sound for your game - direction, distance, walls and room echo - measured, with headphone "
                           "demos you can hear.",
                  "does": ["Designs reverb zones (room, hall, cave...) and distance / wall settings from your words",
                           "Renders binaural headphone demos: a sound walking round your head, distance, each zone",
                           "Measures everything: ear-to-ear timing per direction, 6 dB per doubling, each zone's echo time",
                           "Demos at a measured -16 LUFS, never clipping",
                           "Your OK puts the zones, wall and distance settings into your game (HoolaAudio)"],
                  "needs": ["The places in your game (a cave, a hall, outdoors...)"],
                  "never": ["Claim front / back or height cues a round-head model cannot give (said plainly)",
                            "Change your game before your OK"]},
    "twin_arch": {"name": "Digital Twin Architect", "live": True, "icon": "game", "group": GAME_GROUP,
                  "pitch": "A twin of your line or shop floor with what-if simulation - every number traced to your data or "
                           "a stated assumption; it reads, never controls.",
                  "does": ["Your stations, machines, cycle times, breakdowns and shifts as a model",
                           "Simulates throughput, utilisation, work in progress, lead time and the bottleneck",
                           "What-ifs: one more machine, a faster station, a second shift - with the same random numbers",
                           "Checks its own engine against exact answers and queueing theory, and against your real week",
                           "A layout picture with each station's load"],
                  "needs": ["Your stations and their numbers (or your data tags), and one real week's output"],
                  "never": ["Write, command or control anything in your plant", "Call a twin validated without your real week",
                            "A 3D twin view (not built yet)"]},
    "haptics_dev": {"name": "Haptic Feedback Systems Engineer", "live": True, "icon": "game", "group": GAME_GROUP,
                    "pitch": "One vibration pattern per meaning for your game, phone apps and your own device - checked, "
                             "with an off switch for every player.",
                    "does": ["Picks a pattern for each moment you name (jump, coin, hit, game over...)",
                             "Checks pulse length for the motor, gaps you can feel, and that no two patterns feel the same",
                             "States battery cost per play",
                             "Exports iPhone Core Haptics files, Android code and a DRV2605 driver (compiled here)",
                             "Your OK puts them into your game (HoolaHaptics) with an off switch and intensity"],
                    "needs": ["The moments that should buzz, and the device (phone, controller or your own board)"],
                    "never": ["Buzz for everything", "Ship patterns without an off switch",
                              "Promise vibration in iPhone browsers (they have none)"]},
    # v0.410 SOFTWARE ARCHITECTURE, ENGINEERING & CORE SYSTEMS (docs/SOFTWARE_DESK_PLAN.md). Code they write goes to HER
    # GitHub through the Developer Sahayak's draft PR + CI path; heavy builds run in HER CI, never on her PC.
    "architect": {"name": "Principal Software Architect", "live": True, "icon": "code", "group": SW_GROUP,
                  "pitch": "Designs your system the way a principal architect would: decisions, diagrams, capacity and risks - "
                           "then checks every pull request against it.",
                  "does": ["Reads your GitHub repo first (read only) or starts from your idea for a new system",
                           "Writes the architecture: context, quality targets, components, data, main flows, security",
                           "Draws the diagrams: system context, containers, the main flow, deployment",
                           "Decision records (ADRs) with the options it did not pick and why",
                           "Capacity worked out in code from your numbers: requests per second, storage, servers",
                           "Risks, failure modes, a phased roadmap and the questions it needs answered",
                           "A PDF you can hand to your team; changes in your words make the next version",
                           "Reads your pull requests against the approved design (on its own if you switch it on)"],
                  "needs": ["What the system must do, who uses it and roughly how many people a day",
                            "Optional: your GitHub repo (connected once in the Developer Sahayak)"],
                  "never": ["Push, merge or deploy anything - its PR notes go out only on your tap",
                            "Run your code on its server or touch your PC",
                            "Make up scale numbers: no users-a-day number, no capacity sheet",
                            "Call a design approved by a certified authority"]},
    "compiler_eng": {"name": "Compiler Construction Engineer", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Domain-specific languages: grammar, parser, interpreter or compiler with golden tests."},
    "kernel_dev": {"name": "Kernel / OS Developer", "live": False, "icon": "code", "group": SW_GROUP,
                   "pitch": "Kernel patches, drivers and crash-log diagnosis; boot-tested in QEMU in your own CI."},
    "graphics_eng": {"name": "Graphics Engine Programmer", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Renderers and shaders (Vulkan, ray tracing): shader validation and CPU-rendered checks."},
    "dbengine_dev": {"name": "Database Engine Developer", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Query plans and indexes from your real database, storage and query-engine code, benchmarks."},
    "distsys_eng": {"name": "Distributed Systems Engineer", "live": False, "icon": "code", "group": SW_GROUP,
                    "pitch": "Consensus, retries, idempotency and failover - with failure-injection tests and formal specs."},
    "hypervisor_eng": {"name": "Virtualization / Hypervisor Engineer", "live": False, "icon": "code", "group": SW_GROUP,
                       "pitch": "Container runtimes and VMs: configs, security profiles and hardening, tested in your CI."},
    "lowlatency_eng": {"name": "Backend Systems Engineer (Low Latency)", "live": False, "icon": "code", "group": SW_GROUP,
                       "pitch": "Lock-free, zero-copy hot paths with microbenchmarks and p99 analysis of your latency data."},
    "mainframe_arch": {"name": "Mainframe Modernization Architect", "live": False, "icon": "code", "group": SW_GROUP,
                       "pitch": "COBOL inventory, dependency map and migration plan; translations proved side by side."},
    "refactor_eng": {"name": "Legacy Code Refactoring Specialist", "live": False, "icon": "code", "group": SW_GROUP,
                     "pitch": "Maps the worst code, writes tests first, then many small safe refactor PRs, each green on CI."},
    # v0.453 EDUCATION, RESEARCH & LAB: the Shiksha suite (v0.381 / v0.387 / v0.403) and Prayogshala (v0.415 / v0.441) were
    # live on the server and the phone but never in the Hub. Hiring one adds the Education Desk to the console sidebar; it
    # does NOT gate the tools - every user had them before this version and keeps them (see EDU_OPEN).
    "tutor": {"name": "Personal Tutor (Guru Sahayak)", "live": True, "icon": "book", "group": EDU_GROUP,
              "pitch": "Teaches one learner at a time: a hint first, then a step, the full answer last - and practice that comes back before it is forgotten.",
              "does": ["Explains a doubt with a hint ladder, one rung each time the learner asks",
                       "Checks an answer with code or the answer key before calling it right",
                       "Practice and revision on a spaced schedule, with an exam-mode window",
                       "An NCERT mastery path with gates: the next chapter opens once this one is learnt",
                       "Practice in the learner's own language",
                       "A weekly progress report for the guardian, sent only on your tap"],
              "needs": ["The learner's class, subjects and the language to teach in",
                        "For a child under 18: the guardian's consent and a daily time limit"],
              "never": ["Write the answer to graded homework, a test or an exam (hints and explanations only)",
                        "Work with a child without the guardian's consent, or past the daily time you set",
                        "Share a child's details or report with anyone but the guardian, and that only on your tap",
                        "Call an answer certain when no code or answer key checked it"]},
    "school_office": {"name": "School Office Assistant (Daftar)", "live": True, "icon": "book", "group": EDU_GROUP,
                      "pitch": "Runs the school office: attendance, grading, timetable and report cards - with every mark signed off by the teacher.",
                      "does": ["Daily attendance and an absence alert card for each guardian, sent on your tap",
                               "Grades answer sheets, OMR sheets, Google Forms quizzes, code and rubric work",
                               "Its marks are suggestions until the teacher signs them off",
                               "Builds the timetable from periods, teachers and subjects",
                               "Report cards made only from signed-off marks"],
                      "needs": ["Classes and sections, periods per day", "Teachers and their subjects, term names and your grade scale"],
                      "never": ["Make a mark final without the teacher's sign-off",
                                "Handle a child's marks or attendance without the guardian's consent",
                                "Send a guardian a message, alert or report card without your tap, or to any other child's guardian",
                                "Send bulk WhatsApp messages by itself"]},
    "curriculum": {"name": "Curriculum & Exam Designer (Pathyakram)", "live": True, "icon": "book", "group": EDU_GROUP,
                   "pitch": "Question banks, board-pattern papers with answer keys, year and lesson plans, and rubrics - every item approved by a teacher.",
                   "does": ["A question bank where every AI question is a draft until a teacher approves it",
                            "Papers in your board's pattern with an answer key and blueprint",
                            "Year plans, lesson plans and marking rubrics",
                            "Swaps a question in a paper without rebuilding it",
                            "Shares a paper or plan only when the teacher taps"],
                   "needs": ["Your board (CBSE / ICSE / state), classes, subjects, medium and session"],
                   "never": ["Copy copyrighted syllabus or textbook text (chapter names, codes and official links only)",
                             "State a board pattern or marks as certain without a source - it says 'estimate'",
                             "Send a paper, quiz or plan out without the teacher's or your tap",
                             "Touch a leaked or 'leaked' exam paper"]},
    "research": {"name": "Research Assistant (Shodh)", "live": True, "icon": "book", "group": EDU_GROUP,
                 "pitch": "Finds and reads the literature through official scholarly APIs, maps the gaps and keeps your references exact.",
                 "does": ["Searches OpenAlex, Crossref, arXiv and PubMed; every DOI is checked on Crossref",
                          "Screens papers against your question and summarises the ones that pass",
                          "A review matrix and the research gaps across the papers",
                          "References in BibTeX or RIS in your university's style",
                          "Data analysis as code in a locked sandbox, so every number can be traced",
                          "Section drafts that carry an AI-assistance note"],
                 "needs": ["Your topic, field and citation style", "Optionally an email address for polite use of the scholarly APIs"],
                 "never": ["Cite a paper or reference no official API returned",
                           "Write a thesis, assignment or paper for you to submit as your own",
                           "Put a number in the results that the analysis did not produce",
                           "Get past a paywall (only legal open-access copies)"]},
    "school_register": {"name": "School Register (Shiksha)", "live": True, "icon": "book", "group": EDU_GROUP,
                        "pitch": "The school's register: classes, learners, guardian consent and the gradebook every other education employee works from.",
                        "does": ["Classes, sections and learners in one register",
                                 "Guardian consent recorded per learner before any child's data is used",
                                 "A shared question bank across classes",
                                 "The gradebook, where only teacher-signed marks are final"],
                        "needs": ["Your institution, board, medium and academic year"],
                        "never": ["Use a child's details without the guardian's consent",
                                  "Show marks to anyone but the learner's own guardian",
                                  "Treat an AI mark as final"]},
    "lab": {"name": "Virtual Science Lab (Prayogshala)", "live": True, "icon": "book", "group": EDU_GROUP,
            "pitch": "22 NCERT physics practicals in a realistic 3D lab: real equipment, the steps, the record book, the graph and the viva.",
            "does": ["Theory, steps, record book, graph and viva for each practical",
                     "Readings computed by the same physics code that checks them, within 1 %",
                     "Ask Hoola inside any lab when a step is unclear",
                     "Works on a phone or a computer, no install"],
            "needs": ["Nothing: open a lab and start"],
            "never": ["Show a reading its own physics code did not compute",
                      "Stand in for a practical your board requires to be done in a real lab"]},
    "erp": {"name": 'ERP Architect (SAP / Oracle)', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Reads your SAP or NetSuite modules and fields and turns them into integration specs, field mappings and migration sheets.',
        "does": ['Integration specs, field mappings and migration sheets from your real system', 'The whole ERP lifecycle as one desk: blueprint, data, security, testing, cutover, support', 'Reads run at once; every write goes plan, dry run, your tap, then verified'],
        "needs": ['Your own SAP or NetSuite connection, joined on the Systems page (the key is sealed)'],
        "never": ['Make an ERP entry without your tap', 'Delete records, at any size', 'Work without saying whether it is the production or the test system']},
    "crm_arch": {"name": 'CRM Architect (Salesforce)', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Reads your Salesforce objects, flows and permissions and plans the customisation, with a test list.',
        "does": ['Describes your org and runs read-only SOQL', 'Customisation plans, security matrices and test lists', 'Configuration changes go through a validated deploy that you approve'],
        "needs": ['Your Salesforce org, joined with your own login'],
        "never": ['Change your live org without your tap', 'Delete records, at any size', 'Guess whether a change is data or configuration']},
    "tpm": {"name": 'Technical Product Manager', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'The engineering side of delivery: dependencies, architecture decisions, NFRs, tech debt, capacity, release train and risks.',
        "does": ['Critical path, capacity and delivery metrics worked out in code, never guessed', 'RAID log, release readiness and who has gone quiet', 'Status built only from what each owner actually said'],
        "needs": ['Your tracker (Jira / Linear / Asana) or a sheet of the work'],
        "never": ['Promise a date to anyone on your behalf', 'Write a status the team did not give', 'Change your tracker without your tap']},
    "bpa": {"name": 'Process Automation Architect', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Connects the work between two systems as a step-by-step flow and runs it.',
        "does": ['Designs the flow between your apps (Composio, SAP, Oracle, Salesforce)', 'Runs it on one test record first, then on all', 'Every writing step passes the trust gate'],
        "needs": ['The apps you want joined, connected with your own accounts'],
        "never": ['Run a flow on all records before a test record passed and you said yes', 'Write to another system without its trust gate']},
    "ecom_arch": {"name": 'E-Commerce Systems Architect', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Checks your catalogue, stock, prices and checkout - what breaks under a rush - and fixes listings.',
        "does": ['Catalogue, stock, price and checkout checks on your own store', 'Load-risk notes: what fails when traffic spikes', 'Listing fixes drafted for your OK'],
        "needs": ['Your Shopify store or a sheet of your catalogue'],
        "never": ['Change a price or the catalogue without your tap', 'Use a stock number that was not read from your store']},
    "health_int": {"name": 'Healthcare Integration (HL7 / FHIR)', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'The ABDM paperwork end to end: FHIR R4 record structure, the ABHA flow, the M1 / M2 / M3 checklist and audit papers.',
        "does": ['FHIR R4 structures and sample data', 'ABHA flow and milestone checklists', 'Audit-ready documents'],
        "needs": ["Your hospital or clinic's systems described in a sheet"],
        "never": ["Read or send any real patient's data", "Take the ABDM production route on your behalf - that stays in your organisation's name"]},
    "bank_int": {"name": 'Core Banking Integrator', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Statement reconciliation, ledger matching, reporting formats and the Account Aggregator readiness checklist.',
        "does": ['Reconciliation by reference, then amount and date together', 'Ledger matching where each line is used once', 'Account Aggregator readiness checklist'],
        "needs": ['Statements and your Tally or ledger export'],
        "never": ['Move money or connect to a bank directly (RBI rules: only a regulated entity can be an FIU)', 'Write a full account number - last 4 digits only']},
    "supply_opt": {"name": 'Supply Chain Optimisation', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'The cheapest plan across routes, warehouses and orders, reorder points and stock levels - savings shown in rupees.',
        "does": ['Reorder points from real demand and lead time', 'Dead stock and stockout dates', 'Every saving shown with its working'],
        "needs": ['At least 14 days of sales and stock history'],
        "never": ['Place an order - you place it', 'Show a saving without the calculation behind it']},
    "plm": {"name": 'PLM Specialist', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'Reads Windchill parts, BOMs and change orders and drafts the change with its impact.',
        "does": ['BOM explosion with costs rolled up from the parts', 'Where-used for any part', 'Change drafts with their impact'],
        "needs": ['Your Windchill server (Teamcenter is read-only)'],
        "never": ['Write to a BOM without your tap', 'Leave your object checked out after a half-finished run']},
    "regtech": {"name": 'RegTech / Compliance Automation', "live": True, "icon": "code", "group": ENT_GROUP,
        "pitch": 'A compliance calendar that watches every date, prepares the filing papers and warns when a rule is about to break.',
        "does": ['Due-date calendar with the source of every date', 'Filing papers prepared', 'Exposure worked out only from penalty figures you gave'],
        "needs": ['The returns and registrations your business has'],
        "never": ['File on a government portal for you - you file', 'Give legal advice: it cites the rule, not an opinion']},
    # v0.512 CONSTRUCTION & REAL ESTATE - Wave 1 (records and money, register #s in brackets; tier A; the tier-C
    # refusals ride construction/gates.py and every tool description)
    "const_store": {"name": 'Material Store Manager (Saaman)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Store ka hisaab: GRN, issue, stock, barbadi - the sheet the store in-charge signs.',
        "does": ['Goods received notes with challan / invoice numbers (#61)', 'Issues to gangs and sites, min-max reorder alerts',
                 'Reconciliation: received vs issued vs on-hand with the wastage %'],
        "needs": ['Your item list and reorder levels (Hoola learns them as you go)'],
        "never": ['Order anything itself - the indent card waits for your tap', 'Invent a rate, a quantity or a vendor']},
    "const_labour": {"name": 'Labour & Wages Desk (Mazdoor Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Muster, licences, wage audit and the BOCW cess / TDS arithmetic - determined numbers only.',
        "does": ['Daily muster rolls (#85), contract-labour licence and BOCW renewal calendar',
                 'Wage-audit working paper with the trail: workers x days x rate, OT rule stated (#87)',
                 'BOCW cess 1% and Sec 393(1) TDS from the state pack - a stale pack refuses to answer (#90)'],
        "needs": ['Your wage rates with their source (Hoola never supplies a minimum wage from memory)'],
        "never": ['Move money - wages are paid by you, recorded after', 'File a licence or a return for you',
                  'Give the minimum wage from memory - the pack cites, it never guesses']},
    "const_customer": {"name": 'Customer Money & Handover Desk (Grahak Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Demand letters, receipts, possession checklists and the DLP clock after handover.',
        'does': ['Milestone-linked demand drafts with the interest clause from YOUR agreement (#92)',
                 'Receipts against demands, part-paid tracked', 'Handover checklist per unit, keys and utilities recorded (#97)',
                 'DLP tickets with the window arithmetic and vendor-dispatch records (#98)',
                 'Sales pipeline + unit inventory as your marks (#94), marketing assets with the RERA number required (#95), agreement-for-sale checklist (#96), handover dues arithmetic (#97), investor/lender pack draft with empty sign line (#99, Wave 4)'],
        "needs": ['Your projects, units and payment milestones'],
        "never": ['Send a demand or a vendor letter itself - sent only on your word',
                  'Decide a legal entitlement (interest claims ride the letter, not the ledger)']},
    "const_quality": {"name": 'Quality Records Keeper (Gunvatta)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'ITPs with hold points, NCRs, material-test lots, the IS 456 cube draft - drafts, never verdicts; permits and toolbox talks for the EHS officer.',
        "does": ['Inspection & test plans per activity with HOLD points (#75)', 'NCR log with severity and close-out',
                 'Material test register: lab results as reported, verdict pending until a human says it (#76)',
                 'IS 456 Table 11 cube-acceptance DRAFT (M20+; below refuses rather than guess sigma)',
                 'Punch list by trade from the site snags (#78)',
                 'Permit-to-work DRAFTS: hazard + controls; ISSUED only on the safety officer\'s named word (#81)',
                 'Toolbox-talk records: topic, day, gang, headcount (#81)',
                 'Material test register: pass/fail ARITHMETIC on YOUR fed limits with sources - acceptance stays the QC engineer\'s (#76, Wave 4)'],
        "needs": ['Your QA plan (the sitesup cube_limits ride the same law)'],
        "never": ['Accept work or a cube - the QA engineer signs', 'Grade a lab result by itself',
                  'Issue a permit-to-work or a safety clearance - the safety officer signs']},
    "const_meet": {"name": 'Meeting Secretary (Baithak)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'OAC / site / coordination meetings: minutes as said, actions chased till closed.',
        "does": ['Meeting records with attendees and minutes (#67)', 'Action items with owners and due dates, late-first chase',
                 'One clean minutes PDF to circulate'],
        "needs": ['Nothing - tell it the meeting happened and what was said'],
        "never": ['Mark an action done by itself - closed on your word', 'Take a decision the meeting did not take']},
    # v0.531 CONSTRUCTION WAVE 2 - file-builders & checkers (tier B: a named licensee on every output)
    "const_approvals": {"name": 'Approvals Office (Liaison Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Building permission se OC tak - file ke kaagaz, checklist, fees aur renewal calendar.',
        "does": ['Approval files per authority with the document checklist (#28)',
                 'The packet assembler: forms, drawings, NOCs, undertakings - index PDF with the gaps shown (#29, #36)',
                 'Fire-NOC packet, EC / CTE-CTO tracker, utility liaison files (#30, #31, #32)',
                 'Statutory calendar: NOC renewals and consent validity, late-first chase (#34)',
                 'Heritage/AAI/CRZ clearance APPLICABILITY register - your yes/no/unsure marks with the liaison\'s name, nothing fetched (#33, Wave 4)'],
        "needs": ['Your authority list and their actual document demands (the starter checklist bends to your ULB)'],
        "never": ['File anything on a portal - the owner\'s DSC / the licensee files', 'Sign or certify any form',
                  'Invent a fee or a rule - the pack cites or the tool refuses']},
    "const_qs": {"name": 'QS Desk (Naap-Rate)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'IS 1200 take-off with the formula trail, rate build-up, BOQ, cost control - working paper, never a certificate.',
        "does": ['Quantity take-off by IS 1200 formulae - qty + formula + inputs stored together, recompute runs on demand (#37)',
                 'Bar-bending schedule DRAFTS with the d^2/162 trail (#73)',
                 'Rate build-up from SOR / quotes - overhead + profit shown, source named (#38)',
                 'BOQ lines and the abstract by head (#39)', 'Cost controller: budget vs committed vs actual (#41)',
                 'Retention and price-variation / escalation by the contract\'s own numbers (#49)',
                 'Cost plan vs estimate variance + VE options register (#40); works-contract GST rows on the bill with the pack rate, net after YOUR ITC (#89, Wave 4)'],
        "needs": ['Your drawings read by a human (Hoola does the rule arithmetic on the readings)'],
        "never": ['Certify measurement - the billing engineer does', 'Take dimensions off a drawing by itself (document-level only)',
                  'Borrow a rate without its source']},
    "const_rera": {"name": 'RERA & Escrow Desk', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'MahaRERA project pack, quarterly update drafts, form packs, 70% escrow reconcile.',
        "does": ['Project registration data pack with the MahaRERA number (#35)',
                 'Quarterly update DRAFTS - the completion % is YOUR number, never computed by Hoola (#35)',
                 'Form 3/4/5 data packs prepared for the NAMED professional, sign line empty',
                 'Escrow ledger: receipts in; withdrawals only with the certificate reference (#93)',
                 '70% reserve reconciliation from the state pack, stale pack refuses; CA audit due from the pack'],
        "needs": ['Your registration details, quarters and receipts'],
        "never": ['Certify completion % or an escrow withdrawal - promoter / CA / architect / engineer declare',
                  'File anything with MahaRERA for you', 'Let a withdrawal through without the certificate ref']},
    "const_contracts": {"name": 'Contracts Desk (Theka-Kaayda)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Contract register, obligations chase, variation papers, claims working papers.',
        "does": ['Contract register with notice windows from YOUR contract (#44)',
                 'Obligations both sides with the due-date chase, late first (#44)',
                 'Variation papers DRAFT: desc, rate basis, money - approval recorded with the CLIENT\'s name (#45)',
                 'Claims working papers: entitlement matrix (event, clause, effect, evidence) + notice-compliance arithmetic (#46)',
                 'Insurance & bond rows on the contract register (#51)',
                 'LD calculator - all four numbers from YOUR clause with sources, cap check; the deduction stays tier C (#48). Arbitration bundle index for counsel (#50, Wave 4)'],
        "needs": ['Your contracts - the clauses, the notice windows, the LD terms'],
        "never": ['Approve a change order - the client does', 'Issue a notice or decide entitlement - advocate / counsel',
                  'Sign a contract']},
    "const_tender": {"name": 'Tender Desk (Bid Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Tender watch, bid/no-bid sheet, pre-qual dossier, price pack, vendor register.',
        "does": ['Tender watch with due dates and EMD, due-soon chase (#52)',
                 'Bid / no-bid sheet - YOUR decision with YOUR factor rows, recorded (#52)',
                 'Pre-qualification dossier rows, each with its source (#55)',
                 'Bid price pack riding the QS take-off and rates (#54)',
                 'Vendor register with YOUR ratings - preferred / ok / watch / blocked (#58)',
                 'Purchase register (indent -> PO status) (#57), expediting board (promise vs need-by) (#59), EXIM shipment register (#60, Wave 4)'],
        "needs": ['The tenders you are watching and your go / no-go factors'],
        "never": ['Bid into a portal by itself - the bid manager submits', 'Make the bid / no-bid call',
                  'Rate a vendor on its own opinion']},
    "const_drawqa": {"name": 'Drawing QA Desk (Dekh-Rekh)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Drawing register, bye-law rule rows, declared-vs-limit arithmetic - the architect reviews.',
        "does": ['Drawing register: dwg no, revision, scale-as-noted, source - document level, PDF/DWG-first (#16)',
                 'Bye-law rules as DATA: clause + source required, pack rows and project rules side by side (#9)',
                 'Declared value vs limit - within / breach ARITHMETIC with the citation (#9)',
                 'Review pack PDF for the project architect, sign line EMPTY (#16)'],
        "needs": ['The bye-law limits that bind your plot (with their clause + source)'],
        "never": ['Claim model-level checking - a PDF was never a model',
                  'Approve or pass a drawing - the project architect does', 'Supply a bye-law limit from memory']},
    "const_bim": {"name": 'BIM Desk (Model Kaam)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Open formats only: IFC read honestly, BCF issues out, IDS subset checks, clash candidates, 4D/5D on the model\'s own quantities.',
        "does": ['IFC (STEP text) read: classes, GUIDs, quantities, placements - the read says what it saw (#18)',
                 'Model health report: duplicate GUIDs, nameless, no-quantity, no-placement gaps (#18)',
                 'ISO 19650 naming check + CDE register with status codes, revisions, superseded copies, transmittals (#19)',
                 'Clash candidates on declared extents (axis-aligned, rotation ignored); not-checkable counted; BCF 2.1 zip out (#20)',
                 'IDS subset check: entity + property facets; what it cannot verify says UNVERIFIED (#18)',
                 '4D mapping (your activities) + 5D rows: the model\'s own quantities, qty x rate only with a sourced rate (#21)',
                 'As-built set register: HER required list, received/na marks by name, completeness + missing (#25, Wave 3.5)',
                 'Digital-twin DATA LINK: asset -> IFC GUID, sensor feed rows with sourced bands flagged (#109, Wave 3.5; twin = register, never a live 3D view)',
                 'COBie Component CSV check: required headers + rows missing asset/type (#109, Wave 3.5)'],
        "needs": ['Your IFC files exported with quantities + placements; your IDS XML; your rates with sources'],
        "never": ['Claim model-level checking from a PDF or DWG - this desk reads IFC only',
                  'Accept or resolve a clash - the BIM coordinator does (recorded by name)',
                  'Invent a quantity - the model\'s numbers ride with their GUID, or the row refuses',
                  'Approve the as-built set - the site architect / QS does (tier C)',
                  'Be a live 3D twin or a sensor platform - a data-link register is what it is']},
    "const_predesign": {"name": 'Pre-design Desk (Shuruat)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Load take-down, preliminary sizing by IS tables, MEP estimates, fire rule hits - working papers for the named engineer.',
        "does": ['Slab load take-down: LL from the IS 875 pack rows, self-weight with the trail (#10)',
                 'Column load + preliminary size by IS 456 cl 39.3 (short braced axial), rounding shown (#10)',
                 'Beam depth check by cl 23.2.1 basic ratios - spans over 10 m refused (modification factors are the engineer\'s) (#10)',
                 'Electrical kVA, water KLD (CPHEEO row), HVAC TR - every factor FED with its source (#11)',
                 'Fire rule rows (clause + source required) -> declared vs limit, breach/within with the citation (#12)',
                 'Fire demand arithmetic: density x area + hose, density source named (#12)',
                 'Formwork contact area by geometry on YOUR dims; striking time vs IS 456 Table 10 (OPC + >15 degC only, else refused) (#74, Wave 3.5)',
                 'Prop/shoring load vs the supplier table\'s allowable (source required) + scaffold tag register by name (#74, Wave 3.5)'],
        "needs": ['Your occupancies, thicknesses, tributary areas, fck/fy, MEP factors - each with its source'],
        "never": ['Sign or certify a design / stability certificate - the registered engineer does (tier C)',
                  'Size a member beyond the preliminary working paper (eccentricity, slenderness = engineer)',
                  'Issue Form A/B - only the Licensed Agency does',
                  'Order formwork struck or tag a scaffold safe - the site engineer / competent person do (tier C)',
                  'Striking times outside Table 10 scope (blending cements, <= 15 degC) - refused, never improvised']},
    "const_survey": {"name": 'Survey Desk (Naap-Zameen)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Traverse closure, shoelace areas, grid volumes, scan deviations, RERA carpet statements - arithmetic for the survey lead.',
        "does": ['Survey jobs from coordinate rows or LandXML CgPoints (surfaces/observations NOT parsed - said on the tin) (#22)',
                 'Traverse loop closure + precision; shoelace boundary area vs the 7/12 record with its source (#22)',
                 'Grid cut/fill volumes (average-height method, cut and fill kept separate) (#23)',
                 'Scan deviations from CSV exports (E57/LAS NOT parsed): per-point 3D deviation, RMS, out-of-tolerance list (#24)',
                 'RERA carpet-area statements under HER wall policy, tolerance check, discrepancy report PDF with the sign line EMPTY (#26)',
                 'GIS layers: GeoJSON rings read as text, areas ONLY in projected metres (degree layers refused), overlay values as YOUR readings (#27, Wave 3.5)',
                 'Setting-out sheets + as-laid vs design (plan deviation, RMS) + level checks with the sign kept (#77, Wave 3.5)'],
        "needs": ['The point coordinates / spot levels / deviations - readings from your instruments'],
        "never": ['Certify a survey or an area statement - the licensed surveyor / architect / CE do (tier C)',
                  'Interpret the orthomosaic or the point cloud - it does arithmetic on YOUR readings',
                  'Guess a Z, a policy, or a tolerance',
                  'Compute an area from lat/lng degrees or fetch/interpret a map server - both refused']},
    "const_delay": {"name": 'Delay Desk (Deri-Kaagaz)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'As-planned vs as-built with slip days, windows, notice-compliance arithmetic - working paper, never an entitlement verdict.',
        "does": ['Baseline + as-built programmes as DATA - criticality is YOUR mark, no CPM computed (#47)',
                 'Analysis windows (your choice of ranges) and which activities fell inside (#47)',
                 'Slip days per activity, your critical flags beside them, windows touched (#47)',
                 'Notice-compliance arithmetic: event -> notice days vs the contract window, cited (#47)',
                 'Working paper PDF for the forensic planner, sign lines EMPTY (#47)'],
        "needs": ['Your baseline and actual dates, your criticality marks, the contract\'s notice window'],
        "never": ['Decide delay entitlement / EOT - the forensic planner + counsel do (tier C refusal)',
                  'Issue the notice - it is drafted into the record only',
                  'Compute a CPM network or declare a critical path']},
    "const_green": {"name": 'Performance Desk (Hara-Hisaab)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Meters, tariffs, ECBC/daylight checks, embodied carbon, water/RWH, green credits, Cx scripts, T&C records, M&V - explained, not certified.',
        "does": ['Meter readings + your bill\'s tariff slabs -> the bill arithmetic and EPI benchmark (#104)',
                 'ECBC / daylight rule rows (clause + source) -> declared vs limit arithmetic (#111, #113)',
                 'Energy-model INPUT register with every assumption sourced - EnergyPlus is NOT run here (#112)',
                 'Embodied carbon: qty x EPD factor (factor source named), hot-spot list ranked (#114)',
                 'Water demand (CPHEEO row) + rainwater harvest with YOUR coefficient and IMD station (#115)',
                 'Green-rating credit tracker with evidence refs; the score is a sum, the rating is the assessor\'s (#110)',
                 'Cx test scripts + issue log; T&C records with as-installed vs design tolerance arithmetic (#116, #117)',
                 'M&V: least-squares baseline model (a, b, r2 printed) and the savings identity, your IPMVP option (#118)'],
        "needs": ['Your meter data, your bill, your sourced rule rows, your EPD factors, your test reports'],
        "never": ['Certify an energy audit / green rating / commissioning - the assessor, Cx authority do (tier C)',
                  'Run a building simulation and hand you results',
                  'Accept a T&C result - the arithmetic flags, the T&C engineer accepts']},
    # ---- Wave 4 (v0.586.0): the remaining seats (plan §12 rows, five new desks) ----
    "const_land": {"name": 'Land & Feasibility Desk (Zameen Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Parcel register, title checklist, 7/12 reconciliation, FSI worksheet, cost/funding totals, JV shares - arithmetic for the developer.',
        "does": ['Parcel register: survey no, village, area AS FED with its 7/12 / mutation source (#1)',
                 'Title document checklist with the mark and the NAME of whoever marked it (#2)',
                 'Land-record rows reconciled against the claimed area - mismatches listed (#3)',
                 'Development worksheet: FSI fed WITH SOURCE -> permissible vs programme, balance (#4)',
                 'Cost & funding totals, equity:debt, simple-interest outgo on YOUR rate (#5)',
                 'JV share register from the deed -> party-wise entitlement arithmetic (#6)'],
        "needs": ['Your 7/12 / mutation / agreement rows, the FSI source, the deed shares'],
        "never": ['Certify a clear title - the title advocate does (tier C)',
                  'Fetch or interpret a land record - rows are pasted with their source',
                  'Advise the funding structure or sign a JV term - CFO / owner / legal head do']},
    "const_plan": {"name": 'Planning & Controls Desk (Niyojan Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Baseline variance, resources, risks (P x I), site instructions, cash-flow, EVM, dashboard, agencies, plant bookings - controls arithmetic, no criticality.',
        "does": ['Activity register with YOUR baseline; actual dates and % complete as YOUR word (#63)',
                 'Date variance per activity - critical path is NEVER computed (planner marks it, tier C) (#63)',
                 'Resource loading + planned vs actual output (#65); risk register, score = P x I on YOUR marks (#66)',
                 'Site-instruction register + PMC visit log (#69)',
                 'Cash-flow: your baseline vs your bills; EVM: SPI/CPI arithmetic, no EAC forecast (#42, #43)',
                 'Director dashboard: ONLY what the registers already said (#68)',
                 'Specialist-agency register (#79); plant bookings with double-booking NAMED + utilisation (#80)'],
        "needs": ['Your baseline, your % complete, your P/I marks, your bills'],
        "never": ['Declare the critical path or an extension of time - planner / PMC do (tier C)',
                  'Forecast EAC or slip "automatically" - arithmetic only, judgement yours']},
    "const_ehs": {"name": 'EHS & Welfare Desk (Suraksha Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Training & competency register with expiry arithmetic, environmental readings vs FED limits, labour-camp register - Hoola seats no sensors.',
        "does": ['Training & competency register: worker, trade, training, validity -> expired / due-30d lists (#83)',
                 'Environmental readings AS FED vs limits FED WITH SOURCES -> exceedance arithmetic (#84)',
                 'Labour-camp register (capacity vs occupancy) + facilities checklist with the checker NAME (#86)'],
        "needs": ['Your training logs, your monitoring reports, your CPCB/SPCB limit sources'],
        "never": ['Declare a site safe or resume work - the EHS head does (tier C)',
                  'Seat a sensor or fetch an air/water reading - rows come from YOUR reports',
                  'Give the welfare verdict - the labour welfare officer does']},
    "const_studio": {"name": 'Visualisation & Presentation Desk (Studio)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Shot-brief register, asset checklists, report outlines - the render and the deck stay yours.',
        "does": ['Shot briefs: view, time-of-day, purpose -> the register (#119)',
                 'Per-shot asset checklists: pending vs ready (#119)',
                 'Report / slide outline register with section status (#120)'],
        "needs": ['Your shots, your purpose notes, your asset status'],
        "never": ['Render a frame or produce the deck - Hoola keeps the register, the GPU/designer work'],
        },
    "const_learn": {"name": 'Training & Coaching Desk (Siksha Desk)', "live": True, "icon": "hammer", "group": CONST_GROUP,
        "pitch": 'Trainee register, assessments on YOUR pass line, quizzes with the key, contractor records discipline - explained, never advised.',
        "does": ['Trainee / module / assessment registers; pass list = arithmetic on YOUR pass line (#121)',
                 'Topic register with syllabus mapping + quizzes (answer key held) -> score arithmetic (#122)',
                 'Contractor records-discipline checklist + coaching notes (#123)'],
        "needs": ['Your marks sheets, your syllabus, your pass policy'],
        "never": ['Issue a certificate - the training centre does',
                  'Give tax or investment advice - the CA / consultant does (tier C)']},
}


def _row(s, tenant: str, key: str) -> HiredEmployee | None:
    return s.scalars(select(HiredEmployee).where(HiredEmployee.tenant_id == tenant, HiredEmployee.key == key)
                     .order_by(HiredEmployee.hired_at.desc())).first()


def _view(r: HiredEmployee | None) -> dict[str, Any]:
    if r is None:
        return {"status": "none"}
    try:
        st = json.loads(r.settings or "{}")
    except ValueError:
        st = {}
    return {"status": r.status, "trust": r.trust, "hired_at": r.hired_at.isoformat() if r.hired_at else "",
            "left_at": r.left_at.isoformat() if r.left_at else "", "settings": st}


def status(tenant: str, key: str) -> str:
    """'none' | 'hired' | 'paused' | 'left'."""
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        return r.status if r else "none"


def is_hired(tenant: str, key: str) -> bool:
    """Hired and working (paused counts as hired for the desk, not for the 24/7 jobs: see is_working)."""
    return status(tenant, key) in ("hired", "paused")


def is_working(tenant: str, key: str) -> bool:
    return status(tenant, key) == "hired"


def hired_keys(tenant: str) -> dict[str, str]:
    """{key: status} for every employee she has hired and not let go (the surfaces use this to show desks)."""
    ensure_table()
    out: dict[str, str] = {}
    with session() as s:
        for r in s.scalars(select(HiredEmployee).where(HiredEmployee.tenant_id == tenant)
                           .order_by(HiredEmployee.hired_at)).all():
            if r.status in ("hired", "paused"):
                out[r.key] = r.status
            else:
                out.pop(r.key, None)
    return out


def working_tenants(key: str) -> list[str]:
    """Every tenant whose `key` employee is hired and not paused (the 24/7 scheduler walks these)."""
    ensure_table()
    with session() as s:
        return sorted({r.tenant_id for r in s.scalars(select(HiredEmployee).where(HiredEmployee.key == key,
                                                                                  HiredEmployee.status == "hired")).all()})


def catalog(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    out = []
    with session() as s:
        for key, c in CATALOG.items():
            out.append({"key": key, "group": "Business", **c, **_view(_row(s, tenant, key))})
    return out


def hire(tenant: str, key: str, trust: str = "seekh") -> dict[str, Any]:
    c = CATALOG.get(key)
    if c is None:
        raise HireError("Aisa koi employee nahi.")
    if not c.get("live"):
        raise HireError(f"{c['name']} abhi taiyaar ho raha hai; jald aayega.")
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is not None and r.status in ("hired", "paused"):
            r.status = "hired"
            return {"key": key, **_view(r), "already": True}
        r = HiredEmployee(tenant_id=tenant, key=key, status="hired",
                          trust=trust if trust in TRUST else "seekh", settings="{}")
        s.add(r)
        s.flush()
        return {"key": key, **_view(r)}


def _set(tenant: str, key: str, status_: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is None or r.status == "left":
            raise HireError("Yeh employee abhi hired nahi hai.")
        r.status = status_
        if status_ == "left":
            r.left_at = now()
        return {"key": key, **_view(r)}


def pause(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "paused")


def resume(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "hired")


def leave(tenant: str, key: str) -> dict[str, Any]:
    return _set(tenant, key, "left")


def settings(tenant: str, key: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        return _view(_row(s, tenant, key)).get("settings", {})


def save_settings(tenant: str, key: str, **kw: Any) -> dict[str, Any]:
    """Merge keys into the employee's settings (trust is its own column)."""
    ensure_table()
    with session() as s:
        r = _row(s, tenant, key)
        if r is None or r.status == "left":
            raise HireError("Yeh employee abhi hired nahi hai.")
        st = _view(r)["settings"]
        trust = kw.pop("trust", None)
        if trust in TRUST:
            r.trust = trust
        st.update({k: v for k, v in kw.items() if v is not None})
        r.settings = json.dumps(st, ensure_ascii=False)
        return _view(r)
