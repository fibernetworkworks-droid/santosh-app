"""TLS certificates checked from what she pastes: one PEM certificate, a chain (leaf first, then intermediates), or `openssl s_client
-showcerts` output. Each certificate: who it is for, who issued it, the dates and days left, the key (RSA under 2048 bits, small
curves), the signature hash (SHA-1, MD5), whether it is a CA, self-signed. The chain: in order (each issued by the next), the leaf's
names covering the host names she gives (wildcards one label deep), expired or not yet valid, expiring within her warning days, a
leaf valid longer than the 398 days browsers accept. Only public certificates - a private key pasted here is refused."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from .common import SecInputError, day, finder, finish


class CertError(SecInputError):
    pass


PEM = re.compile(r"-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----", re.S)


def _name(n) -> str:
    from cryptography.x509.oid import NameOID
    for oid in (NameOID.COMMON_NAME, NameOID.ORGANIZATION_NAME):
        v = n.get_attributes_for_oid(oid)
        if v:
            return str(v[0].value)
    return n.rfc4514_string()[:120] or "(no name)"


def _match(host: str, names: list[str]) -> bool:
    h = host.lower().rstrip(".")
    for n in names:
        n = n.lower().rstrip(".")
        if n == h:
            return True
        if n.startswith("*.") and "." in h and h.split(".", 1)[1] == n[2:] and h.split(".", 1)[0]:
            return True
    return False


def analyse(text: str, hosts: str = "", warn_days: float = 30, today: Any = None) -> dict[str, Any]:
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa
    t = str(text or "")
    if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", t):
        raise CertError("That holds a private key - never paste keys. Paste only the certificates.")
    blocks = PEM.findall(t)
    if not blocks:
        raise CertError("Paste certificates in PEM form (-----BEGIN CERTIFICATE-----), or `openssl s_client -connect host:443 -showcerts` output.")
    td = day(today) if today else date.today()
    now = datetime(td.year, td.month, td.day, tzinfo=timezone.utc)
    issues, add = finder()
    certs = []
    for i, b in enumerate(blocks):
        try:
            c = x509.load_pem_x509_certificate(b.encode())
        except ValueError as e:
            raise CertError(f"Certificate {i + 1} could not be read: {e}")
        nb, na = c.not_valid_before_utc, c.not_valid_after_utc
        pk = c.public_key()
        if isinstance(pk, rsa.RSAPublicKey):
            key = f"RSA {pk.key_size}"
            weak = pk.key_size < 2048
        elif isinstance(pk, ec.EllipticCurvePublicKey):
            key = f"EC {pk.curve.name}"
            weak = pk.curve.key_size < 256
        elif isinstance(pk, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
            key, weak = ("Ed25519" if isinstance(pk, ed25519.Ed25519PublicKey) else "Ed448"), False
        elif isinstance(pk, dsa.DSAPublicKey):
            key, weak = f"DSA {pk.key_size}", True
        else:
            key, weak = type(pk).__name__, False
        try:
            h = c.signature_hash_algorithm.name if c.signature_hash_algorithm else "none"
        except Exception:   # noqa: BLE001
            h = "unknown"
        try:
            san = [str(x) for x in c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)]
            ips = [str(x) for x in c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)]
        except x509.ExtensionNotFound:
            san, ips = [], []
        try:
            ca = c.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
        except x509.ExtensionNotFound:
            ca = False
        certs.append({"i": i, "subject": _name(c.subject), "issuer": _name(c.issuer), "subject_full": c.subject.rfc4514_string()[:240],
                      "issuer_full": c.issuer.rfc4514_string()[:240], "not_before": nb.date().isoformat(), "not_after": na.date().isoformat(),
                      "days_left": (na - now).days, "lifetime": (na - nb).days, "key": key, "weak_key": weak, "hash": h, "san": san[:100], "ips": ips[:20], "ca": ca,
                      "self_signed": c.subject == c.issuer, "serial": format(c.serial_number, "x")[:40], "_s": c.subject, "_i": c.issuer})
    leaf = certs[0]
    for c in certs:
        role = "leaf" if c["i"] == 0 else "intermediate" if not c["self_signed"] else "root"
        c["role"] = role
        if c["days_left"] < 0:
            add("bad", "Expired", f"{c['subject']} expired on {c['not_after']}.", "Renew it.", c["subject"])
        elif c["days_left"] <= warn_days:
            add("warn", "Expires soon", f"{c['subject']} expires in {c['days_left']} day(s), on {c['not_after']}.", "Renew it now (or check the automatic renewal).", c["subject"])
        if c["not_before"] > td.isoformat():
            add("bad", "Not yet valid", f"{c['subject']} is only valid from {c['not_before']}.", "Check the clock that issued it.", c["subject"])
        if c["weak_key"]:
            add("bad", "Weak key", f"{c['subject']} uses {c['key']}.", "Reissue with RSA 2048+ or ECDSA P-256+.", c["subject"])
        if c["hash"] in ("sha1", "md5") and role != "root":
            add("bad", "Weak signature", f"{c['subject']} is signed with {c['hash'].upper()} - browsers reject it.", "Reissue signed with SHA-256.", c["subject"])
    if leaf["ca"]:
        add("warn", "Order", "The first certificate is a CA - the server's own certificate should come first.", "Send the leaf first, then the intermediates.")
    if not leaf["ca"] and leaf["lifetime"] > 398:
        add("warn", "Too long", f"The leaf is valid for {leaf['lifetime']} days - publicly trusted certificates are limited to 398.", "Browsers reject it if it comes from a public CA.")
    if leaf["self_signed"] and len(certs) == 1:
        add("warn", "Self-signed", "The certificate signs itself - browsers will not trust it.", "Use one from a public CA (or your internal CA, trusted on every client).")
    order_ok = True
    for a, b in zip(certs, certs[1:]):
        if a["_i"] != b["_s"]:
            order_ok = False
            add("warn", "Chain order", f"{a['subject']} was not issued by the next one ({b['subject']}).", "Order the chain leaf -> intermediate -> (root, usually left out).")
    if order_ok and not certs[-1]["self_signed"] and len(certs) == 1 and not leaf["self_signed"]:
        add("info", "Intermediates", f"Only the leaf was given; its issuer ({leaf['issuer']}) must be sent by the server too.", "Check the server sends the full chain.")
    hl = [h.strip() for h in re.split(r"[,\s]+", str(hosts or "")) if h.strip()]
    cover = []
    for h in hl:
        ok = _match(h, leaf["san"]) or h in leaf["ips"]
        cover.append({"host": h, "ok": ok})
        if not ok:
            add("bad", "Name", f"{h} is not among the certificate's names ({', '.join(leaf['san'][:6]) or 'none'}).", "Reissue with this name.", h)
    if not leaf["san"]:
        add("warn", "No names", "The leaf has no Subject Alternative Names - browsers ignore the common name.", "Reissue with the host names as SANs.")
    for c in certs:
        c.pop("_s")
        c.pop("_i")
    res = {"certs": certs, "count": len(certs), "chain_ok": order_ok, "cover": cover, "today": td.isoformat(), "leaf_days": leaf["days_left"],
           "verdict": f"{leaf['subject']}: {('expired ' + str(-leaf['days_left']) + ' day(s) ago') if leaf['days_left'] < 0 else str(leaf['days_left']) + ' day(s) left'}, {len(certs)} certificate(s)"}
    res["note"] = "Read from the certificates you pasted; revocation and trust in a browser's root store are not checked here."
    return finish(res, issues)
