"""Duties (groups of tools), role packs (which duties make a job) and how risky each tool is.

kind_of(tool): read  = only looks at things, never changes anything outside
               action = changes or sends one thing
               big   = sends to many, deletes, shares, money, public posts, the PC: always asks when staff asked for it
Any tool not listed below is an action of duty "" (not part of any job)."""
from __future__ import annotations

DUTIES: dict[str, dict] = {
    "customers": {"label": "Graahakon se baat", "say": "graahakon ke sawaal ka jawab, WhatsApp aur Hoola Network par baat",
                  "prefix": ("hoola_",), "tools": {"biz_handover", "biz_note"}},
    "appointments": {"label": "Appointment aur calendar", "say": "appointment lena, badalna, yaad dilana",
                     "prefix": ("calendar_",), "tools": {"add_calendar_event", "biz_free_slots", "biz_book", "biz_my_appointments",
                                                        "biz_cancel"}},
    "reminders": {"label": "Follow-up aur yaad", "say": "follow-up, reminder, roz ke kaam",
                  "prefix": (), "tools": {"create_reminder", "list_reminders", "cancel_reminder", "create_routine", "list_routines",
                                          "cancel_routine", "set_phone_alarm", "set_phone_timer", "list_add", "list_show", "list_done"}},
    "email": {"label": "Email", "say": "email padhna, jawab ka draft, follow-up", "prefix": ("email_",), "tools": set()},
    "tickets": {"label": "Shikayat / ticket", "say": "shikayat darj karna, ticket aage badhana, graahak ko update",
                "prefix": (), "tools": {"hoola_business", "hoola_my_business", "hoola_chain", "biz_complaint", "biz_ticket_status"}},
    "collections": {"label": "Paise ki vasooli", "say": "baaki paison ki yaad dilana, bill aur payment card banana (paise kabhi khud nahi)",
                    "prefix": ("bazar_", "tally_"), "tools": {"biz_my_dues", "biz_pay_link", "biz_promise"}},
    "records": {"label": "Register aur files", "say": "sheet, register, documents, forms",
                "prefix": ("sheet_", "drive_", "form_", "slides_", "notebook_"),
                "tools": {"sheets_find", "doc_create", "make_document", "pdf_tools", "file_read", "photos_pick", "photos_picked", "photos_send",
                          "photos_upload", "photos_albums"}},
    "campaigns": {"label": "WhatsApp campaign", "say": "approved template se graahakon ko WhatsApp (sirf official API)",
                  "prefix": (), "tools": {"list_lead_lists", "get_lead_list", "check_template", "submit_template",
                                          "check_template_status", "create_campaign", "confirm_send", "get_campaign_status",
                                          "control_campaign"}},
    "video": {"label": "Video editing", "say": "reels, shorts, status aur YouTube ke liye video edit (captions, logo, music)",
              "prefix": (), "tools": {"video_edit", "video_studio"}},
    "operator": {"label": "Computer operator", "say": "websites par form, application, download, status check (OTP / submit / payment aap karti hain)",
                 "prefix": (), "tools": {"computer_operator"}},
    "tailoring": {"label": "Silai ka kaam", "say": "order, naap, trial, delivery, daam taiyaar karna (naya daam aapki haan se)",
                  "prefix": (), "tools": {"darzi", "darzi_dekho", "biz_order_status"}},
    "stall": {"label": "Galla aur stock", "say": "UPI se roz ki bikri, sabse achha ghanta, kal ka doodh-chini, stock order (aapki haan se)",
              "prefix": (), "tools": {"chai", "chai_dekho"}},
    "office_admin": {"label": "Office sambhalna", "say": "saamaan, repair, AMC / renewal, team ki deadline, petty cash, hafte ka note (kharcha aapki haan se)",
                     "prefix": (), "tools": {"office", "office_dekho"}},
    "typing": {"label": "Typing aur anuvaad", "say": "letter / application likhna, voice se type, translation, grammar (sign aapki haan se)",
               "prefix": (), "tools": {"lekhak", "lekhak_dekho", "make_document", "pdf_tools", "file_read"}},
    "mobile_repair": {"label": "Repair aur recharge", "say": "repair job + photo, warranty, 'taiyaar hai' draft, recharge register + yaad (bill aapki haan se), phone ki dikkat ka step-by-step ilaaj",
                      "prefix": (), "tools": {"mobile_shop", "mobile_shop_dekho", "biz_repair_status", "phone_doctor"}},
    "gst_work": {"label": "GST ka kaam", "say": "client ke bill, GSTR-1 JSON, 2B milaan + IMS, 3B hisaab, notice ka jawab (filing aapki haan se)",
                 "prefix": (), "tools": {"gst", "gst_dekho", "file_read", "pdf_tools"}},
    "payroll_work": {"label": "Salary / payroll", "say": "hazri, salary, PF / ESIC / PT / TDS, payslip, bank file, full & final (payment aapki haan se, aap karengi)",
                     "prefix": (), "tools": {"payroll", "payroll_dekho", "file_read"}},
    "finance_analysis": {"label": "Hisaab-kitaab ka vishleshan", "say": "P&L, ratio, cash kitne din, lene-dene, loan aur advance tax ka hisaab, MIS report (bahar bhejna aapki haan se)",
                         "prefix": (), "tools": {"paisa", "paisa_dekho", "file_read"}},
    "audit_work": {"label": "Audit ka kaam", "say": "materiality, ledger ki tulna, entries ki jaanch, cash / TDS niyam, sample, confirmation, working papers (sign aur raay CA ki)",
                   "prefix": (), "tools": {"audit", "audit_dekho", "file_read", "pdf_tools"}},
    "research": {"label": "Jaankari dhoondhna", "say": "web, maps, mausam, public APIs",
                 "prefix": ("maps_", "api_"), "tools": {"google_search", "web_sources", "open_website", "browse_web", "browse_result", "get_weather",
                                                       "memory_search"}},
}
# hoola_* tools that belong to tickets, not customers
_TICKET_FIRST = {"hoola_business", "hoola_my_business", "hoola_chain"}
# what a customer on WhatsApp can make Hoola do: only these, always about that customer (employee/inbox.py)
CUSTOMER_TOOLS = {"biz_repair_status", "biz_order_status", "biz_free_slots", "biz_book", "biz_my_appointments", "biz_cancel", "biz_complaint", "biz_ticket_status",
                  "biz_my_dues", "biz_pay_link", "biz_promise", "biz_handover", "biz_note"}

