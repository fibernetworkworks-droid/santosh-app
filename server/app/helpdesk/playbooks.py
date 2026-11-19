"""The common IT problems of a small Indian office, how to recognise them in her / her staff's words, and the fixes in
the order a careful technician tries them: quick and harmless first, anything that CHANGES a system setting, installs,
uninstalls or resets only after her Haan (`change`), anything that can lose data last (`careful`).

Step fields:
  id, title, how (exactly what the person does), check (what to look at to know if it worked)
  change   = "" | setting | install | uninstall | reset | account | network | firmware   -> a card waits for HER tap
  careful  = True when data / settings may be lost (always last; backup first)
  admin    = True when it needs the PC's admin rights (the office's IT person / her)
Playbook fields:
  label, words (her words: English / Hinglish / Hindi), escalate (vendor kind), escalate_when (when it is a technician's
  job), tell (what the technician will ask: collect it while helping), security (a security incident), asset (asset kind)
"""
from __future__ import annotations

import re

S = dict

PLAYBOOKS: dict[str, dict] = {
    "printer": {
        "label": "Printer is not working", "asset": "printer", "escalate": "printer",
        "words": ("printer", "print nahi", "print nhi", "printout", "paper jam", "page atak", "toner", "cartridge", "ink",
                  "spooler", "print queue", "प्रिंटर", "प्रिंट"),
        "escalate_when": ["Paper jams again and again, or a broken part / strange noise inside", "An error code on the display (E-xx) that a restart does not clear",
                          "Lines / smudges on prints even after a new toner", "The printer does not turn on at all (no power light)"],
        "tell": ["Printer brand + model (on the sticker)", "The error on the display / blinking lights", "Connected by USB or by Wi-Fi / LAN",
                 "Failing from one PC or from all"],
        "steps": [
            S(id="power_paper", title="Check power, paper, toner", check="Is the printer light green? Paper in the tray? Any error on the display?",
              how="Check the printer is on, there is paper in the tray, the cover is closed, and the display does not show 'paper jam / toner low'. If there is a jam, turn the printer off and pull the paper out slowly and straight (do not tear it)."),
            S(id="cable", title="Cable / Wi-Fi", check="Does the printer show as 'Ready' / 'Online' in the PC's list?",
              how="Push the USB cable in firmly at both ends (try another USB port). For a Wi-Fi / LAN printer, use the same Wi-Fi the PC is on; check the printer's Wi-Fi light."),
            S(id="restart_both", title="Restart printer + PC", check="Did a test page print after the restart?",
              how="Turn the printer off, wait 30 seconds, turn it on. Restart the PC too. Then type one line in Notepad and print it."),
            S(id="queue", title="Stuck print queue", check="Did it print after the queue was emptied?",
              how="Start > Settings > Bluetooth & devices > Printers > your printer > 'Open print queue' > right-click every document > Cancel."),
            S(id="default_printer", title="Is the right printer selected?", change="setting", check="Is the right printer name in the print dialog?",
              how="Settings > Printers > your printer > 'Set as default' (and turn off 'Let Windows manage my default printer'). When printing, pick the right name from the list."),
            S(id="spooler", title="Restart the Print Spooler service", change="setting", admin=True, check="Queue empty + it printed?",
              how="Type 'services' in Start > Services > right-click 'Print Spooler' > Restart. (From an admin account.)"),
            S(id="driver", title="Reinstall the printer driver", change="install", admin=True, check="A test page after the new driver?",
              how="Get the driver for your model only from the printer maker's own website (HP / Canon / Epson / Brother support page). Never from any other site or a 'driver updater' app."),
        ]},
    "network": {
        "label": "Internet / Wi-Fi / LAN is not working", "asset": "router", "escalate": "isp",
        "words": ("internet", "wifi", "wi-fi", "wi fi", "net nahi", "net nhi", "net slow", "net band", "net gaya", "net down", "net chala", "network", "lan", "router", "broadband", "no internet",
                  "connected no internet", "ethernet", "fiber", "fibre", "ont", "speed kam", "इंटरनेट", "नेट"),
        "escalate_when": ["LOS or a red light on the router / ONT (no fibre signal)", "No internet on any device, even after a router restart",
                          "All LAN points in one area are dead (a switch / cable job)", "Speed far below the plan, for several days"],
        "tell": ["ISP name + customer ID / landline number (on the bill)", "Router / ONT lights (PON, LOS, Internet)",
                 "On all devices or on one", "Since when"],
        "steps": [
            S(id="scope", title="On all devices or one?", check="Does the internet work on a phone on this same Wi-Fi?",
              how="Check on another PC / phone on this same Wi-Fi. Down on all = router / ISP; down on only one = that device."),
            S(id="lights", title="Router / ONT lights", check="Is the LOS light off? Is the Internet / PON light green?",
              how="A red 'LOS' on the fibre ONT = no fibre signal: this is the ISP's job (escalate it straight away). Check no cable is loose and the thin fibre cable is not bent."),
            S(id="router_restart", title="Restart the router", check="Did the internet come back after 2-3 minutes?",
              how="Unplug the router (and ONT) from power and plug it back after 30 seconds. Wait 2-3 minutes and check. Do not press the Reset button (the small hole)."),
            S(id="cable_port", title="LAN cable / port", check="Did 'Network' appear on the PC as soon as the cable went in?",
              how="On LAN: push the cable in firmly at both ends, try another port on the router, try a different cable."),
            S(id="forget_wifi", title="Forget the Wi-Fi and join again", change="network", check="Internet after joining again?",
              how="On the PC: Wi-Fi > right-click your network > Forget > select it again and enter the Wi-Fi password (from the router's sticker / where the office keeps it). Do not tell Hoola the password."),
            S(id="troubleshooter", title="Windows network troubleshooter", check="Did the troubleshooter fix anything?",
              how="Settings > System > Troubleshoot > Other troubleshooters > Network and Internet > Run. Read what it says and tell Hoola."),
            S(id="network_reset", title="Network reset (PC)", change="reset", admin=True, careful=True, check="Internet after the restart?",
              how="Settings > Network & internet > Advanced network settings > Network reset. Every Wi-Fi password and VPN will have to be entered again."),
        ]},
    "slow_pc": {
        "label": "Computer slow / hanging", "asset": "pc", "escalate": "it",
        "words": ("slow", "hang", "atak", "dheema", "dheere", "freeze", "not responding", "lag", "100% disk", "ram full", "computer slow",
                  "pc slow", "laptop slow", "धीमा", "हैंग"),
        "escalate_when": ["Disk always at 100% + PC older than 5 years (HDD) = time to fit an SSD", "Blue screen (BSOD) again and again",
                          "Runs very hot / loud fan noise", "Hangs right after a restart too"],
        "tell": ["PC / laptop model, how old", "RAM and HDD / SSD (Settings > System > About)", "Windows version", "When it happens: at startup / in Tally / in the browser"],
        "steps": [
            S(id="restart", title="Full restart", check="Fine after the restart?",
              how="Start > Power > Restart (not Shut down, Restart). If it has not been turned off for days, this is the biggest fix."),
            S(id="task_manager", title="Which program is heavy?", check="What is at the top of CPU / Memory / Disk?",
              how="Ctrl + Shift + Esc > Task Manager > Processes. Click CPU / Memory / Disk and look at the top entry. If it is your own program, close it; if you do not recognise the name, tell Hoola the name."),
            S(id="disk_space", title="Space on the C drive", check="More than 15% free on the C drive?",
              how="File Explorer > This PC > see how full the C drive is. Move big videos / old files from Downloads and Desktop to another drive or a pen drive."),
            S(id="tabs", title="Browser tabs", check="Faster after closing tabs?",
              how="If 20-30 tabs are open in Chrome / Edge, close them; bookmark the ones you need."),
            S(id="startup_apps", title="Apps that start with the PC", change="setting", check="Did it start faster on the next restart?",
              how="Task Manager > Startup apps > 'Disable' the ones you do not need (updaters, chat apps). Leave antivirus / Tally / printer alone."),
            S(id="windows_update", title="Windows update", change="install", check="After the update?",
              how="Settings > Windows Update > Check for updates > install, restart. Not in the middle of work: do it in the evening."),
            S(id="disk_cleanup", title="Disk Cleanup", change="setting", check="How much space was freed?",
              how="Type 'Disk Cleanup' in Start > C drive > 'Clean up system files' > tick Temporary files, Recycle Bin > OK. Do not tick 'Downloads'."),
        ]},
    "email": {
        "label": "Email (Outlook / Gmail) is not working", "asset": "pc", "escalate": "it",
        "words": ("email", "e-mail", "mail nahi", "outlook", "gmail", "inbox", "mail send", "mail aa nahi", "mailbox full", "smtp", "pst",
                  "ईमेल", "मेल"),
        "escalate_when": ["Company-domain mail (name@company.com) is down for everyone: a job for the mail hosting provider",
                          "Outlook data file (PST) damaged / very large", "Mail is going out to others by itself (account may be hacked: open Phishing / account too)"],
        "tell": ["The email address's domain (gmail.com / company.com)", "Full text of the error / a screenshot", "Working on the phone, or down there too",
                 "Outlook version"],
        "steps": [
            S(id="webmail", title="Open it in the browser", check="Does the mail open in the browser (gmail.com / outlook.com / webmail)?",
              how="Open the same account in the browser. Works there = the problem is only Outlook / the app; not there either = the account / mail server."),
            S(id="internet_outbox", title="Internet and Outbox", check="Is the Outbox empty now?",
              how="Is the internet working? If a mail is stuck in Outlook's Outbox, remove the big attachment and send again (send a file over 25 MB as a Drive / OneDrive link)."),
            S(id="storage_full", title="Mailbox full?", check="Storage is not at 100%?",
              how="Gmail: 'storage used' at the bottom. If it is full, delete old mails with big attachments (search: larger:10M) and empty the Trash."),
            S(id="restart_outlook", title="Close and reopen Outlook", check="After reopening?",
              how="Close Outlook completely (it must not show in Task Manager either), then open it. Restart the PC if you can."),
            S(id="password_prompt", title="Keeps asking for the password", check="Did it stop after signing in?",
              how="Never tell Hoola the password. Open the account in the browser and check: if the password was changed, enter the new password in Outlook yourself. For Gmail with 2-step, connect Outlook with 'Sign in with Google'."),
            S(id="safe_mode", title="Outlook safe mode", check="Does it work in safe mode?",
              how="Windows + R > 'outlook.exe /safe' > OK. If it works in safe mode, an add-in is the cause."),
            S(id="repair_profile", title="Outlook profile / Office repair", change="reset", admin=True, careful=True, check="After the new profile?",
              how="Control Panel > Mail > Show Profiles > Add (a new profile), or Control Panel > Programs > Microsoft Office > Change > Quick Repair. Back up the PST file first."),
        ]},
    "account": {
        "label": "Forgot password / account locked", "asset": "pc", "escalate": "it", "account": True,
        "words": ("password bhool", "password bhul", "forgot password", "locked", "lock ho", "account lock", "login nahi", "sign in nahi",
                  "account disabled", "too many attempts", "2fa", "two step", "authenticator", "पासवर्ड", "लॉक"),
        "escalate_when": ["Nobody remembers the password of the office admin account", "The account may be hacked (password changed by itself, strange mails sent)",
                          "No recovery phone / email either"],
        "tell": ["Which account (Windows / Gmail / Microsoft / Tally / portal) - the name, NOT the password", "What error appears", "Who has the recovery phone / email"],
        "steps": [
            S(id="basics", title="Caps Lock, language, right account", check="Caps Lock off, keyboard in English, right user selected?",
              how="Check the Caps Lock light is off, the keyboard language is ENG (on the taskbar), and the right user / email is selected. Press the eye icon that shows the password to see what is being typed."),
            S(id="wait_lock", title="Wait for the lock to clear", check="After 15-30 minutes?",
              how="After several wrong passwords an account locks for a while. Wait 15-30 minutes without trying."),
            S(id="self_reset", title="Do 'Forgot password' yourself", check="Is the new password set?",
              how="Use 'Forgot password' on that company's real page (Gmail: accounts.google.com, Microsoft: account.live.com/password/reset). The OTP comes only to your own phone; tell it to no one. Hoola never asks for a password / OTP."),
            S(id="admin_unlock", title="Unlock / new password by the admin", change="account", admin=True, check="Did the admin unlock it?",
              how="The office admin (you / the IT person) resets that user's password or unlocks the account from the admin account (Windows: Computer Management > Local Users; Google Workspace / Microsoft 365 admin page). The user sets their own new password at the next login."),
            S(id="two_step", title="Turn on 2-step verification", change="account", check="Is 2-step on?",
              how="When the account is back, turn on 2-step verification at once and correct the recovery phone / email. Print the backup codes and keep them locked away."),
        ]},
    "tally": {
        "label": "Tally problem", "asset": "pc", "escalate": "tally_partner",
        "words": ("tally", "tallyprime", "tally prime", "tally erp", "license", "licence", "company data", "data path", "tally band",
                  "tally error", "memory access violation", "टैली"),
        "escalate_when": ["Licence 'not activated / expired' and a renewal / TSS question", "Company data corrupt / does not open even after 'repair'",
                          "In multi-user, the data does not show from another PC (a server PC / sharing job)", "Upgrade / migration (ERP 9 to Prime)"],
        "tell": ["TallyPrime release (Help > About)", "Licence serial (shown on the screen) - NOT the activation key / password",
                 "Full text of the error", "Which PC / folder holds the data, how many people use it at once"],
        "steps": [
            S(id="error_text", title="Full text of the error", check="Error text written down / photographed?",
              how="Take a photo of the error message or write it down (the same text is searched on Tally's help site). Do not press Ctrl+Alt+R (repair) yet."),
            S(id="restart_tally", title="Close and reopen Tally", check="Working after reopening?",
              how="Close Tally completely (tally.exe must not show in Task Manager), then open it. If it is open twice on the same PC, close one."),
            S(id="data_path", title="Data path / server PC", check="Does the company show in the company list?",
              how="If the data comes from a multi-user setup / server, that server PC must be on and on the network. In Tally, use Select Company > 'Change path' to pick the right folder (check the folder was not renamed / the pen drive was not removed)."),
            S(id="licence", title="Check the licence", check="Is the licence 'Active' in Gateway / Help > About?",
              how="Help > About / F1: licence status. If 'Not activated', turn the internet on and close and reopen Tally. Buying a renewal / TSS is your decision: through your Tally partner."),
            S(id="backup_first", title="Backup first", check="Was the backup file created?",
              how="Use Data > Backup to back up the company to a pen drive / another drive. Required before a repair."),
            S(id="repair", title="Company repair", change="reset", careful=True, check="Did the company open after the repair?",
              how="Only after the backup: Select Company > Ctrl+Alt+R on the company (Repair). Large data takes time; do not close it midway."),
            S(id="update_tally", title="New release", change="install", admin=True, check="After the update?",
              how="Only from tallysolutions.com / 'Update' inside Tally. Only while TSS is valid. Back up first."),
        ]},
    "office_apps": {
        "label": "Word / Excel / MS Office problem", "asset": "pc", "escalate": "it",
        "words": ("word", "excel", "powerpoint", "ms office", "microsoft office", "office activate", "unlicensed product", "file nahi khul",
                  "file corrupt", "excel hang", "docx", "xlsx", "product activation", "वर्ड", "एक्सेल"),
        "escalate_when": ["'Unlicensed product' and the office has no licence (buying a licence is your decision)", "An important file is corrupt, even 'Open and Repair' fails"],
        "tell": ["Office version (File > Account)", "Error text", "In one file or in all"],
        "steps": [
            S(id="save_copy", title="Save a copy of the file", check="Copy made?",
              how="First make a copy of the file that seems damaged in another folder. For a file that came by pen drive / WhatsApp, click 'Enable Editing' only if you trust the sender (never macros / 'Enable Content')."),
            S(id="restart_app", title="Close and reopen the program", check="Did it reopen?",
              how="Close Word / Excel completely (in Task Manager too), then open it. If it hangs, wait 15 seconds: AutoRecover saves the file."),
            S(id="open_repair", title="Open and Repair", check="Did the file open?",
              how="Word / Excel > File > Open > Browse > select the file > the arrow next to Open > 'Open and Repair'. In Excel, also check File > Info > Manage Workbook for an older AutoSave version."),
            S(id="safe_mode", title="Safe mode", check="Does it work in safe mode?",
              how="Windows + R > 'excel /safe' or 'winword /safe'. If it works in safe mode, an add-in is the cause: turn it off in File > Options > Add-ins."),
            S(id="sign_in", title="Account / licence", check="Does File > Account show 'Product activated'?",
              how="File > Account: sign in with the office's Microsoft account. If 'Unlicensed', check which account holds your licence. Never use a crack / 'activator' (it brings a virus)."),
            S(id="quick_repair", title="Office Quick Repair", change="install", admin=True, check="After the repair?",
              how="Control Panel > Programs and Features > Microsoft Office > Change > Quick Repair (if that fails, Online Repair). Files are not deleted."),
        ]},
    "whatsapp_web": {
        "label": "WhatsApp Web / Desktop problem", "asset": "pc", "escalate": "it",
        "words": ("whatsapp web", "whatsapp desktop", "whatsapp pc", "qr code", "link device", "linked device", "whatsapp computer",
                  "whatsapp nahi khul", "व्हाट्सएप वेब"),
        "escalate_when": ["Account 'banned' or 'logged out' for no reason (a job for WhatsApp support)", "Someone else's device shows as linked (may be hacked: 'Log out' at once)"],
        "tell": ["Web or Desktop app", "Is WhatsApp working on the phone?", "Error text"],
        "steps": [
            S(id="phone_net", title="Phone internet / WhatsApp update", check="WhatsApp fine on the phone?",
              how="Does WhatsApp open on the phone, is the internet working? Update WhatsApp from the Play Store."),
            S(id="relink", title="Link again", check="Did the chats appear after the QR scan?",
              how="On the phone: WhatsApp > three dots > Linked devices > 'Log out' the old PC > 'Link a device' > scan the QR on the PC screen. Do not send a photo of the QR to anyone."),
            S(id="check_devices", title="Check linked devices", check="Only your own devices showing?",
              how="If an unknown PC / browser shows in Linked devices, Log out at once and turn on Settings > Account > Two-step verification (set the 6-digit PIN yourself, share it with no one)."),
            S(id="browser", title="Try another browser / app", check="In another browser / the Desktop app?",
              how="A new version of Chrome / Edge, or WhatsApp Desktop from the Microsoft Store. On an office PC, use WhatsApp's 'Keep me signed in' only on your own PC."),
            S(id="clear_site", title="Clear browser data (WhatsApp only)", change="setting", check="After a new QR?",
              how="In Chrome on web.whatsapp.com: the lock icon > Site settings > Clear data. Then link again."),
        ]},
    "ups_power": {
        "label": "UPS / power problem", "asset": "ups", "escalate": "electrician",
        "words": ("ups", "inverter", "beep", "bijli", "power cut", "light gayi", "battery backup", "power nahi", "pc band ho gaya", "spike",
                  "socket", "यूपीएस", "बिजली"),
        "escalate_when": ["UPS battery 2-3 years old and backup under 5 minutes", "Burning smell, hot plug, sparks: turn off the main switch at once, call an electrician",
                          "Earthing may be faulty (a shock on touching the PC)", "The UPS does not turn on at all"],
        "tell": ["UPS brand / model / VA", "How old the battery is", "How many devices are on it", "What the beep is like (continuous / on and off)"],
        "steps": [
            S(id="safety", title="Safety first", check="No smell / heat / sparks?",
              how="If there is a burning smell, a hot plug or sparks, touch nothing: turn off the main switch and call an electrician (stop here)."),
            S(id="beep", title="What the beep means", check="What is the beep like?",
              how="An on-and-off beep = the power is out and it is running on battery: save your work and turn the PC off. A continuous beep = overload or a bad battery."),
            S(id="load", title="Reduce the load", check="Did the beep stop after removing the printer / heater?",
              how="Do not plug heavy things like a laser printer, heater, kettle or AC into the UPS: only the PC, monitor and router."),
            S(id="plugs", title="Plug / extension", check="In another socket?",
              how="Plug the UPS straight into a good wall socket (not an extension board). Push the PC's power cable in firmly."),
            S(id="battery_age", title="Battery age", check="When was the battery fitted?",
              how="A UPS battery usually lasts 2-3 years. If the backup is short, replacing the battery is the vendor's job (note the date in the asset)."),
        ]},
    "cctv": {
        "label": "CCTV / NVR / DVR problem", "asset": "cctv", "escalate": "cctv",
        "words": ("cctv", "camera", "nvr", "dvr", "recording", "no video", "video loss", "hikvision", "cp plus", "dahua", "camera band",
                  "सीसीटीवी", "कैमरा"),
        "escalate_when": ["'Video loss' on a camera even after the cable / power is fine", "Hard disk 'error / not found' (nothing is being recorded)",
                          "A new camera / moving a camera", "Nobody remembers the NVR admin password (the vendor resets it only after seeing the bill)"],
        "tell": ["NVR / DVR brand + model", "Which camera (number / location)", "Message on the screen (video loss / HDD error)", "Since when"],
        "steps": [
            S(id="which", title="One camera or all?", check="Which cameras are down?",
              how="Look at the monitor to see which camera is black / 'video loss'. All down = NVR / power; one down = that camera's cable / power."),
            S(id="power", title="Power / adapter / PoE", check="Does the camera's red IR light come on at night?",
              how="Is that camera's adapter / PoE switch on? Is the cable cut / loose anywhere (check after rain)."),
            S(id="restart_nvr", title="Restart the NVR", check="Did the cameras come back after the restart?",
              how="NVR menu > Shutdown / Reboot (better than pulling the power). Then wait 2-3 minutes."),
            S(id="hdd", title="Is it recording?", check="Does Playback show yesterday's recording?",
              how="Check yesterday's / today's recording in Playback. HDD status should be 'Normal' (Menu > Storage). 'Error / Uninitialized' = vendor; do not press 'Initialize / Format' yourself (old recordings will be erased)."),
            S(id="time", title="NVR date / time", change="setting", check="Date / time correct?",
              how="A wrong time causes trouble with evidence: Menu > System > Time: set the correct date / time (or NTP)."),
        ]},
    "display": {
        "label": "Monitor / projector / screen problem", "asset": "projector", "escalate": "it",
        "words": ("projector", "monitor", "display", "screen black", "no signal", "hdmi", "vga", "screen nahi", "tv screen", "second screen",
                  "duplicate", "extend", "प्रोजेक्टर", "मॉनिटर"),
        "escalate_when": ["The projector's lamp light is red / a 'lamp replace' message", "Lines on the monitor / a broken panel", "'No signal' even after changing the cable / port"],
        "tell": ["Monitor / projector model", "HDMI / VGA / USB-C", "Laptop or PC", "Message on the screen"],
        "steps": [
            S(id="power_input", title="Power and input", check="'No signal' on the screen, or black?",
              how="The monitor / projector is on, and the right INPUT (HDMI 1 / HDMI 2 / VGA) is selected with the remote / button."),
            S(id="cable", title="Reconnect the cable", check="A picture after the cable?",
              how="Pull the HDMI / VGA out at both ends and push it in firmly; try another cable / another port."),
            S(id="win_p", title="Windows + P", check="Did it show after choosing Duplicate?",
              how="On the laptop press Windows + P > 'Duplicate' (the same on both) or 'Extend'. This only changes how the screen is shown."),
            S(id="restart", title="Cable first, then power on", check="When powered on in this order?",
              how="Laptop off, connect the cable, projector on, then laptop on."),
            S(id="resolution", title="Resolution", change="setting", check="Clear after changing the resolution?",
              how="Settings > System > Display > Display resolution: 'Recommended'. On a projector 1920x1080 or 1280x720."),
        ]},
    "scanner": {
        "label": "Scanner is not working", "asset": "scanner", "escalate": "printer",
        "words": ("scanner", "scan nahi", "scan", "scanning", "adf", "स्कैनर", "स्कैन"),
        "escalate_when": ["Paper keeps jamming / feeding wrong in the ADF (feeder)", "Lines on scans even after cleaning the glass"],
        "tell": ["Scanner / printer model", "USB or network", "Which software you scan from"],
        "steps": [
            S(id="power_cable", title="Power / cable / cover", check="Scanner on and visible on the PC?",
              how="Scanner on, USB pushed in firmly, cover / feeder properly closed."),
            S(id="windows_scan", title="From Windows Scan / Fax and Scan", check="Did it scan from there?",
              how="Start > 'Windows Fax and Scan' > New Scan. If it works from there, the scanner is fine and your old software is stuck."),
            S(id="restart", title="Restart scanner + PC", check="After the restart?",
              how="Turn the scanner off and on, restart the PC."),
            S(id="glass", title="Clean the glass", check="Lines gone?",
              how="With the power off, wipe the glass with a dry soft cloth (a little glass cleaner on the cloth, not on the glass)."),
            S(id="driver", title="Reinstall the driver", change="install", admin=True, check="After the new driver?",
              how="Get the scanner driver / app for your model only from the maker's own website."),
        ]},
    "vpn": {
        "label": "VPN / remote access is not working", "asset": "pc", "escalate": "it",
        "words": ("vpn", "remote desktop", "rdp", "anydesk", "teamviewer", "remote access", "forticlient", "remote se", "वीपीएन"),
        "escalate_when": ["The office VPN server / router is down (not working for anyone)", "Certificate / account expired"],
        "tell": ["Which VPN / remote app", "Error text", "From home internet or from the office", "For everyone or only one person"],
        "steps": [
            S(id="internet", title="Internet first", check="Do websites open without the VPN?",
              how="Does the internet work without the VPN? If not, fix the internet first (the Internet problem)."),
            S(id="reconnect", title="Disconnect > connect", check="After connecting again?",
              how="In the VPN app: Disconnect, wait 10 seconds, then Connect. Close and reopen the app."),
            S(id="who_asked", title="Who asked for remote access?", check="Did you start it yourself?",
              how="Never give an AnyDesk / TeamViewer code to a stranger, especially on a 'bank / KYC / refund' call: this is the most common fraud."),
            S(id="time_sync", title="Is the PC's time correct?", change="setting", check="After fixing the time?",
              how="Settings > Time & language > turn on 'Set time automatically' > Sync now. A VPN certificate fails when the time is wrong."),
            S(id="reinstall", title="Reinstall the VPN app", change="install", admin=True, check="After the new install?",
              how="Only from the place the office / VPN company names. Get the settings / profile from the IT person."),
        ]},
    "security": {
        "label": "Virus / strange popup / suspected phishing", "asset": "pc", "escalate": "it", "security": True,
        "words": ("virus", "malware", "ransomware", "hack", "hacked", "popup", "pop-up", "files encrypted", "files locked", "phishing", "fake mail",
                  "fraud mail", "suspicious", "antivirus", "defender", "ajeeb link", "link par click", "वायरस", "हैक"),
        "escalate_when": ["File names changed / files will not open / a 'ransom' note (ransomware): at once", "Someone entered a password / money is gone",
                          "The antivirus cannot remove the 'threat'"],
        "tell": ["What appeared (screenshot)", "On which PC, when", "What was clicked / downloaded / filled in", "Are there other PCs on the network?"],
        "steps": [
            S(id="disconnect", title="Take it off the network at once", check="Wi-Fi off / LAN cable out?",
              how="If you suspect something, turn off that PC's Wi-Fi / pull out the LAN cable (do not shut the PC down, the evidence stays on it). Do not plug in a pen drive."),
            S(id="dont_pay", title="Fill in nothing, give nothing", check="Nobody gave a password / OTP / money?",
              how="Do not call the number on the popup, do not pay a 'ransom', do not give the code of a remote app (AnyDesk). If money is gone, call 1930 at once."),
            S(id="scan", title="Antivirus full scan", check="What did the scan report?",
              how="Windows Security > Virus & threat protection > Scan options > Full scan (or the office antivirus). Tell Hoola the name of what it found."),
            S(id="passwords", title="Change passwords from another device", change="account", check="Passwords of the important accounts changed?",
              how="If a password was entered on the link: from a CLEAN phone / another PC, change that account's password yourself (email, bank, GST, Tally) and turn on 2-step. Do not give the password to Hoola."),
            S(id="offline_scan", title="Microsoft Defender Offline scan", change="setting", admin=True, check="Clean after the offline scan?",
              how="Windows Security > Scan options > 'Microsoft Defender Antivirus (offline scan)' > Scan now. The PC restarts and scans for 15 minutes: save your work first."),
        ]},
    "backup": {
        "label": "Backup / saving data", "asset": "pc", "escalate": "it",
        "words": ("backup", "back up", "data loss", "file delete", "file mit", "pen drive", "hard disk", "external drive", "recover",
                  "data chala gaya", "restore", "बैकअप"),
        "escalate_when": ["The hard disk asks to be 'formatted' / makes a click-click noise (a data recovery lab's job: write nothing more to it)",
                          "Important data is gone and there is no backup"],
        "tell": ["What data (Tally / documents / photos)", "Where it was (PC / drive / folder)", "When the last backup was"],
        "steps": [
            S(id="stop_writing", title="Write nothing to that drive", check="Nothing new saved to the drive?",
              how="If a file was deleted, do not save / install anything new on that drive: it lowers the chance of getting it back."),
            S(id="recycle", title="Recycle Bin / previous version", check="Found there?",
              how="Check the Recycle Bin. Right-click the folder > 'Restore previous versions'. Also the 'Trash / Recycle bin' in OneDrive / Google Drive."),
            S(id="what_to_backup", title="What must be backed up", check="List made?",
              how="Tally data folder, Documents / Desktop, Outlook PST, GST / bank files, the accounts Excel files. Keep the list in Hoola's asset note."),
            S(id="three_two_one", title="3-2-1 backup", check="A second copy in a different place?",
              how="At least two copies: one on an external drive / NAS, one outside the office (cloud or home). Unplug the external drive after the backup and store it (ransomware wipes that too)."),
            S(id="schedule", title="Turn on automatic backup", change="setting", check="Backup schedule set?",
              how="Windows: Settings > Accounts > Windows backup, or File History (Control Panel). Tally: Data > Backup every evening. Once a week, restore and check that the file opens."),
        ]},
    "pc_power": {
        "label": "Computer does not turn on / blue screen", "asset": "pc", "escalate": "it",
        "words": ("chalu nahi", "start nahi", "on nahi", "boot", "blue screen", "bsod", "black screen", "beep sound", "restart loop",
                  "no display", "बंद हो गया", "चालू नहीं"),
        "escalate_when": ["Completely dead (no light / fan) even on a good socket", "Beeps and shows nothing",
                          "Blue screen again and again (write down the stop code)", "'No bootable device' / disk not found"],
        "tell": ["PC / laptop model", "Lights / fan / beep", "What the screen says (stop code)", "Was anything new fitted / was it dropped"],
        "steps": [
            S(id="power", title="Power / socket / button", check="Fan / light on?",
              how="Another socket, is the UPS on? Laptop: plug in the charger for 10 minutes. Check the monitor's own power and cable too."),
            S(id="hard_reset", title="Remove all power", check="Did it turn on after this?",
              how="Pull out the power cable, hold the power button for 15 seconds, then plug the cable in and turn it on. Laptop: remove the charger and hold power for 30 seconds."),
            S(id="usb_out", title="Remove pen drives / new devices", check="Did it turn on after removing them?",
              how="Remove the pen drive, external disk and printer USB, then turn it on."),
            S(id="stop_code", title="Write down the stop code", check="Blue screen code written down?",
              how="Take a photo of the 'Stop code' on the blue screen (like CRITICAL_PROCESS_DIED) and the QR: the technician searches by it."),
            S(id="startup_repair", title="Startup Repair", change="reset", admin=True, careful=True, check="After the repair?",
              how="Turning it off three times just as it starts brings up 'Automatic Repair' > Advanced options > Startup Repair. 'Reset this PC' only with your approval and after a backup."),
        ]},
}

