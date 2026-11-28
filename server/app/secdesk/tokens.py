"""JSON Web Tokens read without trusting them: each token's header and claims decoded (base64url) - never verified, never kept.
Algorithm none, a symmetric algorithm where a key pair was expected, keys fetched from a URL in the header (jku / x5u / jwk), a key
id that looks like a path, no expiry, a lifetime longer than her rule, expired or not yet valid against her date, missing issuer
or audience, and personal or secret-looking data inside the token (anyone holding it can read it). The signature is removed
before anything is stored: paste test or expired tokens - a live token is a key to the account."""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from typing import Any

from .common import SecInputError, finder, finish


class TokenError(SecInputError):
    pass


JWT = re.compile(r"\b(eyJ[A-Za-z0-9_-]{5,})\.(eyJ[A-Za-z0-9_-]{5,}|[A-Za-z0-9_-]*)\.([A-Za-z0-9_-]*)")
SENSITIVE = re.compile(r"pass(word)?|pwd|secret|ssn|social|aadhaar|pan(_?no)?$|card|cvv|iban|account_?number|dob|birth|phone|mobile|address|salary", re.I)


def _b64(s: str) -> Any:
    try:
        raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        return json.loads(raw)
    except (ValueError, json.JSONDecodeError) as e:
        raise TokenError(f"A token part could not be read as JSON: {e}")


def strip(text: str) -> str:
    """The text with every token's signature removed - what is stored."""
    return JWT.sub(lambda m: f"{m.group(1)}.{m.group(2)}.<signature removed>", str(text or ""))


def analyse(text: str, max_hours: float = 24, now: Any = None, expect_alg: str = "") -> dict[str, Any]:
    toks = JWT.findall(str(text or ""))
    if not toks:
        raise TokenError("Paste a JWT (three parts separated by dots, starting eyJ). Use test or expired tokens.")
    t0 = now if isinstance(now, (int, float)) else (datetime.fromisoformat(str(now)).replace(tzinfo=timezone.utc).timestamp() if now else datetime.now(timezone.utc).timestamp())
    issues, add = finder()
    rows = []
    for n, (h64, p64, sig) in enumerate(toks[:50], 1):
        hd, pl = _b64(h64), _b64(p64)
        if not isinstance(hd, dict) or not isinstance(pl, dict):
            raise TokenError(f"Token {n}: the header and claims must be JSON objects.")
        w = f"token {n}"
        alg = str(hd.get("alg", ""))
        fl = []
        if alg.lower() == "none" or not alg:
            fl.append("alg none")
            add("bad", "No signature", f"{w} uses alg {alg or '(missing)'} - anyone can write such a token.", "Reject alg none on the server; pin the algorithm.", w)
        elif expect_alg and alg != expect_alg:
            fl.append("unexpected alg")
            add("bad" if alg.upper().startswith("HS") and expect_alg.upper()[:2] in ("RS", "ES", "PS") else "warn", "Algorithm", f"{w} uses {alg}, not the {expect_alg} you expect.",
                "Pin the algorithm in the verifier - never take it from the token.", w)
        if not sig and alg.lower() != "none":
            fl.append("no signature")
            add("bad", "No signature", f"{w} has an empty signature part.", "Check the verifier rejects it.", w)
        for k in ("jku", "x5u", "jwk"):
            if k in hd:
                fl.append(k)
                add("warn", "Key from the token", f"{w} names its own key ({k}) - a verifier that follows it trusts the attacker's key.", "Use only keys you configured; ignore jku / x5u / jwk.", w)
        kid = str(hd.get("kid", ""))
        if re.search(r"\.\./|/|\\|'|;|\|", kid):
            fl.append("odd kid")
            add("warn", "Key id", f"{w} has kid '{kid[:40]}' - path or query characters; a lookup by kid can be abused.", "Look kids up in a fixed list.", w)
        exp, iat, nbf = pl.get("exp"), pl.get("iat"), pl.get("nbf")
        life = None
        if not isinstance(exp, (int, float)):
            fl.append("no expiry")
            add("bad", "No expiry", f"{w} never expires.", "Set exp - minutes to hours for access tokens.", w)
        else:
            if isinstance(iat, (int, float)):
                life = (exp - iat) / 3600
                if life > max_hours:
                    fl.append("long life")
                    add("warn", "Long life", f"{w} lives {life:.4g} hour(s) - your rule is {max_hours:g}.", "Shorten it and use refresh tokens.", w)
            if exp < t0:
                fl.append("expired")
        if isinstance(nbf, (int, float)) and nbf > t0:
            fl.append("not yet valid")
        if "iss" not in pl:
            add("warn", "No issuer", f"{w} has no iss - a verifier cannot tell who made it.", "Set iss and check it.", w)
        if "aud" not in pl:
            add("warn", "No audience", f"{w} has no aud - a token for one service works on another.", "Set aud and check it.", w)
        sens = sorted(k for k in pl if SENSITIVE.search(str(k)))
        if sens:
            fl.append("sensitive claims")
            add("warn", "Readable data", f"{w} carries {', '.join(sens[:5])} - a JWT is only encoded, anyone holding it can read them.", "Keep only ids in the token.", w)
        def ts(v: Any) -> str:
            return datetime.fromtimestamp(v, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if isinstance(v, (int, float)) else "-"
        rows.append({"n": n, "alg": alg, "typ": hd.get("typ", ""), "kid": kid[:60], "iss": str(pl.get("iss", ""))[:120], "aud": pl.get("aud") if isinstance(pl.get("aud"), (str, list)) else "",
                     "sub": str(pl.get("sub", ""))[:80], "iat": ts(iat), "exp": ts(exp), "life_h": life, "claims": sorted(map(str, pl.keys()))[:40], "flags": fl,
                     "header": {k: (v if isinstance(v, (str, int, float, bool)) else "…") for k, v in hd.items()}})
    res = {"tokens": len(rows), "rows": rows, "max_hours": max_hours, "verdict": f"{len(rows)} token(s), {sum(1 for r in rows if r['flags'])} with a problem"}
    res["note"] = "Decoded only - the signature was not checked and was removed before saving. Whether your server verifies tokens correctly needs a test against the server."
    return finish(res, issues)