ROLES: dict[str, dict] = {
    "front_desk": {"label": "Front desk", "say": "Dukaan / clinic / office ka pehla chehra: sawaal, appointment, follow-up",
                   "duties": ["customers", "appointments", "reminders", "email", "research"]},
    "support_collect": {"label": "Support + vasooli", "say": "Shikayat sambhalna, graahak ko update dena, baaki paison ki yaad dilana",
                        "duties": ["customers", "tickets", "collections", "email", "records", "reminders", "research"]},
    "office": {"label": "Office sahayak", "say": "Inbox, calendar, documents, follow-up aur roz ki briefing",
               "duties": ["email", "appointments", "reminders", "records", "research"]},
    "accounts": {"label": "Hisaab-kitaab sahayak", "say": "Bills padhna, Tally entry ka draft, baaki paise, CA ke liye kaagaz",
                 "duties": ["collections", "records", "email", "reminders"]},
    "field_service": {"label": "Field service", "say": "Technician ki list, shikayat, visit, roz ki ops report",
                      "duties": ["customers", "tickets", "appointments", "reminders", "records"]},
    "sales": {"label": "Sales aur follow-up", "say": "Naye enquiry ka jawab, lead follow-up, quotation draft, offer campaign",
              "duties": ["customers", "campaigns", "email", "records", "reminders", "research"]},
    "hr_admin": {"label": "HR aur admin", "say": "Job post, interview, attendance register, roster, renewals",
                 "duties": ["records", "email", "appointments", "reminders"]},
    "marketing": {"label": "Marketing", "say": "Tyohaar ke post ideas, poster, offer campaign, reels, competitor ki khabar",
                  "duties": ["campaigns", "records", "research", "video"]},
    "video_editor": {"label": "Video editor", "say": "Dukaan / business ki reels, shorts, status aur YouTube video edit karna",
                     "duties": ["video", "records", "research"]},
    "computer_operator": {"label": "Computer operator", "say": "Online form, sarkari portal, bill / certificate download, status check, application",
                          "duties": ["operator", "records", "research", "reminders"]},
    "tailor": {"label": "Darzi sahayak", "say": "Silai ke order, har graahak ka naap, trial / delivery ki tareekh, 'taiyaar hai' message, daam",
               "duties": ["tailoring", "customers", "appointments", "reminders", "collections", "records"]},
    "chai_stall": {"label": "Chai stall sahayak", "say": "UPI alerts se roz ki bikri, sabse achha ghanta, kal ka doodh / chini, stock order",
                   "duties": ["stall", "reminders", "collections", "records", "research"]},
    "office_manager": {"label": "Office manager (Daftar sahayak)",
                       "say": "Saamaan aur reorder, repair ticket, AMC / licence / rent renewal, team ki deadline, petty cash, hafte ka office note",
                       "duties": ["office_admin", "reminders", "email", "records", "appointments", "research"]},
    "typist": {"label": "Typist aur translator (Lekhak sahayak)",
               "say": "Aapki awaaz se letter / application, Hindi-Marathi-English anuvaad, grammar, photo / Kruti Dev se Unicode typing",
               "duties": ["typing", "records", "email", "research"]},
    "mobile_shop": {"label": "Mobile dukaan sahayak", "say": "Repair job aur photo, warranty, 'taiyaar hai' message, recharge register aur yaad, bill aapki haan se",
                    "duties": ["mobile_repair", "customers", "reminders", "collections", "records", "research"]},
    "gst_practitioner": {"label": "GST sahayak (practitioner)",
                         "say": "Har client ke bill check, GSTR-1 / 3B taiyaar, 2B milaan, due date aur late fee, notice ka jawab; filing aapki haan se",
                         "duties": ["gst_work", "reminders", "email", "records", "customers", "research"]},
    "audit_assistant": {"label": "Auditor ka sahayak",
                        "say": "Har audit ki taiyaari: TB + day book ki jaanch, materiality, sample, confirmation, client ke sawaal, working papers; raay aur sign CA ke",
                        "duties": ["audit_work", "reminders", "email", "records", "research"]},
    "financial_analyst": {"label": "Financial analyst",
                          "say": "Tally aur bank se P&L, ratio, cash forecast, vasooli, MSME payment, loan ki kshamta, advance tax, MIS report",
                          "duties": ["finance_analysis", "reminders", "email", "records", "research"]},
    "payroll_officer": {"label": "Payroll officer",
                        "say": "Har mahine ki salary, PF / ESIC / PT / TDS, payslip, bank file, ECR, joining / leaving, bonus aur gratuity; payment aapki haan se",
                        "duties": ["payroll_work", "reminders", "email", "records", "research"]},
    "custom": {"label": "Apna kaam", "say": "Aap khud chuniye Hoola kaun se kaam karega", "duties": []},
}

