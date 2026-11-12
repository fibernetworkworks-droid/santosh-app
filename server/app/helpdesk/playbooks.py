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
        "label": "Printer not working", "asset": "printer", "escalate": "printer",
        "words": ("printer", "print nahi", "print nhi", "printout", "paper jam", "page atak", "toner", "cartridge", "ink",
                  "spooler", "print queue", "प्रिंटर", "प्रिंट"),
        "escalate_when": ["Paper jam baar baar, ya andar koi toota hissa / ajeeb awaaz", "Display par error code (E-xx) jo restart se na jaye",
                          "Streaks or smudges on the print even after fitting new toner", "Printer does not switch on at all (no power light)"],
        "tell": ["Printer brand + model (sticker par)", "Display ka error / blinking lights", "Connected by USB or by Wi-Fi / LAN",
                 "Not working on one PC, or on all"],
        "steps": [
            S(id="power_paper", title="Check power, paper and toner", check="Is the printer light green? Is there paper in the tray? Any error on the display?",
              how="The printer is on, there is paper in the tray, the cover is closed, and the display shows no 'paper jam / toner low'. If there is a jam, switch the printer off and pull the paper out straight and gently (do not tear it)."),
            S(id="cable", title="Cable / Wi-Fi", check="Does the printer show 'Ready' / 'Online' in the PC's list?",
              how="Plug the USB cable in firmly at both ends (try another USB port). For a Wi-Fi / LAN printer, make sure it is on the same Wi-Fi as the PC; check the printer's Wi-Fi light."),
            S(id="restart_both", title="Printer + PC restart", check="Did a test page print after the restart?",
              how="Switch the printer off, wait 30 seconds, then switch it on. Restart the PC too. Then type one line in Notepad and print it."),
            S(id="queue", title="Atki hui print queue", check="Did it print once the queue was empty?",
              how="Start > Settings > Bluetooth & devices > Printers > your printer > 'Open print queue' > right-click every document > Cancel."),
            S(id="default_printer", title="Is the right printer selected?", change="setting", check="Is the right printer name in the print dialog?",
              how="Settings > Printers > your printer > 'Set as default' (and turn off 'Let Windows manage my default printer'). Choose the right name in the list when you print."),
            S(id="spooler", title="Print Spooler service restart", change="setting", admin=True, check="Queue empty and did it print?",
              how="Type 'services' in Start > Services > right-click 'Print Spooler' > Restart. (Use an admin account.)"),
            S(id="driver", title="Reinstall the printer driver", change="install", admin=True, check="Test page after the new driver?",
              how="Only from the printer company's own website (HP / Canon / Epson / Brother support page), the driver for your model. Never from another site or a 'driver updater' app."),
        ]},
    "network": {
        "label": "Internet / Wi-Fi / LAN not working", "asset": "router", "escalate": "isp",
        "words": ("internet", "wifi", "wi-fi", "wi fi", "net nahi", "net nhi", "net slow", "net band", "net gaya", "net down", "net chala", "network", "lan", "router", "broadband", "no internet",
                  "connected no internet", "ethernet", "fiber", "fibre", "ont", "speed kam", "इंटरनेट", "नेट"),
        "escalate_when": ["LOS or red light on the router / ONT (no fibre signal)", "No internet on any device, even after restarting the router",
                          "All LAN points in one place are down (a switch / cable job)", "Speed far below the plan, for several days"],
        "tell": ["ISP ka naam + customer ID / landline number (bill par)", "Router / ONT ki lights (PON, LOS, Internet)",
                 "Sab devices par ya ek par", "Since when"],
        "steps": [
            S(id="scope", title="Sab par ya ek par?", check="Does the internet work on a phone on this same Wi-Fi?",
              how="Check on another PC / phone on the same Wi-Fi. If all are down, it is the router / ISP; if only one, it is that device."),
            S(id="lights", title="Router / ONT ki lights", check="LOS light band? Internet / PON light hari?",
              how="A red 'LOS' on the fibre ONT means no fibre signal: this is the ISP's job (pass it straight on). Check the cable is not loose or the thin fibre cable bent."),
            S(id="router_restart", title="Router restart", check="Did the internet come back after 2-3 minutes?",
              how="Unplug the router (and ONT), plug it back in after 30 seconds, and wait 2-3 minutes. Do not press the reset button (the small hole)."),
            S(id="cable_port", title="LAN cable / port", check="Did 'Network' appear on the PC as soon as the cable was plugged in?",
              how="For LAN: press the cable in firmly at both ends, try another router port, and try a different cable."),
            S(id="forget_wifi", title="Forget the Wi-Fi and join again", change="network", check="Internet after reconnecting?",
              how="On the PC: Wi-Fi > right-click your network > Forget > choose it again and enter the Wi-Fi password (from the router sticker, or wherever the office keeps it). Do not tell Hoola the password."),
            S(id="troubleshooter", title="Windows network troubleshooter", check="Did the troubleshooter fix anything?",
              how="Settings > System > Troubleshoot > Other troubleshooters > Network and Internet > Run. Tell Hoola what it says."),
            S(id="network_reset", title="Network reset (PC)", change="reset", admin=True, careful=True, check="Internet after the restart?",
              how="Settings > Network & internet > Advanced network settings > Network reset. You will have to enter all Wi-Fi passwords and VPNs again."),
        ]},
    "slow_pc": {
        "label": "Computer slow / hang", "asset": "pc", "escalate": "it",
        "words": ("slow", "hang", "atak", "dheema", "dheere", "freeze", "not responding", "lag", "100% disk", "ram full", "computer slow",
                  "pc slow", "laptop slow", "धीमा", "हैंग"),
        "escalate_when": ["Disk always at 100% and the PC is over 5 years old (HDD) = a job for fitting an SSD", "Neeli screen (BSOD) baar baar",
                          "Tez garam / pankhe ki tez awaaz", "Still hangs right away after a restart"],
        "tell": ["PC / laptop model and age", "RAM aur HDD / SSD (Settings > System > About)", "Windows version", "When it happens: at start-up / in Tally / in the browser"],
        "steps": [
            S(id="restart", title="Full restart", check="Better after the restart?",
              how="Start > Power > Restart (not Shut down, Restart). If it has not been restarted for days, this is the biggest cure."),
            S(id="task_manager", title="Which program is heavy?", check="Which is at the top for CPU / Memory / Disk?",
              how="Ctrl + Shift + Esc > Task Manager > Processes. Click CPU / Memory / Disk and look at the top one. If it is your own program, close it; if you do not recognise the name, tell Hoola the name."),
            S(id="disk_space", title="Space on the C drive", check="Is more than 15% of the C drive free?",
              how="File Explorer > This PC > see how full the C drive is. Move big videos / old files from Downloads and Desktop to another drive or a pen drive."),
            S(id="tabs", title="Browser ke tab", check="Faster after closing tabs?",
              how="If 20-30 tabs are open in Chrome / Edge, close them; bookmark the ones you need."),
            S(id="startup_apps", title="Apps that run at start-up", change="setting", check="Did it start faster at the next restart?",
              how="Task Manager > Startup apps > 'Disable' the ones that are not needed (updaters, chat apps). Leave antivirus / Tally / printer alone."),
            S(id="windows_update", title="Windows update", change="install", check="After the update?",
              how="Settings > Windows Update > Check for updates > install, restart. Not in the middle of work: do it in the evening."),
            S(id="disk_cleanup", title="Disk Cleanup", change="setting", check="How much space was freed?",
              how="Type 'Disk Cleanup' in Start > C drive > 'Clean up system files' > tick Temporary files and Recycle Bin > OK. Do not tick 'Downloads'."),
        ]},
    "email": {
        "label": "Email (Outlook / Gmail) not working", "asset": "pc", "escalate": "it",
        "words": ("email", "e-mail", "mail nahi", "outlook", "gmail", "inbox", "mail send", "mail aa nahi", "mailbox full", "smtp", "pst",
                  "ईमेल", "मेल"),
        "escalate_when": ["Company domain mail (name@company.com) down for everyone: a job for the mail hosting provider",
                          "Outlook data file (PST) kharab / bahut badi", "Mails are going out to others on their own (possible hacked account: also open Phishing / account)"],
        "tell": ["Email address ka domain (gmail.com / company.com)", "Full error text / screenshot", "Does it work on the phone, or is it down there too",
                 "Outlook ka version"],
        "steps": [
            S(id="webmail", title="Open it in the browser", check="Does the mail open in a browser (gmail.com / outlook.com / webmail)?",
              how="Open the same account in the browser. If it works there, the problem is only Outlook / the app; if not, it is the account / mail server."),
            S(id="internet_outbox", title="Net aur Outbox", check="Outbox empty?",
              how="Is the internet working? If a mail is stuck in the Outlook Outbox, remove the large attachment and send again (share files over 25 MB as a Drive / OneDrive link)."),
            S(id="storage_full", title="Mailbox full?", check="Is storage not at 100%?",
              how="Gmail: see 'storage used' at the bottom. If full, delete old mails with big attachments (search: larger:10M) and empty the Trash."),
            S(id="restart_outlook", title="Close and reopen Outlook", check="After reopening?",
              how="Close Outlook completely (it should not show in Task Manager either), then open it. Restart the PC if you can."),
            S(id="password_prompt", title="Baar baar password maang raha", check="Stuck after sign-in?",
              how="Never tell Hoola the password. Open the account in the browser: if the password was changed, enter the new one in Outlook yourself. For Gmail with 2-step, connect Outlook with 'Sign in with Google'."),
            S(id="safe_mode", title="Outlook safe mode", check="Does it work in safe mode?",
              how="Windows + R > 'outlook.exe /safe' > OK. If it works in safe mode, an add-in is the cause."),
            S(id="repair_profile", title="Outlook profile / Office repair", change="reset", admin=True, careful=True, check="After the new profile?",
              how="Control Panel > Mail > Show Profiles > Add (new profile), or Control Panel > Programs > Microsoft Office > Change > Quick Repair. Back up the PST file first."),
        ]},
    "account": {
        "label": "Password bhool gaye / account lock", "asset": "pc", "escalate": "it", "account": True,
        "words": ("password bhool", "password bhul", "forgot password", "locked", "lock ho", "account lock", "login nahi", "sign in nahi",
                  "account disabled", "too many attempts", "2fa", "two step", "authenticator", "पासवर्ड", "लॉक"),
        "escalate_when": ["Nobody remembers the office admin account password", "Suspected hacked account (password changed by itself, odd mails sent)",
                          "No recovery phone / email either"],
        "tell": ["Which account (Windows / Gmail / Microsoft / Tally / portal) - the name, NOT the password", "What error appears", "Recovery phone / email kiske paas"],
        "steps": [
            S(id="basics", title="Caps Lock, bhasha, sahi account", check="Caps Lock off, keyboard in English, correct user chosen?",
              how="Make sure the Caps Lock light is off, the keyboard language is ENG (on the taskbar) and the right user / email is chosen. Press the eye icon to show the password and check what is being typed."),
            S(id="wait_lock", title="Wait for the lock to clear", check="After 15-30 minutes?",
              how="Several wrong passwords lock an account for a while. Wait 15-30 minutes without trying."),
            S(id="self_reset", title="Use 'Forgot password' yourself", check="Was a new password set?",
              how="On the real page of the same company, use 'Forgot password' (Gmail: accounts.google.com, Microsoft: account.live.com/password/reset). Give the OTP only on your own phone and never tell it to anyone. Hoola never asks for a password / OTP."),
            S(id="admin_unlock", title="Unlock / new password from the admin", change="account", admin=True, check="Did the admin unlock it?",
              how="The office admin (you / the IT person) resets or unlocks that user's password from their admin account (Windows: Computer Management > Local Users; Google Workspace / Microsoft 365 admin page). The user sets their own new password at the next login."),
            S(id="two_step", title="2-step verification on", change="account", check="Is 2-step on?",
              how="As soon as you get the account back, turn on 2-step verification and fix the recovery phone / email. Print the backup codes and keep them locked away."),
        ]},
    "tally": {
        "label": "Tally problem", "asset": "pc", "escalate": "tally_partner",
        "words": ("tally", "tallyprime", "tally prime", "tally erp", "license", "licence", "company data", "data path", "tally band",
                  "tally error", "memory access violation", "टैली"),
        "escalate_when": ["Licence 'not activated / expired' and a question about renewal / TSS", "Company data is corrupt and will not open even after 'repair'",
                          "In multi-user, data is not visible from another PC (a server PC / sharing job)", "Upgrade / migration (ERP 9 se Prime)"],
        "tell": ["TallyPrime ka release (Help > About)", "Licence serial (shown on screen) - NOT the activation key / password",
                 "Full error text", "Which PC / folder the data is in, and how many people use it at once"],
        "steps": [
            S(id="error_text", title="Full error text", check="Error ka text likh liya / photo?",
              how="Take a photo of the error message or write it down (Tally's help site searches for exactly that text). Do not press Ctrl+Alt+R (repair) yet."),
            S(id="restart_tally", title="Close and reopen Tally", check="Working after reopening?",
              how="Close Tally completely (tally.exe should not show in Task Manager), then open it. If it was open twice on one PC, close one."),
            S(id="data_path", title="Data ka raasta / server PC", check="Does the company show in the company list?",
              how="If the data comes from a server in multi-user mode, that server PC must be on and on the network. In Tally, Select Company > 'Change path' and choose the right folder (check the folder was not renamed and the pen drive was not removed)."),
            S(id="licence", title="Check the licence", check="Gateway / Help > About mein licence 'Active'?",
              how="Help > About / F1: licence status. If it says 'Not activated', turn the internet on and close and reopen Tally. Buying a renewal / TSS is your decision: talk to your Tally partner."),
            S(id="backup_first", title="Back up first", check="Backup ki file bani?",
              how="Data > Backup, to a pen drive / another drive. This is essential before any repair."),
            S(id="repair", title="Company repair", change="reset", careful=True, check="Did the company open after the repair?",
              how="Only after the backup: Select Company > Ctrl+Alt+R (Repair) on the company. Big data takes time; do not close it in the middle."),
            S(id="update_tally", title="New release", change="install", admin=True, check="After the update?",
              how="Only from tallysolutions.com / 'Update' inside Tally. Only if TSS is valid. Back up first."),
        ]},
    "office_apps": {
        "label": "Word / Excel / MS Office problem", "asset": "pc", "escalate": "it",
        "words": ("word", "excel", "powerpoint", "ms office", "microsoft office", "office activate", "unlicensed product", "file nahi khul",
                  "file corrupt", "excel hang", "docx", "xlsx", "product activation", "वर्ड", "एक्सेल"),
        "escalate_when": ["'Unlicensed product' and the office has no licence (buying a licence is your decision)", "Important file is corrupt, even 'Open and Repair' does not work"],
        "tell": ["Office ka version (File > Account)", "Error text", "In one file or in all"],
        "steps": [
            S(id="save_copy", title="File ki copy bachao", check="Copy bani?",
              how="First make a copy of the suspect file in another folder. For a file that came by pen drive / WhatsApp, press 'Enable Editing' only if you trust the sender (never 'Enable Content' for macros)."),
            S(id="restart_app", title="Close and reopen the program", check="Did it open again?",
              how="Close Word / Excel completely (also in Task Manager), then open it. If it hangs, wait 15 seconds: AutoRecover saves your file."),
            S(id="open_repair", title="Open and Repair", check="File khuli?",
              how="Word / Excel > File > Open > Browse > choose the file > the arrow beside Open > 'Open and Repair'. In Excel also look at older AutoSave versions under File > Info > Manage Workbook."),
            S(id="safe_mode", title="Safe mode", check="Does it work in safe mode?",
              how="Windows + R > 'excel /safe' or 'winword /safe'. If it works in safe mode, an add-in is the cause: turn it off under File > Options > Add-ins."),
            S(id="sign_in", title="Account / licence", check="File > Account mein 'Product activated'?",
              how="File > Account: sign in with the Microsoft account the office licence belongs to. If it says 'Unlicensed', find out which account holds the licence. Never use a crack / 'activator' (it brings viruses)."),
            S(id="quick_repair", title="Office Quick Repair", change="install", admin=True, check="After the repair?",
              how="Control Panel > Programs and Features > Microsoft Office > Change > Quick Repair (if that does not work, Online Repair). Your files are not deleted."),
        ]},
    "whatsapp_web": {
        "label": "WhatsApp Web / Desktop problem", "asset": "pc", "escalate": "it",
        "words": ("whatsapp web", "whatsapp desktop", "whatsapp pc", "qr code", "link device", "linked device", "whatsapp computer",
                  "whatsapp nahi khul", "व्हाट्सएप वेब"),
        "escalate_when": ["Account 'banned' or 'logged out' for no reason (a job for WhatsApp support)", "Kisi aur ka device linked dikhe (hack ka shak: turant 'Log out')"],
        "tell": ["Web ya Desktop app", "Is WhatsApp working on the phone?", "Error text"],
        "steps": [
            S(id="phone_net", title="Phone ka net / WhatsApp update", check="Is WhatsApp fine on the phone?",
              how="Does WhatsApp open on the phone and is the internet working? Update WhatsApp from the Play Store."),
            S(id="relink", title="Link it again", check="Did the chats appear after scanning the QR?",
              how="On the phone: WhatsApp > three dots > Linked devices > 'Log out' the old PC > 'Link a device' > scan the QR on the PC screen. Do not send a photo of the QR to anyone."),
            S(id="check_devices", title="Linked devices jaancho", check="Only your own devices shown?",
              how="If Linked devices shows an unknown PC / browser, log it out at once and turn on Settings > Account > Two-step verification (keep the 6-digit PIN to yourself)."),
            S(id="browser", title="Change the browser / app", check="Doosre browser / Desktop app mein?",
              how="A newer Chrome / Edge, or WhatsApp Desktop from the Microsoft Store. On an office PC, use 'Keep me signed in' only on your own PC."),
            S(id="clear_site", title="Browser ka data saaf (sirf WhatsApp)", change="setting", check="After scanning the QR again?",
              how="In Chrome, on web.whatsapp.com click the lock icon > Site settings > Clear data. Then link again."),
        ]},
    "ups_power": {
        "label": "UPS / power problem", "asset": "ups", "escalate": "electrician",
        "words": ("ups", "inverter", "beep", "bijli", "power cut", "light gayi", "battery backup", "power nahi", "pc band ho gaya", "spike",
                  "socket", "यूपीएस", "बिजली"),
        "escalate_when": ["UPS battery 2-3 saal purani aur backup 5 minute se kam", "Burning smell, hot plug, sparks: switch off at the main switch at once and call an electrician",
                          "Earthing ka shak (PC ko chhune par current)", "UPS does not switch on at all"],
        "tell": ["UPS brand / model / VA", "How old the battery is", "How many devices are on it", "What the beep is like (continuous / on and off)"],
        "steps": [
            S(id="safety", title="Safety first", check="No smell / heat / sparks?",
              how="If there is a burning smell, a hot plug or sparks, touch nothing: switch off at the main switch and call an electrician (stop here)."),
            S(id="beep", title="Beep ka matlab", check="What kind of beep is it?",
              how="An on-and-off beep = the power has gone and it is running on battery: save your work and shut down the PC. A continuous beep = overload or a bad battery."),
            S(id="load", title="Reduce the load", check="Did the beep stop after removing the printer / heater?",
              how="Do not plug heavy items such as a laser printer, heater, kettle or AC into the UPS: only the PC, monitor and router."),
            S(id="plugs", title="Plug / extension", check="In another socket?",
              how="Plug the UPS straight into a good wall socket (not an extension board). Press the PC power cable in firmly."),
            S(id="battery_age", title="Battery ki umar", check="When was the battery fitted?",
              how="A UPS battery usually lasts 2-3 years. If the backup time is short, replacing the battery is the vendor's job (note the date in the asset record)."),
        ]},
    "cctv": {
        "label": "CCTV / NVR / DVR problem", "asset": "cctv", "escalate": "cctv",
        "words": ("cctv", "camera", "nvr", "dvr", "recording", "no video", "video loss", "hikvision", "cp plus", "dahua", "camera band",
                  "सीसीटीवी", "कैमरा"),
        "escalate_when": ["'Video loss' on a camera even after the cable / power are fine", "Hard disk 'error / not found' (not recording)",
                          "New camera / moving a camera", "Nobody remembers the NVR admin password (the vendor will reset it only against the bill)"],
        "tell": ["NVR / DVR brand + model", "Kaun sa camera (number / jagah)", "Screen par message (video loss / HDD error)", "Since when"],
        "steps": [
            S(id="which", title="Ek camera ya sab?", check="Which cameras are down?",
              how="On the monitor, see which camera is black / 'video loss'. All down = NVR / power; one down = that camera's cable / power."),
            S(id="power", title="Bijli / adapter / PoE", check="Does the camera's red IR light glow at night?",
              how="Is that camera's adapter / PoE switch on? Check that the wire is not cut or loose (look after the rain)."),
            S(id="restart_nvr", title="NVR restart", check="Do the cameras return after a restart?",
              how="NVR menu > Shutdown / Reboot (better than pulling the power). Then wait 2-3 minutes."),
            S(id="hdd", title="Is it recording?", check="Does playback show yesterday's recording?",
              how="In playback, look at yesterday's / today's recording. The HDD status should be 'Normal' (Menu > Storage). 'Error / Uninitialized' = the vendor; do not press 'Initialize / Format' yourself (old recordings will be erased)."),
            S(id="time", title="NVR ki tareekh / time", change="setting", check="Are the date / time right?",
              how="A wrong time causes problems in the evidence: Menu > System > Time: set the correct date / time (or NTP)."),
        ]},
    "display": {
        "label": "Monitor / projector / screen problem", "asset": "projector", "escalate": "it",
        "words": ("projector", "monitor", "display", "screen black", "no signal", "hdmi", "vga", "screen nahi", "tv screen", "second screen",
                  "duplicate", "extend", "प्रोजेक्टर", "मॉनिटर"),
        "escalate_when": ["Projector ki lamp light laal / 'lamp replace' message", "Monitor par lakeerein / toota panel", "'No signal' even after changing the cable / port"],
        "tell": ["Monitor / projector model", "HDMI / VGA / USB-C", "Laptop ya PC", "Screen par message"],
        "steps": [
            S(id="power_input", title="Bijli aur input", check="Screen par 'No signal' ya kaali?",
              how="The monitor / projector is on, and the right INPUT (HDMI 1 / HDMI 2 / VGA) is chosen with the remote / button."),
            S(id="cable", title="Reconnect the cable", check="Picture after the cable?",
              how="Unplug the HDMI / VGA cable at both ends and press it back in firmly; try another cable / another port."),
            S(id="win_p", title="Windows + P", check="Did it show after choosing Duplicate?",
              how="On the laptop press Windows + P > 'Duplicate' (same on both) or 'Extend'. This is only the way of showing."),
            S(id="restart", title="Cable first, then switch on", check="When switched on in this order?",
              how="Laptop off, plug in the cable, switch on the projector, then switch on the laptop."),
            S(id="resolution", title="Resolution", change="setting", check="Clear after changing the resolution?",
              how="Settings > System > Display > Display resolution: 'Recommended'. Projector par 1920x1080 ya 1280x720."),
        ]},
    "scanner": {
        "label": "Scanner not working", "asset": "scanner", "escalate": "printer",
        "words": ("scanner", "scan nahi", "scan", "scanning", "adf", "स्कैनर", "स्कैन"),
        "escalate_when": ["ADF (feeder) mein kaagaz baar baar phansta / ulta", "Streaks on the scan even after cleaning the glass"],
        "tell": ["Scanner / printer model", "USB ya network", "Which software it scans from"],
        "steps": [
            S(id="power_cable", title="Bijli / cable / dhakkan", check="Is the scanner on and shown in the PC?",
              how="The scanner is on, the USB is pressed in firmly, and the cover / feeder is closed properly."),
            S(id="windows_scan", title="Windows Scan / Fax and Scan se", check="Did it scan from there?",
              how="Start > 'Windows Fax and Scan' > New Scan. If it scans from there, the scanner is fine and your old software is stuck."),
            S(id="restart", title="Scanner + PC restart", check="After the restart?",
              how="Switch the scanner off and on, restart the PC."),
            S(id="glass", title="Glass saaf", check="Streaks gone?",
              how="Switch off the power and wipe the glass with a dry soft cloth (a little glass cleaner on the cloth, not on the glass)."),
            S(id="driver", title="Driver again", change="install", admin=True, check="After the new driver?",
              how="Only from the company's own website: the scanner driver / app for your model."),
        ]},
    "vpn": {
        "label": "VPN / remote access not working", "asset": "pc", "escalate": "it",
        "words": ("vpn", "remote desktop", "rdp", "anydesk", "teamviewer", "remote access", "forticlient", "remote se", "वीपीएन"),
        "escalate_when": ["The office VPN server / router is down (not working for anyone)", "Certificate / account expire"],
        "tell": ["Kaun sa VPN / remote app", "Error text", "Ghar ke net se ya office se", "Sab ka ya sirf ek ka"],
        "steps": [
            S(id="internet", title="Internet first", check="Do websites open without the VPN?",
              how="Is the internet working without the VPN? If not, fix the internet first (see the Internet problem)."),
            S(id="reconnect", title="Disconnect > connect", check="After reconnecting?",
              how="In the VPN app, Disconnect, wait 10 seconds, then Connect. Close and reopen the app."),
            S(id="who_asked", title="Remote access kisne maanga?", check="Did you start it yourself?",
              how="Never give an AnyDesk / TeamViewer code to a stranger, especially on a 'bank / KYC / refund' call: this is the biggest fraud."),
            S(id="time_sync", title="Is the PC time right?", change="setting", check="After fixing the time?",
              how="Settings > Time & language > turn on 'Set time automatically' > Sync now. The VPN certificate fails when the time is wrong."),
            S(id="reinstall", title="VPN app again", change="install", admin=True, check="After the fresh install?",
              how="Only from the place the office / VPN company tells you. Get the settings / profile from the IT person."),
        ]},
    "security": {
        "label": "Virus / ajeeb popup / phishing ka shak", "asset": "pc", "escalate": "it", "security": True,
        "words": ("virus", "malware", "ransomware", "hack", "hacked", "popup", "pop-up", "files encrypted", "files locked", "phishing", "fake mail",
                  "fraud mail", "suspicious", "antivirus", "defender", "ajeeb link", "link par click", "वायरस", "हैक"),
        "escalate_when": ["File names changed / files will not open / a 'ransom' note (ransomware): act at once", "Someone entered a password / money went",
                          "Antivirus cannot remove a 'threat'"],
        "tell": ["What was shown (screenshot)", "On which PC, and when", "What was clicked / downloaded / filled in", "Are there other PCs on the network?"],
        "steps": [
            S(id="disconnect", title="Disconnect from the internet at once", check="Wi-Fi band / LAN cable nikali?",
              how="If you suspect it, turn off that PC's Wi-Fi / unplug the LAN cable (do not shut the PC down: the evidence stays). Do not plug in a pen drive."),
            S(id="dont_pay", title="Do not fill in or give anything", check="Did anyone give a password / OTP / money?",
              how="Do not dial the number shown in a popup, do not pay the 'ransom', and do not give the code of a remote app (AnyDesk). If money has gone, call 1930 at once."),
            S(id="scan", title="Antivirus full scan", check="What did the scan say?",
              how="Windows Security > Virus & threat protection > Scan options > Full scan (or the office antivirus). Tell Hoola the name of what it found."),
            S(id="passwords", title="Doosre device se password badlo", change="account", check="Were the passwords of important accounts changed?",
              how="If a password was entered on a link: from a CLEAN phone / another PC, change that account's password yourself (email, bank, GST, Tally) and turn on 2-step. Do not give the password to Hoola."),
            S(id="offline_scan", title="Microsoft Defender Offline scan", change="setting", admin=True, check="Clean after the offline scan?",
              how="Windows Security > Scan options > 'Microsoft Defender Antivirus (offline scan)' > Scan now. The PC restarts and scans for 15 minutes: save your work first."),
        ]},
    "backup": {
        "label": "Backup / data bachana", "asset": "pc", "escalate": "it",
        "words": ("backup", "back up", "data loss", "file delete", "file mit", "pen drive", "hard disk", "external drive", "recover",
                  "data chala gaya", "restore", "बैकअप"),
        "escalate_when": ["Hard disk asks to be 'formatted' / clicking sound (a data recovery lab job: write nothing else to it)",
                          "Important data is gone and there is no backup"],
        "tell": ["Kya data (Tally / documents / photos)", "Where it was (PC / drive / folder)", "When the last backup was"],
        "steps": [
            S(id="stop_writing", title="Do not write anything to that drive", check="Has nothing new been saved on the drive?",
              how="If a file is gone, do not save or install anything new on the same drive: the chance of getting it back falls."),
            S(id="recycle", title="Recycle Bin / earlier version", check="Found there?",
              how="Check the Recycle Bin. Right-click the folder > 'Restore previous versions'. Also check 'Trash / Recycle bin' in OneDrive / Google Drive."),
            S(id="what_to_backup", title="What must be saved", check="List bani?",
              how="The Tally data folder, Documents / Desktop, Outlook PST, GST / bank files, accounts Excel files. Hoola keeps the list in the asset note."),
            S(id="three_two_one", title="3-2-1 backup", check="Doosri copy alag jagah?",
              how="At least two copies: one on an external drive / NAS, one away from the office (cloud or home). Unplug and put away the external drive after the backup (ransomware can erase that too)."),
            S(id="schedule", title="Set up automatic backup", change="setting", check="Backup schedule bana?",
              how="Windows: Settings > Accounts > Windows backup, or File History (Control Panel). Tally: Data > Backup every evening. Once a week, restore a file to check that it opens."),
        ]},
    "pc_power": {
        "label": "Computer does not start / blue screen", "asset": "pc", "escalate": "it",
        "words": ("chalu nahi", "start nahi", "on nahi", "boot", "blue screen", "bsod", "black screen", "beep sound", "restart loop",
                  "no display", "बंद हो गया", "चालू नहीं"),
        "escalate_when": ["Completely dead (no light / fan) even in a good socket", "Beeps but shows nothing",
                          "Neeli screen baar baar (stop code likh lijiye)", "'No bootable device' / disk not found"],
        "tell": ["PC / laptop model", "Lights / pankha / beep", "What is written on the screen (stop code)", "Anything new fitted / dropped?"],
        "steps": [
            S(id="power", title="Bijli / socket / button", check="Fan / light on?",
              how="Try another socket, is the UPS on? Laptop: plug in the charger for 10 minutes. Check the monitor's own power and cable too."),
            S(id="hard_reset", title="Remove all power", check="Did it start after this?",
              how="Unplug the power cable, hold the power button for 15 seconds, then plug in and switch on. Laptop: remove the charger and hold power for 30 seconds."),
            S(id="usb_out", title="Remove pen drives / new devices", check="Did it start after removing them?",
              how="Unplug the pen drive, external disk and printer USB, then switch on."),
            S(id="stop_code", title="Note the stop code", check="Did you note the blue screen code?",
              how="Take a photo of the 'Stop code' (such as CRITICAL_PROCESS_DIED) and the QR on the blue screen: the technician searches with it."),
            S(id="startup_repair", title="Startup Repair", change="reset", admin=True, careful=True, check="After the repair?",
              how="Switch off three times as it starts and 'Automatic Repair' appears > Advanced options > Startup Repair. 'Reset this PC' only with your approval and after a backup."),
        ]},
}

