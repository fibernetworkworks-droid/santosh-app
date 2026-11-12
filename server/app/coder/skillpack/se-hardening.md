---
name: se-hardening
description: Server hardening - appsec checklist, blocked law codified
when_to_use: server security, secure my server, hardening, firewall, ssh, vulnerabilities, hacked, security checklist
---
GOAL: paragonie/awesome-appsec and the malware/persistence technique
lists (in general) are the syllabus - learn from attack-surface
catalogs where the doors are, then close the doors of your own server.
No exploits are written here; the aim is a checklist that itself
becomes printed evidence.

CHECKLIST - every line is verified from printed output, not from a
guess:
1. FEWER PORTS: pull the full list of listening ports; every extra port
   is closed or kept with a written justification. Only the necessary
   doors stay open.
2. UPDATES: print the OS and package versions; stale security patches
   first - an old version is an open lock.
3. NO SECRETS ON DISK: zero plaintext secrets in config/env files;
   no secrets in any skill file either; a secret is available only at
   runtime.
4. LOGS AS EVIDENCE: every hardening change goes in session_log with an
   entry - what changed, when, why. A change without a log is treated
   as not made.
5. SANITY: a basic sanity check with browser_check - the app is up, the
   expected page appears, no stray domain/console noise.
6. DEFAULTS: default creds, default paths, sample configs - check them
   all in print; no factory setting is spared.
With every change, a printed diff: the output before, the output after
and the change in between - all three clearly visible.

THE BLOCKED LAW (codified): BLOCKED_APPS - opening
cmd/powershell/terminal/regedit/diskpart is REFUSED; BLOCKED_KEYS -
win+r, win+x, ctrl+shift+esc, win+l are refused. Why? Because malware
persistence rides on exactly these: shell spawn, autorun/registry keys,
scheduled tasks, disk-level tampering. This law is not WEAKENED, it is
DOCUMENTED - write in the audit report why these doors are closed and
which attack family rides on them. If someone asks for an exception:
ask_approval + a reason + a time window, all printed. An attempt to get
around the law is itself a finding and goes into the log.

AUDIT DOORS: run the audit through the cyber/it_admin/devops lanes -
ports, updates, secrets, logs, blocked-law status. The order is always
the same: current state printed -> change -> new state printed -> diff
report. A live test against production only in a stated window, after
ask_approval; the window's start/end is printed too. Every audit ends
in one plain table: item, status, fix, proof line - the next job comes
from the table, not from memory.

NEVER: whitelist a blocked app "just this once"; write secrets in
skills/config files; open an inbound port without approval; write a
checklist and forget it - a printed re-check again after a few days; a
live test on production without stating the window; say "it is
hardened" without printed output.
