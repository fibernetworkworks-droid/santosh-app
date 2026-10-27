"""Cyber Suraksha Sahayak: alert parsing + grouping + scoring + her 'normal' rules (never for critical kinds), dedupe; email headers
(SPF / DKIM / DMARC, Reply-To, display-name and look-alike spoofing) on top of the helpdesk phishing check; links looked up never
opened, files only hashed; her domain posture (DNS / TLS / headers, deep checks only when verified); HIBP; CVE / KEV / CERT-In
matching with helpdesk assets; incident note with the helpdesk CERT-In clock + Word / PDF; block / wipe cards decided only by her
tap (Cloudflare API on tap, fingerprint for wipe); tools (actors, keys refused in chat); API; worker tick. All APIs faked."""
import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.cyber.models  # noqa: F401  (tables for the env fixture's init_db)
import app.helpdesk.models  # noqa: F401
from tests.test_life import conv_ctx

T = "default"
ZONE = "a" * 32

SSH_LOG = "\n".join(
    [f"Oct 23 02:{10 + i:02d}:01 tally-srv sshd[911]: Failed password for root from 45.155.205.12 port {40000 + i} ssh2" for i in range(12)]
    + ["Oct 23 02:30:44 tally-srv sshd[912]: Failed password for invalid user test from 45.155.205.12 port 41000 ssh2",
       "Oct 23 02:31:10 tally-srv sshd[913]: Accepted password for root from 45.155.205.12 port 41022 ssh2",
       "Oct 23 09:01:10 tally-srv sshd[914]: Accepted publickey for meghana from 49.36.10.5 port 51022 ssh2",
       "Oct 23 09:05:00 tally-srv fail2ban.actions[300]: NOTICE [sshd] Ban 185.220.101.4"]
    + [f"Oct 23 03:00:{i:02d} gw kernel: [UFW BLOCK] IN=eth0 OUT= SRC=103.21.4.7 DST=10.0.0.2 LEN=40 PROTO=TCP SPT=5555 DPT={20 + i}"
       for i in range(15)])

DEFENDER_CSV = """Detection time,Device name,User,Threat name,Severity,Action taken
2026-10-23 10:01,ACCOUNTS-PC,ramesh,Trojan:Win32/Wacatac.B!ml,Severe,Quarantined
2026-10-23 10:05,RECEPTION-PC,sunita,Ransom:Win32/LockBit.A,Severe,Failed
2026-10-23 10:07,BILLING-PC,anita,PUA:Win32/Presenoker,Low,Removed
"""

WORKSPACE_MAIL = """From: Google Workspace Alerts <google-workspace-alerts-noreply@google.com>
Subject: Alert: Email forwarding rule created for accounts@ainewtika.com
To: build@ainewtika.com

A new email forwarding rule was created by accounts@ainewtika.com forwarding to x9pay@protonmail.com.
"""

CLOUDFLARE_JSON = json.dumps([{"clientIP": "198.51.100.77", "action": "block", "ruleId": "wp-login-guard", "clientRequestPath": "/wp-login.php",
                               "datetime": "2026-10-23T11:00:00Z"} for _ in range(25)]
                             + [{"clientIP": "203.0.113.9", "action": "log", "ruleId": "sqli-100", "clientRequestPath": "/search?q=1' or 1=1",
                                 "datetime": "2026-10-23T11:05:00Z"}])

PHISH_RAW = """Return-Path: <bounce@mailer-x.ru>
Received: from mailer-x.ru (mailer-x.ru [91.200.1.2]) by mx.google.com
Authentication-Results: mx.google.com; spf=softfail smtp.mailfrom=mailer-x.ru; dkim=none; dmarc=fail (p=NONE) header.from=ainewtika.co
From: "Meghana Ingle (ainewtika.com)" <meghana@ainewtika.co>
Reply-To: meghana.ceo.urgent@gmail.com
Subject: Urgent payment today
Content-Type: text/plain

Please transfer Rs 2,40,000 to the new vendor account today, urgent. Details at https://ainevvtika.com/pay and do not call me.
"""

