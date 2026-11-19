---
name: se-hardening
description: Server hardening - appsec checklist, blocked law codified
when_to_use: server security, secure my server, hardening, firewall, ssh, vulnerabilities, hacked, security checklist
---
GOAL: paragonie/awesome-appsec and the malware / persistence technique
lists (generically) are the syllabus - learn from the attack-surface
catalogs where the doors are, then close the doors of our own server.
No exploits are written here; what is written is a checklist that
becomes printed evidence by itself.

CHECKLIST - every line is verified from printed output, not from a
guess:
1. FEW PORTS: get the full list of listening ports; every extra port
   is closed or carries a written justification. Only the needed
   doors stay open.
2. UPDATES: print the OS and package versions; stale security
   patches first - an old version is an open lock.
3. NO SECRETS ON DISK: zero plaintext secrets in config / env files;
   no secrets in any skill file either; a secret is available only
   at runtime.
4. LOGS AS EVIDENCE: every hardening change with an entry in
   session_log - what changed, when, why. Without a log entry the
   change is treated as not done.
5. SANITY: a basic sanity check with browser_check - the app is up,
   the expected page comes, no stray domain / console noise.
6. DEFAULTS: default credentials, default paths, sample configs -
   check them all in print; no factory setting survives.
A printed diff with every change: the output before, the output
after, and the change in between - all three clearly visible.

THE BLOCKED LAW (codified): BLOCKED_APPS - opening cmd / powershell /
terminal / regedit / diskpart is REFUSED; BLOCKED_KEYS - win+r,
win+x, ctrl+shift+esc, win+l are refused. Why? Because malware
persistence rides exactly these: shell spawn, autorun / registry
keys, scheduled tasks, disk-level tampering. This law is not
WEAKENED, it is DOCUMENTED - write in the audit report why these
doors are closed and which attack family rides on them. If someone
asks for an exception: ask_approval + a reason + a time window, all
printed. An attempt to get around the law is itself a finding and it
goes into the log.

AUDIT DOORS: run the audit through the cyber / it_admin / devops
lanes - ports, updates, secrets, logs, blocked-law status. The same
order every time: current state printed → change → new state printed
→ diff report. A live test against production only in an announced
window, after ask_approval; the window's start / end is printed too.
Every audit ends in one plain table: item, status, fix, proof line -
the next job comes from the table, not from memory.

NEVER: whitelist a blocked app "just this once"; write secrets into
skills / config files; open an inbound port without approval; write
the checklist and forget it - a printed re-check again after a fixed
number of days; a live test on production without announcing the
window; say "it is hardened" without printed output.

ALSO ASKED AS (Hinglish asks this skill answers): server pe ssh secure kaise
karu, kisi ne hack karne ki koshish ki, server ki security check karo
