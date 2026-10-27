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
    "slow": {"label": "Phone slow / hang hota hai", "words": ("slow", "hang", "atak", "lag", "dheema", "dheere", "freeze", "ruk jata"),
             "fault": "software", "escalate": "repair", "steps": [
        S(id="restart", title="Phone restart", how="Power button dabake rakhiye > Restart. Kai din se band nahi hua to yahi sabse bada ilaaj hai."),
        S(id="storage", title="Storage khaali karo", setting="storage", check="storage_used_pct",
          how="90% se zyada bhara ho to phone dheema hota hai. Bade videos / WhatsApp media / purane downloads hataiye ya Google Photos / PC par rakhiye."),
        S(id="heavy_app", title="Sabse zyada chalne wala app", setting="app_info", pkg="top", check="top_apps",
          how="Is app ki 'Storage > Clear cache' kijiye; zaroorat na ho to 'Force stop' ya uninstall."),
        S(id="update_apps", title="Apps update", url="https://play.google.com/store/apps",
          how="Play Store > Profile photo > 'Manage apps & device' > 'Update all'."),
        S(id="system_update", title="Phone ka software update", setting="system_update", check="security_patch",
          how="Settings > Software update / System update > Check for updates. Wi-Fi aur 50% battery ke saath."),
        S(id="safe_mode", title="Safe mode mein dekhiye",
          how="Power button dabaiye, screen par 'Power off' ko lamba dabaiye > Safe mode. Safe mode mein theek chale to koi download kiya app wajah hai: haal ke apps ek-ek karke hataiye. Restart karte hi safe mode band."),
        S(id="factory_reset", title="Factory reset (aakhri upay)", setting="settings", careful=True,
          how="Pehle Google backup + WhatsApp chat backup + photos ka backup. Phir Settings > System > Reset > Erase all data. Sab data mit jata hai: sirf aapki haan ke baad."),
    ]},
    "battery_drain": {"label": "Battery jaldi khatam", "words": ("battery jaldi", "battery khatam", "battery drain", "backup kam", "charge nahi tikta",
                                                                "battery nahi chalti", "battery down"),
                      "fault": "battery", "escalate": "repair", "steps": [
        S(id="battery_usage", title="Kaun battery kha raha hai", setting="battery_usage", check="top_apps",
          how="Battery usage mein sabse upar wala app dekhiye. Woh app aap kam chalati hain to uski battery 'Restricted' kijiye."),
        S(id="brightness", title="Brightness auto", setting="display", check="brightness_pct",
          how="Display > Brightness 'Adaptive / Auto' on, aur screen timeout 30 second."),
        S(id="battery_saver", title="Battery saver", setting="battery_saver", how="Battery 20% par apne aap Battery saver chalu ho, aisa set kijiye."),
        S(id="location_off", title="Location zaroorat par hi", setting="location", check="location_on",
          how="Map / ride ke baad Location band kar dijiye; apps ko 'Only while using' do."),
        S(id="restart", title="Phone restart", how="Kai din se chal raha ho to restart: atke hue kaam ruk jaate hain."),
        S(id="system_update", title="Software update", setting="system_update", how="Naye update mein battery ki kharabi theek hoti hai."),
        S(id="battery_health", title="Battery ki haalat", check="battery_health",
          how="2-3 saal purani battery ya phooli hui battery (back cover utha ho) badalni padti hai: phooli battery khatarnak hai, use mat kijiye."),
    ]},
    "heating": {"label": "Phone garam hota hai", "words": ("garam", "heat", "gram", "hot", "tapta", "jal raha"),
                "fault": "battery", "escalate": "repair", "steps": [
        S(id="cool_down", title="Thanda hone do", check="battery_temp_c",
          how="Abhi charging se hataiye, cover nikaliye, dhoop / gaadi ke dashboard se door rakhiye, 10 minute kuch mat chalaiye."),
        S(id="charge_right", title="Sahi charger, bina cover", check="plugged",
          how="Original / achhe brand ka charger aur cable. Charge karte waqt game / video call nahi, takiye par nahi."),
        S(id="heavy_app", title="Bhaari app band", setting="app_info", pkg="top", check="top_apps",
          how="Game, camera, video ya hotspot zyada der chalne se garam hota hai. Is app ko Force stop kijiye."),
        S(id="restart", title="Phone restart", how="Atka hua background kaam ruk jata hai."),
        S(id="system_update", title="Software update", setting="system_update", how="Update mein garmi ki kharabi theek ho sakti hai."),
        S(id="safe_mode", title="Safe mode mein garmi dekhiye", how="Safe mode mein bhi bina chalaye garam ho to hardware / battery ki dikkat: dukaan."),
    ]},
    "not_charging": {"label": "Charge nahi hota / dheere hota hai", "words": ("charge nahi", "charging nahi", "slow charging", "charge dheere",
                                                                             "charging slow", "charger"),
                     "fault": "charging_port", "escalate": "repair", "steps": [
        S(id="other_cable", title="Doosra cable / charger", check="plugged",
          how="Doosre achhe cable aur charger se try kijiye; cable mudi / kati ho to wahi wajah hai."),
        S(id="clean_port", title="Charging port saaf",
          how="Phone band karke torch se port dekhiye. Kachra ho to sookhe naram toothbrush / plastic toothpick se dheere saaf kijiye. Pin / sui kabhi nahi."),
        S(id="restart", title="Phone restart", how="Restart karke dobara charge lagaiye."),
        S(id="cool_charge", title="Garam phone dheere charge hota hai", check="battery_temp_c",
          how="Phone garam ho to thanda hone dijiye; cover hata ke charge kijiye."),
        S(id="safe_mode", title="Safe mode mein charge", how="Safe mode mein theek charge ho to koi app wajah hai."),
        S(id="port_repair", title="Port / battery badalna", how="Doosre cable se bhi na ho to charging port ya battery kharab: dukaan par 15-30 minute ka kaam hota hai."),
    ]},
    "no_network": {"label": "Network / signal nahi", "words": ("network nahi", "signal nahi", "no service", "emergency call only", "range nahi",
                                                              "sim nahi", "sim not detected", "no sim", "network"),
                   "fault": "network", "escalate": "operator", "steps": [
        S(id="airplane_toggle", title="Airplane mode on-off", setting="airplane", check="airplane",
          how="Airplane mode 10 second on karke off kijiye: network dobara dhoondhta hai."),
        S(id="restart", title="Phone restart", how="Restart ke baad network aata hai ya nahi dekhiye."),
        S(id="sim_reinsert", title="SIM nikal ke dobara", check="sim_state",
          how="Phone band, SIM tray nikaliye, SIM ka sona hissa naram kapde se saaf, sahi lagaiye. Doosre slot mein bhi try."),
        S(id="network_auto", title="Network apne aap chune", setting="mobile_network",
          how="Mobile network > Network operators > 'Automatically select'. Preferred network type 4G/5G (Auto)."),
        S(id="validity", title="Recharge / validity", how="Incoming band ho to plan ki validity khatam ho sakti hai: operator app (MyJio / Airtel Thanks / Vi) mein dekhiye."),
        S(id="reset_network", title="Network settings reset", setting="settings", careful=True,
          how="Settings > System > Reset > Reset Wi-Fi, mobile & Bluetooth. Saved Wi-Fi password phir se daalne padenge."),
        S(id="sim_replace", title="Nayi SIM (same number)", how="Doosre phone mein bhi SIM na chale to SIM kharab: operator store se same number ki nayi SIM (ID ke saath)."),
    ]},
    "mobile_data": {"label": "Mobile data / internet nahi chalta", "words": ("data nahi", "internet nahi", "net nahi", "net nahi chal", "mobile data",
                                                                           "4g nahi", "5g nahi"),
                    "fault": "network", "escalate": "operator", "steps": [
        S(id="data_toggle", title="Mobile data on-off", setting="wireless", how="Quick settings se Mobile data band karke 10 second baad chalu."),
        S(id="balance", title="Data khatam to nahi", how="Aaj ka data khatam ho gaya ho to speed bahut kam: operator app mein balance dekhiye."),
        S(id="data_saver", title="Data saver band", setting="data_usage", check="data_saver",
          how="Data saver on ho to apps background mein net nahi le paate."),
        S(id="airplane_toggle", title="Airplane mode on-off", setting="airplane", how="10 second on karke off."),
        S(id="apn_reset", title="APN reset", setting="mobile_network",
          how="Mobile network > Access Point Names > Menu (3 dots) > Reset to default."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="reset_network", title="Network settings reset", setting="settings", careful=True,
          how="Settings > System > Reset > Reset Wi-Fi, mobile & Bluetooth."),
    ]},
    "wifi": {"label": "Wi-Fi nahi judta", "words": ("wifi", "wi-fi", "wi fi", "router", "broadband"),
             "fault": "network", "escalate": "repair", "steps": [
        S(id="wifi_toggle", title="Wi-Fi off-on", setting="wifi", check="wifi_on", how="Wi-Fi band karke chalu kijiye."),
        S(id="forget", title="Network bhool ke dobara judo", setting="wifi", how="Wi-Fi naam par lamba dabaiye > Forget, phir password daal ke dobara judiye."),
        S(id="router", title="Router restart", how="Router ka switch band, 30 second baad chalu. Doosre phone par bhi na chale to broadband ki dikkat: provider ko shikayat."),
        S(id="date_time", title="Date-time apne aap", setting="date_time", check="auto_time",
          how="Galat time hone par Wi-Fi / websites nahi chalte: 'Automatic date & time' on."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="reset_network", title="Network settings reset", setting="settings", careful=True,
          how="Settings > System > Reset > Reset Wi-Fi, mobile & Bluetooth."),
    ]},
    "calls_not_ringing": {"label": "Call aati hai par ring nahi bajti", "words": ("ring nahi", "ringtone nahi", "call ki awaaz", "missed call",
                                                                                 "call nahi sunai", "silent"),
                          "fault": "speaker", "escalate": "repair", "steps": [
        S(id="dnd_off", title="Do Not Disturb band", setting="dnd", check="dnd", how="DND on ho to call ring nahi karti: band kijiye ya schedule hataiye."),
        S(id="ring_volume", title="Ring volume", setting="sound", check="ring_volume_pct",
          how="Volume button dabake Ring volume poora, aur Silent / Vibrate se Normal."),
        S(id="blocked", title="Number block to nahi", how="Phone app > Settings > Blocked numbers mein dekhiye."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="speaker_test", title="Speaker test", how="Gaana chala ke dekhiye: awaaz hi na aaye to speaker kharab: dukaan."),
    ]},
    "sound_mic": {"label": "Awaaz / mic ki dikkat", "words": ("awaaz nahi", "aawaz", "sound nahi", "speaker", "mic", "mike", "saamne wale ko awaaz",
                                                             "earpiece", "volume"),
                  "fault": "speaker", "escalate": "repair", "steps": [
        S(id="bluetooth_off", title="Bluetooth band", setting="bluetooth", check="bluetooth_on",
          how="Earbuds / speaker jude hon to awaaz udhar jaati hai: Bluetooth band kijiye."),
        S(id="volume", title="Volume", setting="sound", check="media_volume_pct", how="Media, ring aur call volume poora."),
        S(id="clean_grill", title="Speaker / mic jaali saaf",
          how="Sookhe naram brush se speaker aur mic ke chhed saaf. Cover / screen guard chhed dhak raha ho to hataiye."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="test", title="Recorder se test", how="Voice recorder mein bol ke suniye: aawaz na ho to mic, sunai na de to speaker: dukaan."),
    ]},
    "notifications_late": {"label": "Message / notification late aate hain", "words": ("notification", "late aata", "message late", "whatsapp late",
                                                                                      "der se aata"),
                           "fault": "software", "escalate": "repair", "steps": [
        S(id="battery_saver_off", title="Battery saver band", setting="battery_saver", check="battery_saver",
          how="Battery saver apps ko background mein rok deta hai."),
        S(id="app_battery", title="App ki battery 'Unrestricted'", setting="app_info", pkg="com.whatsapp",
          how="App info > Battery > Unrestricted / No restrictions. Kuch phones mein 'Autostart' bhi on kijiye."),
        S(id="app_notifications", title="Notification on", setting="app_notifications", pkg="com.whatsapp", how="Notifications on, sound on."),
        S(id="data_saver", title="Data saver band", setting="data_usage", check="data_saver", how="Data saver band."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
    "app_crash": {"label": "App band ho jata hai / nahi khulta", "words": ("app band", "crash", "khulta nahi", "nahi khul", "stopped", "rukk",
                                                                          "app nahi chal"),
                  "fault": "software", "escalate": "repair", "steps": [
        S(id="clear_cache", title="App ka cache saaf", setting="app_info", pkg="",
          how="App info > Storage > Clear cache (Clear data nahi: usse login / data jaata hai)."),
        S(id="update_app", title="App update", url="https://play.google.com/store/apps", how="Play Store mein app update kijiye."),
        S(id="storage", title="Storage", setting="storage", check="storage_used_pct", how="Storage bhara ho to app crash hote hain."),
        S(id="date_time", title="Date-time apne aap", setting="date_time", check="auto_time", how="Galat time par bank / UPI apps nahi chalte."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="reinstall", title="App dobara install", careful=True,
          how="Pehle backup (WhatsApp: Settings > Chats > Chat backup). Phir uninstall karke Play Store se dobara."),
    ]},
    "storage_full": {"label": "Storage full", "words": ("storage", "memory full", "space nahi", "jagah nahi", "storage full", "memory bhar"),
                     "fault": "software", "escalate": "repair", "steps": [
        S(id="storage", title="Kya jagah le raha hai", setting="storage", check="storage_used_pct", how="Storage screen mein sabse bada hissa dekhiye."),
        S(id="whatsapp_media", title="WhatsApp media saaf",
          how="WhatsApp > Settings > Storage and data > Manage storage > bade videos / forwarded files delete."),
        S(id="photos_backup", title="Photos backup karke 'Free up space'", url="https://photos.google.com",
          how="Google Photos > Profile > 'Free up space' (backup ho chuki photos hi hatati hai)."),
        S(id="unused_apps", title="Bekaar apps hatao", setting="apps", how="Jo apps mahino se nahi chale, uninstall."),
        S(id="downloads", title="Downloads folder", how="Files app > Downloads: purani PDF / video delete."),
    ]},
    "touch": {"label": "Touch nahi chalta / apne aap chalta hai", "words": ("touch", "ghost", "apne aap", "screen kaam nahi", "touch nahi"),
              "fault": "display", "escalate": "repair", "steps": [
        S(id="clean_screen", title="Screen guard / screen saaf",
          how="Haath sookhe, screen saaf; toota screen guard hataiye; charger nikal ke dekhiye (kharab charger se ghost touch hota hai)."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="safe_mode", title="Safe mode mein dekhiye", how="Safe mode mein bhi kharab ho to display ki dikkat."),
        S(id="system_update", title="Software update", setting="system_update", how="Update."),
    ]},
    "screen_broken": {"label": "Screen tooti / lines / black", "words": ("screen toot", "toota", "crack", "lines", "black screen", "display",
                                                                        "screen nahi dikh"),
                      "fault": "display", "escalate": "repair", "steps": [
        S(id="backup_now", title="Abhi backup", how="Jab tak thoda bhi dikh raha hai: Google backup, WhatsApp chat backup, photos backup."),
        S(id="careful_use", title="Kaanch se bachiye", how="Toote kaanch par tape lagaiye, ungli na kaate. Display badalna padega: dukaan."),
    ]},
    "water": {"label": "Phone paani mein gir gaya", "words": ("paani", "pani", "water", "geela", "bhig", "baarish mein"),
              "fault": "water", "escalate": "repair", "steps": [
        S(id="power_off", title="Turant band", how="Phone turant band kijiye. Chalu karke check mat kijiye."),
        S(id="no_charge", title="Charge mat lagao", how="Charge bilkul nahi: short ho sakta hai."),
        S(id="dry", title="Cover, SIM tray nikalo, pochho",
          how="Cover aur SIM tray nikaliye, bahar ka paani naram kapde se pochhiye, port neeche ki taraf rakhiye. Hair dryer ki garam hawa nahi."),
        S(id="shop_fast", title="Jaldi dukaan", how="Andar ka paani jang lagata hai: aaj hi repair dukaan (cleaning). Chawal mein rakhne se andar ka paani nahi nikalta."),
    ]},
    "wont_turn_on": {"label": "Phone chalu nahi hota", "words": ("chalu nahi", "on nahi", "dead", "band pada", "start nahi", "switch on nahi"),
                     "fault": "motherboard", "escalate": "repair", "steps": [
        S(id="charge_30", title="30 minute charge", how="Original charger par 30 minute lagaiye (battery bilkul khatam ho to der se nishaan aata hai)."),
        S(id="force_restart", title="Force restart", how="Power + Volume down ek saath 15-20 second dabaiye."),
        S(id="other_charger", title="Doosra charger", how="Doosre charger / socket se try."),
        S(id="shop", title="Dukaan", how="Phir bhi na chale to battery / board: dukaan. Phone ka bill saath le jaiye (warranty)."),
    ]},
    "otp_not_coming": {"label": "OTP / SMS nahi aata", "words": ("otp nahi", "sms nahi", "message nahi aata", "otp", "code nahi aata"),
                       "fault": "network", "escalate": "operator", "steps": [
        S(id="signal", title="Signal", check="signal_level", how="Network achha ho wahan jaiye; Airplane mode on-off."),
        S(id="storage", title="Storage", setting="storage", check="storage_used_pct", how="Storage poori bhari ho to SMS nahi aate."),
        S(id="validity", title="Recharge validity", how="Validity khatam to incoming SMS ruk jaate hain."),
        S(id="spam_filter", title="Spam / blocked mein dekhiye", how="Messages app > Spam & blocked mein OTP to nahi gaya."),
        S(id="dnd_dlt", title="DND service", how="Operator ki DND full block ho to bhi bank OTP aate hain; na aayein to operator helpline."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
    "bluetooth": {"label": "Bluetooth / earbuds nahi judte", "words": ("bluetooth", "earbuds", "airdopes", "neckband", "speaker nahi jud"),
                  "fault": "other", "escalate": "repair", "steps": [
        S(id="bt_toggle", title="Bluetooth off-on", setting="bluetooth", check="bluetooth_on", how="Band karke chalu."),
        S(id="forget_pair", title="Bhool ke dobara jodo", setting="bluetooth", how="Device naam > Forget / Unpair, earbuds ko case mein reset (button 10 sec), phir jodiye."),
        S(id="restart", title="Phone restart", how="Restart."),
    ]},
    "camera": {"label": "Camera nahi chalta / blur", "words": ("camera", "photo blur", "camera nahi"),
               "fault": "camera", "escalate": "repair", "steps": [
        S(id="lens_clean", title="Lens saaf", how="Lens naram kapde se saaf; cover lens dhak to nahi raha."),
        S(id="camera_cache", title="Camera app ka cache", setting="apps", how="Apps > Camera > Storage > Clear cache."),
        S(id="restart", title="Phone restart", how="Restart."),
        S(id="safe_mode", title="Safe mode mein camera", how="Safe mode mein bhi na chale to camera hardware: dukaan."),
    ]},
    "lost_stolen": {"label": "Phone kho gaya / chori", "words": ("kho gaya", "chori", "stolen", "lost", "gum ho", "chhin"),
                    "fault": "other", "escalate": "official", "steps": [
        S(id="block_sim", title="SIM band karwao", how="Turant operator helpline / store par SIM block karwaiye (OTP / UPI ka galat use rokne ke liye)."),
        S(id="find_device", title="Google Find My Device", url="https://www.google.com/android/find",
          how="Doosre phone / computer se apne Google account se: phone ki jagah dekhiye, 'Secure device' se lock, zaroorat ho to 'Erase'."),
        S(id="bank_block", title="Bank / UPI band", how="Bank helpline par UPI / net banking rukwaiye. Paise gaye hon to turant 1930 par call."),
        S(id="police", title="Police complaint", how="Najdeeki thane mein ya state police portal par online complaint; copy rakhiye."),
        S(id="duplicate_sim", title="Same number ki nayi SIM", how="Operator store se ID ke saath."),
        S(id="ceir", title="CEIR par IMEI block (Sanchar Saathi)", url="https://ceir.sancharsaathi.gov.in",
          how="Chahiye: phone ka bill, police complaint ki copy, ID proof, IMEI (dabbe / bill par), OTP ke liye ek number. Block hone par phone kisi bhi network par nahi chalega; milne par unblock."),
    ]},
    "forgot_lock": {"label": "Lock / pattern / password bhool gaye", "words": ("pattern bhool", "password bhool", "lock bhool", "pin bhool",
                                                                              "lock khul", "frp", "google lock"),
                    "fault": "unlock", "escalate": "repair", "steps": [
        S(id="find_device_erase", title="Find My Device se erase", url="https://www.google.com/android/find", careful=True,
          how="Lock hatane ka sahi tareeka phone reset hai: data mit jata hai (Google backup se wapas aata hai). Reset ke baad wahi Google account chahiye."),
        S(id="service_centre", title="Brand service centre", how="Bill aur ID ke saath brand ke service centre par. Hoola lock todne ke 'jugaad' nahi batata."),
    ]},
    "hacked_fraud": {"label": "Hack / fraud / ajeeb apps", "words": ("hack", "fraud", "virus", "ajeeb app", "paise kat", "screen share",
                                                                    "remote", "anydesk", "khud se click", "scam"),
                     "fault": "software", "escalate": "official", "steps": [
        S(id="money_1930", title="Paise gaye? Turant 1930", url="https://cybercrime.gov.in",
          how="Paise kat gaye hon to der mat kijiye: 1930 par call (National Cyber Crime Helpline) ya cybercrime.gov.in par shikayat; bank ko bhi."),
        S(id="internet_off", title="Internet band", setting="airplane", how="Airplane mode on: koi remote se phone na chala sake."),
        S(id="remove_apps", title="Anjaan / screen-share apps hatao", setting="apps",
          how="AnyDesk, TeamViewer, QuickSupport ya koi anjaan app jo aapne nahi daala: uninstall."),
        S(id="accessibility", title="Accessibility mein anjaan app", setting="accessibility",
          how="Accessibility > Installed apps: jo anjaan ho uski permission band (yahi se fraud apps phone chalate hain)."),
        S(id="usb_debug", title="USB debugging band", setting="developer", check="usb_debugging", how="Developer options > USB debugging off."),
        S(id="password", title="Google password badlo", url="https://myaccount.google.com/security",
          how="Doosre bharose ke device se Google password badaliye aur 'Security checkup' kijiye."),
        S(id="chakshu", title="Fraud call / SMS ki report (Chakshu)", url="https://sancharsaathi.gov.in",
          how="Sanchar Saathi > Chakshu par fraud call / SMS / WhatsApp ki report."),
        S(id="system_update", title="Software update", setting="system_update", check="security_patch", how="Security update."),
    ]},
    "gps": {"label": "Location / GPS galat", "words": ("gps", "location galat", "map galat", "location nahi"),
            "fault": "other", "escalate": "repair", "steps": [
        S(id="location_on", title="Location on", setting="location", check="location_on", how="Location on, 'Google Location Accuracy' on."),
        S(id="open_sky", title="Khule mein", how="Chhat / khuli jagah 1-2 minute; cover mein metal plate ho to hataiye."),
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
            f"Storage {g('storage_used_pct'):.0f}% bhari hai ({g('storage_free_gb') or 0:.1f} GB khaali): phone dheema, app crash, SMS rukna.",
            ["slow", "app_crash", "storage_full", "otp_not_coming", "camera"])
    if g("ram_low") or (isinstance(g("ram_free_pct"), (int, float)) and g("ram_free_pct") < 10):
        add("ram", "warn", "RAM bahut kam khaali: bahut saare apps khule hain.", ["slow", "app_crash", "heating"])
    if isinstance(g("uptime_hours"), (int, float)) and g("uptime_hours") >= 72:
        add("uptime", "info", f"Phone {g('uptime_hours') / 24:.0f} din se restart nahi hua.",
            ["slow", "heating", "battery_drain", "no_network", "mobile_data", "app_crash", "notifications_late"])
    t = g("battery_temp_c")
    if isinstance(t, (int, float)) and t >= 42:
        add("temp", "bad" if t >= 46 else "warn", f"Battery {t:.0f}°C par hai (40 se upar garam).", ["heating", "not_charging", "battery_drain"])
    if g("battery_health") in ("dead", "overheat", "over_voltage", "failure"):
        add("battery_health", "bad", f"Phone khud battery ko '{g('battery_health')}' bata raha hai: battery badalni padegi.",
            ["battery_drain", "heating", "not_charging", "wont_turn_on"])
    if isinstance(g("thermal_status"), int) and g("thermal_status") >= 3:
        add("thermal", "bad", "Phone ne garmi ki wajah se apni speed kam kar di hai.", ["heating", "slow"])
    if g("battery_saver"):
        add("battery_saver", "info", "Battery saver chalu hai: notification late aur phone thoda dheema.", ["notifications_late", "slow"])
    if g("airplane"):
        add("airplane", "bad", "Airplane mode chalu hai: call / net nahi chalega.", ["no_network", "mobile_data", "otp_not_coming"])
    if g("sim_state") in ("absent", "not_ready", "locked", "network_locked"):
        add("sim", "bad", {"absent": "SIM nahi mil rahi.", "locked": "SIM PIN / PUK maang rahi hai.",
                           "network_locked": "Phone doosre network ke liye locked hai.", "not_ready": "SIM taiyaar nahi."}[g("sim_state")],
            ["no_network", "otp_not_coming", "mobile_data"])
    if isinstance(g("signal_level"), int) and g("signal_level") <= 1 and not g("airplane"):
        add("signal", "warn", "Signal bahut kamzor (0-1 dande).", ["no_network", "mobile_data", "otp_not_coming", "battery_drain"])
    if g("data_saver"):
        add("data_saver", "info", "Data saver chalu hai.", ["mobile_data", "notifications_late"])
    if g("auto_time") is False:
        add("auto_time", "warn", "Date-time apne aap set nahi hai: bank / UPI / Wi-Fi mein dikkat.", ["app_crash", "wifi", "otp_not_coming"])
    if g("dnd"):
        add("dnd", "warn", "Do Not Disturb chalu hai: call / notification ki awaaz nahi.", ["calls_not_ringing", "notifications_late"])
    if g("ringer") in ("silent", "vibrate") or g("ring_volume_pct") == 0:
        add("ringer", "warn", f"Phone {g('ringer') if g('ringer') != 'normal' else 'ring volume 0'} par hai.", ["calls_not_ringing"])
    if g("media_volume_pct") == 0:
        add("media_volume", "info", "Media volume 0 hai.", ["sound_mic"])
    if g("bluetooth_on"):
        add("bluetooth", "info", "Bluetooth chalu hai (awaaz earbuds / speaker par ja sakti hai).", ["sound_mic", "calls_not_ringing"])
    patch = str(g("security_patch") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", patch):
        from datetime import date
        try:
            age = (date.today() - date.fromisoformat(patch)).days
            if age > 365:
                add("patch", "warn", f"Security update {age // 30} mahine purana ({patch}).", ["hacked_fraud", "slow", "app_crash"])
        except ValueError:
            pass
    if g("usb_debugging"):
        add("usb_debugging", "warn", "USB debugging chalu hai: zaroorat na ho to band kijiye.", ["hacked_fraud"])
    if g("vpn"):
        add("vpn", "info", "VPN chalu hai.", ["mobile_data", "wifi", "hacked_fraud"])
    cur = g("current_ma")
    if g("plugged") not in (None, "none") and g("charging_status") == "charging" and isinstance(cur, int) and 0 < cur < 400:
        add("slow_charge", "warn", f"Charge sirf ~{cur} mA aa raha hai: cable / charger / port kamzor.", ["not_charging"])
    if g("plugged") not in (None, "none") and g("charging_status") in ("not_charging", "discharging"):
        add("not_charging_now", "bad", "Charger laga hai par phone charge nahi le raha.", ["not_charging"])
    top = g("top_apps") or []
    if top:
        a = top[0]
        add("top_app", "info", f"Pichhle 24 ghante sabse zyada: {a.get('label')} ({a.get('minutes')} min).",
            ["battery_drain", "heating", "slow"])
    return f