GOOD_RAW = """Return-Path: <noreply@ainewtika.com>
Received: from mail-sor-f41.google.com by mx.google.com
Authentication-Results: mx.google.com; spf=pass smtp.mailfrom=ainewtika.com; dkim=pass header.d=ainewtika.com; dmarc=pass header.from=ainewtika.com
From: Sandesh <sandesh@ainewtika.com>
Subject: Agenda
Content-Type: text/plain

Kal 11 baje meeting hai.
"""


class Fake:
    """One fake for every official API the module calls."""

    def __init__(self):
        self.calls: list[str] = []
        self.bad_urls = {"https://ainevvtika.com/pay"}
        self.cf_rules: dict[str, dict] = {}

    def __call__(self, req: httpx.Request) -> httpx.Response:
        u = req.url
        self.calls.append(f"{req.method} {u.host}{u.path}")
        if u.host == "webrisk.googleapis.com":
            uri = u.params.get("uri")
            return httpx.Response(200, json={"threat": {"threatTypes": ["SOCIAL_ENGINEERING"]}} if uri in self.bad_urls else {})
        if u.host == "www.virustotal.com":
            assert req.headers.get("x-apikey") == "vt-key-0123456789abcdef"
            if "/files/" in u.path:
                h = u.path.rsplit("/", 1)[-1]
                if h == EVIL:
                    return httpx.Response(200, json={"data": {"attributes": {"last_analysis_stats": {"malicious": 41, "suspicious": 1, "harmless": 0,
                                                                                                     "undetected": 20}, "meaningful_name": "invoice.exe",
                                                                             "popular_threat_classification": {"suggested_threat_label": "trojan.agenttesla"}}}})
                return httpx.Response(404, json={"error": {"code": "NotFoundError"}})
            return httpx.Response(404, json={})
        if u.host == "haveibeenpwned.com":
            if u.path.startswith("/api/v3/breacheddomain/"):
                assert req.headers.get("hibp-api-key") and "Hoola" in req.headers.get("user-agent", "")
                return httpx.Response(200, json={"accounts": ["Canva", "LinkedIn"], "meghana": ["Canva"]})
            if u.path.startswith("/api/v3/breachedaccount/"):
                return httpx.Response(200, json=[{"Name": "Canva"}]) if "accounts" in u.path else httpx.Response(404)
            if u.path.startswith("/api/v3/breach/"):
                name = u.path.rsplit("/", 1)[-1]
                return httpx.Response(200, json={"Title": name, "BreachDate": "2019-05-24", "DataClasses": ["Email addresses", "Passwords"]})
        if u.host == "services.nvd.nist.gov":
            kw = u.params.get("keywordSearch", "")
            if "tally" in kw.lower():
                return httpx.Response(200, json={"vulnerabilities": [{"cve": {"id": "CVE-2026-11111", "published": "2026-10-10T10:00:00.000",
                    "descriptions": [{"lang": "en", "value": "Tally Prime before 6.1 allows remote code execution via crafted company file."}],
                    "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8, "baseSeverity": "CRITICAL"}}]}}},
                    {"cve": {"id": "CVE-2026-22222", "published": "2026-10-11T10:00:00.000",
                             "descriptions": [{"lang": "en", "value": "Some unrelated product mentions tallying votes."}], "metrics": {}}}]})
            return httpx.Response(200, json={"vulnerabilities": []})
        if u.host == "www.cisa.gov":
            return httpx.Response(200, json={"vulnerabilities": [{"cveID": "CVE-2026-33333", "vendorProject": "TP-Link", "product": "Archer C6",
                                                                  "vulnerabilityName": "TP-Link Archer C6 Command Injection", "dateAdded": "2026-10-01",
                                                                  "shortDescription": "OS command injection.", "requiredAction": "Apply updates."}]})
        if u.host == "certin.example":
            return httpx.Response(200, text="""<rss><channel><item><title>Multiple vulnerabilities in TP-Link Archer routers</title>
                <link>https://www.cert-in.org.in/x</link><description>TP-Link Archer C6 ...</description></item></channel></rss>""")
        if u.host == "api.cloudflare.com":
            assert req.headers["authorization"] == "Bearer cf-token-0123456789abcdefghij"
            if u.path == "/client/v4/user/tokens/verify":
                return httpx.Response(200, json={"success": True, "result": {"status": "active"}})
            if req.method == "POST" and u.path.endswith("/firewall/access_rules/rules"):
                body = json.loads(req.content)
                rid = f"r{len(self.cf_rules) + 1}"
                self.cf_rules[rid] = body
                return httpx.Response(200, json={"success": True, "result": {"id": rid, "mode": body["mode"]}})
            if req.method == "DELETE":
                self.cf_rules.pop(u.path.rsplit("/", 1)[-1], None)
                return httpx.Response(200, json={"success": True, "result": {"id": "x"}})
        return httpx.Response(404, json={})


EVIL = "e" * 64


@pytest.fixture
def cy(env, monkeypatch):
    from app.cyber import intel as I
    from app.cyber import service as S
    from app.helpdesk import service as HS
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(HS, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    fake = Fake()
    I.set_transport(httpx.MockTransport(fake))
    monkeypatch.setenv("CYBER_CERTIN_FEED", "https://certin.example/rss")
    S.EVENTS, S.FAKE = events, fake
    yield S
    I.set_transport(None)


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_parse_correlate_score_dedupe_teach(cy):
    from app.cyber import rules as R
    S = cy
    S.save_settings(T, own_ips=["49.36.10.5"], crown_hosts=["tally-srv"])
    out = S.intake(T, SSH_LOG, source="server")
    by: dict = {}
    for a in sorted(out["matters"] + out["watch"], key=lambda a: a["score"]):
        by[a["kind"]] = a
    assert "login_after_fail" in by and by["login_after_fail"]["score"] >= 90 and by["login_after_fail"]["never_mute"]
    assert "45.155.205.12" in by["login_after_fail"]["title"] and any("admin" in w for w in by["login_after_fail"]["why"])
    assert "brute_force" in by and by["brute_force"]["level"] == "matters"
    assert out["matters"][0]["kind"] == "login_after_fail"                       # worst first
    assert out["noise"] >= 2                                                     # port scan + her own login + fail2ban ban
    assert all(a["kind"] != "port_scan" for a in out["matters"])
    assert "Zaroori" in out["say"] and kinds(S)[-1] == "cyber_alerts"
    noise = [a for a in S.alerts(T, "noise")]
    assert any(a["kind"] == "port_scan" for a in noise) and any(a["kind"] == "login_ok" and a["ip"] == "49.36.10.5" for a in noise)
    # the same log again = counted, not repeated
    n0 = len(S.alerts(T, status=""))
    again = S.intake(T, SSH_LOG, source="server")
    assert again["new"] == 0 and again["bumped"] >= 3 and len(S.alerts(T, status="")) == n0
    # Defender CSV: quarantined = low, ransomware failed = top
    d = S.intake(T, DEFENDER_CSV, source="antivirus")
    ks = {a["kind"]: a for a in d["matters"]}
    assert "ransomware" in ks and ks["ransomware"]["host"] == "RECEPTION-PC" and ks["ransomware"]["score"] >= 95
    assert R.parse(DEFENDER_CSV)["format"] == "csv"
    # Workspace alert mail + Cloudflare JSON
    w = S.intake(T, WORKSPACE_MAIL)
    assert w["matters"][0]["kind"] == "forwarding_rule" and w["matters"][0]["source"] == "workspace"
    c = S.intake(T, CLOUDFLARE_JSON, source="waf")
    ck = {a["kind"] for a in c["matters"] + c["watch"]}
    assert "brute_force" in ck and "waf_bypass" in ck
    # her rule: a watch-level alert she says is normal becomes noise next time; a NEVER_MUTE one stays visible
    bypass = next(a for a in c["matters"] + c["watch"] if a["kind"] == "waf_bypass")
    with pytest.raises(S.CyberError):
        S.teach(T, bypass["number"], "pentest wala", actor="staff:x")
    t = S.teach(T, bypass["number"], "hamara apna security test")
    assert t["scope"] == "ip" and "Seekh liya" in t["say"]
    S.set_alert(T, bypass["id"], "open")
    from app.cyber.models import CyberAlert
    from app.db import session
    with session() as s:                                     # a later week: the old one is closed, a fresh one arrives
        s.get(CyberAlert, bypass["id"]).status = "dismissed"
    c2 = S.intake(T, CLOUDFLARE_JSON, source="waf")
    nb = next(a for a in S.alerts(T, status="") if a["kind"] == "waf_bypass" and a["id"] != bypass["id"])
    assert nb["level"] == "noise" and nb["known_benign"] and "hamara apna security test" in " ".join(nb["why"])
    assert all(a["kind"] != "waf_bypass" for a in c2["matters"])
    rf = S.teach(T, w["matters"][0]["number"], "maine banaya tha")
    assert "kabhi chhupaya nahi" in rf["say"]
    assert S.get_alert(T, w["matters"][0]["id"])["level"] == "matters"
    # secrets in pasted logs are masked
    m = S.intake(T, "Oct 23 10:00:00 web app[1]: login failed for admin password=Hunter2xyz from 8.8.4.4")
    assert "Hunter2xyz" not in json.dumps(S.alerts(T, status="")) and "Hunter2xyz" not in json.dumps(m)


def test_email_link_file_checks(cy):
    S = cy
    S.save_settings(T, vip_names=["Meghana"], work_emails=["build@ainewtika.com"])
    S.add_domain(T, "ainewtika.com")
    with pytest.raises(S.CyberError):
        S.set_key(T, "webrisk", "short")
    S.set_key(T, "webrisk", "AIzaFakeWebRiskKey0123456789")
    S.set_key(T, "virustotal", "vt-key-0123456789abcdef")
    r = S.check_email(T, PHISH_RAW)
    ids = {f["id"] for f in r["flags"]}
    assert r["verdict"] == "likely_phish"
    assert {"dmarc_fail", "spf_soft", "reply_to", "lookalike_own", "vip_spoof"} <= ids, ids
    assert any(i.startswith("reputation_") for i in ids) and any(i.startswith("lookalike_link_") for i in ids)
    assert r["auth"] == {"spf": "softfail", "dkim": "none", "dmarc": "fail"} and r["reply_to"] == "meghana.ceo.urgent@gmail.com"
    assert "helpdesk" not in r and kinds(S)[-1] == "cyber_check"
    assert not any("GET ainevvtika.com" in c for c in S.FAKE.calls)                 # the link itself was never opened
    ok = S.check_email(T, GOOD_RAW)
    assert ok["verdict"] == "unclear" and not [f for f in ok["flags"] if f["level"] == "bad"]
    # she clicked: the helpdesk incident (CERT-In clock) is reused, not rebuilt
    from app.helpdesk import service as HS
    HS.save_settings(T, office_name="Newtika", entity="company")
    rc = S.check_email(T, PHISH_RAW, clicked=True)
    assert rc["helpdesk"]["cert_in"]["applies"] is True and rc["helpdesk"]["incident"]["report_due"]
    assert "helpdesk_alert" in kinds(S)
    # links: looked up only
    lk = S.check_link(T, ["https://ainevvtika.com/pay", "https://www.ainewtika.com/"])
    assert lk["verdict"] == "malicious" and lk["reputation"]["provider"].startswith("webrisk")
    clean = S.check_link(T, ["https://www.ainewtika.com/about"])
    assert clean["verdict"] == "clean"
    # files: hash only; the bytes are never sent anywhere
    fr = S.check_file(T, sha256=EVIL)
    assert fr["verdict"] == "malicious" and fr["virustotal"]["label"] == "trojan.agenttesla" and fr["virustotal"]["malicious"] == 41
    data = b"MZ\x90\x00 pretend program bytes"
    fr2 = S.check_file(T, data=data, name="bill.pdf")
    assert fr2["sha256"] and "upload nahi" in fr2["say"]
    assert not any(c.startswith("POST www.virustotal.com") for c in S.FAKE.calls)
    assert len(S.checks(T)) == 7 and len(S.checks(T, "file")) == 2


def test_domain_posture_breach(cy, monkeypatch):
    S = cy
    dns = {("ainewtika.com", "TXT"): ["v=spf1 include:_spf.google.com +all", "google-site-verification=x"],
           ("ainewtika.com", "MX"): ["1 smtp.google.com"], ("_dmarc.ainewtika.com", "TXT"): ["v=DMARC1; p=none"],
           ("google._domainkey.ainewtika.com", "TXT"): ["v=DKIM1; k=rsa; p=MIIB"], ("ainewtika.com", "CAA"): []}
    monkeypatch.setattr(S, "_dns", lambda name, t: dns.get((name, t), []))
    monkeypatch.setattr(S, "_tls", lambda host: {"days_left": 9, "host_ok": True, "not_after": "2026-11-01", "issuer": "Let's Encrypt"})
    fetched = []

    def fetch(url, n=65536):
        fetched.append(url)
        if url.endswith("/.git/HEAD"):
            return 200, {}, b"ref: refs/heads/main\n"
        if url.endswith("/.env"):
            return 404, {}, b""
        if url.endswith("/"):
            return 200, {"server": "nginx/1.18.0", "content-type": "text/html"}, b"<html>"
        return 404, {}, b""
    monkeypatch.setattr(S, "_fetch", fetch)
    a = S.add_domain(T, "https://www.AiNewtika.com/x")
    assert a["domain"]["domain"] == "ainewtika.com" and not a["domain"]["verified"] and "_hoola-cyber.ainewtika.com" in a["say"]
    p = S.posture(T, "ainewtika.com")
    ids = {f["id"] for f in p["domain"]["flags"]}
    assert {"spf_open", "dmarc_none", "dmarc_no_rua", "caa_missing", "tls_soon", "hsts", "version_server", "not_verified"} <= ids, ids
    assert "dkim_unknown" not in ids and p["domain"]["dns"]["dkim"] == ["google"]
    assert not any(u.endswith("/.git/HEAD") for u in fetched)                        # no deep look before she proves it
    assert p["domain"]["score"] < 70 and kinds(S)[-1] == "cyber_posture"
    v0 = S.verify_domain(T, "ainewtika.com")
    assert not v0["domain"]["verified"]
    tok = v0["domain"]["token"]
    dns[("_hoola-cyber.ainewtika.com", "TXT")] = [f"hoola-cyber-verify={tok}"]
    assert S.verify_domain(T, "ainewtika.com")["domain"]["verified"]
    p2 = S.posture(T, "ainewtika.com")
    assert "exposed_.git_HEAD" in {f["id"] for f in p2["domain"]["flags"]}
    with pytest.raises(S.CyberError):
        S.breach(T, "ainewtika.com")                                                 # no key yet
    S.set_key(T, "hibp", "0123456789abcdef0123456789abcdef")
    b = S.breach(T, "ainewtika.com")
    assert len(b["rows"]) == 2 and b["rows"][0]["email"].startswith("ac***") and "password bhi leak" in b["say"]
    S.save_settings(T, work_emails=["accounts@ainewtika.com", "sandesh@ainewtika.com"])
    b2 = S.breach(T)
    assert [r["email"] for r in b2["rows"]] == ["ac***s@ainewtika.com"]


def test_advisories_from_helpdesk_assets(cy):
    S = cy
    from app.helpdesk import service as HS
    HS.save_asset(T, name="Office router", kind="router", brand="TP-Link", model="Archer C6")
    HS.save_asset(T, name="Accounts PC", kind="pc", os="Windows 10 Pro")
    sy = S.sync_assets(T)
    assert sy["added"] == 2 and {w["product"] for w in sy["software"]} >= {"Archer C6", "Windows 10"}
    S.add_software(T, "Tally Prime", "tally solutions", "5.0", where="Accounts PC")
    with pytest.raises(S.CyberError):
        S.add_software(T, "x", cpe="bad")
    r = S.refresh_advisories(T)
    refs = {a["ref"] for a in S.advisories(T)}
    assert "CVE-2026-33333" in refs and "CVE-2026-11111" in refs and "CVE-2026-22222" not in refs   # unrelated 'tallying' dropped
    assert any(a["source"] == "certin" for a in S.advisories(T))
    kev = next(a for a in S.advisories(T) if a["ref"] == "CVE-2026-33333")
    assert kev["exploited"] and "hamle ho rahe" in kev["say"] and kev["where"] == "Office router"
    assert r["urgent"] and kinds(S)[-1] == "cyber_advisory"
    again = S.refresh_advisories(T)
    assert again["new"] == 0
    S.mark_advisory(T, kev["id"], "patched")
    assert "CVE-2026-33333" not in {a["ref"] for a in S.advisories(T)}


def test_incident_note_and_cert_in(cy):
    S = cy
    from app.helpdesk import service as HS
    HS.save_settings(T, office_name="Newtika Pvt Ltd", entity="company", contact_name="Meghana")
    S.save_settings(T, crown_hosts=["tally-srv"])
    out = S.intake(T, SSH_LOG, source="server")
    laf = next(a for a in out["matters"] if a["kind"] == "login_after_fail")
    inc = S.new_incident(T, alert_ids=[laf["number"]], systems="tally-srv")
    v = inc["incident"]
    assert v["number"] == "IN-0001" and v["kind"] == "account" and v["helpdesk_incident"]
    assert v["cert_in"]["applies"] is True and v["cert_in_due"] and "6 ghante" in inc["say"]
    assert S.get_alert(T, laf["id"])["status"] == "incident"
    assert any("Kai galat koshishon" in t["what"] for t in v["timeline"])
    S.incident_add(T, v["number"], "Root ka password badla, SSH par key-login lagaya", "2026-10-23T03:10")
    S.incident_update(T, v["number"], impact="Tally server par 40 minute tak kisi aur ka login", done="Password badla", personal_data=True)
    v2 = S.get_incident(T, v["id"])
    assert v2["dpdp"] and "72" in v2["dpdp"]["say"] and v2["timeline"][-1]["at"] >= v2["timeline"][0]["at"]
    title, text = S.note_text(T, v["id"])
    assert "Newtika Pvt Ltd" in text and "## CERT-In" in text and "Root ka password badla" in text and "## Seekh" in text
    from app import chatfiles
    stored = []
    import app.chatfiles as cf
    orig = cf.store

    def store(tenant, name, data, ct=""):
        stored.append((name, data[:4]))
        return {"file_id": f"f{len(stored)}", "name": name}
    cf.store = store
    try:
        nf = S.note_files(T, v["id"])
    finally:
        cf.store = orig
    assert [n for n, _ in stored] == ["IN-0001_incident_note.docx", "IN-0001_incident_note.pdf"] and stored[1][1] == b"%PDF"
    assert "pc_file" in kinds(S) and nf["files"]
    with pytest.raises(S.CyberError):
        S.incident_close(T, v["id"])                                                # lessons first
    with pytest.raises(S.CyberError):
        S.incident_close(T, v["id"], "SSH key only", actor="staff:x")
    assert S.incident_close(T, v["id"], "SSH sirf key se, fail2ban on")["incident"]["status"] == "closed"
    _ = chatfiles


def test_containment_only_on_her_tap(cy):
    S = cy
    S.save_settings(T, own_ips=["49.36.10.5"])
    with pytest.raises(S.CyberError):
        S.request_action(T, "block_ip", "10.0.0.5")                                  # private
    with pytest.raises(S.CyberError):
        S.request_action(T, "block_ip", "49.36.10.5")                                # her own
    with pytest.raises(S.CyberError):
        S.request_action(T, "block_ip", "45.155.0.0/16")                             # too wide
    # without a Cloudflare key: steps only
    st = S.request_action(T, "block_ip", "45.155.205.12", "brute force")
    a = st["action"]
    assert a["via"] == "steps" and a["status"] == "waiting" and st["needs_tap"] and kinds(S)[-1] == "cyber_action"
    assert S.request_action(T, "block_ip", "45.155.205.12")["action"]["id"] == a["id"]        # same card, not twice
    with pytest.raises(S.CyberError):
        S.decide_action(T, a["id"], True, a["hash"])                                  # not a tap
    with pytest.raises(S.CyberError):
        S.decide_action(T, a["id"], True, "wrong", by_tap=True)
    with pytest.raises(S.CyberError):
        S.action_done(T, a["id"])                                                     # before her haan
    d = S.decide_action(T, a["id"], True, a["hash"], by_tap=True)
    assert d["action"]["status"] == "approved" and "console" in d["say"]
    assert S.action_done(T, a["id"], True, "Cloudflare mein kiya")["action"]["status"] == "done"
    S.del_key(T, "cloudflare")
    # with her Cloudflare token + zone: the API runs only on her tap
    with pytest.raises(S.CyberError):
        S.set_key(T, "cloudflare", "cf-token-0123456789abcdefghij", "nozone")
    S.set_key(T, "cloudflare", "cf-token-0123456789abcdefghij", ZONE)
    c = S.request_action(T, "block_ip", "185.220.101.4", "wp-login hamla")["action"]
    assert c["via"] == "cloudflare" and not S.FAKE.cf_rules
    no = S.request_action(T, "block_ip", "91.200.1.2")["action"]
    S.decide_action(T, no["id"], False, no["hash"], by_tap=True)
    assert not S.FAKE.cf_rules
    ok = S.decide_action(T, c["id"], True, c["hash"], by_tap=True)
    assert ok["action"]["status"] == "done" and ok["action"]["result"]["rule_id"] == "r1"
    assert S.FAKE.cf_rules["r1"]["configuration"] == {"target": "ip", "value": "185.220.101.4"} and S.FAKE.cf_rules["r1"]["mode"] == "block"
    un = S.request_action(T, "unblock_ip", "185.220.101.4")["action"]
    S.decide_action(T, un["id"], True, un["hash"], by_tap=True)
    assert not S.FAKE.cf_rules and any(x["status"] == "undone" for x in S.actions(T))
    # wipe: card + fingerprint once a phone key is active
    w = S.request_action(T, "wipe_device", "Ramesh ka Android (kho gaya)")["action"]
    assert w["wipe"] and "HAMESHA" in w["risk"]
    from app import approvekey as ak
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    pub = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    ak.register(T, "phone-1", pub, "OnePlus")
    assert ak.active_on(T) and S.action_needs_fingerprint(T, w["id"])
    with pytest.raises(S.CyberError, match="fingerprint_needed"):
        S.decide_action(T, w["id"], True, w["hash"], by_tap=True)
    ch = S.action_challenge(T, w["id"])
    sig = base64.b64encode(key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))).decode()
    with pytest.raises(S.CyberError, match="fingerprint_invalid"):
        S.decide_action(T, w["id"], True, w["hash"], proof={"challenge_id": ch["challenge_id"], "device_id": "phone-1", "signature": "AAAA"}, by_tap=True)
    ch = S.action_challenge(T, w["id"])
    sig = base64.b64encode(key.sign(ch["message"].encode(), ec.ECDSA(hashes.SHA256()))).decode()
    r = S.decide_action(T, w["id"], True, w["hash"], proof={"challenge_id": ch["challenge_id"], "device_id": "phone-1", "signature": sig}, by_tap=True)
    assert r["action"]["status"] == "approved" and any("Wipe" in x for x in r["action"]["steps"])
    # old cards go stale
    old = S.request_action(T, "disable_user", "accounts@ainewtika.com")["action"]
    S.tick(datetime.now(timezone.utc) + timedelta(hours=25), net=False)
    assert next(x for x in S.actions(T) if x["id"] == old["id"])["status"] == "stale"


def test_tools_actors_and_keys(cy):
    from app.agent import cyber_tools as CT
    from app.agent.tools import Ctx, ToolError
    _ = cy
    ctx = conv_ctx()
    out = asyncio.run(CT.cyber(ctx, "intake", text=SSH_LOG, source="server"))
    assert out["matters"]
    with pytest.raises(ToolError):
        asyncio.run(CT.cyber(Ctx(T, ctx.conversation_id, "customer:wa:9876543210"), "intake", text=SSH_LOG))
    staff = Ctx(T, ctx.conversation_id, "staff:abc")
    with pytest.raises(ToolError):
        asyncio.run(CT.cyber(staff, "teach", alert=out["matters"][0]["number"], reason="x"))
    with pytest.raises(ToolError):
        asyncio.run(CT.cyber(staff, "settings", own_ips=["1.1.1.1"]))
    card = asyncio.run(CT.cyber(staff, "contain", kind="block_ip", target="45.155.205.12", reason="brute force"))
    assert card["needs_tap"] and card["action"]["status"] == "waiting"            # staff may raise a card, never decide
    assert not hasattr(CT, "approve") and "decide" not in json.dumps(CT.CYBER_TOOLS[0]["input_schema"]["properties"]["action"]["enum"])
    with pytest.raises(ToolError, match="Keys"):
        asyncio.run(CT.cyber(ctx, "settings", vip_names=["api_key = AIzaSyA123456789012345678901234567"]))
    day = asyncio.run(CT.cyber_dekho(ctx, "day"))
    assert day["waiting"] and "Suraksha" in day["say"]
    keys = asyncio.run(CT.cyber_dekho(ctx, "keys"))
    assert set(keys["keys"]) >= {"webrisk", "virustotal", "hibp", "cloudflare"} and "token" not in json.dumps(keys).lower().replace("token +", "")
    assert asyncio.run(CT.cyber_dekho(ctx, "never"))["never"]
    assert set(CT.CYBER_HANDLERS) == {t["name"] for t in CT.CYBER_TOOLS} == set(CT.CYBER_LABELS)


def test_api_and_morning(cy, monkeypatch):
    from app.cyber.api import make_router
    S = cy
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    r = c.post("/api/cyber/intake/file", files={"file": ("defender.csv", DEFENDER_CSV.encode(), "text/csv")}, data={"source": "antivirus"})
    assert r.status_code == 200 and r.json()["matters"][0]["kind"] == "ransomware"
    assert c.put("/api/cyber/keys/virustotal", json={"token": "vt-key-0123456789abcdef"}).json()["ok"]
    assert "vt-key" not in json.dumps(c.get("/api/cyber").json())
    f = c.post("/api/cyber/check/file", files={"file": ("x.bin", b"hello world", "application/octet-stream")})
    assert f.status_code == 200 and f.json()["sha256"].startswith("b94d27b9")
    act = c.post("/api/cyber/actions", json={"kind": "isolate_pc", "target": "RECEPTION-PC", "reason": "ransomware"}).json()["action"]
    assert c.post(f"/api/cyber/actions/{act['id']}/decide", json={}).status_code == 400
    assert c.post(f"/api/cyber/actions/{act['id']}/decide", json={"yes": True, "hash": "x"}).status_code == 400
    ok = c.post(f"/api/cyber/actions/{act['id']}/decide", json={"yes": True, "hash": act["hash"]})
    assert ok.status_code == 200 and ok.json()["action"]["status"] == "approved"
    inc = c.post("/api/cyber/incidents", json={"title": "Ransomware on reception", "kind": "ransomware", "clock": False}).json()["incident"]
    assert c.post(f"/api/cyber/incidents/{inc['id']}/close", json={}).status_code == 400
    assert c.get("/api/cyber/incidents").json()["incidents"][0]["number"] == inc["number"]
    # morning note at her time, once
    S.save_settings(T, morning_time="09:15")
    from zoneinfo import ZoneInfo
    at = datetime(2026, 10, 24, 9, 20, tzinfo=ZoneInfo("Asia/Kolkata"))
    S.EVENTS.clear()
    assert S.tick(at, net=False)["morning"] == 1 and kinds(S) == ["cyber_day"]
    assert S.tick(at + timedelta(minutes=5), net=False)["morning"] == 0
