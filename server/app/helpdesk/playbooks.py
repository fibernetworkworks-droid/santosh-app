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
        "label": "Printer nahi chal raha", "asset": "printer", "escalate": "printer",
        "words": ("printer", "print nahi", "print nhi", "printout", "paper jam", "page atak", "toner", "cartridge", "ink",
                  "spooler", "print queue", "प्रिंटर", "प्रिंट"),
        "escalate_when": ["Paper jam baar baar, ya andar koi toota hissa / ajeeb awaaz", "Display par error code (E-xx) jo restart se na jaye",
                          "Print par lakeerein / dhabbe naya toner daalne ke baad bhi", "Printer chalu hi nahi hota (power light nahi)"],
        "tell": ["Printer brand + model (sticker par)", "Display ka error / blinking lights", "USB se juda hai ya Wi-Fi / LAN se",
                 "Ek PC se nahi chal raha ya sabse"],
        "steps": [
            S(id="power_paper", title="Bijli, kaagaz, toner dekho", check="Printer ki light hari? Kaagaz tray mein? Display par koi error?",
              how="Printer chalu hai, tray mein kaagaz hai, dhakkan band hai, display par 'paper jam / toner low' to nahi. Jam ho to printer band karke dheere se kaagaz seedha kheenchiye (phaadiye mat)."),
            S(id="cable", title="Cable / Wi-Fi", check="Printer PC ki list mein 'Ready' / 'Online' dikh raha?",
              how="USB cable dono taraf achhe se lagaiye (doosra USB port try karein). Wi-Fi / LAN printer ho to wahi Wi-Fi jis par PC hai; printer ka Wi-Fi light dekhiye."),
            S(id="restart_both", title="Printer + PC restart", check="Restart ke baad test page nikla?",
              how="Printer band, 30 second ruk kar chalu. PC bhi restart. Phir Notepad mein ek line likh kar print karke dekhiye."),
            S(id="queue", title="Atki hui print queue", check="Queue khaali hone ke baad print hua?",
              how="Start > Settings > Bluetooth & devices > Printers > apna printer > 'Open print queue' > saare document par right-click > Cancel."),
            S(id="default_printer", title="Sahi printer chuna hai?", change="setting", check="Print dialog mein sahi printer naam?",
              how="Settings > Printers > apna printer > 'Set as default' (aur 'Let Windows manage my default printer' band). Print karte waqt list mein sahi naam chunein."),
            S(id="spooler", title="Print Spooler service restart", change="setting", admin=True, check="Queue khaali + print hua?",
              how="Start mein 'services' likhiye > Services > 'Print Spooler' par right-click > Restart. (Admin wale account se.)"),
            S(id="driver", title="Printer ka driver dobara daalo", change="install", admin=True, check="Naye driver ke baad test page?",
              how="Sirf printer company ki apni website (HP / Canon / Epson / Brother support page) se apne model ka driver. Kisi aur site ya 'driver updater' app se kabhi nahi."),
        ]},
    "network": {
        "label": "Internet / Wi-Fi / LAN nahi chal raha", "asset": "router", "escalate": "isp",
        "words": ("internet", "wifi", "wi-fi", "wi fi", "net nahi", "net nhi", "net slow", "net band", "net gaya", "net down", "net chala", "network", "lan", "router", "broadband", "no internet",
                  "connected no internet", "ethernet", "fiber", "fibre", "ont", "speed kam", "इंटरनेट", "नेट"),
        "escalate_when": ["Router / ONT par LOS ya laal light (fibre ka signal nahi)", "Sab devices par net nahi, router restart se bhi nahi",
                          "Ek hi jagah ke saare LAN point band (switch / cable ka kaam)", "Speed plan se bahut kam, kai din se"],
        "tell": ["ISP ka naam + customer ID / landline number (bill par)", "Router / ONT ki lights (PON, LOS, Internet)",
                 "Sab devices par ya ek par", "Kab se"],
        "steps": [
            S(id="scope", title="Sab par ya ek par?", check="Phone par isi Wi-Fi se net chal raha?",
              how="Doosre PC / phone par isi Wi-Fi se dekhiye. Sab par band = router / ISP; sirf ek par = woh device."),
            S(id="lights", title="Router / ONT ki lights", check="LOS light band? Internet / PON light hari?",
              how="Fibre ONT par 'LOS' laal = fibre ka signal nahi: yeh ISP ka kaam hai (seedha aage bhejiye). Taar dheela to nahi, fibre ki patli taar mudi to nahi."),
            S(id="router_restart", title="Router restart", check="2-3 minute baad net aaya?",
              how="Router (aur ONT) ki bijli nikaal kar 30 second baad lagaiye. 2-3 minute ruk kar dekhiye. Reset button (chhota ched) mat dabaiye."),
            S(id="cable_port", title="LAN cable / port", check="Cable lagate hi PC par 'Network' aaya?",
              how="LAN par: cable dono taraf dabakar lagaiye, router ka doosra port try kijiye, cable badal kar dekhiye."),
            S(id="forget_wifi", title="Wi-Fi bhool kar dobara jodo", change="network", check="Dobara judne ke baad net?",
              how="PC par Wi-Fi > apne network par right-click > Forget > phir se chunein aur Wi-Fi password (router ke sticker / jo office mein likha hai) daaliye. Password Hoola ko mat bataiye."),
            S(id="troubleshooter", title="Windows network troubleshooter", check="Troubleshooter ne kuch theek kiya?",
              how="Settings > System > Troubleshoot > Other troubleshooters > Network and Internet > Run. Jo bataye padhkar Hoola ko bataiye."),
            S(id="network_reset", title="Network reset (PC)", change="reset", admin=True, careful=True, check="Restart ke baad net?",
              how="Settings > Network & internet > Advanced network settings > Network reset. Saare Wi-Fi password aur VPN dobara daalne padenge."),
        ]},
    "slow_pc": {
        "label": "Computer slow / hang", "asset": "pc", "escalate": "it",
        "words": ("slow", "hang", "atak", "dheema", "dheere", "freeze", "not responding", "lag", "100% disk", "ram full", "computer slow",
                  "pc slow", "laptop slow", "धीमा", "हैंग"),
        "escalate_when": ["Disk 100% hamesha + PC 5 saal se purana (HDD) = SSD lagwane ka kaam", "Neeli screen (BSOD) baar baar",
                          "Tez garam / pankhe ki tez awaaz", "Restart ke baad bhi turant hang"],
        "tell": ["PC / laptop model, kitna purana", "RAM aur HDD / SSD (Settings > System > About)", "Windows version", "Kab hota hai: chalu karte hi / Tally / browser"],
        "steps": [
            S(id="restart", title="Poora restart", check="Restart ke baad theek?",
              how="Start > Power > Restart (Shut down nahi, Restart). Kai din se band nahi hua to yahi sabse bada ilaaj."),
            S(id="task_manager", title="Kaun sa program bhaari?", check="CPU / Memory / Disk mein sabse upar kaun?",
              how="Ctrl + Shift + Esc > Task Manager > Processes. CPU / Memory / Disk par click karke sabse upar wala dekhiye. Apna program ho to band kijiye; naam samajh na aaye to Hoola ko naam bataiye."),
            S(id="disk_space", title="C drive mein jagah", check="C drive mein 15% se zyada khaali?",
              how="File Explorer > This PC > C drive kitni bhari. Downloads, Desktop ke bade video / purani files doosri drive ya pen drive par."),
            S(id="tabs", title="Browser ke tab", check="Tab band karne ke baad tez?",
              how="Chrome / Edge mein 20-30 tab khule hon to band kijiye; zaroori wale bookmark kar lijiye."),
            S(id="startup_apps", title="Shuru hote hi chalne wale apps", change="setting", check="Agle restart par jaldi chalu hua?",
              how="Task Manager > Startup apps > jo zaroori nahi (updaters, chat apps) unhe 'Disable'. Antivirus / Tally / printer ko chhodiye."),
            S(id="windows_update", title="Windows update", change="install", check="Update ke baad?",
              how="Settings > Windows Update > Check for updates > install, restart. Kaam ke beech mein nahi: shaam ko."),
            S(id="disk_cleanup", title="Disk Cleanup", change="setting", check="Kitni jagah khaali hui?",
              how="Start mein 'Disk Cleanup' > C drive > 'Clean up system files' > Temporary files, Recycle Bin tick > OK. 'Downloads' tick mat kijiye."),
        ]},
    "email": {
        "label": "Email (Outlook / Gmail) nahi chal raha", "asset": "pc", "escalate": "it",
        "words": ("email", "e-mail", "mail nahi", "outlook", "gmail", "inbox", "mail send", "mail aa nahi", "mailbox full", "smtp", "pst",
                  "ईमेल", "मेल"),
        "escalate_when": ["Company domain ka mail (naam@company.com) sab ka band: mail hosting wale ka kaam",
                          "Outlook data file (PST) kharab / bahut badi", "Mail apne aap doosron ko ja rahe (account hack ka shak: Phishing / account bhi kholiye)"],
        "tell": ["Email address ka domain (gmail.com / company.com)", "Error ka poora text / screenshot", "Phone par chal raha ya wahan bhi band",
                 "Outlook ka version"],
        "steps": [
            S(id="webmail", title="Browser mein kholo", check="Browser (gmail.com / outlook.com / webmail) mein mail khul raha?",
              how="Wahi account browser mein kholiye. Wahan chal raha = sirf Outlook / app ki dikkat; wahan bhi nahi = account / mail server."),
            S(id="internet_outbox", title="Net aur Outbox", check="Outbox khaali hua?",
              how="Net chal raha hai? Outlook mein Outbox mein atka mail ho to bada attachment hatakar dobara bhejiye (25 MB se badi file ko Drive / OneDrive link se)."),
            S(id="storage_full", title="Mailbox bhara hua?", check="Storage 100% to nahi?",
              how="Gmail: neeche 'storage used'. Bhara ho to purane bade attachment wale mail (search: larger:10M) hataiye, Trash khaali kijiye."),
            S(id="restart_outlook", title="Outlook band karke kholo", check="Dobara kholne par?",
              how="Outlook poora band kijiye (Task Manager mein bhi na dikhe), phir kholiye. Ho sake to PC restart."),
            S(id="password_prompt", title="Baar baar password maang raha", check="Sign in ke baad ruk gaya?",
              how="Password Hoola ko kabhi mat bataiye. Browser mein account kholke dekhiye: password badla gaya ho to Outlook mein naya password khud daaliye. 2-step wale Gmail mein Outlook ko 'Sign in with Google' se jodiye."),
            S(id="safe_mode", title="Outlook safe mode", check="Safe mode mein chal raha?",
              how="Windows + R > 'outlook.exe /safe' > OK. Safe mode mein chale to koi add-in wajah hai."),
            S(id="repair_profile", title="Outlook profile / Office repair", change="reset", admin=True, careful=True, check="Naye profile ke baad?",
              how="Control Panel > Mail > Show Profiles > Add (naya profile) ya Control Panel > Programs > Microsoft Office > Change > Quick Repair. Pehle PST file ka backup."),
        ]},
    "account": {
        "label": "Password bhool gaye / account lock", "asset": "pc", "escalate": "it", "account": True,
        "words": ("password bhool", "password bhul", "forgot password", "locked", "lock ho", "account lock", "login nahi", "sign in nahi",
                  "account disabled", "too many attempts", "2fa", "two step", "authenticator", "पासवर्ड", "लॉक"),
        "escalate_when": ["Office ke admin account ka password kisi ko yaad nahi", "Account hack hone ka shak (password apne aap badla, ajeeb mail gaye)",
                          "Recovery phone / email bhi nahi"],
        "tell": ["Kaun sa account (Windows / Gmail / Microsoft / Tally / portal) - naam, password NAHI", "Kya error aata hai", "Recovery phone / email kiske paas"],
        "steps": [
            S(id="basics", title="Caps Lock, bhasha, sahi account", check="Caps Lock band, keyboard English, sahi user chuna?",
              how="Caps Lock ki light band ho, keyboard ki bhasha ENG ho (taskbar par), sahi user / email chuna ho. Password dikhane wali aankh dabakar dekhiye kya type ho raha."),
            S(id="wait_lock", title="Lock khulne ka intezaar", check="15-30 minute baad?",
              how="Kai baar galat password se account kuch der ke liye lock hota hai. 15-30 minute bina koshish kiye rukiye."),
            S(id="self_reset", title="'Forgot password' khud karo", check="Naya password ban gaya?",
              how="Usi company ke asli page par 'Forgot password' (Gmail: accounts.google.com, Microsoft: account.live.com/password/reset). OTP sirf apne phone par, kisi ko mat bataiye. Hoola kabhi password / OTP nahi maangta."),
            S(id="admin_unlock", title="Admin se unlock / naya password", change="account", admin=True, check="Admin ne kholke diya?",
              how="Office ka admin (aap / IT wale) apne admin account se us user ka password reset kare ya unlock kare (Windows: Computer Management > Local Users; Google Workspace / Microsoft 365 admin page). User agli baar login par apna naya password khud rakhe."),
            S(id="two_step", title="2-step verification on", change="account", check="2-step on hua?",
              how="Account wapas mile to turant 2-step verification on kijiye aur recovery phone / email theek kijiye. Backup codes print karke taale mein."),
        ]},
    "tally": {
        "label": "Tally ki dikkat", "asset": "pc", "escalate": "tally_partner",
        "words": ("tally", "tallyprime", "tally prime", "tally erp", "license", "licence", "company data", "data path", "tally band",
                  "tally error", "memory access violation", "टैली"),
        "escalate_when": ["Licence 'not activated / expired' aur renewal / TSS ka sawaal", "Company data corrupt / 'repair' ke baad bhi nahi khulta",
                          "Multi-user mein doosre PC se data nahi dikhta (server PC / sharing ka kaam)", "Upgrade / migration (ERP 9 se Prime)"],
        "tell": ["TallyPrime ka release (Help > About)", "Licence serial (screen par dikhta hai) - activation key / password NAHI",
                 "Error ka poora text", "Data kis PC / folder mein hai, kitne log ek saath chalate hain"],
        "steps": [
            S(id="error_text", title="Error ka poora text", check="Error ka text likh liya / photo?",
              how="Error message ki photo lijiye ya likhiye (Tally ki help site par wahi text dhoondhte hain). Ctrl+Alt+R (repair) abhi mat dabaiye."),
            S(id="restart_tally", title="Tally band karke kholo", check="Dobara kholne par chal raha?",
              how="Tally poora band kijiye (Task Manager mein tally.exe na dikhe), phir kholiye. Ek hi PC par do baar khula ho to ek band."),
            S(id="data_path", title="Data ka raasta / server PC", check="Company list mein company dikh rahi?",
              how="Multi-user / server se data aata ho to woh server PC chalu aur network par ho. Tally mein Select Company > 'Change path' se sahi folder chunein (folder ka naam badla / pen drive nikli to nahi)."),
            S(id="licence", title="Licence dekho", check="Gateway / Help > About mein licence 'Active'?",
              how="Help > About / F1: licence status. 'Not activated' ho to net chalu karke Tally band-chalu. Renewal / TSS kharidna aapka faisla: aapke Tally partner se."),
            S(id="backup_first", title="Pehle backup", check="Backup ki file bani?",
              how="Data > Backup se company ka backup pen drive / doosri drive par. Repair se pehle zaroori."),
            S(id="repair", title="Company repair", change="reset", careful=True, check="Repair ke baad company khuli?",
              how="Backup ke baad hi: Select Company > company par Ctrl+Alt+R (Repair). Bade data mein time lagta hai; beech mein band mat kijiye."),
            S(id="update_tally", title="Naya release", change="install", admin=True, check="Update ke baad?",
              how="Sirf tallysolutions.com / Tally ke andar 'Update' se. TSS valid ho tabhi. Pehle backup."),
        ]},
    "office_apps": {
        "label": "Word / Excel / MS Office ki dikkat", "asset": "pc", "escalate": "it",
        "words": ("word", "excel", "powerpoint", "ms office", "microsoft office", "office activate", "unlicensed product", "file nahi khul",
                  "file corrupt", "excel hang", "docx", "xlsx", "product activation", "वर्ड", "एक्सेल"),
        "escalate_when": ["'Unlicensed product' aur office ke paas licence nahi (licence kharidna aapka faisla)", "Zaroori file corrupt, 'Open and Repair' se bhi nahi"],
        "tell": ["Office ka version (File > Account)", "Error text", "Ek file mein ya sab mein"],
        "steps": [
            S(id="save_copy", title="File ki copy bachao", check="Copy bani?",
              how="Kharab lagne wali file ki pehle ek copy doosre folder mein. Pen drive / WhatsApp se aayi file ho to 'Enable Editing' tabhi jab bhejne wale par bharosa ho (macro / 'Enable Content' bilkul nahi)."),
            S(id="restart_app", title="Program band karke kholo", check="Dobara khula?",
              how="Word / Excel poora band (Task Manager mein bhi), phir kholiye. Hang ho to 15 second rukiye: AutoRecover file bachata hai."),
            S(id="open_repair", title="Open and Repair", check="File khuli?",
              how="Word / Excel > File > Open > Browse > file chunein > Open ke bagal ka teer > 'Open and Repair'. Excel mein File > Info > Manage Workbook se purana AutoSave version bhi dekhiye."),
            S(id="safe_mode", title="Safe mode", check="Safe mode mein chal raha?",
              how="Windows + R > 'excel /safe' ya 'winword /safe'. Safe mode mein chale to koi add-in wajah: File > Options > Add-ins se band."),
            S(id="sign_in", title="Account / licence", check="File > Account mein 'Product activated'?",
              how="File > Account: office wala Microsoft account se sign in. 'Unlicensed' ho to licence aapke paas kis account par hai yeh dekhiye. Crack / 'activator' kabhi nahi (virus aata hai)."),
            S(id="quick_repair", title="Office Quick Repair", change="install", admin=True, check="Repair ke baad?",
              how="Control Panel > Programs and Features > Microsoft Office > Change > Quick Repair (na ho to Online Repair). Files nahi mitti."),
        ]},
    "whatsapp_web": {
        "label": "WhatsApp Web / Desktop ki dikkat", "asset": "pc", "escalate": "it",
        "words": ("whatsapp web", "whatsapp desktop", "whatsapp pc", "qr code", "link device", "linked device", "whatsapp computer",
                  "whatsapp nahi khul", "व्हाट्सएप वेब"),
        "escalate_when": ["Account 'banned' ya 'logged out' bina wajah (WhatsApp support ka kaam)", "Kisi aur ka device linked dikhe (hack ka shak: turant 'Log out')"],
        "tell": ["Web ya Desktop app", "Phone par WhatsApp chal raha?", "Error text"],
        "steps": [
            S(id="phone_net", title="Phone ka net / WhatsApp update", check="Phone par WhatsApp theek?",
              how="Phone par WhatsApp khul raha, net chal raha? Play Store se WhatsApp update."),
            S(id="relink", title="Dobara link karo", check="QR scan ke baad chat aaye?",
              how="Phone par WhatsApp > teen bindu > Linked devices > purana PC 'Log out' > 'Link a device' > PC ki screen ka QR scan. QR ki photo kisi ko mat bhejiye."),
            S(id="check_devices", title="Linked devices jaancho", check="Sirf apne hi devices dikh rahe?",
              how="Linked devices mein koi anjaan PC / browser dikhe to turant Log out aur Settings > Account > Two-step verification on (6 ankon ka PIN aap khud rakhiye, kisi ko nahi)."),
            S(id="browser", title="Browser / app badal kar", check="Doosre browser / Desktop app mein?",
              how="Chrome / Edge naya version, ya Microsoft Store se WhatsApp Desktop. Office PC par WhatsApp ke 'Keep me signed in' sirf apne PC par."),
            S(id="clear_site", title="Browser ka data saaf (sirf WhatsApp)", change="setting", check="Dobara QR ke baad?",
              how="Chrome mein web.whatsapp.com par taale ke nishaan > Site settings > Clear data. Phir dobara link."),
        ]},
    "ups_power": {
        "label": "UPS / bijli ki dikkat", "asset": "ups", "escalate": "electrician",
        "words": ("ups", "inverter", "beep", "bijli", "power cut", "light gayi", "battery backup", "power nahi", "pc band ho gaya", "spike",
                  "socket", "यूपीएस", "बिजली"),
        "escalate_when": ["UPS battery 2-3 saal purani aur backup 5 minute se kam", "Jalne ki gandh, garam plug, chingari: turant main switch band, electrician",
                          "Earthing ka shak (PC ko chhune par current)", "UPS chalu hi nahi hota"],
        "tell": ["UPS brand / model / VA", "Battery kitni purani", "Kitne device ispe", "Beep kaisa (lagaatar / ruk ruk kar)"],
        "steps": [
            S(id="safety", title="Pehle suraksha", check="Gandh / garmi / chingari nahi?",
              how="Jalne ki gandh, garam plug ya chingari ho to kuch mat chhuiye: main switch band karke electrician ko bulaiye (yahin ruk jaiye)."),
            S(id="beep", title="Beep ka matlab", check="Beep kaisi hai?",
              how="Ruk ruk kar beep = bijli gayi, battery par chal raha: kaam save karke PC band kijiye. Lagaatar beep = overload ya battery kharab."),
            S(id="load", title="Load kam karo", check="Printer / heater hatane ke baad beep band?",
              how="Laser printer, heater, kettle, AC jaise bhaari cheezein UPS mein mat lagaiye: sirf PC, monitor, router."),
            S(id="plugs", title="Plug / extension", check="Doosre socket mein?",
              how="UPS ko seedha deewar ke achhe socket mein (extension board mein nahi). PC ka power cable dabakar lagaiye."),
            S(id="battery_age", title="Battery ki umar", check="Battery kab lagi thi?",
              how="UPS battery aam taur par 2-3 saal chalti hai. Backup kam ho to battery badalne ka kaam vendor ka (asset mein tareekh likh dijiye)."),
        ]},
    "cctv": {
        "label": "CCTV / NVR / DVR ki dikkat", "asset": "cctv", "escalate": "cctv",
        "words": ("cctv", "camera", "nvr", "dvr", "recording", "no video", "video loss", "hikvision", "cp plus", "dahua", "camera band",
                  "सीसीटीवी", "कैमरा"),
        "escalate_when": ["Camera par 'video loss' cable / power theek hone ke baad bhi", "Hard disk 'error / not found' (recording nahi ho rahi)",
                          "Naya camera / jagah badalni", "NVR ka admin password kisi ko yaad nahi (vendor bill dekhkar hi reset karega)"],
        "tell": ["NVR / DVR brand + model", "Kaun sa camera (number / jagah)", "Screen par message (video loss / HDD error)", "Kab se"],
        "steps": [
            S(id="which", title="Ek camera ya sab?", check="Kaun se camera band?",
              how="Monitor par dekhiye kaun sa camera kaala / 'video loss'. Sab band = NVR / bijli; ek band = us camera ki cable / power."),
            S(id="power", title="Bijli / adapter / PoE", check="Camera ki laal IR light raat mein jalti?",
              how="Us camera ka adapter / PoE switch chalu hai? Taar kahin kati / dheeli to nahi (baarish ke baad dekhiye)."),
            S(id="restart_nvr", title="NVR restart", check="Restart ke baad camera aaye?",
              how="NVR ka menu > Shutdown / Reboot (bijli kheenchne se behtar). Phir 2-3 minute rukiye."),
            S(id="hdd", title="Recording ho rahi?", check="Playback mein kal ki recording dikh rahi?",
              how="Playback mein kal / aaj ki recording dekhiye. HDD status 'Normal' ho (Menu > Storage). 'Error / Uninitialized' = vendor; 'Initialize / Format' apne aap mat dabaiye (purani recording mitt jayegi)."),
            S(id="time", title="NVR ki tareekh / time", change="setting", check="Tareekh / time sahi?",
              how="Galat time ho to sabooton mein dikkat: Menu > System > Time: sahi tareekh / time (ya NTP)."),
        ]},
    "display": {
        "label": "Monitor / projector / screen ki dikkat", "asset": "projector", "escalate": "it",
        "words": ("projector", "monitor", "display", "screen black", "no signal", "hdmi", "vga", "screen nahi", "tv screen", "second screen",
                  "duplicate", "extend", "प्रोजेक्टर", "मॉनिटर"),
        "escalate_when": ["Projector ki lamp light laal / 'lamp replace' message", "Monitor par lakeerein / toota panel", "Cable / port badalne ke baad bhi 'No signal'"],
        "tell": ["Monitor / projector model", "HDMI / VGA / USB-C", "Laptop ya PC", "Screen par message"],
        "steps": [
            S(id="power_input", title="Bijli aur input", check="Screen par 'No signal' ya kaali?",
              how="Monitor / projector chalu, aur remote / button se sahi INPUT (HDMI 1 / HDMI 2 / VGA) chuna hai."),
            S(id="cable", title="Cable dobara lagao", check="Cable ke baad picture?",
              how="HDMI / VGA dono taraf nikaal kar dabakar lagaiye; doosri cable / doosra port try kijiye."),
            S(id="win_p", title="Windows + P", check="Duplicate chunne ke baad dikha?",
              how="Laptop par Windows + P dabaiye > 'Duplicate' (dono par same) ya 'Extend'. Yeh sirf dikhane ka tareeka hai."),
            S(id="restart", title="Pehle cable, phir chalu", check="Is kram mein chalu karne par?",
              how="Laptop band, cable lagaiye, projector chalu, phir laptop chalu."),
            S(id="resolution", title="Resolution", change="setting", check="Resolution badalne ke baad saaf?",
              how="Settings > System > Display > Display resolution: 'Recommended'. Projector par 1920x1080 ya 1280x720."),
        ]},
    "scanner": {
        "label": "Scanner nahi chal raha", "asset": "scanner", "escalate": "printer",
        "words": ("scanner", "scan nahi", "scan", "scanning", "adf", "स्कैनर", "स्कैन"),
        "escalate_when": ["ADF (feeder) mein kaagaz baar baar phansta / ulta", "Scan par lakeerein glass saaf karne ke baad bhi"],
        "tell": ["Scanner / printer model", "USB ya network", "Kaun sa software se scan"],
        "steps": [
            S(id="power_cable", title="Bijli / cable / dhakkan", check="Scanner chalu aur PC mein dikhta?",
              how="Scanner chalu, USB dabakar laga, dhakkan / feeder theek band."),
            S(id="windows_scan", title="Windows Scan / Fax and Scan se", check="Wahan se scan hua?",
              how="Start > 'Windows Fax and Scan' > New Scan. Wahan se ho jaye to scanner theek hai, apna purana software atka hai."),
            S(id="restart", title="Scanner + PC restart", check="Restart ke baad?",
              how="Scanner band-chalu, PC restart."),
            S(id="glass", title="Glass saaf", check="Lakeerein gayi?",
              how="Bijli band karke glass ko sookhe naram kapde se (thoda sa glass cleaner kapde par, glass par nahi)."),
            S(id="driver", title="Driver dobara", change="install", admin=True, check="Naye driver ke baad?",
              how="Sirf company ki apni website se apne model ka scanner driver / app."),
        ]},
    "vpn": {
        "label": "VPN / remote access nahi chal raha", "asset": "pc", "escalate": "it",
        "words": ("vpn", "remote desktop", "rdp", "anydesk", "teamviewer", "remote access", "forticlient", "remote se", "वीपीएन"),
        "escalate_when": ["Office ka VPN server / router band (sab ka nahi chal raha)", "Certificate / account expire"],
        "tell": ["Kaun sa VPN / remote app", "Error text", "Ghar ke net se ya office se", "Sab ka ya sirf ek ka"],
        "steps": [
            S(id="internet", title="Pehle internet", check="Bina VPN ke websites khul rahi?",
              how="Bina VPN ke net chal raha? Nahi to pehle internet theek (Internet wali dikkat)."),
            S(id="reconnect", title="Disconnect > connect", check="Dobara judne par?",
              how="VPN app mein Disconnect, 10 second, phir Connect. App band karke kholiye."),
            S(id="who_asked", title="Remote access kisne maanga?", check="Aap ne khud shuru kiya?",
              how="AnyDesk / TeamViewer ka code kabhi kisi anjaan ko mat dijiye, khaaskar 'bank / KYC / refund' wale call par: yahi sabse bada fraud hai."),
            S(id="time_sync", title="PC ka time sahi?", change="setting", check="Time theek karne ke baad?",
              how="Settings > Time & language > 'Set time automatically' on > Sync now. Galat time par VPN certificate fail hota hai."),
            S(id="reinstall", title="VPN app dobara", change="install", admin=True, check="Naye install ke baad?",
              how="Sirf office / VPN company ki batayi jagah se. Settings / profile IT wale se lijiye."),
        ]},
    "security": {
        "label": "Virus / ajeeb popup / phishing ka shak", "asset": "pc", "escalate": "it", "security": True,
        "words": ("virus", "malware", "ransomware", "hack", "hacked", "popup", "pop-up", "files encrypted", "files locked", "phishing", "fake mail",
                  "fraud mail", "suspicious", "antivirus", "defender", "ajeeb link", "link par click", "वायरस", "हैक"),
        "escalate_when": ["Files ke naam badal gaye / khul nahi rahi / 'ransom' note (ransomware): turant", "Kisi ne password daal diya / paise gaye",
                          "Antivirus 'threat' hata nahi paa raha"],
        "tell": ["Kya dikha (screenshot)", "Kis PC par, kab", "Kya click / download / bhara", "Network par aur PC hain?"],
        "steps": [
            S(id="disconnect", title="Turant net se hatao", check="Wi-Fi band / LAN cable nikali?",
              how="Shak ho to us PC ka Wi-Fi band kijiye / LAN cable nikaaliye (PC band mat kijiye, saboot rehta hai). Pen drive mat lagaiye."),
            S(id="dont_pay", title="Kuch mat bharo, mat do", check="Kisi ne password / OTP / paisa to nahi diya?",
              how="Popup par diya number mat milaiye, 'ransom' mat dijiye, remote app (AnyDesk) ka code mat dijiye. Paise gaye hon to turant 1930."),
            S(id="scan", title="Antivirus full scan", check="Scan ne kya bataya?",
              how="Windows Security > Virus & threat protection > Scan options > Full scan (ya office ka antivirus). Jo mila uska naam Hoola ko bataiye."),
            S(id="passwords", title="Doosre device se password badlo", change="account", check="Zaroori accounts ke password badle?",
              how="Agar link par password bhara tha: SAAF phone / doosre PC se us account (email, bank, GST, Tally) ka password khud badaliye aur 2-step on. Password Hoola ko nahi."),
            S(id="offline_scan", title="Microsoft Defender Offline scan", change="setting", admin=True, check="Offline scan ke baad saaf?",
              how="Windows Security > Scan options > 'Microsoft Defender Antivirus (offline scan)' > Scan now. PC restart hokar 15 minute scan karta hai: kaam save karke."),
        ]},
    "backup": {
        "label": "Backup / data bachana", "asset": "pc", "escalate": "it",
        "words": ("backup", "back up", "data loss", "file delete", "file mit", "pen drive", "hard disk", "external drive", "recover",
                  "data chala gaya", "restore", "बैकअप"),
        "escalate_when": ["Hard disk 'format karo' maang rahi / click-click awaaz (data recovery lab ka kaam: aur kuch mat likhiye)",
                          "Zaroori data mit gaya aur backup nahi"],
        "tell": ["Kya data (Tally / documents / photos)", "Kahan tha (PC / drive / folder)", "Aakhri backup kab"],
        "steps": [
            S(id="stop_writing", title="Usi drive par kuch mat likho", check="Drive par naya kuch save to nahi kiya?",
              how="File mit gayi ho to usi drive par naya kuch save / install mat kijiye: wapas milne ka mauka kam hota hai."),
            S(id="recycle", title="Recycle Bin / purana version", check="Wahan mili?",
              how="Recycle Bin dekhiye. Folder par right-click > 'Restore previous versions'. OneDrive / Google Drive mein 'Trash / Recycle bin' bhi."),
            S(id="what_to_backup", title="Kya bachana zaroori", check="List bani?",
              how="Tally data folder, Documents / Desktop, Outlook PST, GST / bank ki files, accounts ke Excel. Inki list Hoola ke asset note mein."),
            S(id="three_two_one", title="3-2-1 backup", check="Doosri copy alag jagah?",
              how="Kam se kam do copy: ek external drive / NAS par, ek office ke bahar (cloud ya ghar). External drive backup ke baad nikal kar rakhiye (ransomware usse bhi mita deta hai)."),
            S(id="schedule", title="Apne aap backup chalu", change="setting", check="Backup schedule bana?",
              how="Windows: Settings > Accounts > Windows backup, ya File History (Control Panel). Tally: roz shaam Data > Backup. Hafte mein ek baar restore karke dekhiye ki file khulti hai."),
        ]},
    "pc_power": {
        "label": "Computer chalu nahi hota / neeli screen", "asset": "pc", "escalate": "it",
        "words": ("chalu nahi", "start nahi", "on nahi", "boot", "blue screen", "bsod", "black screen", "beep sound", "restart loop",
                  "no display", "बंद हो गया", "चालू नहीं"),
        "escalate_when": ["Bilkul jaan nahi (light / pankha nahi) achhe socket se bhi", "Beep ki awaaz ke saath kuch nahi dikhta",
                          "Neeli screen baar baar (stop code likh lijiye)", "'No bootable device' / disk nahi mili"],
        "tell": ["PC / laptop model", "Lights / pankha / beep", "Screen par kya likha (stop code)", "Kuch naya laga / gira to nahi"],
        "steps": [
            S(id="power", title="Bijli / socket / button", check="Pankha / light chalu?",
              how="Doosra socket, UPS chalu? Laptop: charger lagakar 10 minute. Monitor ki apni bijli aur cable bhi."),
            S(id="hard_reset", title="Poori bijli nikaal kar", check="Iske baad chalu hua?",
              how="Bijli cable nikaliye, power button 15 second dabaiye, phir cable lagakar chalu. Laptop: charger hatakar power 30 second."),
            S(id="usb_out", title="Pen drive / naye device hatao", check="Hatane ke baad chalu?",
              how="Pen drive, external disk, printer ka USB nikaal kar chalu kijiye."),
            S(id="stop_code", title="Stop code likho", check="Neeli screen ka code likha?",
              how="Neeli screen par 'Stop code' (jaise CRITICAL_PROCESS_DIED) aur QR ki photo lijiye: technician isi se dhoondhta hai."),
            S(id="startup_repair", title="Startup Repair", change="reset", admin=True, careful=True, check="Repair ke baad?",
              how="Teen baar chalu hote hi band karne par 'Automatic Repair' aata hai > Advanced options > Startup Repair. 'Reset this PC' sirf aapki haan aur backup ke baad."),
        ]},
}