# Industry packs: one tap fills role + starting rules + a hint for "about". The owner can change everything afterwards.
PRESETS: dict[str, dict] = {
    "clinic": {"label": "Clinic / dentist", "role": "front_desk", "kind": "clinic", "slot_minutes": 20, "after_hours": "note",
               "about_hint": "Doctor ka naam, timing, fees, services (checkup, cleaning, RCT...), pata, parking",
               "rules": ["Dawai, dose ya bimari par koi salah nahi: 'Doctor sahab hi batayenge' kahna.",
                         "Dard / sujan / khoon jaise urgent shabd aaye to turant owner ko handover.",
                         "Patient ki report ya bimari kisi aur ko nahi batani."]},
    "shop": {"label": "Dukaan / kirana / retail", "role": "front_desk", "kind": "shop", "slot_minutes": 30, "after_hours": "note",
             "about_hint": "Kya bechte hain, khaas items aur daam, home delivery area, timing, UPI",
             "rules": ["Udhaar (credit) sirf owner ki haan se.", "Jo daam list mein nahi, woh owner se poochkar batana."]},
    "isp": {"label": "Broadband / cable / LCO", "role": "support_collect", "kind": "isp", "slot_minutes": 60, "after_hours": "answer",
            "about_hint": "Plans aur daam, area, naya connection kaise, router restart steps, support number",
            "rules": ["Net band ho to pehle router restart aur cable check karwana, phir shikayat darj karna.",
                      "Plan badalna ya chhoot sirf owner ki haan se.", "Technician ka number customer ko nahi dena."]},
    "ca": {"label": "CA / tax office", "role": "office", "kind": "ca", "slot_minutes": 30, "after_hours": "note",
           "about_hint": "Services (GST, ITR, audit), fees, documents list, timing",
           "rules": ["Tax ki salah nahi: CA sahab se milne ka time dena.", "PAN / Aadhaar number chat mein mat maangna; documents office mein."]},
    "coaching": {"label": "Coaching / school", "role": "support_collect", "kind": "coaching", "slot_minutes": 30, "after_hours": "note",
                 "about_hint": "Courses, batch timing, fees, admission steps, pata",
                 "rules": ["Bachche ke marks ya jaankari sirf unke maa-baap ko.", "Fees mein chhoot sirf owner ki haan se."]},
    "salon": {"label": "Salon / parlour", "role": "front_desk", "kind": "salon", "slot_minutes": 30, "after_hours": "note",
              "about_hint": "Services aur daam, timing, kaun kaun stylist",
              "rules": ["Booking ke 10 minute late hone par slot aage badh sakta hai, yeh customer ko batana."]},
    "restaurant": {"label": "Restaurant / tiffin", "role": "front_desk", "kind": "restaurant", "slot_minutes": 60, "after_hours": "note",
                   "about_hint": "Menu aur daam, delivery area, table booking, timing",
                   "rules": ["Bade order (20+ plate) owner ki haan se."]},
    "tailor": {"label": "Darzi / boutique", "role": "tailor", "kind": "tailor", "slot_minutes": 20, "after_hours": "note",
               "about_hint": "Kya silte hain (blouse, suit, lehenga, shirt...), daam, kitne din lagte hain, trial ka samay, pata",
               "rules": ["Naya daam ya chhoot sirf owner ki haan se.", "Delivery ki tareekh niyam dekhkar hi pakki karna.",
                         "Graahak ka naap kisi aur ko nahi batana."]},
    "chai": {"label": "Chai stall / tapri / nashta", "role": "chai_stall", "kind": "chai", "slot_minutes": 30, "after_hours": "quiet",
             "about_hint": "Menu aur daam (chai, special, coffee, nashta), timing, doodhwala, kitne cup roz",
             "rules": ["Stock ka order sirf owner ki haan se.", "Udhaar sirf owner ki haan se."]},
    "mobile_shop": {"label": "Mobile recharge + repair", "role": "mobile_shop", "kind": "mobile_shop", "slot_minutes": 20,
                    "after_hours": "note",
                    "about_hint": "Kaun se phone theek karte hain, display / battery ke daam, kitne din, warranty, recharge (Jio / Airtel / Vi / BSNL), timing",
                    "rules": ["Bill aur daam sirf owner ki haan se.", "Graahak ke phone ka password kabhi mat maangna.",
                              "IMEI badalne ka kaam kabhi nahi.", "Lock / FRP hatane ke liye phone ka bill / dabba dekhna zaroori."]},
    "office": {"label": "Office / company", "role": "office", "kind": "office", "slot_minutes": 30, "after_hours": "quiet",
               "about_hint": "Company kya karti hai, kaun kis kaam ka", "rules": []},
    "audit_firm": {"label": "CA / audit firm", "role": "audit_assistant", "kind": "ca", "slot_minutes": 30, "after_hours": "note",
                   "about_hint": "Kaun se audit (statutory, tax, internal, stock), kitne client, partner kaun, client se kaagaz kaise aate hain",
                   "rules": ["Audit report / raay sirf partner sign karega.", "UDIN aur form filing Hoola nahi karega.",
                             "Client ya party ko letter / sawaal sirf owner ki haan se.", "Ek client ki baat doosre ko nahi."]},
    "finance": {"label": "Accounts / finance office", "role": "financial_analyst", "kind": "office", "slot_minutes": 30,
                "after_hours": "quiet",
                "about_hint": "Tally / Busy kaun chalata hai, bank kaun sa, loan / OD, kaun se graahak late dete hain, kaun supplier MSME hai",
                "rules": ["Report bank / CA / investor ko sirf owner ki haan se.", "Paisa kabhi nahi bhejna.",
                          "Vasooli ke message owner ki haan se.", "Hisaab ko salah ki tarah pakka mat batana."]},
    "payroll": {"label": "Payroll / HR (salary wala office)", "role": "payroll_officer", "kind": "office", "slot_minutes": 30,
                "after_hours": "quiet",
                "about_hint": "Kitne log, salary kab dete hain, PF / ESIC registered hai kya, kaun sa state (PT), advance ka niyam",
                "rules": ["Salary sirf owner ki haan se.", "Bank login / OTP kabhi nahi.", "Kisi ki salary doosre ko nahi batana.",
                          "PAN / bank account poora kabhi chat mein nahi likhna."]},
    "gst_practitioner": {"label": "GST practitioner / tax consultant", "role": "gst_practitioner", "kind": "ca", "slot_minutes": 30,
                         "after_hours": "note",
                         "about_hint": "Kitne client, monthly / QRMP / composition, fees, bill bhejne ki last date, kaun portal par file karta hai",
                         "rules": ["Return file sirf owner ki haan se.", "Portal ka password ya OTP kabhi mat maangna.",
                                   "Tax ka challan client khud bharega.", "Ek client ki jaankari doosre client ko nahi."]},
    "office_manager": {"label": "Office manager", "role": "office_manager", "kind": "office", "slot_minutes": 30, "after_hours": "quiet",
                       "about_hint": "Office ka pata, kitne log, kaun kis kaam ka, vendors (AC, printer, net, safai)",
                       "rules": ["Koi bhi kharcha (order, repair, renewal) sirf owner ki haan se.",
                                 "Team ko yaad-dihani ka message draft banana; owner khud bhejengi.",
                                 "Licence / NOC ki tareekh kagaz se lena, andaza nahi."]},
    "typist": {"label": "Typing / DTP / anuvaad centre", "role": "typist", "kind": "office", "slot_minutes": 30, "after_hours": "quiet",
               "about_hint": "Kaunse kaam (application, affidavit draft, translation, Kruti Dev), bhashayein, daam",
               "rules": ["Letter mein sirf wahi baat jo graahak / owner ne kahi; kuch bhi apne se nahi jodna.",
                         "Sign aur stamp sirf owner ki haan se.", "Court / passport ke liye notary / certified translator ki zaroorat batana."]},
}

