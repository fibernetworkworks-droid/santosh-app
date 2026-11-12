"""The common phone problems in India, how to recognise them in her words, what the phone's own check says about them,
and the fixes in the order a good technician would try them (safe and quick first; anything that loses data last and
only with her decision). Each step can open the right Android settings screen (`setting`, see PhoneCheck.openSetting).

`escalate`: where it goes when the steps don't fix it
  repair      -> a repair shop / the brand's service centre (or her own Mobile Dukaan job) with the fault named
  operator    -> the SIM operator's store / helpline
  official    -> government channels (CEIR on Sanchar Saathi, 1930 / cybercrime.gov.in, Chakshu)
"""
from __future__ import annotations

import re

# step: id, title (short), how (what exactly to do), setting (screen to open), pkg (app for app screens: "top" = the
# app used most), url (official page), careful (needs her decision: data loss / cost), check (snapshot key it relates to)
S = dict

ISSUES: dict[str, dict] = {
    "slow": {"label": "Phone is slow / hangs", "words": ("slow", "hang", "atak", "lag", "dheema", "dheere", "freeze", "ruk jata"),
             "fault": "software", "escalate": "repair", "steps": [
        S(id="restart", title="Phone restart", how="Hold the power button > Restart. If it has not been restarted for days, this is the biggest fix."),
        S(id="storage", title="Free up storage", setting="storage", check="storage_used_pct",
          how="If storage is more than 90% full, the phone slows down. Remove big videos / WhatsApp media / old downloads, or keep them in Google Photos / on a PC."),
        S(id="heavy_app", title="The app used the most", setting="app_info", pkg="top", check="top_apps",
          how="Do 'Storage > Clear cache' for this app; if you do not need it, 'Force stop' or uninstall it."),
        S(id="update_apps", title="Apps update", url="https://play.google.com/store/apps",
          how="Play Store > Profile photo > 'Manage apps & device' > 'Update all'."),
        S(id="system_update", title="Phone software update", setting="system_update", check="security_patch",
          how="Settings > Software update / System update > Check for updates. With Wi-Fi and at least 50% battery."),
        S(id="safe_mode", title="Check in safe mode",
          how="Hold the power button, then long-press 'Power off' on the screen > Safe mode. If the phone works fine in safe mode, a downloaded app is the cause: remove recent apps one by one. Safe mode ends when you restart."),
        S(id="factory_reset", title="Factory reset (last resort)", setting="settings", careful=True,
          how="First back up with Google, back up WhatsApp chats and back up photos. Then Settings > System > Reset > Erase all data. All data is erased: only after your approval."),
    ]},
    "battery_drain": {"label": "Battery drains fast", "words": ("battery jaldi", "battery khatam", "battery drain", "backup kam", "charge nahi tikta",
                                                                "battery nahi chalti", "battery down"),
                      "fault": "battery", "escalate": "repair", "steps": [
        S(id="battery_usage", title="What is using the battery", setting="battery_usage", check="top_apps",
          how="Look at the top app in Battery usage. If you rarely use that app, set its battery to 'Restricted'."),
        S(id="brightness", title="Auto brightness", setting="display", check="brightness_pct",
          how="Display > turn on 'Adaptive / Auto' brightness, and set screen timeout to 30 seconds."),
        S(id="battery_saver", title="Battery saver", setting="battery_saver", how="Set Battery saver to turn on by itself at 20% battery."),
        S(id="location_off", title="Location only when needed", setting="location", check="location_on",
          how="Turn Location off after using maps / a ride; give apps 'Only while using'."),
        S(id="restart", title="Phone restart", how="If it has been on for days, restart: stuck tasks stop."),
        S(id="system_update", title="Software update", setting="system_update", how="A new update fixes battery faults."),
        S(id="battery_health", title="Battery health", check="battery_health",
          how="A battery 2-3 years old, or a swollen one (back cover lifting), needs replacing: a swollen battery is dangerous, do not use it."),
    ]},
    "heating": {"label": "Phone gets hot", "words": ("garam", "heat", "gram", "hot", "tapta", "jal raha"),
                "fault": "battery", "escalate": "repair", "steps": [
        S(id="cool_down", title="Let it cool down", check="battery_temp_c",
          how="Unplug it from the charger now, take off the cover, keep it away from sun / a car dashboard, and run nothing for 10 minutes."),
        S(id="charge_right", title="Right charger, no cover", check="plugged",
          how="Use an original / good-brand charger and cable. Do not play games / make video calls while charging, and do not leave it on a pillow."),
        S(id="heavy_app", title="Close heavy apps", setting="app_info", pkg="top", check="top_apps",
          how="Games, camera, video or hotspot running for long make the phone hot. Force stop this app."),
        S(id="restart", title="Phone restart", how="A stuck background task stops."),
        S(id="system_update", title="Software update", setting="system_update", how="An update can fix overheating faults."),
        S(id="safe_mode", title="Check heat in safe mode", how="If it gets hot even in safe mode without being used, it is a hardware / battery problem: go to a shop."),
    ]},
    "not_charging": {"label": "Does not charge / charges slowly", "words": ("charge nahi", "charging nahi", "slow charging", "charge dheere",
                                                                             "charging slow", "charger"),
                     "fault": "charging_port", "escalate": "repair", "steps": [
        S(id="other_cable", title="Another cable / charger", check="plugged",
          how="Try another good cable and charger; if the cable is bent / cut, that is the cause."),
        S(id="clean_port", title="Clean the charging port",
          how="Switch the phone off and look at the port with a torch. If there is dirt, clean it gently with a dry soft toothbrush / plastic toothpick. Never a pin / needle."),
        S(id="restart", title="Phone restart", how="Restart and plug in the charger again."),
        S(id="cool_charge", title="A hot phone charges slowly", check="battery_temp_c",
          how="If the phone is hot, let it cool; take off the cover and charge."),
        S(id="safe_mode", title="Charge in safe mode", how="If it charges fine in safe mode, an app is the cause."),
        S(id="port_repair", title="Replace the port / battery", how="If it fails with another cable too, the charging port or battery is faulty: a shop does it in 15-30 minutes."),
    ]},
    "no_network": {"label": "No network / signal", "words": ("network nahi", "signal nahi", "no service", "emergency call only", "range nahi",
                                                              "sim nahi", "sim not detected", "no sim", "network"),
                   "fault": "network", "escalate": "operator", "steps": [
        S(id="airplane_toggle", title="Airplane mode on-off", setting="airplane", check="airplane",
          how="Turn Airplane mode on for 10 seconds and then off: the phone searches for the network again."),
        S(id="restart", title="Phone restart", how="Check whether the network comes back after a restart."),
        S(id="sim_reinsert", title="Take out the SIM and put it back", check="sim_state",
          how="Switch the phone off, take out the SIM tray, wipe the gold part of the SIM with a soft cloth and put it back properly. Try the other slot too."),
        S(id="network_auto", title="Choose the network automatically", setting="mobile_network",
          how="Mobile network > Network operators > 'Automatically select'. Preferred network type 4G/5G (Auto)."),
        S(id="validity", title="Recharge / validity", how="If incoming calls have stopped, the plan validity may have ended: check in the operator app (MyJio / Airtel Thanks / Vi)."),
        S(id="reset_network", title="Network settings reset", setting="settings", careful=True,
          how="Settings > System > Reset > Reset Wi-Fi, mobile & Bluetooth. You will have to enter saved Wi-Fi passwords again."),
        S(id="sim_replace", title="New SIM (same number)", how="If the SIM does not work in another phone either, the SIM is faulty: get a new SIM with the same number from the operator store (with ID)."),
    ]},
    "mobile_data": {"label": "Mobile data / internet does not work", "words": ("data nahi", "internet nahi", "net nahi", "net nahi chal", "mobile data",
                                                                           "4g nahi", "5g nahi"),
                    "fault": "network", "escalate": "operator", "steps": [
        S(id="data_toggle", title="Mobile data on-off", setting="wireless", how="Turn Mobile data off from Quick settings and on again after 10 seconds."),
        S(id="balance", title="Check the data has not run out", how="If today's data is used up, speed is very low: check the balance in the operator app."),
        S(id="data_saver", title="Turn off Data saver", setting="data_usage", check="data_saver",
          how="When Data saver is on, apps cannot use the internet in the background."),
        S(id="airplane_toggle", title="Airplane mode on-off", setting="airplane", how="On for 10 seconds, then off."),
        S(id="apn_reset", title="APN reset", setting="mobile_network",
          how="Mobile network > Access Point Names > Menu (3 dots) > Reset to default."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="reset_network", title="Network settings reset", setting="settings", careful=True,
          how="Settings > System > Reset > Reset Wi-Fi, mobile & Bluetooth."),
    ]},
    "wifi": {"label": "Wi-Fi does not connect", "words": ("wifi", "wi-fi", "wi fi", "router", "broadband"),
             "fault": "network", "escalate": "repair", "steps": [
        S(id="wifi_toggle", title="Wi-Fi off-on", setting="wifi", check="wifi_on", how="Turn Wi-Fi off and on."),
        S(id="forget", title="Forget the network and reconnect", setting="wifi", how="Long-press the Wi-Fi name > Forget, then connect again by entering the password."),
        S(id="router", title="Router restart", how="Switch the router off and on after 30 seconds. If it fails on another phone too, it is a broadband problem: complain to the provider."),
        S(id="date_time", title="Automatic date and time", setting="date_time", check="auto_time",
          how="With a wrong time, Wi-Fi / websites do not work: turn on 'Automatic date & time'."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="reset_network", title="Network settings reset", setting="settings", careful=True,
          how="Settings > System > Reset > Reset Wi-Fi, mobile & Bluetooth."),
    ]},
    "calls_not_ringing": {"label": "Calls come in but the phone does not ring", "words": ("ring nahi", "ringtone nahi", "call ki awaaz", "missed call",
                                                                                 "call nahi sunai", "silent"),
                          "fault": "speaker", "escalate": "repair", "steps": [
        S(id="dnd_off", title="Turn off Do Not Disturb", setting="dnd", check="dnd", how="If DND is on, calls do not ring: turn it off or remove the schedule."),
        S(id="ring_volume", title="Ring volume", setting="sound", check="ring_volume_pct",
          how="Press the volume button to set Ring volume to full, and change Silent / Vibrate to Normal."),
        S(id="blocked", title="Check the number is not blocked", how="Look in Phone app > Settings > Blocked numbers."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="speaker_test", title="Speaker test", how="Play a song: if there is no sound at all, the speaker is faulty: go to a shop."),
    ]},
    "sound_mic": {"label": "Sound / mic problem", "words": ("awaaz nahi", "aawaz", "sound nahi", "speaker", "mic", "mike", "saamne wale ko awaaz",
                                                             "earpiece", "volume"),
                  "fault": "speaker", "escalate": "repair", "steps": [
        S(id="bluetooth_off", title="Turn off Bluetooth", setting="bluetooth", check="bluetooth_on",
          how="If earbuds / a speaker are connected, the sound goes there: turn Bluetooth off."),
        S(id="volume", title="Volume", setting="sound", check="media_volume_pct", how="Media, ring and call volume at full."),
        S(id="clean_grill", title="Clean the speaker / mic grille",
          how="Clean the speaker and mic holes with a dry soft brush. If the cover / screen guard blocks the holes, remove it."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="test", title="Test with the recorder", how="Speak into the voice recorder and listen: if there is no voice, the mic is faulty; if you cannot hear it, the speaker is faulty: go to a shop."),
    ]},
    "notifications_late": {"label": "Messages / notifications arrive late", "words": ("notification", "late aata", "message late", "whatsapp late",
                                                                                      "der se aata"),
                           "fault": "software", "escalate": "repair", "steps": [
        S(id="battery_saver_off", title="Turn off Battery saver", setting="battery_saver", check="battery_saver",
          how="Battery saver stops apps in the background."),
        S(id="app_battery", title="Set the app's battery to 'Unrestricted'", setting="app_info", pkg="com.whatsapp",
          how="App info > Battery > Unrestricted / No restrictions. On some phones turn on 'Autostart' too."),
        S(id="app_notifications", title="Notification on", setting="app_notifications", pkg="com.whatsapp", how="Notifications on, sound on."),
        S(id="data_saver", title="Turn off Data saver", setting="data_usage", check="data_saver", how="Data saver off."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
    "app_crash": {"label": "App closes by itself / does not open", "words": ("app band", "crash", "khulta nahi", "nahi khul", "stopped", "rukk",
                                                                          "app nahi chal"),
                  "fault": "software", "escalate": "repair", "steps": [
        S(id="clear_cache", title="Clear the app's cache", setting="app_info", pkg="",
          how="App info > Storage > Clear cache (not Clear data: that removes the login / data)."),
        S(id="update_app", title="App update", url="https://play.google.com/store/apps", how="Update the app in the Play Store."),
        S(id="storage", title="Storage", setting="storage", check="storage_used_pct", how="When storage is full, apps crash."),
        S(id="date_time", title="Automatic date and time", setting="date_time", check="auto_time", how="With a wrong time, bank / UPI apps do not work."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="reinstall", title="Reinstall the app", careful=True,
          how="Back up first (WhatsApp: Settings > Chats > Chat backup). Then uninstall and install again from the Play Store."),
    ]},
    "storage_full": {"label": "Storage full", "words": ("storage", "memory full", "space nahi", "jagah nahi", "storage full", "memory bhar"),
                     "fault": "software", "escalate": "repair", "steps": [
        S(id="storage", title="What is taking the space", setting="storage", check="storage_used_pct", how="Look at the biggest part on the Storage screen."),
        S(id="whatsapp_media", title="Clear WhatsApp media",
          how="WhatsApp > Settings > Storage and data > Manage storage > delete big videos / forwarded files."),
        S(id="photos_backup", title="Back up photos, then 'Free up space'", url="https://photos.google.com",
          how="Google Photos > Profile > 'Free up space' (it removes only photos that are already backed up)."),
        S(id="unused_apps", title="Remove unused apps", setting="apps", how="Uninstall apps that have not been used for months."),
        S(id="downloads", title="Downloads folder", how="Files app > Downloads: delete old PDFs / videos."),
    ]},
    "touch": {"label": "Touch does not work / works by itself", "words": ("touch", "ghost", "apne aap", "screen kaam nahi", "touch nahi"),
              "fault": "display", "escalate": "repair", "steps": [
        S(id="clean_screen", title="Screen guard / clean the screen",
          how="Dry hands, clean screen; remove a broken screen guard; unplug the charger and check (a bad charger causes ghost touch)."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="safe_mode", title="Check in safe mode", how="If it is faulty even in safe mode, it is a display problem."),
        S(id="system_update", title="Software update", setting="system_update", how="Update."),
    ]},
    "screen_broken": {"label": "Screen cracked / lines / black", "words": ("screen toot", "toota", "crack", "lines", "black screen", "display",
                                                                        "screen nahi dikh"),
                      "fault": "display", "escalate": "repair", "steps": [
        S(id="backup_now", title="Back up now", how="As long as anything is still visible: Google backup, WhatsApp chat backup, photos backup."),
        S(id="careful_use", title="Protect yourself from the glass", how="Put tape over the broken glass so it does not cut your finger. The display needs replacing: go to a shop."),
    ]},
    "water": {"label": "Phone fell in water", "words": ("paani", "pani", "water", "geela", "bhig", "baarish mein"),
              "fault": "water", "escalate": "repair", "steps": [
        S(id="power_off", title="Switch off at once", how="Switch the phone off at once. Do not turn it on to check."),
        S(id="no_charge", title="Do not charge", how="Do not charge at all: it can short-circuit."),
        S(id="dry", title="Take out the cover and SIM tray, and wipe",
          how="Take out the cover and SIM tray, wipe the outside water with a soft cloth, and keep the port facing down. No hot air from a hair dryer."),
        S(id="shop_fast", title="Go to a shop soon", how="Water inside causes rust: go to a repair shop today (cleaning). Putting it in rice does not remove the water inside."),
    ]},
    "wont_turn_on": {"label": "Phone does not turn on", "words": ("chalu nahi", "on nahi", "dead", "band pada", "start nahi", "switch on nahi"),
                     "fault": "motherboard", "escalate": "repair", "steps": [
        S(id="charge_30", title="Charge for 30 minutes", how="Charge on the original charger for 30 minutes (if the battery is completely empty, the sign appears late)."),
        S(id="force_restart", title="Force restart", how="Hold Power + Volume down together for 15-20 seconds."),
        S(id="other_charger", title="Another charger", how="Try another charger / socket."),
        S(id="shop", title="Shop", how="If it still does not turn on, it is the battery / board: go to a shop. Take the phone's bill with you (warranty)."),
    ]},
    "otp_not_coming": {"label": "OTP / SMS does not arrive", "words": ("otp nahi", "sms nahi", "message nahi aata", "otp", "code nahi aata"),
                       "fault": "network", "escalate": "operator", "steps": [
        S(id="signal", title="Signal", check="signal_level", how="Go where the network is good; turn Airplane mode on and off."),
        S(id="storage", title="Storage", setting="storage", check="storage_used_pct", how="When storage is completely full, SMS do not arrive."),
        S(id="validity", title="Recharge validity", how="When validity ends, incoming SMS stop."),
        S(id="spam_filter", title="Check Spam / blocked", how="Check Messages app > Spam & blocked in case the OTP went there."),
        S(id="dnd_dlt", title="DND service", how="Even with the operator's full-block DND, bank OTPs arrive; if they do not, call the operator helpline."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
    "bluetooth": {"label": "Bluetooth / earbuds do not connect", "words": ("bluetooth", "earbuds", "airdopes", "neckband", "speaker nahi jud"),
                  "fault": "other", "escalate": "repair", "steps": [
        S(id="bt_toggle", title="Bluetooth off-on", setting="bluetooth", check="bluetooth_on", how="Turn off and on."),
        S(id="forget_pair", title="Forget and pair again", setting="bluetooth", how="Device name > Forget / Unpair, reset the earbuds in their case (hold the button 10 sec), then pair again."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
    "camera": {"label": "Camera does not work / blurry", "words": ("camera", "photo blur", "camera nahi"),
               "fault": "camera", "escalate": "repair", "steps": [
        S(id="lens_clean", title="Clean the lens", how="Clean the lens with a soft cloth; check the cover is not blocking the lens."),
        S(id="camera_cache", title="Camera app cache", setting="apps", how="Apps > Camera > Storage > Clear cache."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="safe_mode", title="Camera in safe mode", how="If it does not work even in safe mode, it is the camera hardware: go to a shop."),
    ]},
    "lost_stolen": {"label": "Phone lost / stolen", "words": ("kho gaya", "chori", "stolen", "lost", "gum ho", "chhin"),
                    "fault": "other", "escalate": "official", "steps": [
        S(id="block_sim", title="Get the SIM blocked", how="Get the SIM blocked at once through the operator helpline / store (to stop misuse of OTP / UPI)."),
        S(id="find_device", title="Google Find My Device", url="https://www.google.com/android/find",
          how="From another phone / computer, with your Google account: see where the phone is, lock it with 'Secure device', and 'Erase' if needed."),
        S(id="bank_block", title="Stop bank / UPI", how="Have UPI / net banking stopped through the bank helpline. If money is gone, call 1930 at once."),
        S(id="police", title="Police complaint", how="Complain at the nearest police station or on the state police portal online; keep a copy."),
        S(id="duplicate_sim", title="New SIM with the same number", how="From the operator store, with ID."),
        S(id="ceir", title="Block the IMEI on CEIR (Sanchar Saathi)", url="https://ceir.sancharsaathi.gov.in",
          how="You need: the phone's bill, a copy of the police complaint, ID proof, the IMEI (on the box / bill), and a number for the OTP. Once blocked, the phone will not work on any network; if it is found, unblock it."),
    ]},
    "forgot_lock": {"label": "Forgot lock / pattern / password", "words": ("pattern bhool", "password bhool", "lock bhool", "pin bhool",
                                                                              "lock khul", "frp", "google lock"),
                    "fault": "unlock", "escalate": "repair", "steps": [
        S(id="find_device_erase", title="Erase with Find My Device", url="https://www.google.com/android/find", careful=True,
          how="The proper way to remove the lock is a phone reset: the data is erased (it comes back from the Google backup). After the reset you need the same Google account."),
        S(id="service_centre", title="Brand service centre", how="Go to the brand's service centre with the bill and ID. Hoola does not suggest tricks to break a lock."),
    ]},
    "hacked_fraud": {"label": "Hacked / fraud / strange apps", "words": ("hack", "fraud", "virus", "ajeeb app", "paise kat", "screen share",
                                                                    "remote", "anydesk", "khud se click", "scam"),
                     "fault": "software", "escalate": "official", "steps": [
        S(id="money_1930", title="Money lost? Call 1930 at once", url="https://cybercrime.gov.in",
          how="If money has been debited, do not wait: call 1930 (National Cyber Crime Helpline) or complain on cybercrime.gov.in; tell the bank too."),
        S(id="internet_off", title="Switch off the internet", setting="airplane", how="Turn Airplane mode on so nobody can control the phone remotely."),
        S(id="remove_apps", title="Remove unknown / screen-share apps", setting="apps",
          how="AnyDesk, TeamViewer, QuickSupport or any unknown app you did not install: uninstall it."),
        S(id="accessibility", title="Unknown app in Accessibility", setting="accessibility",
          how="Accessibility > Installed apps: turn off the permission of any unknown app (fraud apps control the phone this way)."),
        S(id="usb_debug", title="Turn off USB debugging", setting="developer", check="usb_debugging", how="Developer options > USB debugging off."),
        S(id="password", title="Change the Google password", url="https://myaccount.google.com/security",
          how="From another trusted device, change the Google password and run 'Security checkup'."),
        S(id="chakshu", title="Report the fraud call / SMS (Chakshu)", url="https://sancharsaathi.gov.in",
          how="Report the fraud call / SMS / WhatsApp on Sanchar Saathi > Chakshu."),
        S(id="system_update", title="Software update", setting="system_update", check="security_patch", how="Security update."),
    ]},
    "gps": {"label": "Location / GPS is wrong", "words": ("gps", "location galat", "map galat", "location nahi"),
            "fault": "other", "escalate": "repair", "steps": [
        S(id="location_on", title="Location on", setting="location", check="location_on", how="Location on, 'Google Location Accuracy' on."),
        S(id="open_sky", title="Outdoors", how="Stand on a roof / open place for 1-2 minutes; remove the cover if it has a metal plate."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
}

SETTING_LABEL = {
    "battery_usage": "Battery usage", "battery_saver": "Battery saver", "storage": "Storage", "wifi": "Wi-Fi",
    "bluetooth": "Bluetooth", "mobile_network": "Mobile network", "wireless": "Network", "airplane": "Airplane mode",
    "data_usage": "Data usage", "date_time": "Date & time", "display": "Display", "sound": "Sound", "dnd": "Do Not Disturb",
    "apps": "Apps", "app_info": "App info", "app_notifications": "App notifications", "location": "Location",
    "security": "Security", "accessibility": "Accessibility", "developer": "Developer options", "system_update": "Software update",
    "about": "About phone", "settings": "Settings",
}


def detect(text: str) -> list[str]:
    """Issue ids in her words, best match first ('other' when nothing fits)."""
    t = " " + re.sub(r"\s+", " ", str(text or "").lower()) + " "
    scored = []
    for iid, spec in ISSUES.items():
        best = 0
        for w in spec["words"]:
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t):
                best = max(best, len(w))
        if best:
            scored.append((best, iid))
    return [i for _, i in sorted(scored, reverse=True)] or ["other"]


def findings(snap: dict) -> list[dict]:
    """What the phone's own check says, in plain words. Each: id, level (info|warn|bad), text, issues it matters for."""
    if not snap:
        return []
    f: list[dict] = []

    def add(fid, level, text, issues):
        f.append({"id": fid, "level": level, "text": text, "issues": issues})
    g = snap.get
    if isinstance(g("storage_used_pct"), (int, float)) and g("storage_used_pct") >= 90:
        add("storage", "bad" if g("storage_used_pct") >= 95 else "warn",
            f"Storage is {g('storage_used_pct'):.0f}% full ({g('storage_free_gb') or 0:.1f} GB free): slow phone, app crashes, SMS stop.",
            ["slow", "app_crash", "storage_full", "otp_not_coming", "camera"])
    if g("ram_low") or (isinstance(g("ram_free_pct"), (int, float)) and g("ram_free_pct") < 10):
        add("ram", "warn", "Very little free RAM: too many apps are open.", ["slow", "app_crash", "heating"])
    if isinstance(g("uptime_hours"), (int, float)) and g("uptime_hours") >= 72:
        add("uptime", "info", f"The phone has not been restarted for {g('uptime_hours') / 24:.0f} days.",
            ["slow", "heating", "battery_drain", "no_network", "mobile_data", "app_crash", "notifications_late"])
    t = g("battery_temp_c")
    if isinstance(t, (int, float)) and t >= 42:
        add("temp", "bad" if t >= 46 else "warn", f"Battery is at {t:.0f}°C (above 40 is hot).", ["heating", "not_charging", "battery_drain"])
    if g("battery_health") in ("dead", "overheat", "over_voltage", "failure"):
        add("battery_health", "bad", f"The phone itself reports the battery as '{g('battery_health')}': it needs replacing.",
            ["battery_drain", "heating", "not_charging", "wont_turn_on"])
    if isinstance(g("thermal_status"), int) and g("thermal_status") >= 3:
        add("thermal", "bad", "The phone has reduced its speed because of heat.", ["heating", "slow"])
    if g("battery_saver"):
        add("battery_saver", "info", "Battery saver is on: notifications come late and the phone is a bit slow.", ["notifications_late", "slow"])
    if g("airplane"):
        add("airplane", "bad", "Airplane mode is on: calls / internet will not work.", ["no_network", "mobile_data", "otp_not_coming"])
    if g("sim_state") in ("absent", "not_ready", "locked", "network_locked"):
        add("sim", "bad", {"absent": "SIM not found.", "locked": "The SIM is asking for a PIN / PUK.",
                           "network_locked": "The phone is locked to another network.", "not_ready": "SIM not ready."}[g("sim_state")],
            ["no_network", "otp_not_coming", "mobile_data"])
    if isinstance(g("signal_level"), int) and g("signal_level") <= 1 and not g("airplane"):
        add("signal", "warn", "Very weak signal (0-1 bars).", ["no_network", "mobile_data", "otp_not_coming", "battery_drain"])
    if g("data_saver"):
        add("data_saver", "info", "Data saver is on.", ["mobile_data", "notifications_late"])
    if g("auto_time") is False:
        add("auto_time", "warn", "Date and time are not set automatically: this causes problems with bank / UPI / Wi-Fi.", ["app_crash", "wifi", "otp_not_coming"])
    if g("dnd"):
        add("dnd", "warn", "Do Not Disturb is on: no sound for calls / notifications.", ["calls_not_ringing", "notifications_late"])
    if g("ringer") in ("silent", "vibrate") or g("ring_volume_pct") == 0:
        add("ringer", "warn", f"Phone is on {g('ringer') if g('ringer') != 'normal' else 'ring volume 0'}.", ["calls_not_ringing"])
    if g("media_volume_pct") == 0:
        add("media_volume", "info", "Media volume is 0.", ["sound_mic"])
    if g("bluetooth_on"):
        add("bluetooth", "info", "Bluetooth is on (sound may be going to earbuds / a speaker).", ["sound_mic", "calls_not_ringing"])
    patch = str(g("security_patch") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", patch):
        from datetime import date
        try:
            age = (date.today() - date.fromisoformat(patch)).days
            if age > 365:
                add("patch", "warn", f"Security update is {age // 30} months old ({patch}).", ["hacked_fraud", "slow", "app_crash"])
        except ValueError:
            pass
    if g("usb_debugging"):
        add("usb_debugging", "warn", "USB debugging is on: turn it off if you do not need it.", ["hacked_fraud"])
    if g("vpn"):
        add("vpn", "info", "VPN is on.", ["mobile_data", "wifi", "hacked_fraud"])
    cur = g("current_ma")
    if g("plugged") not in (None, "none") and g("charging_status") == "charging" and isinstance(cur, int) and 0 < cur < 400:
        add("slow_charge", "warn", f"Charging at only ~{cur} mA: the cable / charger / port is weak.", ["not_charging"])
    if g("plugged") not in (None, "none") and g("charging_status") in ("not_charging", "discharging"):
        add("not_charging_now", "bad", "A charger is plugged in but the phone is not charging.", ["not_charging"])
    top = g("top_apps") or []
    if top:
        a = top[0]
        add("top_app", "info", f"Most used in the last 24 hours:{a.get('label')} ({a.get('minutes')} min).",
            ["battery_drain", "heating", "slow"])
    return f