GENERIC = {"label": "Another IT problem", "asset": "", "escalate": "it", "words": (),
           "escalate_when": ["The do-it-yourself fixes do not work", "Broken hardware / a burning smell"],
           "tell": ["Device name / model", "Full text of the error / a photo", "Since when, for how many people"],
           "steps": [
               S(id="error_text", title="Error text / photo", check="Photo / text received?", how="Take a photo of what the screen says, or write down the full text."),
               S(id="restart", title="Restart", check="After the restart?", how="Close the program / turn off the device and start it again."),
               S(id="scope", title="On all or on one?", check="On another PC / user too?", how="Try the same thing on another PC / with another user."),
               S(id="recent_change", title="What changed recently?", check="Anything newly installed / updated / dropped?",
                 how="Any new program, update, cable or power cut recently? That is the most useful thing to tell."),
           ]}

CHANGE_LABEL = {"setting": "Changing a system setting", "install": "Install / update", "uninstall": "Removing a program", "reset": "Reset / repair",
                "account": "Account / password change", "network": "Network setting", "firmware": "Firmware update", "other": "Change"}
VENDOR_KINDS = ("amc", "it", "isp", "printer", "cctv", "tally_partner", "electrician", "software", "other")
VENDOR_LABEL = {"amc": "AMC provider", "it": "Computer technician", "isp": "Internet (ISP)", "printer": "Printer service",
                "cctv": "CCTV provider", "tally_partner": "Tally partner", "electrician": "Electrician", "software": "Software vendor", "other": "Vendor"}
ASSET_KINDS = ("pc", "laptop", "printer", "scanner", "router", "switch", "ups", "cctv", "projector", "monitor", "server", "phone", "software", "other")


def playbook(cat: str) -> dict:
    return PLAYBOOKS.get(cat) or GENERIC


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower())


def detect(text: str) -> list[str]:
    """Playbooks whose words are in her text, best first (longest matching word wins ties)."""
    t = " " + _norm(text) + " "
    scored = []
    for cid, p in PLAYBOOKS.items():
        hits = [w for w in p["words"] if (f" {w}" in t if len(w) <= 4 and w.isascii() else w in t)]
        if hits:
            scored.append((len(hits), max(len(h) for h in hits), cid))
    # specific beats generic: "outlook slow" is email, "tally slow" is tally
    order = sorted(scored, key=lambda x: (-x[0], -x[1]))
    out = [c for _, _, c in order]
    for first, over in (("tally", "slow_pc"), ("email", "slow_pc"), ("printer", "network"), ("whatsapp_web", "network"),
                        ("vpn", "network"), ("cctv", "network"), ("security", "email"), ("account", "email")):
        if first in out and over in out and out.index(over) < out.index(first):
            out.remove(first)
            out.insert(out.index(over), first)
    return out