LEVELS = ("seekh", "saathi", "bharosa")
LEVEL_LABEL = {"seekh": "Seekh raha hai: har kaam se pehle poochega",
               "saathi": "Saathi: roz ke kaam khud, bade kaam poochke",
               "bharosa": "Bharosa: seemaa ke andar sab khud, report dega"}
CAP = {"seekh": 0, "saathi": 40, "bharosa": 150}      # actions per duty per day before it asks again
PROMOTE_AFTER = {"seekh": 15, "saathi": 40}            # "Haan" taps in a row before the app suggests the next level

READ = {
    "list_lead_lists", "get_lead_list", "check_template", "check_template_status", "get_campaign_status", "list_reminders",
    "list_show", "list_routines", "get_weather", "google_search", "web_sources", "open_website", "browse_web", "browse_result",
    "artifact_list", "email_check", "email_read", "email_triage", "email_attachment", "email_bulk_status", "email_contacts",
    "email_accounts", "calendar_agenda", "calendar_find_event", "calendar_free_slots", "sheets_find", "sheet_info",
    "sheet_read", "sheet_query", "drive_find", "drive_list_folder", "drive_read_file", "drive_storage", "form_find",
    "form_responses", "form_summary", "slides_find", "slides_read", "photos_pick", "photos_picked", "photos_albums",
    "notebook_list", "notebook_open", "notebook_ask", "youtube_search", "youtube_video", "youtube_watch", "youtube_channel",
    "youtube_comments", "youtube_my_channel", "youtube_my_videos", "youtube_analytics", "app_check", "hoola_me",
    "hoola_find", "hoola_connections", "hoola_inbox", "hoola_threads", "hoola_thread", "hoola_look", "hoola_groups",
    "hoola_group_digest", "hoola_learned", "hoola_samaj", "hoola_community_search", "hoola_skills", "hoola_my_business",
    "bazar_find", "bazar_activity", "maps_search", "maps_directions", "pc_status", "pc_search", "pc_list", "pc_read",
    "pc_task_result", "tally_report", "file_read", "api_find", "api_docs", "api_call", "memory_search", "phone_health",
    "tv_channel", "employee", "india_info",
    "biz_free_slots", "biz_my_appointments", "biz_ticket_status", "biz_my_dues", "biz_handover", "biz_note",
    "darzi_dekho", "biz_order_status", "chai_dekho", "mobile_shop_dekho", "biz_repair_status",
    "darzi_dekho", "biz_order_status", "office_dekho", "lekhak_dekho", "gst_dekho", "payroll_dekho", "paisa_dekho", "audit_dekho",
}
BIG = {
    "email_bulk", "email_delete", "email_forward", "drive_trash", "drive_share", "sheet_share", "form_share", "slides_share",
    "slides_delete", "sheet_delete_rows", "notebook_delete", "create_campaign", "confirm_send", "control_campaign",
    "submit_template", "bazar_run", "youtube_upload", "youtube_update_video", "hoola_samaj_post", "hoola_group_post",
    "hoola_group_manage", "hoola_chain", "pc_do", "tally_entry", "cancel_routine", "calendar_cancel_event", "photos_send",
    "drive_send_file", "agent_army", "hoola_make",
}


def duty_of(tool: str) -> str:
    if tool in _TICKET_FIRST:
        return "tickets"
    for d, spec in DUTIES.items():
        if tool in spec["tools"] or any(tool.startswith(p) for p in spec["prefix"]):
            return d
    return ""


def kind_of(tool: str) -> str:
    if tool in READ:
        return "read"
    return "big" if tool in BIG else "action"


def role_duties(role: str, custom: list[str] | None = None) -> list[str]:
    if role == "custom":
        return [d for d in (custom or []) if d in DUTIES]
    return list((ROLES.get(role) or ROLES["front_desk"])["duties"])
