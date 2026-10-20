"""Duties (groups of tools), role packs (which duties make a job) and how risky each tool is.

kind_of(tool): read  = only looks at things, never changes anything outside
               action = changes or sends one thing
               big   = sends to many, deletes, shares, money, public posts, the PC: always asks when staff asked for it
Any tool not listed below is an action of duty "" (not part of any job)."""
from __future__ import annotations

DUTIES: dict[str, dict] = {
    "customers": {"label": "Graahakon se baat", "say": "graahakon ke sawaal ka jawab, unke message, Hoola Network par baat",
                  "prefix": ("hoola_",), "tools": set()},
    "appointments": {"label": "Appointment aur calendar", "say": "appointment lena, badalna, yaad dilana",
                     "prefix": ("calendar_",), "tools": {"add_calendar_event"}},
    "reminders": {"label": "Follow-up aur yaad", "say": "follow-up, reminder, roz ke kaam",
                  "prefix": (), "tools": {"create_reminder", "list_reminders", "cancel_reminder", "create_routine", "list_routines",
                                          "cancel_routine", "set_phone_alarm", "set_phone_timer", "list_add", "list_show", "list_done"}},
    "email": {"label": "Email", "say": "email padhna, jawab ka draft, follow-up", "prefix": ("email_",), "tools": set()},
    "tickets": {"label": "Shikayat / ticket", "say": "shikayat darj karna, ticket aage badhana, graahak ko update",
                "prefix": (), "tools": {"hoola_business", "hoola_my_business", "hoola_chain"}},
    "collections": {"label": "Paise ki vasooli", "say": "baaki paison ki yaad dilana, bill aur payment card banana (paise kabhi khud nahi)",
                    "prefix": ("bazar_", "tally_"), "tools": set()},
    "records": {"label": "Register aur files", "say": "sheet, register, documents, forms",
                "prefix": ("sheet_", "drive_", "form_", "slides_", "notebook_"),
                "tools": {"sheets_find", "doc_create", "make_document", "file_read", "photos_pick", "photos_picked", "photos_send",
                          "photos_upload", "photos_albums"}},
    "campaigns": {"label": "WhatsApp campaign", "say": "approved template se graahakon ko WhatsApp (sirf official API)",
                  "prefix": (), "tools": {"list_lead_lists", "get_lead_list", "check_template", "submit_template",
                                          "check_template_status", "create_campaign", "confirm_send", "get_campaign_status",
                                          "control_campaign"}},
    "research": {"label": "Jaankari dhoondhna", "say": "web, maps, mausam, public APIs",
                 "prefix": ("maps_", "api_"), "tools": {"google_search", "open_website", "browse_web", "browse_result", "get_weather",
                                                       "memory_search"}},
}
# hoola_* tools that belong to tickets, not customers
_TICKET_FIRST = {"hoola_business", "hoola_my_business", "hoola_chain"}

ROLES: dict[str, dict] = {
    "front_desk": {"label": "Front desk", "say": "Dukaan / clinic / office ka pehla chehra: sawaal, appointment, follow-up",
                   "duties": ["customers", "appointments", "reminders", "email", "research"]},
    "support_collect": {"label": "Support + vasooli", "say": "Shikayat sambhalna, graahak ko update dena, baaki paison ki yaad dilana",
                        "duties": ["customers", "tickets", "collections", "email", "records", "reminders", "research"]},
    "custom": {"label": "Apna kaam", "say": "Aap khud chuniye Hoola kaun se kaam karega", "duties": []},
}
LEVELS = ("seekh", "saathi", "bharosa")
LEVEL_LABEL = {"seekh": "Seekh raha hai: har kaam se pehle poochega",
               "saathi": "Saathi: roz ke kaam khud, bade kaam poochke",
               "bharosa": "Bharosa: seemaa ke andar sab khud, report dega"}
CAP = {"seekh": 0, "saathi": 40, "bharosa": 150}      # actions per duty per day before it asks again
PROMOTE_AFTER = {"seekh": 15, "saathi": 40}            # "Haan" taps in a row before the app suggests the next level

READ = {
    "list_lead_lists", "get_lead_list", "check_template", "check_template_status", "get_campaign_status", "list_reminders",
    "list_show", "list_routines", "get_weather", "google_search", "open_website", "browse_web", "browse_result",
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
    "tv_channel", "employee",
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