GENERIC = {"label": "Koi aur IT dikkat", "asset": "", "escalate": "it", "words": (),
           "escalate_when": ["Ghar ke upay se na ho", "Hardware toota / jalne ki gandh"],
           "tell": ["Device ka naam / model", "Error ka poora text / photo", "Kab se, kitne logon ko"],
           "steps": [
               S(id="error_text", title="Error ka text / photo", check="Photo / text mila?", how="Screen par jo likha hai uski photo ya poora text likhiye."),
               S(id="restart", title="Restart", check="Restart ke baad?", how="Program / device band karke dobara chalu kijiye."),
               S(id="scope", title="Sab par ya ek par?", check="Doosre PC / user par bhi?", how="Doosre PC / user par wahi kaam karke dekhiye."),
               S(id="recent_change", title="Haal mein kya badla?", check="Kuch naya install / update / gira?",
                 how="Haal mein koi naya program, update, cable, bijli jaana? Woh batana sabse kaam aata hai."),
           ]}

CHANGE_LABEL = {"setting": "System setting badalna", "install": "Install / update", "uninstall": "Program hatana", "reset": "Reset / repair",
                "account": "Account / password ka badlaav", "network": "Network setting", "firmware": "Firmware update", "other": "Badlaav"}
VENDOR_KINDS = ("amc", "it", "isp", "printer", "cctv", "tally_partner", "electrician", "software", "other")
VENDOR_LABEL = {"amc": "AMC wale", "it": "Computer technician", "isp": "Internet (ISP)", "printer": "Printer service",
                "cctv": "CCTV wale", "tally_partner": "Tally partner", "electrician": "Electrician", "software": "Software vendor", "other": "Vendor"}
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
