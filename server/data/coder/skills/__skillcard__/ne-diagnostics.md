---
name: ne-diagnostics
description: Diagnostics ladder - pc_status to PCAP, printed steps
---
GOAL: user bola "net down", "site nahi khul rahi", "call atak gayi"
- Hoola ka kaam guess nahi, LADDER chalana hai: shallow check pehle,
deep packet sabse aakhri me. Syllabus: PCAP/Scapy side ke tool
catalogs (capture/parse tools ka dher - tshark, tcpdump, scapy
family) aur awesome-RTC jaisa realtime-communications catalog; dono
generically padho, research base bante hain. Par asli lane hamesha
Hoola ke operator doors se khulti hai, catalog se nahi.

THE LADDER (har seedha sirf pichhle run ke printed output ke baad;
jump karna mana hai):
1. pc_status: machine ka haal - up hai? interface up? IP mila?
   CPU/mem/disk ka haal? Aadhe-se-zyada "network issues" yahin khatam:
   wifi off tha, DHCP nahi mila, disk full.
2. session_log: abhi-abhi kya hua - kaunsa process, kaunsa connect,
   kab fail hua. Recent truth hi kaam aata hai, purani yaad nahi.
3. browser_check: web lane ka sach - DNS chala? TLS bana? kaunsa
   status code? "site nahi khul rahi" ko error-level tak utaro, warna
   report adhoori hai.
4. noc / it_admin / devops doors: server-side view - routes, firewall
   rules, service health, logs. health_int se poora picture: kaunsa
   system kahan lal hai, bottleneck kahan. pc_read se local logs aur
   capture summaries padho - file khud se nahi, door se.
5. DEEP PACKET (PCAP/Scapy): SIRF lab me, prayog door pe. Apne hi
   server/PC pe capture; capture file tenant ke andar hi rahegi;
   timestamp, filter aur duration pehle likhoge, baad me safai hogi.

RUN RULES: ek run = ek command + ek printed output; output chat me
paste hai to hi agla step. "Ping sahi hai" mat bolo - output dikhao,
phir bolo. Narrow filter pehle (host/port), wide baad me - warna
capture bhaari aur bekaar.

RTC CATALOG: abhi ke liye RESEARCH-ONLY. Voice/video calls lane
aane par isi catalog se tools aur concepts uthenge; abhi koi RTC
experiment nahi. Jab calls aayein, ladder wahi se shuru hogi -
pc_status se, packet se nahi.

THE LAWS: infra badalna (route, firewall, service restart, capture
start) = pehle ask_approval, chup-chaap nahi; printed output hi
evidence hai, andaaza nahi; captures tenant ke andar hi rahenge;
sirf apne device/traffic ko chhoona, kisi aur ka kabhi nahi.

NEVER: capture bina bataye chalana ("capture on, is filter se, X
minute" - pehle batao); capture file tenant se bahar upload karna;
dusre ke device ya traffic pe sniff karna; ladder skip karke
"network down hi hoga" bolna; bina printed output ke agla step
lena; prod pe load ya experiment bina approved window ke.
