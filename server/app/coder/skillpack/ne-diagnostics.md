---
name: ne-diagnostics
description: Diagnostics ladder - pc_status to PCAP, printed steps
when_to_use: network, internet slow, wifi, wifi slow, net down, website not opening, connection problem, diagnose, ping, dns, latency, disconnect, connection drops
---
GOAL: the user says "the net is down", "the site will not open", "the
call froze" - Hoola's job is not to guess but to run the LADDER:
shallow checks first, deep packets last. Syllabus: the tool catalogs
on the PCAP / Scapy side (a pile of capture / parse tools - the
tshark, tcpdump, scapy family) and a realtime-communications catalog
like awesome-RTC; read both generically, they are the research base.
But the real lane always opens through Hoola's operator doors, not
from a catalog.

THE LADDER (each rung only after the printed output of the previous
run; jumping is not allowed):
1. pc_status: the machine's state - is it up? interface up? got an
   IP? CPU / memory / disk? More than half of "network issues" end
   here: wifi was off, no DHCP lease, disk full.
2. session_log: what just happened - which process, which
   connection, when it failed. Only the recent truth is useful, not
   an old memory.
3. browser_check: the truth about the web lane - did DNS resolve?
   did TLS come up? which status code? Bring "the site will not
   open" down to the error level, or the report is incomplete.
4. noc / it_admin / devops doors: the server-side view - routes,
   firewall rules, service health, logs. The whole picture from
   health_int: which system is red where, where the bottleneck is.
   Read local logs and capture summaries with pc_read - through the
   door, not the file directly.
5. DEEP PACKET (PCAP / Scapy): ONLY in the lab, through the prayog
   door. Capture on our own server / PC only; the capture file
   stays inside the tenant; write down the timestamp, filter and
   duration first, clean up afterwards.

RUN RULES: one run = one command + one printed output; the next
step only when the output is pasted in chat. Do not say "ping is
fine" - show the output, then say it. A narrow filter first (host /
port), wide later - otherwise the capture is heavy and useless.

RTC CATALOG: RESEARCH-ONLY for now. When the voice / video calls
lane arrives, tools and concepts will be taken from this catalog;
no RTC experiment today. When calls come, the ladder starts in the
same place - from pc_status, not from a packet.

THE LAWS: changing infra (a route, the firewall, a service restart,
starting a capture) = ask_approval first, never quietly; printed
output is the only evidence, not a guess; captures stay inside the
tenant; touch only our own device / traffic, never anyone else's.

NEVER: run a capture without saying so ("capture on, with this
filter, X minutes" - say it first); upload a capture file outside
the tenant; sniff someone else's device or traffic; skip the ladder
and say "the network must be down"; take the next step without
printed output; load or experiment on prod outside an approved
window.

ALSO ASKED AS (Hinglish asks this skill answers): internet baar baar
disconnect ho raha hai, net slow hai, wifi nahi chal raha, site nahi khul
rahi
