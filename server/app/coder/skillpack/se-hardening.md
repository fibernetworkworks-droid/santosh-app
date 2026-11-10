---
name: se-hardening
description: Server hardening - appsec checklist, blocked law codified
when_to_use: server security, secure my server, hardening, firewall, ssh, vulnerabilities, hacked, security checklist
---
GOAL: paragonie/awesome-appsec aur malware/persistence technique
lists (generically) syllabus hain - attack-surface catalogs se seekho
ki darwaze kahan hote hain, phir apne server ke darwaze band karo.
Yahan exploits nahi likhe jaate; aisi checklist likhi jaati hai jo
khud printed evidence ban jaaye.

CHECKLIST - har line printed output se verify hoti hai, andaaz se
nahi:
1. PORTS KAM: listening ports ki poori list nikaalo; har extra port
   band ya likhit justification ke saath. Sirf zaroori darwaze khule.
2. UPDATES: OS aur package versions printed karo; stale security
   patches sabse pehle - purana version khula taala hai.
3. SECRETS DISK PE NAHI: plaintext secrets config/env files me zero;
   secrets kisi skill file me bhi nahi; secret sirf runtime pe mile.
4. LOGS EVIDENCE: har hardening change session_log me entry ke saath
   - kya badla, kab, kyun. Bina log ke change hua hi nahi maano ge.
5. SANITY: browser_check se basic sanity - app up, expected page aa
   rahi hai, koi stray domain/console noise nahi.
6. DEFAULTS: default creds, default paths, sample configs - sab
   printed check karo; factory setting koi nahi bachega.
Har change ke saath printed diff: pehle ka output, baad ka output,
aur beech ka badlav - teeno saaf dikhen.

THE BLOCKED LAW (codified): BLOCKED_APPS - cmd/powershell/terminal/
regedit/diskpart opens REFUSED; BLOCKED_KEYS - win+r, win+x,
ctrl+shift+esc, win+l refused. Kyun? Kyunki malware persistence inhi
rides hai: shell spawn, autorun/registry keys, scheduled tasks,
disk-level chhedchhad. Ye law WEAKEN nahi hota, DOCUMENT hota hai -
audit report me likho ki ye doors band kyun hain aur kaunsi attack
family unpe sawaar hoti hai. Koi exception maange to ask_approval +
reason + time window, sab printed. Law ko ghumane ki koshish khud ek
finding hai aur wo log me jayegi.

AUDIT DOORS: cyber/it_admin/devops lanes se audit chalao - ports,
updates, secrets, logs, blocked-law status. Order har baar wahi:
current state printed → change → naya state printed → diff report.
Production ke against live test sirf batayi hui window me,
ask_approval ke baad; window ka start/end bhi printed. Har audit ka
anjaam ek seedha table hai: item, status, fix, proof line - table
se hi agla kaam nikalta hai, memory se nahi.

NEVER: blocked app ko "bas is baar" whitelist karna; secrets ko
skills/config files me likhna; inbound port bina approval khulwana;
checklist likh ke bhool jaana - printed re-check fixe din baad phir
se; production pe live test bina window bataye; bina printed output
ke "hardened hai" bolna.
