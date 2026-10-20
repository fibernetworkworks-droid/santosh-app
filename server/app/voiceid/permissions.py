"""What each voice may ask Hoola to do in a call. Enforced on the server, not left to the model.

  owner    everything
  trusted  household and reading things (calendar, files, reading mail), but no money, no sending or deleting,
           no PC, no Hoola Network, no changing the owner's memory
  family   everyday help only: reminders, alarms, lists, weather, search, maps, music, TV, AC, YouTube, pages
  guest    (an unknown voice in strict mode) same as family
Any tool not listed is owner-only.
"""
from __future__ import annotations

FAMILY = {
    "create_reminder", "list_reminders", "cancel_reminder", "set_phone_alarm", "set_phone_timer",
    "list_add", "list_show", "list_done", "get_weather", "google_search", "open_website", "open_on_phone",
    "browse_web", "browse_result", "maps_search", "maps_directions", "maps_navigate",
    "music_control", "tv_remote", "ac_control", "bluetooth",
    "youtube_search", "youtube_video", "youtube_watch", "youtube_channel",
    "artifact_make", "artifact_list", "app_check",
}
TRUSTED = FAMILY | {
    "calendar_agenda", "calendar_free_slots", "calendar_find_event", "calendar_add_event", "add_calendar_event",
    "email_check", "email_read", "email_triage",
    "drive_find", "drive_list_folder", "drive_read_file", "sheet_read", "sheets_find", "sheet_info", "sheet_query",
    "slides_find", "slides_read", "notebook_list", "notebook_open", "notebook_ask",
    "list_routines", "create_routine", "cancel_routine", "photos_pick",
}
LEVELS = ("owner", "trusted", "family")
LEVEL_LABEL = {"owner": "Sab kuch", "trusted": "Bharosemand (paise, mail bhejna, PC nahi)",
               "family": "Ghar ke kaam (reminder, music, TV, search)"}


def allowed(level: str | None, tool: str) -> bool:
    if level in (None, "owner"):
        return True
    return tool in (TRUSTED if level == "trusted" else FAMILY)
