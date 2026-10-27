"""ONDC signing and onboarding crypto.

- Request signing: ed25519 over "(created) (expires) digest" with a BLAKE2b-512 body digest (ONDC auth header spec).
- Site verification: ed25519 signature of the registry's request_id.
- /on_subscribe challenge: X25519 shared key with ONDC's public key, AES-256-ECB decrypt, PKCS#7 unpad.
"""
from __future__ import annotations

import base64
import hashlib
import re
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives import padding, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

b64e = lambda b: base64.b64encode(b).decode()  # noqa: E731


def b64d(s: str) -> bytes:
    return base64.b64decode(s + "=" * (-len(s) % 4))


def body_digest(body: bytes) -> str:
    return b64e(hashlib.blake2b(body, digest_size=64).digest())


def signing_string(created: int, expires: int, digest: str) -> str:
    return f"(created): {created}\n(expires): {expires}\ndigest: BLAKE-512={digest}"


def load_signing_key(private_b64: str) -> Ed25519PrivateKey:
    """Accepts a 32-byte seed or a 64-byte libsodium secret key (seed + public), base64."""
    raw = b64d(private_b64)
    if len(raw) == 64:
        raw = raw[:32]
    if len(raw) != 32:
        raise ValueError("ed25519 private key must be 32 or 64 bytes (base64)")
    return Ed25519PrivateKey.from_private_bytes(raw)


def load_verify_key(public_b64: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(b64d(public_b64))


@dataclass
class KeySet:
    signing_private: str      # base64, 64-byte libsodium format (what ONDC tooling uses)
    signing_public: str       # base64 raw 32 bytes -> registry "signing_public_key"
    encryption_private: str   # base64 DER PKCS#8
    encryption_public: str    # base64 DER SubjectPublicKeyInfo -> registry "encr_public_key"


def generate_keys() -> KeySet:
    sk = Ed25519PrivateKey.generate()
    seed = sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pub = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    xk = X25519PrivateKey.generate()
    xpriv = xk.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    xpub = xk.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return KeySet(b64e(seed + pub), b64e(pub), b64e(xpriv), b64e(xpub))


def sign_body(body: bytes, subscriber_id: str, unique_key_id: str, private_b64: str,
              created: int | None = None, ttl: int = 300) -> str:
    created = int(created if created is not None else time.time())
    expires = created + ttl
    sig = load_signing_key(private_b64).sign(signing_string(created, expires, body_digest(body)).encode())
    return (f'Signature keyId="{subscriber_id}|{unique_key_id}|ed25519",algorithm="ed25519",created="{created}",'
            f'expires="{expires}",headers="(created) (expires) digest",signature="{b64e(sig)}"')


_PARAM = re.compile(r'(\w+)="([^"]*)"')


def parse_auth_header(header: str) -> dict[str, str]:
    h = header.strip()
    if h.lower().startswith("signature "):
        h = h[10:]
    params = dict(_PARAM.findall(h))
    if "keyId" in params:
        parts = params["keyId"].split("|")
        if len(parts) == 3:
            params["subscriber_id"], params["unique_key_id"], params["alg"] = parts
    return params


def verify_body(header: str, body: bytes, public_b64: str, now: int | None = None) -> bool:
    p = parse_auth_header(header)
    try:
        created, expires = int(p["created"]), int(p["expires"])
        sig = b64d(p["signature"])
    except (KeyError, ValueError):
        return False
    now = int(now if now is not None else time.time())
    if not (created - 60 <= now <= expires):
        return False
    try:
        load_verify_key(public_b64).verify(sig, signing_string(created, expires, body_digest(body)).encode())
        return True
    except Exception:
        return False


def sign_text(text: str, private_b64: str) -> str:
    return b64e(load_signing_key(private_b64).sign(text.encode()))


def site_verification_html(request_id: str, private_b64: str) -> str:
    signed = sign_text(request_id, private_b64)
    return ("<!--Contents of ondc-site-verification.html. -->\n<html>\n  <head>\n"
            f"    <meta name='ondc-site-verification' content='{signed}' />\n  </head>\n"
            "  <body>\n    ONDC Site Verification Page\n  </body>\n</html>\n")


def _shared_key(encryption_private_b64: str, ondc_public_b64: str) -> bytes:
    priv = serialization.load_der_private_key(b64d(encryption_private_b64), password=None)
    pub = serialization.load_der_public_key(b64d(ondc_public_b64))
    assert isinstance(priv, X25519PrivateKey) and isinstance(pub, X25519PublicKey)
    return priv.exchange(pub)


def decrypt_challenge(challenge_b64: str, encryption_private_b64: str, ondc_public_b64: str) -> str:
    key = _shared_key(encryption_private_b64, ondc_public_b64)
    dec = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    padded = dec.update(b64d(challenge_b64)) + dec.finalize()
    unpad = padding.PKCS7(128).unpadder()
    return (unpad.update(padded) + unpad.finalize()).decode()


def encrypt_challenge(text: str, encryption_private_b64: str, peer_public_b64: str) -> str:
    """Registry side of the challenge; used by tests and the sandbox registry."""
    key = _shared_key(encryption_private_b64, peer_public_b64)
    p = padding.PKCS7(128).padder()
    data = p.update(text.encode()) + p.finalize()
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return b64e(enc.update(data) + enc.finalize())