GENERIC = {"label": "Any other IT problem", "asset": "", "escalate": "it", "words": (),
           "escalate_when": ["Ghar ke upay se na ho", "Hardware toota / jalne ki gandh"],
           "tell": ["Device ka naam / model", "Full error text / photo", "Since when, and how many people"],
           "steps": [
               S(id="error_text", title="Error ka text / photo", check="Photo / text obtained?", how="Take a photo of what is written on the screen, or write out the full text."),
               S(id="restart", title="Restart", check="After a restart?", how="Close the program / device and start it again."),
               S(id="scope", title="Sab par ya ek par?", check="Doosre PC / user par bhi?", how="Try the same task on another PC / user."),
               S(id="recent_change", title="What changed recently?", check="Anything newly installed / updated / dropped?",
                 how="Any new program, update, cable or power cut recently? Telling this helps the most."),
           ]}

CHANGE_LABEL = {"setting": "Change a system setting", "install": "Install / update", "uninstall": "Remove a program", "reset": "Reset / repair",
                "account": "Account / password change", "network": "Network setting", "firmware": "Firmware update", "other": "Change"}
VENDOR_KINDS = ("amc", "it", "isp", "printer", "cctv", "tally_partner", "electrician", "software", "other")
VENDOR_LABEL = {"amc": "AMC provider", "it": "Computer technician", "isp": "Internet (ISP)", "printer": "Printer service",
                "cctv": "CCTV vendor", "tally_partner": "Tally partner", "electrician": "Electrician", "software": "Software vendor", "other": "Vendor"}
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
